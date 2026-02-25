# /// script
# dependencies = [
#   "huggingface_hub",
#   "google-cloud-storage",
# ]
# ///

import os
import argparse
from huggingface_hub import HfFileSystem
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def transfer_model(repo_id, bucket_name, gcs_path):
    """
    Directly transfer model weights from Hugging Face to Google Cloud Storage
    without downloading to local disk first.
    """
    fs = HfFileSystem()
    
    # Define destination
    gcs_full_path = f"gs://{bucket_name}/{gcs_path}"
    logger.info(f"Starting transfer from {repo_id} to {gcs_full_path}...")
    
    try:
        # Use HfFileSystem to copy the entire repository
        # This will walk the HF repo and copy files to GCS
        # Note: You must have gcsfs installed or appropriate credentials configured
        # for fsspec to handle gs:// paths.
        
        # Alternatively, use a more manual approach if gcsfs isn't available
        # But for this demo, we assume the environment has storage access.
        
        # Get list of files in the repo
        files = fs.ls(repo_id, detail=False)
        
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        
        for file_path in files:
            if fs.isfile(file_path):
                relative_path = os.path.relpath(file_path, repo_id)
                file_info = fs.info(file_path)
                file_size_gb = file_info['size'] / (1024**3)
                
                blob_name = os.path.join(gcs_path, relative_path)
                blob = bucket.blob(blob_name)
                
                logger.info(f"  Transferring {relative_path} ({file_size_gb:.2f} GB)...")
                
                # Check if file is large to provide more feedback
                with fs.open(file_path, "rb") as f_src:
                    blob.upload_from_file(f_src)
                
                logger.info(f"  ✓ Finished {relative_path}")
        
    except Exception as e:
        logger.error(f"Transfer failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transfer HF model to GCS")
    parser.add_argument("--repo-id", type=str, default="google/gemma-3-4b-it", help="HF Repo ID")
    parser.add_argument("--bucket", type=str, required=True, help="GCS Bucket Name")
    parser.add_argument("--path", type=str, default="base_model", help="Path inside bucket")
    
    args = parser.parse_args()
    
    # Check for HF_TOKEN
    if not os.environ.get("HF_TOKEN"):
        logger.warning("HF_TOKEN not found in environment. Public models only.")
        
    transfer_model(args.repo_id, args.bucket, args.path)
