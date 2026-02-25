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
from transformers import AutoModelForImageTextToText, AutoProcessor
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
    
    # LoRA parameters
    parser.add_argument('--lora-r', type=int, default=16,
                       help='LoRA rank (default: 16)')
    parser.add_argument('--lora-alpha', type=int, default=32,
                       help='LoRA alpha (default: 32)')
    parser.add_argument('--lora-dropout', type=float, default=0.05,
                       help='LoRA dropout (default: 0.05)')
    
    # Model parameters
    parser.add_argument('--model-id', type=str, default='google/gemma-3-4b-it',
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
    """Load and prepare a subset of the synthetic DALL-E 3 dataset."""
    try:
        # Define the exact features to avoid schema mismatch errors (CastError)
        # Specifically, long_caption2 and short_caption2 are lists, not strings.
        features = Features({
            "jpg": Image(),
            "json": {
                "long_caption": Value("string"),
                "long_caption2": Sequence(Value("string")),
                "short_caption": Value("string"),
                "short_caption2": Sequence(Value("string")),
                "image_name": Value("string"),
                "md5_pil_hash": Value("string"),
                "md5_file_hash": Value("string"),
                "sha512_hash": Value("string"),
                "resolution": Value("string"),
                "url": Value("string"),
                "width": Value("int64"),
                "height": Value("int64"),
                "source": Value("string"),
                "original_prompt": Value("string"),
            },
            "jpeg": Image(),
            "png": Image(),
            "__key__": Value("string"),
            "__url__": Value("string"),
        })

        # Load the synthetic DALL-E 3 dataset with explicit features
        logger.info(f"Loading synthetic DALL-E 3 dataset from ProGamerGov...")
        dataset = load_dataset(
            "ProGamerGov/synthetic-dataset-1m-dalle3-high-quality-captions", 
            split="train", 
            streaming=True,
            features=features,
            token=hf_token
        )
        
        target_total = train_size + eval_size
        logger.info(f"Streaming {target_total} examples...")
        
        def data_generator():
            count = 0
            for item in dataset:
                try:
                    # Extract image data
                    image_data = item.get('jpg') or item.get('jpeg') or item.get('png')
                    
                    # Extract caption from json metadata
                    caption = None
                    if 'json' in item and isinstance(item['json'], dict):
                        caption = item['json'].get('long_caption')

                    if image_data and caption:
                        yield {
                            "images": image_data,
                            "caption": caption
                        }
                        count += 1
                        if count % 100 == 0:
                            logger.info(f"  Processed {count}/{target_total}...")
                        if count >= target_total:
                            break
                except Exception as e:
                    logger.debug(f"Skipping malformed example: {e}")
                    continue

        # Use from_generator to keep memory footprint low
        full_dataset = Dataset.from_generator(data_generator).cast_column("images", HFImage())
        
        # Shuffle and split
        full_dataset = full_dataset.shuffle(seed=42)
        # Note: selecting from a shuffled dataset might still materialize some indices, 
        # but is generally safer than holding the whole list.
        train_data = full_dataset.select(range(train_size))
        eval_data = full_dataset.select(range(train_size, target_total))

        logger.info(f"✓ Dataset prepared (Train: {len(train_data)}, Eval: {len(eval_data)})")
        gc.collect() # Force cleanup
        return train_data, eval_data
        
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

def load_model_and_processor(model_id, device, hf_token=None):
    """Load Gemma 3 model and processor."""
    logger.info(f"Loading Gemma 3 model: {model_id}")
    
    try:
        model_kwargs = {
            "dtype": torch.bfloat16 if device == 'cuda' else torch.float32,
            "attn_implementation": "sdpa",
            "device_map": "auto" if device == 'cuda' else None,
            "token": hf_token,
            "low_cpu_mem_usage": True, # Optimize peak RAM usage
        }
        
        model = AutoModelForImageTextToText.from_pretrained(model_id, **model_kwargs)
        processor = AutoProcessor.from_pretrained(model_id, token=hf_token) # Pass HF token here
        
        # Ensure padding token is set
        if processor.tokenizer.pad_token is None:
            processor.tokenizer.pad_token = processor.tokenizer.eos_token
            
        logger.info(f"✓ Model loaded on {device}")
        return model, processor
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        sys.exit(1)

def evaluate_model(model, processor, eval_data, prompt, batch_size=8, hf_token=None):
    """Perform evaluation by comparing model output to ground truth captions."""
    logger.info("Evaluating model...")
    model.eval()
    
    # Load semantic similarity metrics
    logger.info("Loading BERTScore metric...")
    bertscore = evaluate.load("bertscore", token=hf_token)
    
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
            generated_ids = model.generate(**inputs, max_new_tokens=64)
            # Find the length of the prompt to slice out the generated part
            input_len = inputs.input_ids.shape[1]
            generated_texts = processor.batch_decode(generated_ids[:, input_len:], skip_special_tokens=True)
            
        for gen, ref in zip(generated_texts, references):
            results.append({"generated": gen.strip(), "reference": ref.strip()})
            
    # Calculate strings
    generated_texts_final = [r['generated'] for r in results]
    reference_texts_final = [r['reference'] for r in results]
    
    # Calculate Semantic Similarity using BERTScore (F1)
    if generated_texts_final:
        logger.info(f"Computing BERTScore for {len(results)} samples...")
        # We use 'roberta-common' or 'bert-base-multilingual-cased' for bertscore
        bert_results = bertscore.compute(
            predictions=generated_texts_final, 
            references=reference_texts_final, 
            lang="en",
            model_type="distilbert-base-uncased" # Lightweight and fast
        )
        
        total_sim = 0
        total_word_overlap = 0
        total_len_ratio = 0
        
        for idx in range(len(results)):
            gen = results[idx]['generated'].lower()
            ref = results[idx]['reference'].lower()
            
            # 1. BERTScore F1 (Semantic)
            # F1 is usually the best balance of precision/recall
            sim = bert_results['f1'][idx] * 100
            results[idx]['semantic_similarity'] = sim
            
            # 2. Word Overlap (Jaccard Similarity)
            gen_words = set(gen.split())
            ref_words = set(ref.split())
            if gen_words or ref_words:
                intersection = gen_words.intersection(ref_words)
                union = gen_words.union(ref_words)
                overlap = len(intersection) / len(union) * 100
            else:
                overlap = 100.0
            results[idx]['word_overlap'] = overlap
            
            # 3. Length Ratio
            if len(ref) > 0:
                len_ratio = min(len(gen) / len(ref), 1.0) * 100
            else:
                len_ratio = 100.0 if len(gen) == 0 else 0.0
            results[idx]['length_ratio'] = len_ratio
            
            total_sim += results[idx]['semantic_similarity']
            total_word_overlap += results[idx]['word_overlap']
            total_len_ratio += results[idx]['length_ratio']
            
        avg_sim = total_sim / len(results)
        avg_overlap = total_word_overlap / len(results)
        avg_len_ratio = total_len_ratio / len(results)
    else:
        avg_sim = avg_overlap = avg_len_ratio = 0

    # Log Aggregate metrics first
    logger.info("="*40)
    logger.info("AGGREGATE EVALUATION METRICS")
    logger.info(f"  Avg Semantic Similarity: {avg_sim:.2f}%")
    logger.info(f"  Avg Word Overlap:       {avg_overlap:.2f}%")
    logger.info(f"  Avg Length Consistency:  {avg_len_ratio:.2f}%")
    logger.info("="*40)

    logger.info("Individual Samples:")
    for i in range(min(3, len(results))):
        logger.info(f"  Sample {i+1}:")
        logger.info(f"    Ref: {results[i]['reference'][:100]}...")
        logger.info(f"    Gen: {results[i]['generated'][:100]}...")
        logger.info(f"    Semantic: {results[i]['semantic_similarity']:.2f}% | Word Overlap: {results[i]['word_overlap']:.2f}%")
        
    return {
        "avg_semantic_similarity": avg_sim, 
        "avg_word_overlap": avg_overlap,
        "avg_length_ratio": avg_len_ratio,
        "samples": results
    }

def train_model(model, processor, train_data, eval_data, args):
    """Train Gemma 3 with LoRA."""
    logger.info("Configuring LoRA and Training...")
    
    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules="all-linear",
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
        max_length=512,
        dataset_text_field="text", # SFTTrainer uses this
        remove_unused_columns=False, # Required for multimodal/custom data
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
    logger.info(f"✓ Fine-tuned model saved to {args.output_dir}")

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
    if token:
        os.environ['HF_TOKEN'] = token
        logger.info("✓ HF_TOKEN set globally")
    
    logger.info("="*80)
    logger.info("Gemma 3 Fine-tuning on Open Images")
    logger.info("="*80)
    
    if torch.cuda.is_available():
        logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    else:
        logger.warning("Running on CPU - this will be extremely slow!")

    authenticate_huggingface(args.hf_token)
    
    DEFAULT_PROMPT = "Describe this image in detail."
    
    # Load data
    token = args.hf_token or os.environ.get('HF_TOKEN')
    train_data, eval_data = load_data(args.train_size, args.eval_size, hf_token=token)
    
    # Load model
    model, processor = load_model_and_processor(args.model_id, args.device, hf_token=token)
    
    # Format data for SFT
    logger.info("Formatting datasets...")
    formatted_train = train_data.map(lambda x: format_data(x, DEFAULT_PROMPT, processor))
    formatted_eval = eval_data.map(lambda x: format_data(x, DEFAULT_PROMPT, processor))
    
    # Baseline Evaluation
    token = args.hf_token or os.environ.get('HF_TOKEN')
    logger.info("Baseline Evaluation...")
    baseline_results = evaluate_model(model, processor, eval_data, DEFAULT_PROMPT, args.eval_batch_size, hf_token=token)
    
    # Train
    train_model(model, processor, formatted_train, formatted_eval, args)
    
    # Reload and Merge (Simplified for Job)
    logger.info("Merging LoRA weights...")
    base_model = AutoModelForImageTextToText.from_pretrained(
        args.model_id, 
        dtype=torch.bfloat16 if args.device == 'cuda' else torch.float32,
        device_map="auto" if args.device == 'cuda' else None,
        token=token
    )
    model = PeftModel.from_pretrained(base_model, args.output_dir)
    model = model.merge_and_unload()
    
    # Final Evaluation
    logger.info("Final Evaluation...")
    final_results = evaluate_model(model, processor, eval_data, DEFAULT_PROMPT, args.eval_batch_size, hf_token=token)
    
    # Save merged model
    merged_dir = f"{args.output_dir}-merged"
    model.save_pretrained(merged_dir)
    processor.save_pretrained(merged_dir)
    
    if args.gcs_output_path:
        upload_directory_to_gcs(merged_dir, args.gcs_output_path)

    # Final Comparison
    logger.info("="*80)
    logger.info("FINE-TUNING PERFORMANCE SUMMARY")
    logger.info("-" * 40)
    logger.info(f"  METRIC                 | BASELINE | FINAL    | IMPROVEMENT")
    logger.info("-" * 40)
    logger.info(f"  Semantic Similarity    | {baseline_results['avg_semantic_similarity']:>7.2f}% | {final_results['avg_semantic_similarity']:>7.2f}% | {final_results['avg_semantic_similarity'] - baseline_results['avg_semantic_similarity']:>+7.2f}%")
    logger.info(f"  Word Overlap (Jaccard) | {baseline_results['avg_word_overlap']:>7.2f}% | {final_results['avg_word_overlap']:>7.2f}% | {final_results['avg_word_overlap'] - baseline_results['avg_word_overlap']:>+7.2f}%")
    logger.info(f"  Length Consistency     | {baseline_results['avg_length_ratio']:>7.2f}% | {final_results['avg_length_ratio']:>7.2f}% | {final_results['avg_length_ratio'] - baseline_results['avg_length_ratio']:>+7.2f}%")
    logger.info("-" * 40)
    logger.info("="*80)
    
    logger.info("✓ Training pipeline completed successfully!")

if __name__ == "__main__":
    main()
