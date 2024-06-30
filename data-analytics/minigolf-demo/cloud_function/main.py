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

import os
from datetime import datetime

import functions_framework

from gemini import generate_commentary
from bigquery_utils import initialize_bq_tables, insert_data, query_data_to_dataframe
from firestore_utils import get_firestore_client, update_user_status
from storage_utils import download_video, upload_image
from generate_visual import generate_visual
from video_processing import process_video

PROJECT_ID = "gml-seoul-2024-demo-01"
BACKGROUND_IMAGE_BUCKET = "image_gml_test"

# Cloud Function entry point
@functions_framework.cloud_event
def image_recognition(cloud_event):
    """
    Cloud Function triggered by a new video upload to Cloud Storage.

    Processes the video and uploads tracking data to BigQuery.
    """
    start_time = datetime.now()
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]
    user_id = file_name.split(".")[0]

    db = get_firestore_client()
    update_user_status(db, user_id, "processing")
    initialize_bq_tables()

    temp_video_file = f"/tmp/{file_name}"
    download_video(bucket_name, file_name, temp_video_file)
    process_video(temp_video_file, user_id)

    df = query_data_to_dataframe(PROJECT_ID, user_id)
    generate_visual(df, user_id)
    upload_image(BACKGROUND_IMAGE_BUCKET, user_id)
    commentary = generate_commentary(PROJECT_ID, bucket_name, user_id, df)
    commentary_data = {
        "user_id": user_id, 
        "commentary": commentary,
    }
    insert_data("commentary", commentary_data)

    # Clean up the temporary file
    if os.path.isfile(temp_video_file):
        os.remove(temp_video_file)
    else:
        print(f"Downloaded file not found: {temp_video_file}")

    update_user_status(db, user_id, "completed")

    end_time = datetime.now()    
    elapsed_time = (end_time - start_time).total_seconds()
    print(f"Processing {file_name} is completed. Execution time: {elapsed_time:.2f} seconds.")
