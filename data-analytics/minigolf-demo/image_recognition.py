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
This is the code for Cloud function.
"""

import functions_framework
import cv2
import math
import os
from time import time
from google.cloud import bigquery, storage
from collections import deque

# Pre-defined position of the golf ball.
BALL = (226, 611, 8, 7)
# Pre-defined position of the hole.
HOLE = (1428, 568, 32, 26)

# Distance change considered significant movement
MOVEMENT_THRESHOLD = 5

BIGQUERY_DATASET_ID = "minigolf"
BIGQUERY_TRACKING_TABLE_ID = "tracking"
BIGQUERY_SHOT_NUM_TABLE_ID = "shot_num"

def check_if_moving(dist_arr, distance):
    """Checks if the ball is currently moving based on recent distances.

    Args:
        dist_arr: A deque containing recent distances.
        distance: The current distance to the hole.

    Returns:
        True if the ball is considered moving, False otherwise.
    """

    # Not enough history yet
    if len(dist_arr) < 10:
        return False
    
    # Calculate average of recent distances
    curr_avg = sum(dist_arr) / len(dist_arr)
    
    # Check if difference is significant
    return abs(distance - curr_avg) >= MOVEMENT_THRESHOLD

def calculate_distance(center_x, center_y):
    """Calculates the Euclidean distance between the ball and the hole.

    Args:
        center_x: x-coordinate of the ball's center.
        center_y: y-coordinate of the ball's center.

    Returns:
        The distance between the ball's center and the hole's center.
    """
    hole_center = ((HOLE[0] + HOLE[2] // 2), (HOLE[1] + HOLE[3] // 2))
    return math.sqrt((hole_center[0] - center_x) ** 2 + (hole_center[1] - center_y) ** 2)

def process_video(video_file, user_id):
    """Processes a video file to extract ball tracking data and shot detection.

    Args:
        video_file: The path to the video file.
        user_id: The ID of the user who uploaded the video.

    Returns:
        tracking_data: A list of dictionaries, where each dictionary represents a frame's
                       tracking data
        shot_num_data: A list of dictionaries representing detected shots, containing shot 
                       information
    """

    # Open video file 
    cap = cv2.VideoCapture(video_file)
    # Create a CSRT object tracker
    tracker = cv2.legacy.TrackerCSRT_create()

    # Read the first frame and initialize the tracker with the bounding box
    ret, frame = cap.read()
    tracker.init(frame, BALL)

    # Initialize list to store tracking data across frames
    tracking_data = []

    # Initialize list to store the frame when the number of shots recorded.
    shot_num_data = []
    frame_number = 0
    num_shots = 0
    
    # Store recent distances for movement check
    dist_history = deque(maxlen=10)
    # Store recent movement statuses (True/False)
    status_history = deque(maxlen=10)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break   # End of video

        success, bbox = tracker.update(frame)

        if success:
            frame_number += 1
            x, y, w, h = bbox  # Extract coordinates and dimensions from bounding box
            center_x, center_y = x + w//2, y + h//2

            # Calculate distance to the hole
            distance = calculate_distance(center_x, center_y)
            is_moving = check_if_moving(dist_history, distance)
            dist_history.append(distance)

            # Detect a new shot when the ball starts moving after being stationary
            if not any(status_history) and is_moving:
                num_shots += 1
                shot_num_data.append({
                    "user_id": user_id,
                    "shot_number": num_shots,
                    "x": int(center_x),
                    "y": int(center_y),
                    "frame_number": frame_number,
                    "distance": f"{distance:.2f}"
                })

            status_history.append(is_moving)
            
            # Store data for the current frame
            tracking_data.append(
                {
                    "user_id": user_id,
                    "frame_number": frame_number,
                    "x": int(center_x),
                    "y": int(center_y),
                    "distance": f"{distance:.2f}",
                    "is_moving" : is_moving,
                    "shot_number": num_shots,
                }
            )

    # Release resources once processing is complete
    cap.release()
    cv2.destroyAllWindows()

    return tracking_data, shot_num_data

def upload_data(tracking_data, shot_num_data):
    """Uploads ball tracking data and detected shots to BigQuery.

    Args:
        tracking_data: A list of dictionaries containing tracking data.
        shot_num_data: A list of dictionaries containing shot information. 
    """

    # Create a BigQuery client object
    client = bigquery.Client()

    # Get references to the BigQuery dataset and table
    dataset_ref = client.dataset(BIGQUERY_DATASET_ID)
    tracking_table_ref = dataset_ref.table(BIGQUERY_TRACKING_TABLE_ID)
    shot_num_table_ref = dataset_ref.table(BIGQUERY_SHOT_NUM_TABLE_ID)

    # Define the schema for the BigQuery table
    tracking_job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("frame_number", "INTEGER"),
            bigquery.SchemaField("x", "INTEGER"),
            bigquery.SchemaField("y", "INTEGER"),
            bigquery.SchemaField("distance", "FLOAT"),
            bigquery.SchemaField("is_moving", "BOOLEAN"),
            bigquery.SchemaField("shot_number", "INTEGER"),
        ]
    )

    shot_num_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("frame_number", "INTEGER"),
            bigquery.SchemaField("x", "INTEGER"),
            bigquery.SchemaField("y", "INTEGER"),
            bigquery.SchemaField("distance", "FLOAT"),
            bigquery.SchemaField("shot_number", "INTEGER"),
        ]
    )

    # Load the data into the BigQuery table
    tracking_job = client.load_table_from_json(tracking_data, tracking_table_ref, job_config=tracking_job_config)
    shot_num_job = client.load_table_from_json(shot_num_data, shot_num_table_ref, job_config=shot_num_config)

    # Handle potential errors during the upload process
    try:
        tracking_job.result()
        shot_num_job.result()
    except Exception as e:
        print(f"Error during upload: {e}")


# Triggered by a change in a Cloud storage bucket
@functions_framework.cloud_event
def image_recognition(cloud_event):
    """Cloud Function triggered by a new file upload in Cloud Storage."""

    start_time = time()
    
    # Extract information from the Cloud Function event
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]
    user_id = file_name.split(".")[0]

    # Download the file from the bucket to temporal folder.
    storage_client = storage.Client()
    temp_file = f"/tmp/{file_name}"

    with open(temp_file, "wb") as temp_file_handle:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)
        blob.download_to_filename(temp_file)
        tracking_data, shot_num_data = process_video(temp_file, user_id)

    # Upload the extracted data to BigQuery
    upload_data(tracking_data, shot_num_data)

    # Clean up temporary file
    if os.path.isfile(temp_file):
      os.remove(temp_file)
    else:
      print(f"Downloaded file not found: {temp_file}")

    end_time = time()
    # Print elapsed time
    print(f"Function execution time: {end_time - start_time:.2f} seconds")
