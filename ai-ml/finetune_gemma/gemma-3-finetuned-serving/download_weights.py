import os
import argparse
from google.cloud import storage
from pathlib import Path

def download_gcs_folder(bucket_name, source_prefix, destination_dir, project_id=None):
    """Downloads a folder from GCS to a local directory."""
    print(f"Downloading gs://{bucket_name}/{source_prefix} to {destination_dir}...")
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=source_prefix)
    
    found = False
    for blob in blobs:
        found = True
        # Construct local path
        relative_path = os.path.relpath(blob.name, source_prefix)
        local_path = Path(destination_dir) / relative_path
        
        # Ensure directories exist
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download file
        if not blob.name.endswith('/'):
            blob.download_to_filename(str(local_path))
            print(f"  ✓ {relative_path}")
    
    if not found:
        print(f"⚠️ No files found in gs://{bucket_name}/{source_prefix}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project", required=False)
    args = parser.parse_args()
    
    download_gcs_folder(args.bucket, args.prefix, args.output, args.project)
