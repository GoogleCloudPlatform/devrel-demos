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
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig
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
    parser = argparse.ArgumentParser(description='Fine-tune Gemma 3 on Open Images dataset')
    
    # Data parameters
    parser.add_argument('--train-size', type=int, default=200,
                       help='Number of training samples (default: 200)')
    parser.add_argument('--eval-size', type=int, default=100,
                       help='Number of evaluation samples (default: 100)')
    
    # Training parameters
    parser.add_argument('--num-epochs', type=int, default=3,
                       help='Number of training epochs (default: 3)')
    parser.add_argument('--learning-rate', type=float, default=2e-5,
                       help='Learning rate (default: 2e-5)')
    parser.add_argument('--batch-size', type=int, default=1,
                       help='Per-device batch size (default: 1)')
    parser.add_argument('--gradient-accumulation-steps', type=int, default=16,
                       help='Gradient accumulation steps (default: 16)')
    parser.add_argument('--eval-batch-size', type=int, default=8,
                       help='Batch size for evaluation (default: 8)')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Run a dry test without loading the full model (local testing)')
    
    # LoRA parameters
    parser.add_argument('--lora-r', type=int, default=16,
                       help='LoRA rank (default: 16)')
    parser.add_argument('--lora-alpha', type=int, default=32,
                       help='LoRA alpha (default: 32)')
    parser.add_argument('--lora-dropout', type=float, default=0.05,
                       help='LoRA dropout (default: 0.05)')
    
    # Model parameters
    parser.add_argument('--model-id', type=str, default='google/gemma-3-27b-it',
                       help='Model ID to fine-tune')
    parser.add_argument('--device', type=str, default='cuda',
                       choices=['cuda', 'cpu'],
                       help='Device to use for training')
    
    # Output parameters
    parser.add_argument('--output-dir', type=str, default='/tmp/gemma3-finetuned',
                       help='Output directory for model checkpoints')
    parser.add_argument('--results-file', type=str, default='/tmp/results.json',
                       help='Path to save results JSON')
    parser.add_argument('--gcs-output-path', type=str, default=None,
                       help='GCS path to upload the final model to')
    
    # HuggingFace parameters
    parser.add_argument('--hf-token', type=str, default=None,
                       help='HuggingFace token (or set HF_TOKEN env var)')
    
    return parser.parse_args()

def authenticate_huggingface(hf_token=None):
    """Authenticate with HuggingFace."""
    token = hf_token or os.environ.get('HF_TOKEN')
    if not token:
        logger.warning("⚠️ No HuggingFace token provided. Ensure access to google/gemma-3-4b-it.")
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
        # Load the dataset
        raw_dataset = load_dataset("timm/oxford-iiit-pet", split="train", streaming=False)
        
        # Get class names from features
        class_names = raw_dataset.features["label"].names

        # Convert to list of dicts with string labels
        def process_pet_data(example):
            return {
                "images": example["image"],
                "caption": class_names[example["label"]] # Using breed as 'caption' for format consistency
            }

        dataset = raw_dataset.map(process_pet_data, remove_columns=raw_dataset.column_names)
        
        # Shuffle and split
        dataset = dataset.shuffle(seed=42)
        train_data = dataset.select(range(min(train_size, len(dataset))))
        eval_data = dataset.select(range(train_size, min(train_size + eval_size, len(dataset))))

        logger.info(f"✓ Dataset prepared (Train: {len(train_data)}, Eval: {len(eval_data)})")
        gc.collect()
        return train_data, eval_data, class_names
        
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

def format_data(example, prompt, processor):
    """Format dataset examples into chat-style messages."""
    # Gemma 3 expects specific message format
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": example["caption"]}],
        },
    ]
    # We apply the chat template here to ensure correct formatting
    example["text"] = processor.apply_chat_template(messages, tokenize=False)
    return example

def load_model_and_processor(model_id, device, hf_token=None, load_model=True):
    """Load Gemma 3 model and processor."""
    try:
        processor = AutoProcessor.from_pretrained(model_id, token=hf_token)
        if processor.tokenizer.pad_token is None:
            processor.tokenizer.pad_token = processor.tokenizer.eos_token
        
        if not load_model:
            logger.info("✓ Processor loaded (Dry Run: skipping model)")
            return None, processor

        logger.info(f"Loading Gemma 3 model: {model_id}")
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
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        else:
            actual_dev = "cpu"
            if device == "mps" or (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
                actual_dev = "mps"
            logger.info(f"  Configuring for {actual_dev} (Quantization disabled)...")

        logger.debug(f"Model Loading Kwargs: {model_kwargs}")
        
        model = AutoModelForImageTextToText.from_pretrained(model_id, **model_kwargs)
        logger.info(f"✓ Model loaded on {model.device}")
        return model, processor
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        sys.exit(1)

def evaluate_model(model, processor, eval_data, prompt, class_names, batch_size=8, hf_token=None):
    """Perform evaluation by comparing model output to ground truth labels."""
    logger.info("Evaluating model...")
    model.eval()
    
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
        
        for ex in batch:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
            batch_messages.append(processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True))
            batch_images.append([ex["images"]]) # List of images for this sample
            references.append(ex["caption"])
            
        inputs = processor(
            text=batch_messages,
            images=batch_images,
            return_tensors="pt",
            padding=True
        ).to(model.device)
        
        with torch.no_grad():
            generated_ids = model.generate(**inputs, max_new_tokens=32)
            # Find the length of the prompt to slice out the generated part
            input_len = inputs.input_ids.shape[1]
            generated_texts = processor.batch_decode(generated_ids[:, input_len:], skip_special_tokens=True)
            
        for gen, ref in zip(generated_texts, references):
            results.append({"generated": gen.strip(), "reference": ref.strip()})
            
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
    """Train Gemma 3 with LoRA."""
    logger.info("Configuring LoRA and Training...")
    
    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        task_type="CAUSAL_LM",
    )
    
    training_args = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        weight_decay=0.01,
        lr_scheduler_type="linear",
        warmup_steps=50,
        logging_steps=10,
        save_strategy="no",
        eval_strategy="no",
        bf16=torch.cuda.is_available(),
        max_length=512, # Correct parameter name for trl SFTConfig
        dataset_text_field="text", 
        remove_unused_columns=False,
        report_to="none",
    )
    
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        peft_config=peft_config,
    )
    
    logger.info("Starting training...")
    trainer.train()
    
    trainer.save_model(args.output_dir)
    logger.info(f"✓ Fine-tuned adapter saved to {args.output_dir}")
    return trainer.model

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
    logger.info("🚀 Gemma 3 Fine-tuner: version v3 (Targeting Python 3.12 + CUDA 12.8)")
    
    # Force HF_TOKEN into environment for all libraries (like load_dataset and evaluate)
    token = args.hf_token or os.environ.get('HF_TOKEN')
    
    # Strip trailing slashes to prevent "Repo id" errors when using local paths
    args.model_id = args.model_id.rstrip('/')
    
    if token:
        os.environ['HF_TOKEN'] = token
        logger.info("✓ HF_TOKEN set globally")
    
    logger.info("="*80)
    logger.info("Gemma 3 Fine-tuning on Oxford-IIIT Pet")
    logger.info("="*80)
    
    if torch.cuda.is_available():
        logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        args.device = 'cuda'
    else:
        logger.warning("CUDA not available. Falling back to CPU.")
        args.device = 'cpu'

    authenticate_huggingface(args.hf_token)
    
    DEFAULT_PROMPT = "Identify the breed of the animal in this image."
    
    # Load data
    token = args.hf_token or os.environ.get('HF_TOKEN')
    train_data, eval_data, class_names = load_data(args.train_size, args.eval_size, hf_token=token)
    
    # Load model and processor (processor only in dry run)
    model, processor = load_model_and_processor(args.model_id, args.device, hf_token=token, load_model=not args.dry_run)
    
    # Format data for SFT
    logger.info("Formatting datasets...")
    formatted_train = train_data.map(lambda x: format_data(x, DEFAULT_PROMPT, processor))
    formatted_eval = eval_data.map(lambda x: format_data(x, DEFAULT_PROMPT, processor))
    
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
    
    # Train
    model = train_model(model, processor, formatted_train, formatted_eval, args)
    
    # Final Evaluation (directly on the trained PeftModel)
    logger.info("Final Evaluation...")
    final_results = evaluate_model(model, processor, eval_data, DEFAULT_PROMPT, class_names, args.eval_batch_size, hf_token=token)
    
    # For 4-bit quantization, we typically save and use adapters rather than merging
    # Weights are already saved in args.output_dir via trainer.save_model()
    # We'll also save the processor there to make it a complete inference-ready directory
    processor.save_pretrained(args.output_dir)
    
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
