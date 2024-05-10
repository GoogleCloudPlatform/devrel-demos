# Copyright 2024 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This script monitors a designated folder for new video files and uploads them to a Google Cloud Storage bucket. 
It is designed to run continuously, checking for new files at regular intervals. 
It waits for a specified period of inactivity before considering a file "complete" and uploading it.

- Replace `STORAGE_BUCKET_NAME` and `PROJECT_ID` with your Google Cloud Storage bucket name and project ID.
- (Optional) Modify `MONITORING_INTERVAL` to change how often the script checks for new files.
- Run the Script: python3 upload.py /path/to/folder
"""

import os
import time
import sys
from pathlib import Path
from google.cloud import storage

# Configuration
# Replace these values with your actual bucket name and project ID
STORAGE_BUCKET_NAME = ""  
PROJECT_ID = ""

# Directory paths
TEMP_FOLDER = "/tmp"

# Monitoring interval (in seconds)
MONITORING_INTERVAL = 3     

# Inactivity threshold (in seconds) - adjust this based on your recording software's behavior
INACTIVITY_THRESHOLD = 10  

# Helper Functions
def get_latest_file(directory):
    """
    Finds and returns the most recently modified file within the specified directory.

    Args:
        directory (str): The path to the directory to search.

    Returns:
        Path: A Path object representing the latest file, or None if the directory is empty.
    """
    directory_path = Path(directory)
    try:
        return max((p for p in directory_path.iterdir() if p.is_file()), key=os.path.getmtime)
    except ValueError:  # Handle empty directory
        return None
    

def upload_file_to_gcs(src_path, dst_path):
    """
    Uploads a file from the local filesystem to a Google Cloud Storage bucket.

    Args:
        src_path (str): The path to the local file to upload.
        dst_path (str): The destination path within the GCS bucket.
    """
    storage_client = storage.Client(project=PROJECT_ID)
    print(f"Uploading {src_path}")

    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
    blob = bucket.blob(dst_path)

    start_time = time.time()
    blob.upload_from_filename(src_path)
    end_time = time.time()

    print(f"Uploaded {src_path} to gs://{STORAGE_BUCKET_NAME}/{dst_path} in {end_time - start_time:.2f} seconds.")


# Main Monitoring Logic
def monitor_and_upload(folder_path):
    """
    Continuously monitors the Pixel folder for new video files and uploads them to GCS.
    """
    if not os.path.isdir(folder_path):
        print(f"Error: Invalid folder path '{folder_path}'.")
        sys.exit(1)  # Exit with an error code

    # Keep track of existing files and their last modified times
    existing_files = {} 

    while True:
        latest_file = get_latest_file(folder_path)

        if latest_file:
            file_path = str(latest_file.absolute())
            last_modified = latest_file.stat().st_mtime

            if file_path not in existing_files:
                # New file detected
                existing_files[file_path] = last_modified
                print(f"New file detected: {file_path} (monitoring for inactivity...)")
            else:
                # Check for inactivity
                if time.time() - last_modified > INACTIVITY_THRESHOLD:
                    # File has been inactive, upload it
                    print(f"File inactive: {file_path}")

                    # Extract video name (without extension) for GCS destination
                    dst_name = latest_file.name.split("_")[0]  
                    upload_file_to_gcs(file_path, dst_name + ".MP4")

                    # Remove from existing files
                    del existing_files[file_path] 
        else:
            print("No new file detected. Waiting...")

        time.sleep(MONITORING_INTERVAL)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 upload.py /path/to/folder")
        sys.exit(1)

    folder_path = sys.argv[1]
    monitor_and_upload(folder_path)