import os
import re
import sys
import argparse
import json
import logging
from pathlib import Path
from datetime import datetime
from sklearn.metrics import accuracy_score, f1_score

import torch
import gc
from datasets import load_dataset
from peft import LoraConfig, PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor
from trl import SFTTrainer, SFTConfig
from huggingface_hub import login
from google.cloud import storage



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
    parser = argparse.ArgumentParser(description='Fine-tune MedGemma on BreakHis dataset')
    
    # Data parameters
    parser.add_argument('--train-size', type=int, default=500,
                       help='Number of training samples (default: 500)')
    parser.add_argument('--eval-size', type=int, default=100,
                       help='Number of evaluation samples (default: 100)')
    parser.add_argument('--dataset-name', type=str, default='sarath2003/BreakHis',
                       help='HuggingFace dataset name')
    
    # Training parameters
    parser.add_argument('--num-epochs', type=int, default=5,
                       help='Number of training epochs (default: 5)')
    parser.add_argument('--learning-rate', type=float, default=5e-4,
                       help='Learning rate (default: 5e-4)')
    parser.add_argument('--batch-size', type=int, default=1,
                       help='Per-device batch size (default: 1)')
    parser.add_argument('--gradient-accumulation-steps', type=int, default=8,
                       help='Gradient accumulation steps (default: 8)')
    parser.add_argument('--eval-batch-size', type=int, default=16,
                       help='Batch size for evaluation (default: 2)')
    
    # LoRA parameters
    parser.add_argument('--lora-r', type=int, default=8,
                       help='LoRA rank (default: 8)')
    parser.add_argument('--lora-alpha', type=int, default=16,
                       help='LoRA alpha (default: 16)')
    parser.add_argument('--lora-dropout', type=float, default=0.1,
                       help='LoRA dropout (default: 0.1)')
    
    # Model parameters
    parser.add_argument('--model-id', type=str, default='google/medgemma-4b-it',
                       help='Model ID to fine-tune')
    parser.add_argument('--device', type=str, default='cuda',
                       choices=['cuda', 'cpu'],
                       help='Device to use for training')
    
    # Output parameters
    parser.add_argument('--output-dir', type=str, default='/tmp/medgemma-finetuned',
                       help='Output directory for model checkpoints')
    parser.add_argument('--results-file', type=str, default='/tmp/results.json',
                       help='Path to save results JSON')
    parser.add_argument('--gcs-output-path', type=str, default=None,
                       help='GCS path to upload the final model to (e.g., gs://bucket-name/path/to/model)')
    
    # HuggingFace parameters
    parser.add_argument('--hf-token', type=str, default=None,
                       help='HuggingFace token (or set HF_TOKEN env var)')
    
    return parser.parse_args()


def authenticate_huggingface(hf_token=None):
    """Authenticate with HuggingFace."""
    token = hf_token or os.environ.get('HF_TOKEN')
    if not token:
        logger.error("No HuggingFace token provided. Set --hf-token or HF_TOKEN environment variable")
        sys.exit(1)
    
    try:
        login(token=token)
        logger.info("✓ Successfully authenticated with HuggingFace")
    except Exception as e:
        logger.error(f"Failed to authenticate with HuggingFace: {e}")
        sys.exit(1)


def load_data(dataset_name, train_size, eval_size):
    """Load and prepare the dataset."""
    logger.info(f"Loading dataset: {dataset_name}")
    
    try:
        dataset = load_dataset(dataset_name, split="train").shuffle(seed=42)
        train_data = dataset.select(range(train_size))
        eval_data = dataset.select(range(train_size, train_size + eval_size))
        
        cancer_classes = train_data.features["label"].names
        
        logger.info(f"✓ Loaded {len(train_data)} training samples")
        logger.info(f"✓ Loaded {len(eval_data)} evaluation samples")
        logger.info(f"✓ Classes: {cancer_classes}")
        
        return train_data, eval_data, cancer_classes
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        sys.exit(1)


def format_data(example, prompt):
    """Format dataset examples into chat-style messages."""
    example["messages"] = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        },
        {
            "role": "assistant",
            "content": [{"type": "text", "text": str(example["label"])}],
        },
    ]
    return example


def load_model_and_processor(model_id, device):
    """Load the model and processor."""
    logger.info(f"Loading model: {model_id}")
     
    if device == 'cuda' and not torch.cuda.is_available():
        logger.warning("CUDA not available, falling back to CPU")
        device = 'cpu'
    
    try:
        model_kwargs = {
            "torch_dtype": torch.bfloat16 if device == 'cuda' else torch.float32, 
            'attn_implementation':'sdpa', 
            'device_map': "auto",
        }
        
        model = AutoModelForImageTextToText.from_pretrained(model_id, **model_kwargs)
        
        processor = AutoProcessor.from_pretrained(model_id)
        processor.tokenizer.padding_side = "right"
        
        logger.info(f"✓ Model loaded on {device}")
        logger.info(f"✓ Model dtype: {next(model.parameters()).dtype}")
        logger.info(f"✓ Model device: {next(model.parameters()).device}")
        
        return model, processor
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        sys.exit(1)


def postprocess_prediction(text):
    """Extract predicted class number from model output."""
    digit_match = re.search(r'\b([0-7])\b', text.strip())
    return int(digit_match.group(1)) if digit_match else -1


def batch_predict(model, processor, prompts, images, batch_size=16, max_new_tokens=40):
    """Run batch inference on the model - MATCHES NOTEBOOK VERSION."""
    import sys
    import time
    
    predictions = []
    
    # Set model to eval mode for faster inference
    logger.info("[batch_predict] Setting model to eval mode...")
    sys.stdout.flush()
    model.eval()
    
    total_batches = (len(prompts) + batch_size - 1) // batch_size
    logger.info(f"[batch_predict] Starting inference:")
    logger.info(f"  Total samples: {len(prompts)}")
    logger.info(f"  Total batches: {total_batches}")
    logger.info(f"  Batch size: {batch_size}")
    sys.stdout.flush()
    
    for i in range(0, len(prompts), batch_size):
        batch_num = i // batch_size + 1
        logger.info(f"\n[BATCH {batch_num}/{total_batches}] Starting...")
        sys.stdout.flush()
        
        # Step 1: Get batch data
        t1 = time.time()
        batch_texts = prompts[i:i + batch_size]
        batch_images = [[img] for img in images[i:i + batch_size]]
        logger.info(f"  [1/5] Prepared batch data ({len(batch_texts)} samples) - {time.time()-t1:.3f}s")
        sys.stdout.flush()
        
        # Step 2: Process inputs
        t2 = time.time()
        logger.info(f"  [2/5] Processing inputs with processor...")
        sys.stdout.flush()
        
        try:
            inputs = processor(
                text=batch_texts,
                images=batch_images,
                padding=True,
                return_tensors="pt"
            )
            logger.info(f"  [2/5] Processor done - {time.time()-t2:.3f}s")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"  ✗ Processor FAILED: {e}")
            sys.stdout.flush()
            raise
        
        # Step 3: Move to GPU
        t3 = time.time()
        logger.info(f"  [3/5] Moving to CUDA...")
        sys.stdout.flush()
        
        try:
            inputs = inputs.to("cuda", torch.bfloat16)
            logger.info(f"  [3/5] Moved to CUDA - {time.time()-t3:.3f}s")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"  ✗ CUDA move FAILED: {e}")
            sys.stdout.flush()
            raise
        
        # Step 4: Get prompt lengths
        t4 = time.time()
        prompt_lengths = inputs["attention_mask"].sum(dim=1)
        logger.info(f"  [4/5] Got prompt lengths - {time.time()-t4:.3f}s")
        sys.stdout.flush()
        
        # Step 5: Generate
        t5 = time.time()
        logger.info(f"  [5/5] Generating (this may take a while)...")
        sys.stdout.flush()
        
        try:
            with torch.inference_mode():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    pad_token_id=processor.tokenizer.pad_token_id
                )
            gen_time = time.time() - t5
            logger.info(f"  [5/5] Generation done - {gen_time:.3f}s ({len(batch_texts)/gen_time:.2f} samples/sec)")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"  ✗ Generation FAILED: {e}")
            sys.stdout.flush()
            raise
        
        # Step 6: Decode
        t6 = time.time()
        for seq, length in zip(outputs, prompt_lengths):
            generated = processor.decode(seq[length:], skip_special_tokens=True)
            predictions.append(postprocess_prediction(generated))
        logger.info(f"  [6/6] Decoded {len(batch_texts)} predictions - {time.time()-t6:.3f}s")
        logger.info(f"[BATCH {batch_num}/{total_batches}] Complete! Total batch time: {time.time()-t1:.3f}s")
        sys.stdout.flush()
    
    logger.info(f"\n✓ All inference complete: {len(predictions)} predictions")
    sys.stdout.flush()
    return predictions


def evaluate_model(model, processor, eval_data, prompt, batch_size=16):
    """Evaluate the model on the evaluation set using scikit-learn."""
    import time
    import sys
    
    logger.info("="*60)
    logger.info("EVALUATION START - DETAILED DIAGNOSTICS")
    logger.info("="*60)
    sys.stdout.flush()
    
    # CHECKPOINT 1
    t_start = time.time()
    logger.info("[CHECKPOINT 1] Starting evaluation function...")
    logger.info(f"  eval_data type: {type(eval_data)}")
    logger.info(f"  eval_data length: {len(eval_data)}")
    logger.info(f"  batch_size: {batch_size}")
    sys.stdout.flush()
    
    # CHECKPOINT 2 - Create user message
    t_cp2 = time.time()
    logger.info(f"[CHECKPOINT 2] Creating user message template... (elapsed: {t_cp2-t_start:.2f}s)")
    sys.stdout.flush()
    
    user_message = {
        "role": "user",
        "content": [
            {"type": "image"},
            {"type": "text", "text": prompt},
        ],
    }
    logger.info("  ✓ User message created")
    sys.stdout.flush()
    
    # CHECKPOINT 3 - Apply chat template
    t_cp3 = time.time()
    logger.info(f"[CHECKPOINT 3] Applying chat template... (elapsed: {t_cp3-t_start:.2f}s)")
    sys.stdout.flush()
    
    try:
        template_prompt = processor.apply_chat_template(
            [user_message],
            add_generation_prompt=True,
            tokenize=False
        )
        t_cp3_done = time.time()
        logger.info(f"  ✓ Template created in {t_cp3_done-t_cp3:.2f}s")
        logger.info(f"  Template length: {len(template_prompt)} chars")
        logger.info(f"  First 150 chars: {template_prompt[:150]}")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"  ✗ FAILED to create template: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.stdout.flush()
        raise
    
    # CHECKPOINT 4 - Create prompt list
    t_cp4 = time.time()
    logger.info(f"[CHECKPOINT 4] Creating prompt list... (elapsed: {t_cp4-t_start:.2f}s)")
    sys.stdout.flush()
    
    eval_prompts = [template_prompt] * len(eval_data)
    logger.info(f"  ✓ Created {len(eval_prompts)} prompts")
    sys.stdout.flush()
    
    # CHECKPOINT 5 - Access images
    t_cp5 = time.time()
    logger.info(f"[CHECKPOINT 5] Accessing images... (elapsed: {t_cp5-t_start:.2f}s)")
    sys.stdout.flush()
    
    eval_images = eval_data["image"]
    logger.info(f"  ✓ Got {len(eval_images)} images")
    sys.stdout.flush()
    
    # CHECKPOINT 6 - Access labels
    t_cp6 = time.time()
    logger.info(f"[CHECKPOINT 6] Accessing labels... (elapsed: {t_cp6-t_start:.2f}s)")
    sys.stdout.flush()
    
    eval_labels = eval_data["label"]
    logger.info(f"  ✓ Got {len(eval_labels)} labels")
    sys.stdout.flush()
    
    # CHECKPOINT 7 - Start batch prediction
    t_cp7 = time.time()
    logger.info(f"[CHECKPOINT 7] Starting batch_predict... (elapsed: {t_cp7-t_start:.2f}s)")
    logger.info("="*60)
    sys.stdout.flush()
    
    # CHECKPOINT 8 - Run Inference
    t_cp8 = time.time()
    logger.info(f"[CHECKPOINT 8] Starting batch prediction... (elapsed: {t_cp8-t_start:.2f}s)")
    sys.stdout.flush()
    inference_start = time.time()
    predictions = batch_predict(
        model, 
        processor, 
        eval_prompts, 
        eval_images, 
        batch_size=batch_size
    )
    inference_time = time.time() - inference_start
    logger.info(f"✓ Inference completed in {inference_time:.1f}s ({len(predictions)/inference_time if inference_time > 0 else 0:.2f} samples/sec)")
    
    # CHECKPOINT 9 - Compute Metrics
    t_cp9 = time.time()
    logger.info(f"[CHECKPOINT 9] Computing metrics... (elapsed: {t_cp9-t_start:.2f}s)")
    sys.stdout.flush()
    metrics_start = time.time()
    accuracy = accuracy_score(eval_labels, predictions)
    f1 = f1_score(eval_labels, predictions, average='weighted', zero_division=0)
    metrics_time = time.time() - metrics_start
    
    metrics = {
        'accuracy': accuracy,
        'f1': f1
    }
    
    # Log results
    prompt_time = t_cp8 - t_start
    total_time = time.time() - t_start
    logger.info("="*60)
    logger.info("EVALUATION RESULTS:")
    logger.info(f"  Accuracy: {metrics['accuracy']:.1%}")
    logger.info(f"  F1 Score: {metrics['f1']:.3f}")
    logger.info(f"  Valid predictions: {sum(1 for p in predictions if p != -1)}/{len(predictions)}")
    logger.info(f"\nTiming breakdown:")
    logger.info(f"  Prompt preparation: {prompt_time:.1f}s ({prompt_time/total_time*100:.1f}%)")
    logger.info(f"  Model inference:    {inference_time:.1f}s ({inference_time/total_time*100:.1f}%)")
    logger.info(f"  Metrics computation: {metrics_time:.1f}s ({metrics_time/total_time*100:.1f}%)")
    logger.info(f"  Total:              {total_time:.1f}s")
    logger.info("="*60)
    
    return metrics


def create_collate_fn(processor):
    """Create custom data collator for vision-language training."""
    def collate_fn(examples):
        texts = []
        images = []
        
        for example in examples:
            images.append([example["image"]])
            texts.append(
                processor.apply_chat_template(
                    example["messages"],
                    add_generation_prompt=False,
                    tokenize=False
                ).strip()
            )
        
        batch = processor(text=texts, images=images, return_tensors="pt", padding=True)
        labels = batch["input_ids"].clone()
        labels[labels == processor.tokenizer.pad_token_id] = -100
        
        image_token_id = processor.tokenizer.convert_tokens_to_ids(
            processor.tokenizer.special_tokens_map["boi_token"]
        )
        labels[labels == image_token_id] = -100
        labels[labels == 262144] = -100
        
        batch["labels"] = labels
        return batch
    
    return collate_fn


def train_model(model, processor, train_data, eval_data, args):
    """Train the model with LoRA."""
    logger.info("Starting fine-tuning...")
    
    # LoRA configuration
    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        target_modules="all-linear",
        task_type="CAUSAL_LM",
    )
    
    # Training configuration
    training_args = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.num_epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        learning_rate=args.learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        max_grad_norm=0.3,
        bf16=torch.cuda.is_available(),
        logging_steps=10,
        save_strategy="epoch",
        eval_strategy="epoch",
        push_to_hub=False,
        report_to="none",
        gradient_checkpointing_kwargs={"use_reentrant": False},
        dataset_kwargs={"skip_prepare_dataset": True},
        remove_unused_columns=False,
        label_names=["labels"],
    )
    
    # Create trainer
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        eval_dataset=eval_data,
        peft_config=peft_config,
        data_collator=create_collate_fn(processor),
    )
    
    # Train
    logger.info(f"Total training steps: ~{(len(train_data) * args.num_epochs) // args.gradient_accumulation_steps}")
    trainer.train()
    
    # Save
    trainer.save_model()
    logger.info(f"✓ Model saved to {args.output_dir}")
    
    return trainer


def upload_directory_to_gcs(local_path, gcs_path):
    """Uploads a directory to a GCS bucket."""
    if not gcs_path.startswith("gs://"):
        logger.error(f"Invalid GCS path: {gcs_path}. It must start with gs://")
        return

    bucket_name, gcs_prefix = gcs_path[5:].split("/", 1)
    
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        logger.info(f"Uploading directory {local_path} to gs://{bucket_name}/{gcs_prefix}")
        
        for local_file in Path(local_path).rglob('*'):
            if local_file.is_file():
                blob_name = os.path.join(gcs_prefix, local_file.relative_to(local_path))
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_file)
                logger.info(f"  Uploaded {local_file} to {blob_name}")
                
        logger.info("✓ Upload complete.")
    except Exception as e:
        logger.error(f"Failed to upload to GCS: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


def save_results(results, output_path):
    """Save results to JSON file."""
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir:  # Only create dir if path includes directory
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"✓ Results saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    """Main training pipeline."""
    args = parse_args()
    
    logger.info("="*80)
    logger.info("MedGemma Fine-tuning Pipeline :) ")
    logger.info("="*80)
    
    # CRITICAL: Check GPU availability first
    logger.info("SYSTEM DIAGNOSTICS:")
    logger.info(f"  PyTorch version: {torch.__version__}")
    logger.info(f"  CUDA available: {torch.cuda.is_available()}")
    logger.info(f"  CUDA version: {torch.version.cuda if torch.cuda.is_available() else 'N/A'}")
    if torch.cuda.is_available():
        logger.info(f"  GPU count: {torch.cuda.device_count()}")
        logger.info(f"  GPU name: {torch.cuda.get_device_name(0)}")
        logger.info(f"  GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        logger.warning("  ⚠️  WARNING: CUDA NOT AVAILABLE - Will run on CPU (very slow!)")
    
    logger.info("\nConfiguration:")
    logger.info(f"  Train size: {args.train_size}")
    logger.info(f"  Eval size: {args.eval_size}")
    logger.info(f"  Epochs: {args.num_epochs}")
    logger.info(f"  Learning rate: {args.learning_rate}")
    logger.info(f"  Training batch size: {args.batch_size}")
    logger.info(f"  Eval batch size: {args.eval_batch_size}")
    logger.info(f"  LoRA rank: {args.lora_r}")
    logger.info(f"  Device: {args.device}")
    logger.info("="*80)
    
    import sys
    sys.stdout.flush()  # Force flush for Cloud Run logs
    
    # Authenticate
    authenticate_huggingface(args.hf_token)
    
    # Define prompt
    PROMPT = """Analyze this breast tissue histopathology image and classify it.

Classes (0-7):
0: benign_adenosis
1: benign_fibroadenoma
2: benign_phyllodes_tumor
3: benign_tubular_adenoma
4: malignant_ductal_carcinoma
5: malignant_lobular_carcinoma
6: malignant_mucinous_carcinoma
7: malignant_papillary_carcinoma

Answer with only the number (0-7):"""
    
    # Load data
    train_data, eval_data, cancer_classes = load_data(
        args.dataset_name, args.train_size, args.eval_size
    )
    
    # Format data
    logger.info("Formatting data...")
    formatted_train = train_data.map(lambda x: format_data(x, PROMPT))
    formatted_eval = eval_data.map(lambda x: format_data(x, PROMPT))
    
    # Load model
    model, processor = load_model_and_processor(args.model_id, args.device)
    
    # Baseline evaluation
    logger.info("\n" + "="*80)
    logger.info("BASELINE EVALUATION")
    logger.info("="*80)
    baseline_metrics = evaluate_model(
        model, 
        processor, 
        formatted_eval, 
        PROMPT,
        batch_size=args.eval_batch_size
    )
    
    # Fine-tune
    logger.info("\n" + "="*80)
    logger.info("FINE-TUNING")
    logger.info("="*80)
    train_model(model, processor, formatted_train, formatted_eval, args)
    
    # Evaluate fine-tuned model
    logger.info("\n" + "="*80)
    logger.info("FINE-TUNED EVALUATION & SAVING")
    logger.info("="*80)

    # Clear memory and reload
    del model
    torch.cuda.empty_cache()
    gc.collect()

    # Load base model
    logger.info(f"Reloading base model: {args.model_id}")
    base_model = AutoModelForImageTextToText.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16 if args.device == 'cuda' else torch.float32,
        attn_implementation='sdpa',
        device_map='auto',
    )
    
    # Load LoRA adapter and merge
    logger.info(f"Loading LoRA adapter from: {args.output_dir}")
    finetuned_model = PeftModel.from_pretrained(base_model, args.output_dir)
    merged_model = finetuned_model.merge_and_unload()
    logger.info("✓ Merged base model and LoRA adapter")

    # Save merged model and processor
    merged_model_dir = f"{args.output_dir}-merged"
    logger.info(f"Saving merged model to: {merged_model_dir}")
    merged_model.save_pretrained(merged_model_dir)
    
    processor_finetuned = AutoProcessor.from_pretrained(args.output_dir)
    processor_finetuned.save_pretrained(merged_model_dir)
    logger.info("✓ Saved merged model and processor")

    # Upload merged model to GCS if path is provided
    if args.gcs_output_path:
        upload_directory_to_gcs(merged_model_dir, args.gcs_output_path)

    # Evaluate the merged model
    logger.info("Evaluating merged model...")
    finetuned_metrics = evaluate_model(
        merged_model,
        processor_finetuned,
        formatted_eval,
        PROMPT,
        batch_size=args.eval_batch_size
    )
    
    # Print results
    logger.info("\n" + "="*80)
    logger.info("FINAL RESULTS")
    logger.info("="*80)
    logger.info(f"Baseline Accuracy:    {baseline_metrics['accuracy']:.1%}")
    logger.info(f"Fine-tuned Accuracy:  {finetuned_metrics['accuracy']:.1%}")
    logger.info(f"Improvement:          {(finetuned_metrics['accuracy'] - baseline_metrics['accuracy'])*100:+.1f}%")
    logger.info(f"\nBaseline F1:          {baseline_metrics['f1']:.3f}")
    logger.info(f"Fine-tuned F1:        {finetuned_metrics['f1']:.3f}")
    logger.info(f"Improvement:          {finetuned_metrics['f1'] - baseline_metrics['f1']:+.3f}")
    logger.info("="*80)
    
    # Save results
    results = {
        "timestamp": datetime.now().isoformat(),
        "config": vars(args),
        "baseline": {
            "accuracy": float(baseline_metrics['accuracy']),
            "f1": float(baseline_metrics['f1'])
        },
        "finetuned": {
            "accuracy": float(finetuned_metrics['accuracy']),
            "f1": float(finetuned_metrics['f1'])
        },
        "improvement": {
            "accuracy": float(finetuned_metrics['accuracy'] - baseline_metrics['accuracy']),
            "f1": float(finetuned_metrics['f1'] - baseline_metrics['f1'])
        }
    }
    save_results(results, args.results_file)
    
    logger.info("\n✓ Training pipeline completed successfully!")


if __name__ == "__main__":
    main()
