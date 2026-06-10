# Resilient Resumes: Interruption-Safe Gemma 4 Fine-Tuning on Cloud Run

*By Shir Meir Lador*

In my last post, I showed how to fine-tune Gemma 4 31B on Cloud Run using NVIDIA RTX 6000 Pro GPUs. It worked well, but training had to fit within Cloud Run's 1-hour GPU task timeout. 

That limit is gone. Cloud Run Jobs now support task timeouts up to **168 hours (7 days)**. 

While multi-day serverless runs are now possible, longer jobs are more exposed to transient platform interruptions like preemptions or infrastructure maintenance. Since low-level VM snapshotting breaks active CUDA contexts on GPUs, the most reliable path to resilience is to let the container restart completely. When an interruption occurs, Cloud Run Jobs automatically spin up a fresh container on a new node via `--max-retries`, giving you a clean slate with zero GPU memory fragmentation.

By pairing this clean container restart with application-level checkpointing on a GCS FUSE volume mount, you get a robust, interruption-safe loop.

---

## The code we added

We modified `finetune_and_evaluate.py` in three simple steps to enable this flow:

1. **Add CLI flags** to control when checkpoints are written.
```python
parser.add_argument('--checkpoint-strategy', type=str, default='steps',
                   choices=['steps', 'epoch', 'no'],
                   help='Checkpoint saving strategy')
parser.add_argument('--save-steps', type=int, default=100,
                   help='Save checkpoint every X steps')
parser.add_argument('--save-total-limit', type=int, default=2,
                   help='Limit total checkpoints retained to save storage')
```

2. **Map the training arguments** directly to Hugging Face's `SFTConfig`.
```python
training_args = SFTConfig(
    output_dir=args.output_dir,
    dataset_text_field="text",
    max_seq_length=1024,
    num_train_epochs=args.num_epochs,
    per_device_train_batch_size=args.batch_size,
    gradient_accumulation_steps=args.gradient_accumulation_steps,
    learning_rate=args.learning_rate,
    logging_steps=10,
    save_strategy=args.checkpoint_strategy,
    save_steps=args.save_steps if args.checkpoint_strategy == 'steps' else 999999,
    save_total_limit=args.save_total_limit if args.checkpoint_strategy != 'no' else None,
)
```

3. **Detect checkpoints and resume** before starting the training loop.
```python
from transformers.trainer_utils import get_last_checkpoint

resume_from_checkpoint = None
if args.checkpoint_strategy != "no" and os.path.isdir(args.output_dir):
    resume_from_checkpoint = get_last_checkpoint(args.output_dir)
    if resume_from_checkpoint:
        logger.info(f"🔎 Resuming fine-tuning from checkpoint: {resume_from_checkpoint}")

trainer.train(resume_from_checkpoint=resume_from_checkpoint)
```

---

## How we verified resumption works

To prove that the checkpoint loading is correct, we ran a direct verification test on Cloud Run:

1. We started our training run on Cloud Run.
2. We let it run past step 200, which automatically saved `checkpoint-200` to GCS.
3. We manually cancelled the active job execution midway.
4. We triggered a second execution targeting the same output directory.

The fresh container booted, mounted the storage bucket, and immediately detected the checkpoint:

```text
🔎 Resuming fine-tuning from checkpoint: /mnt/gcs/gemma4-finetuned/checkpoint-200
Starting training (Resuming: True)...
```

Under the hood, SFTTrainer handles three essential tasks during resumption:
* **Weight restoration** loads the adapter weights from the files inside `checkpoint-200/adapter_model.safetensors`.
* **State restoration** reads `trainer_state.json` and loads `optimizer.pt` and `scheduler.pt` to restore the exact learning rate and optimizer momentum state.
* **Data ordering** loads `rng_state_0.pth` to restore the exact random state, allowing the dataset iterator to skip the first 200 steps and proceed in the correct batch order.

This test confirmed that training continues smoothly from step 201 onwards, completely avoiding any loss of progress or duplicate GPU compute.

---

## Running fine-tuning with a bigger dataset

Our initial verification run with 700 training samples and 200 evaluation samples was just a small test to prove that the checkpointing and resumption pipeline works. For production-grade results, we recommend running the fine-tuning on the full Oxford-IIIT Pet dataset. 

Using the full dataset gives the high-capacity LoRA adapter the surface area it needs to generalize properly, while ensuring our evaluation metrics are statistically robust. 

To run with the full dataset of roughly 3,700 training samples and 3,700 evaluation samples, you can override the job arguments when executing the job:

```bash
gcloud beta run jobs execute gemma4-finetuning-job \
  --region europe-west4 \
  --args="--model-id=/mnt/gcs/google/gemma-4-31b-it/,--output-dir=/mnt/gcs/gemma4-finetuned,--train-size=3700,--eval-size=3700,--merge,--checkpoint-strategy=steps,--save-steps=100,--save-total-limit=2" \
  --async
```

If an interruption occurs during this multi-hour run, Cloud Run will automatically retry the task, mount your GCS bucket, and resume from the last saved 100-step checkpoint. This lets you train on the full dataset with absolute peace of mind and zero wasted GPU hours.

Happy fine-tuning!
