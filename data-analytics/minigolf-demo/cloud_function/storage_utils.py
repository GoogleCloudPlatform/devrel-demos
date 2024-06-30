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

from google.cloud import storage

storage_client = storage.Client()

def download_video(bucket, file_name, temp_file):
    # Download the video to a temporary file
    with open(temp_file, "wb") as temp_file_handle:
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(file_name)
        blob.download_to_filename(temp_file)

def upload_image(bucket, user_id):
    bucket = storage_client.get_bucket(bucket)
    blob = bucket.blob(f"{user_id}.png")
    blob.upload_from_filename(f"/tmp/trajectory.png")
