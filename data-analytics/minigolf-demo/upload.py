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
This code must be executed in the Raspberry Pi that mounts Pixel phone.
"""

import os
import time
import platform
from pathlib import Path
from google.cloud import storage

# Configuration
STORAGE_BUCKET_NAME = "test_golf"
PIXEL_FOLDER = "/media/pixel/Internal shared storage/DCIM/GoPro-Exports"
if platform.system() == 'Darwin':  # Check for macOS - for testing.
    PIXEL_FOLDER = "/Users/hyunuklim" + PIXEL_FOLDER
TEMP_FOLDER = "/tmp"
PROJECT_ID = "next-2024-golf-demo-01"
MONITORING_INTERVAL = 3     # Check for new files every 3 seconds.

# Helper Functions
def get_latest_file(directory):
    """Returns the most recently modified file in a directory."""
    directory_path = Path(directory)
    try:
        return max((p for p in directory_path.iterdir() if p.is_file()), key=os.path.getmtime)
    except ValueError:  # Handle empty directory
        return None

def upload_file_to_gcs(src_path, dst_path):
    """Uploads a file to a Google Cloud Storage bucket."""
    storage_client = storage.Client(project=PROJECT_ID)  # Create client inside the function
    print(f"Uploading {src_path}")

    bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
    blob = bucket.blob(dst_path)

    start_time = time.time()
    blob.upload_from_filename(src_path)
    end_time = time.time()

    print(f"Uploaded {src_path} to gs://{STORAGE_BUCKET_NAME}/{dst_path} in {end_time - start_time:.2f} seconds.")

# Main Monitoring Logic
def monitor_and_upload():
    """Monitors a directory for new files and uploads them to Cloud Storage."""
    # Get initial list of modification times for pre-existing files
    existing_files = {
        file_path.name: file_path.stat().st_mtime 
        for file_path in Path(PIXEL_FOLDER).iterdir() if file_path.is_file()
    }

    while True:
        latest_file = get_latest_file(PIXEL_FOLDER)
        if latest_file and latest_file.name not in existing_files:
            file_path = str(latest_file.absolute())  # Convert Path to string for file operations
            print(f"New file detected: {file_path}")
            print(f"File size: {os.path.getsize(file_path)}")
            dst_name = latest_file.name.split("_")[0]

            upload_file_to_gcs(file_path, dst_name + ".MP4")
            existing_files[latest_file.name] = latest_file.stat().st_mtime  # Update existing files
        else:
            print("No new file detected. Waiting...")

        time.sleep(MONITORING_INTERVAL)

if __name__ == "__main__":
    monitor_and_upload()
