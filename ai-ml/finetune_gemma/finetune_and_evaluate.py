import os
import re
import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime

import torch
import gc
from datasets import load_dataset, Dataset, Image as HFImage, Features, Value, Image, Sequence
from peft import LoraConfig, PeftModel
from transformers import AutoModelForMultimodalLM, AutoProcessor, BitsAndBytesConfig
from trl import SFTTrainer, SFTConfig
import evaluate
from huggingface_hub import login
from google.cloud import storage
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments for configurable training."""
    parser = argparse.ArgumentParser(description='Fine-tune Gemma 4 on Open Images dataset')
    
    # Dataset parameters
    parser.add_argument('--train-size', type=int, default=700,
                       help='Number of training samples (default: 700)')
    parser.add_argument('--eval-size', type=int, default=200,
                       help='Number of evaluation samples (default: 200)')
    
    # Training parameters
    parser.add_argument('--num-epochs', type=int, default=3,
                       help='Number of training epochs (default: 3)')
    parser.add_argument('--learning-rate', type=float, default=5e-5,
                       help='Learning rate (default: 5e-5)')
    parser.add_argument('--batch-size', type=int, default=1,
                       help='Per-device batch size (default: 1)')
    parser.add_argument('--gradient-accumulation-steps', type=int, default=16,
                       help='Gradient accumulation steps (default: 16)')
    parser.add_argument('--eval-batch-size', type=int, default=8,
                       help='Batch size for evaluation (default: 8)')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Run a dry test without loading the full model (local testing)')
    
    # LoRA parameters
    parser.add_argument('--lora-r', type=int, default=64,
                       help='LoRA rank (default: 64)')
    parser.add_argument('--lora-alpha', type=int, default=64,
                       help='LoRA alpha (default: 64)')
    parser.add_argument('--lora-dropout', type=float, default=0.05,
                       help='LoRA dropout (default: 0.05)')
    
    # Model parameters
    parser.add_argument('--model-id', type=str, default='google/gemma-4-31b-it',
                       help='Model ID to fine-tune')
    parser.add_argument('--device', type=str, default='cuda',
                       choices=['cuda', 'cpu'],
                       help='Device to use for training')
    
    # Output parameters
    parser.add_argument('--output-dir', type=str, default='/tmp/gemma4-finetuned',
                       help='Output directory for model checkpoints')
    parser.add_argument('--results-file', type=str, default='/tmp/results.json',
                       help='Path to save results JSON')
    parser.add_argument('--gcs-output-path', type=str, default=None,
                       help='GCS path to upload the final model to')
    parser.add_argument('--merge', action='store_true',
                       help='Merge LoRA adapters into the base model after training')
    
    # HuggingFace parameters
    parser.add_argument('--hf-token', type=str, default=None,
                       help='HuggingFace token (or set HF_TOKEN env var)')
    
    return parser.parse_args()

def authenticate_huggingface(hf_token=None):
    """Authenticate with HuggingFace."""
    token = hf_token or os.environ.get('HF_TOKEN')
    if not token:
        logger.warning("⚠️ No HuggingFace token provided. Ensure access to google/gemma-4-31b-it.")
        return
    
    try:
        login(token=token)
        logger.info("✓ Successfully authenticated with HuggingFace")
    except Exception as e:
        logger.warning(f"Failed to authenticate with HuggingFace: {e}")

def load_data(train_size, eval_size, hf_token=None):
    """Load and prepare a subset of the Oxford-IIIT Pet dataset."""
    try:
        logger.info(f"Loading Oxford-IIIT Pet dataset...")
        # Load train and test splits
        train_dataset_raw = load_dataset("timm/oxford-iiit-pet", split="train", streaming=False)
        test_dataset_raw = load_dataset("timm/oxford-iiit-pet", split="test", streaming=False)
        
        # Get class names from features
        class_names = train_dataset_raw.features["label"].names

        # Convert to list of dicts with string labels
        def process_pet_data(example):
            return {
                "images": example["image"],
                "caption": class_names[example["label"]] # Using breed as 'caption' for format consistency
            }

        train_dataset = train_dataset_raw.map(process_pet_data, remove_columns=train_dataset_raw.column_names)
        test_dataset = test_dataset_raw.map(process_pet_data, remove_columns=test_dataset_raw.column_names)
        
        # Shuffle and select subsets
        train_data = train_dataset.shuffle(seed=42).select(range(min(train_size, len(train_dataset))))
        eval_data = test_dataset.shuffle(seed=42).select(range(min(eval_size, len(test_dataset))))

        logger.info(f"✓ Dataset prepared (Train: {len(train_data)}, Eval: {len(eval_data)})")
        gc.collect()
        return train_data, eval_data, class_names
        
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

def format_data(example, prompt, processor, model_id):
    """Format dataset examples into chat-style messages."""
    # Combine instructions and task into a single user message
    # This is more effective for Gemma models than separate system turns
    full_user_content = f"{prompt}\n\nIdentify the breed of the animal in this image."
    
    # The assistant content should just be the label (e.g. breed name).
    # The official Gemma 4 chat template will automatically inject an empty
    # thought channel for 26B/31B models to stabilize behavior.
    assistant_content = example["caption"]
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": full_user_content},
            ],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": assistant_content}],
        },
    ]
    # We apply the chat template here to ensure correct formatting
    example["text"] = processor.apply_chat_template(messages, tokenize=False, enable_thinking=False)
    
    # Save prompt part for dynamic length calculation in collator
    prompt_messages = messages[:1] # just the user turn
    example["prompt_text"] = processor.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    
    return example

def load_model_and_processor(model_id, device, hf_token=None, load_model=True):
    """Load Gemma 4 model and processor."""
    try:
        processor = AutoProcessor.from_pretrained(model_id, token=hf_token)
        if processor.tokenizer.pad_token is None:
            processor.tokenizer.pad_token = processor.tokenizer.eos_token
        
        if not load_model:
            logger.info("✓ Processor loaded (Dry Run: skipping model)")
            return None, processor

        logger.info(f"Loading Gemma 4 model: {model_id}")
        model_kwargs = {
            "dtype": torch.bfloat16 if device == 'cuda' and torch.cuda.is_available() else torch.float32,
            "attn_implementation": "sdpa",
            "device_map": "auto" if device == 'cuda' and torch.cuda.is_available() else None,
            "token": hf_token,
            "low_cpu_mem_usage": True,
        }

        # Only use quantization if we are REALLY on a CUDA GPU
        if device == 'cuda' and torch.cuda.is_available():
            logger.info("  Configuring 4-bit quantization for CUDA...")
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_storage=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        else:
            actual_dev = "cpu"
            if device == "mps" or (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
                actual_dev = "mps"
            logger.info(f"  Configuring for {actual_dev} (Quantization disabled)...")

        logger.debug(f"Model Loading Kwargs: {model_kwargs}")
        
        model = AutoModelForMultimodalLM.from_pretrained(model_id, **model_kwargs)
        
        # Memory optimization for larger models (31B)
        if "31b" in model_id.lower():
            logger.info("  Enabling gradient checkpointing for 31B model...")
            model.gradient_checkpointing_enable()
            
        logger.info(f"✓ Model loaded on {model.device}")
        return model, processor
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        sys.exit(1)

def evaluate_model(model, processor, eval_data, prompt, class_names, batch_size=8, hf_token=None):
    """Perform evaluation by comparing model output to ground truth labels."""
    logger.info("Evaluating model...")
    model.eval()
    processor.tokenizer.padding_side = "left"
    
    # Load classification metrics
    acc_metric = evaluate.load("accuracy")
    f1_metric = evaluate.load("f1")
    
    results = []
    
    # Process in batches
    for i in range(0, len(eval_data), batch_size):
        batch = eval_data.select(range(i, min(i + batch_size, len(eval_data))))
        
        # Prepare list of messages for each evaluation sample
        batch_messages = []
        batch_images = []
        references = []
        
        # Combined turn to match training format
        full_user_content = f"{prompt}\n\nIdentify the breed of the animal in this image."
        
        for ex in batch:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": full_user_content},
                    ],
                }
            ]
            batch_messages.append(processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False))
            batch_images.append([ex["images"]]) # List of images for this sample
            references.append(ex["caption"])
            
        inputs = processor(
            text=batch_messages,
            images=batch_images,
            return_tensors="pt",
            padding=True
        ).to(model.device)
        
        with torch.no_grad():
            # Increase max_new_tokens to 128 to capture the breed even if the 31B model generates thought tokens first
            generated_ids = model.generate(**inputs, max_new_tokens=128)
            # Find the length of the prompt to slice out the generated part
            input_len = inputs.input_ids.shape[1]
            # Use skip_special_tokens=True for cleaner text matching
            generated_texts_raw = processor.batch_decode(generated_ids[:, input_len:], skip_special_tokens=True)
            
            # Log raw generated texts for debugging
            logger.debug(f"Raw generated texts: {generated_texts_raw}")
            
            # We don't use parse_response here as we want the raw string for the heuristic
            generated_texts = [text.strip() for text in generated_texts_raw]
            
        for gen, ref in zip(generated_texts, references):
            logger.debug(f"Generated response: {gen}")
            results.append({"generated": gen, "reference": ref.strip()})
            
        # Free batch memory
        del inputs
        del generated_ids
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
    # Calculate Classification Metrics
    if results:
        logger.info(f"Computing classification metrics for {len(results)} samples...")
        
        y_true = []
        y_pred = []
        
        class_to_id = {name.lower(): i for i, name in enumerate(class_names)}
        
        for res in results:
            ref_name = res["reference"].lower()
            gen_text = res["generated"].lower()
            
            true_id = class_to_id.get(ref_name, -1)
            y_true.append(true_id)
            
            # Simple heuristic to find class in generated text
            pred_id = -1
            # Sort by length descending to match longest breed names first (e.g. "English Cocker Spaniel" before "Cocker Spaniel")
            sorted_classes = sorted(class_names, key=len, reverse=True)
            for name in sorted_classes:
                if name.lower().replace("_", " ") in gen_text.replace("_", " "):
                    pred_id = class_to_id[name.lower()]
                    break
            y_pred.append(pred_id)
            
            res["correct"] = (pred_id == true_id)
            res["predicted_label"] = class_names[pred_id] if pred_id != -1 else "Unknown"

        # Calculate Accuracy and F1
        avg_acc = acc_metric.compute(predictions=y_pred, references=y_true)["accuracy"] * 100
        avg_f1 = f1_metric.compute(predictions=y_pred, references=y_true, average="macro")["f1"] * 100
        
        # Calculate "Unknown" rate
        unknown_count = y_pred.count(-1)
        unknown_rate = (unknown_count / len(y_pred)) * 100
    else:
        avg_acc = avg_f1 = unknown_rate = 0

    # Log Aggregate metrics
    logger.info("="*40)
    logger.info("AGGREGATE CLASSIFICATION METRICS")
    logger.info(f"  Accuracy:         {avg_acc:.2f}%")
    logger.info(f"  F1 Score (Macro): {avg_f1:.2f}%")
    logger.info(f"  Unknown Rate:     {unknown_rate:.2f}%")
    logger.info("="*40)

    logger.info("Individual Samples:")
    for i in range(min(3, len(results))):
        logger.info(f"  Sample {i+1}:")
        logger.info(f"    Ref: {results[i]['reference']}")
        logger.info(f"    Gen: {results[i]['generated']}")
        logger.info(f"    Pred: {results[i].get('predicted_label', 'N/A')} | Correct: {results[i].get('correct', 'N/A')}")
        
    return {
        "accuracy": avg_acc, 
        "f1": avg_f1,
        "unknown_rate": unknown_rate,
        "samples": results
    }

def train_model(model, processor, train_data, eval_data, args):
    """Train Gemma 4 with LoRA."""
    logger.info("Configuring LoRA and Training...")
    processor.tokenizer.padding_side = "right"
    
    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules="all-linear",
        task_type="CAUSAL_LM",
    )
    
    # Custom Data Collator for Vision-Language Models
    def data_collator(examples):
        texts = [ex["text"] for ex in examples]
        images = [[ex["images"]] for ex in examples]
        captions = [ex["caption"] for ex in examples]
        
        batch = processor(
            text=texts,
            images=images,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=1024
        )
        
        labels = batch["input_ids"].clone()
        labels[batch["attention_mask"] == 0] = -100
        
        for i in range(labels.size(0)):
            # Bulletproof SOTA labeling: Find the breed name (caption) in the tokenized sequence
            # and then step backwards to find the `<|turn>` control token that marks the start 
            # of the assistant's response. Mask everything before it.
            # This guarantees we train on `<|turn>model\n` (and the thought channel for 31B)
            # while avoiding image re-tokenization length mismatches perfectly!
            
            # 1. Tokenize the caption alone to get its IDs (the anchor point)
            caption_ids = processor.tokenizer.encode(captions[i], add_special_tokens=False)
            
            # 2. Find where the caption IDs start in the full sequence
            full_ids = batch["input_ids"][i].tolist()
            
            start_idx = -1
            # Search from the end to avoid matching prompt text if breed name appears there
            for j in range(len(full_ids) - len(caption_ids), 0, -1):
                if full_ids[j:j+len(caption_ids)] == caption_ids:
                    start_idx = j
                    break
            
            if start_idx != -1:
                # 3. Step backwards from the caption to find the `<|turn>` token (ID 105)
                # that marks the beginning of the model's response.
                turn_token_id = processor.tokenizer.encode("<|turn>", add_special_tokens=False)[0]
                model_turn_idx = -1
                
                # We search backwards from just before the breed name
                for k in range(start_idx - 1, -1, -1):
                    if full_ids[k] == turn_token_id:
                        model_turn_idx = k
                        break
                
                if model_turn_idx != -1:
                    # Mask everything before `<|turn>model...`
                    labels[i, :model_turn_idx] = -100
                else:
                    # Fallback (should never happen): Mask just before the caption
                    labels[i, :start_idx] = -100
            else:
                # Absolute fallback (rare): Use the prompt tokenizer method
                prompt_batch = processor(text=[examples[i]["prompt_text"]], return_tensors="pt")
                prompt_len = prompt_batch["attention_mask"][0].sum().item()
                labels[i, :min(prompt_len, labels.size(1))] = -100
                
        batch["labels"] = labels
        return batch

    training_args = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        weight_decay=0.01, 
        lr_scheduler_type="linear",
        warmup_ratio=0.1, # Use ratio instead of fixed steps for local runs
        logging_steps=10,
        save_strategy="no",
        eval_strategy="no",
        bf16=torch.cuda.is_available(),
        max_length=1024, # Increased from 512 to avoid truncation
        dataset_kwargs={"skip_prepare_dataset": True}, # Tell SFTTrainer to use raw dataset via data_collator
        remove_unused_columns=False,
        report_to="none",
    )
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        peft_config=peft_config,
        data_collator=data_collator,
    )
    
    logger.info("Starting training...")
    trainer.train()
    
    trainer.save_model(args.output_dir)
    logger.info(f"✓ Fine-tuned adapter saved to {args.output_dir}")
    return trainer.model

def merge_model_with_base(model_id, adapter_dir, output_dir, hf_token=None):
    """Merge LoRA adapters with the base model to create a standalone model."""
    merged_dir = os.path.join(output_dir, "merged")
    logger.info(f"🚀 Starting model merge: {model_id} + {adapter_dir} -> {merged_dir}")
    
    # 1. Clear GPU memory if possible to make room for BF16 load
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    try:
        # 2. Load base model in BF16 (31B in BF16 = 62GB, fits in 80GB VRAM)
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        logger.info(f"  Loading base model with dtype {dtype} for merging...")
        base_model = AutoModelForMultimodalLM.from_pretrained(
            model_id,
            torch_dtype=dtype,
            device_map="auto",
            token=hf_token,
            trust_remote_code=True
        )
        
        # 3. Load adapter
        logger.info("  Loading adapters...")
        model = PeftModel.from_pretrained(base_model, adapter_dir)
        
        # 4. Merge and unload
        logger.info("  Merging weights (this may take a few minutes)...")
        merged_model = model.merge_and_unload()
        
        # 5. Save merged model
        os.makedirs(merged_dir, exist_ok=True)
        logger.info(f"  Saving merged model to {merged_dir}")
        merged_model.save_pretrained(merged_dir)
        
        # Save processor to the merged directory as well
        processor = AutoProcessor.from_pretrained(model_id, token=hf_token)
        processor.save_pretrained(merged_dir)
        
        return True
    except Exception as e:
        logger.error(f"❌ Merge failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def upload_directory_to_gcs(local_path, gcs_path):
    """Uploads the local model directory to GCS."""
    if not gcs_path.startswith("gs://"):
        logger.error(f"Invalid GCS path: {gcs_path}")
        return

    bucket_name, gcs_prefix = gcs_path[5:].split("/", 1)
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        logger.info(f"Uploading to gs://{bucket_name}/{gcs_prefix}")
        for local_file in Path(local_path).rglob('*'):
            if local_file.is_file():
                blob_name = os.path.join(gcs_prefix, local_file.relative_to(local_path))
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_file)
        logger.info("✓ Upload to GCS complete.")
    except Exception as e:
        logger.error(f"GCS Upload failed: {e}")

def main():
    args = parse_args()
    
    # 0. Version Indicator (for visual confirmation in Cloud Run logs)
    logger.info("🚀 Gemma 4 Fine-tuner: version v5 (Fixed Thought Tokens for 2B models)")
    
    # Force HF_TOKEN into environment for all libraries (like load_dataset and evaluate)
    token = args.hf_token or os.environ.get('HF_TOKEN')
    
    # Strip trailing slashes to prevent "Repo id" errors when using local paths
    args.model_id = args.model_id.rstrip('/')
    
    if token:
        os.environ['HF_TOKEN'] = token
        logger.info("✓ HF_TOKEN set globally")
    
    logger.info("="*80)
    logger.info("Gemma 4 Fine-tuning on Oxford-IIIT Pet")
    logger.info("="*80)
    
    if torch.cuda.is_available():
        logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        args.device = 'cuda'
    else:
        logger.warning("CUDA not available. Falling back to CPU.")
        args.device = 'cpu'

    authenticate_huggingface(args.hf_token)
    
    # Load data
    token = args.hf_token or os.environ.get('HF_TOKEN')
    train_data, eval_data, class_names = load_data(args.train_size, args.eval_size, hf_token=token)
    
    # Construct a dynamic prompt with the list of possible breeds
    breeds_list = ", ".join(class_names)
    DEFAULT_PROMPT = f"Identify the breed of the animal in this image. You must choose exactly one breed from the following list: [{breeds_list}]. Respond with ONLY the exact breed name from this list and nothing else. If you are not sure, respond with 'Unknown'."
    
    # Load model and processor (processor only in dry run)
    model, processor = load_model_and_processor(args.model_id, args.device, hf_token=token, load_model=not args.dry_run)
    
    # Format data for SFT
    logger.info("Formatting datasets...")
    formatted_train = train_data.map(lambda x: format_data(x, DEFAULT_PROMPT, processor, args.model_id))
    formatted_eval = eval_data.map(lambda x: format_data(x, DEFAULT_PROMPT, processor, args.model_id))
    
    if args.dry_run:
        logger.info("="*50)
        logger.info("DRY RUN: DATA VERIFICATION")
        logger.info("-" * 30)
        sample = formatted_train[0]
        logger.info(f"Sample Breed: {train_data[0]['caption']}")
        logger.info(f"Formatted Text:\n{sample['text'][:500]}...")
        logger.info("-" * 30)
        logger.info("✓ Dry run data verification complete! (Model loading skipped)")
        logger.info("="*50)
        return
    
    # Baseline Evaluation
    token = args.hf_token or os.environ.get('HF_TOKEN')
    logger.info("Baseline Evaluation...")
    baseline_results = evaluate_model(model, processor, eval_data, DEFAULT_PROMPT, class_names, args.eval_batch_size, hf_token=token)
    
    # Free up memory before training
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    # Train
    model = train_model(model, processor, formatted_train, formatted_eval, args)
    
    # Free up memory after training
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()

    # Final Evaluation (directly on the trained PeftModel)
    logger.info("Final Evaluation...")
    final_results = evaluate_model(model, processor, eval_data, DEFAULT_PROMPT, class_names, args.eval_batch_size, hf_token=token)
    
    # We'll also save the processor there to make it a complete inference-ready directory
    processor.save_pretrained(args.output_dir)

    # 1. Clear GPU memory to ensure enough VRAM for merging
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 2. Merge model if requested
    if args.merge:
        logger.info("Starting merge process...")
        if merge_model_with_base(args.model_id, args.output_dir, args.output_dir, hf_token=token):
            logger.info("✓ Model merged and saved as a standalone model.")
            # Upload the `merged` subdirectory to GCS
            if args.gcs_output_path:
                upload_directory_to_gcs(os.path.join(args.output_dir, "merged"), os.path.join(args.gcs_output_path, "merged"))
        else:
            logger.warning("⚠️ Merge failed. LoRA adapters still saved in the output directory.")
    
    # Standard GCS upload for LoRA adapters (or base folder)
    if args.gcs_output_path:
        upload_directory_to_gcs(args.output_dir, args.gcs_output_path)

    # Final Comparison
    logger.info("="*80)
    logger.info("FINE-TUNING PERFORMANCE SUMMARY")
    logger.info("-" * 40)
    logger.info(f"  METRIC                 | BASELINE | FINAL    | IMPROVEMENT")
    logger.info("-" * 40)
    logger.info(f"  Accuracy               | {baseline_results['accuracy']:>7.2f}% | {final_results['accuracy']:>7.2f}% | {final_results['accuracy'] - baseline_results['accuracy']:>+7.2f}%")
    logger.info(f"  F1 Score (Macro)       | {baseline_results['f1']:>7.2f}% | {final_results['f1']:>7.2f}% | {final_results['f1'] - baseline_results['f1']:>+7.2f}%")
    logger.info(f"  Unknown Rate           | {baseline_results['unknown_rate']:>7.2f}% | {final_results['unknown_rate']:>7.2f}% | {final_results['unknown_rate'] - baseline_results['unknown_rate']:>+7.2f}%")
    logger.info("-" * 40)
    logger.info("="*80)
    
    logger.info("✓ Training pipeline completed successfully!")

if __name__ == "__main__":
    main()
