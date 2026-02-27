#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Transfer a Hugging Face model to GCS using Cloud Build.")
    parser.add_argument("--model-id", required=True, help="Hugging Face model ID (e.g., google/gemma-3-27b-it)")
    parser.add_argument("--bucket", required=True, help="GCS bucket name (without gs://)")
    parser.add_argument("--token", help="Hugging Face token (optional, defaults to HF_TOKEN env var)")

    args = parser.parse_args()

    hf_token = args.token or os.environ.get("HF_TOKEN")
    if not hf_token:
        print("❌ Error: Hugging Face token must be provided via --token or HF_TOKEN environment variable.")
        sys.exit(1)

    # Resolve the directory of this script to find cloudbuild.yaml and copy_to_gcs.py
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print(f"🚀 Submitting Cloud Build job to transfer {args.model_id} to gs://{args.bucket}...")
    
    cmd = [
        "gcloud", "builds", "submit",
        script_dir,
        "--config", os.path.join(script_dir, "cloudbuild.yaml"),
        "--substitutions", f"_MODEL_ID={args.model_id},_BUCKET={args.bucket},_TOKEN={hf_token}"
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print("❌ Error: Cloud Build job failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
