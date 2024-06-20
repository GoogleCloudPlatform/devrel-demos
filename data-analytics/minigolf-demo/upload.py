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

- Replace `VIDEO_BUCKET` and `PROJECT_ID` with your Google Cloud Storage bucket name and project ID.
- (Optional) Modify `MONITORING_INTERVAL` to change how often the script checks for new files.
- Run the Script: python3 upload.py /path/to/folder
"""

import os
import time
import sys
from pathlib import Path
from google.cloud import storage

# Replace these values with your actual bucket name and project ID
VIDEO_BUCKET = ""
PROJECT_ID = ""

# Directory paths
TEMP_FOLDER = "/tmp"

# Monitoring interval (in seconds)
MONITORING_INTERVAL = 3     

storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(VIDEO_BUCKET)

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
    
def get_file_number():
    """
    Gets the next available file number based on existing files in Cloud Storage.

    Returns:
        str: The formatted file name string, like "minigolf_0001.mp4".
    """
    blobs = list(bucket.list_blobs(prefix="minigolf_"))  # List "minigolf_" files
    blobs.sort(key=lambda blob: blob.name, reverse=True)  # Sort by name descending 

    if blobs:
        latest_file = blobs[0].name  # Get the latest file name 
        latest_number = int(latest_file[9:13])  # Extract the number
        next_number = latest_number + 1
    else:
        next_number = 1  # Start from 1 if no files exist

    return f"minigolf_{next_number:04d}.mp4"
    

def upload_file_to_gcs(src_path):
    """
    Uploads a file from the local filesystem to a Google Cloud Storage bucket.

    Args:
        src_path (str): The path to the local file to upload.
    """
    start_time = time.time()
    print(f"Uploading {src_path}")
    dst_file = get_file_number()
    blob = bucket.blob(dst_file)

    blob.upload_from_filename(src_path, timeout=300)
    end_time = time.time()
    print(f"Uploaded {src_path} to gs://{VIDEO_BUCKET}/{dst_file} in {end_time - start_time:.2f} seconds.")


# Main Monitoring Logic
def monitor_and_upload(folder_path):
    """
    Continuously monitors the Pixel folder for new video files and uploads them to GCS.
    """
    if not os.path.isdir(folder_path):
        print(f"Error: Invalid folder path '{folder_path}'.")
        sys.exit(1)  # Exit with an error code

    # Keep track of existing files and their last modified times
    existing_files = {
        file_path.name: file_path.stat().st_mtime
        for file_path in Path(folder_path).iterdir() if file_path.is_file()
    }

    while True:
        latest_file = get_latest_file(folder_path)
        if latest_file and latest_file.name not in existing_files:
            file_path = str(latest_file.absolute())
            file_size = 0
            while file_size < os.path.getsize(file_path):
                print("File is recording, waiting until recording is completed...")
                file_size = os.path.getsize(file_path)
                time.sleep(3)
            print("recording is completed. Uploading...")
            upload_file_to_gcs(file_path)
            existing_files[latest_file.name] = latest_file.stat().st_mtime
        else:
            print("No new file detected. Monitoring...")
        time.sleep(MONITORING_INTERVAL)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 upload.py /path/to/folder")
        sys.exit(1)

    folder_path = sys.argv[1]
    monitor_and_upload(folder_path)
