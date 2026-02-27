import os
import argparse
import subprocess
from pathlib import Path
from google.cloud import storage

def upload_directory(local_path, bucket_name, gcs_prefix):
    """Uploads a local directory to a GCS bucket."""
    print(f"Uploading {local_path} to gs://{bucket_name}/{gcs_prefix}...")
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    for file_path in Path(local_path).rglob('*'):
        if file_path.is_file():
            # Create a relative path for the GCS blob
            relative_path = file_path.relative_to(local_path)
            blob_path = os.path.join(gcs_prefix, relative_path)
            
            blob = bucket.blob(blob_path)
            blob.upload_from_filename(str(file_path))
            print(f"  ✓ {blob_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()

    local_dir = "/tmp/model"
    os.makedirs(local_dir, exist_ok=True)

    # Use hf download command with hf_transfer for high speed
    print(f"Downloading {args.model_id} from Hugging Face...")
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
    
    cmd = [
        "hf", "download",
        args.model_id,
        "--local-dir", local_dir,
        "--token", args.token
    ]
    
    subprocess.run(cmd, check=True)

    # Upload to GCS (using model-id as the prefix)
    upload_directory(local_dir, args.bucket, args.model_id)
    print("🚀 Model transfer complete!")

if __name__ == "__main__":
    main()
