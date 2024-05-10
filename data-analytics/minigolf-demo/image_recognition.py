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
This Cloud Function processes uploaded videos to track a golf ball's movement and detect shots.
It then stores the tracking data in BigQuery for further analysis.
"""

import functions_framework
import cv2
import math
import os
from datetime import datetime

from google.cloud import bigquery, storage
from collections import deque

# Constants for ball and hole positions (assuming fixed locations in the video)
BALL = (1434, 495, 15, 15)  # (x, y, width, height)
HOLE = (752, 586, 11, 8)

# Threshold for considering distance change as significant movement
MOVEMENT_THRESHOLD = 5

# BigQuery configuration
BIGQUERY_DATASET_ID = "minigolf"
BIGQUERY_TRACKING_TABLE_ID = "tracking"
TRACKING_SCHEMA = [
    bigquery.SchemaField("created_time", "DATETIME"),
    bigquery.SchemaField("user_id", "STRING"),
    bigquery.SchemaField("frame_number", "INTEGER"),
    bigquery.SchemaField("x", "INTEGER"),
    bigquery.SchemaField("y", "INTEGER"),
    bigquery.SchemaField("distance", "FLOAT"),
    bigquery.SchemaField("is_moving", "BOOLEAN"),
    bigquery.SchemaField("shot_number", "INTEGER"),
]

# Set Cloud Storage bucket for background image upload
BG_BUCKET = "test_golf_2"

# Initialize BigQuery client and table reference
bq_client = bigquery.Client()
dataset_ref = bq_client.dataset(BIGQUERY_DATASET_ID)
tracking_table_ref = dataset_ref.table(BIGQUERY_TRACKING_TABLE_ID)

# Initialize Storage client
storage_client = storage.Client()

# List to store any errors during BigQuery inserts
ERRORS = []


def check_if_moving(dist_arr, distance):
    """
    Determines if the ball is moving based on recent distances.

    Args:
        dist_arr: A deque containing recent distances to the hole.
        distance: The current distance to the hole.

    Returns:
        True if the ball is considered moving, False otherwise.
    """
    if len(dist_arr) < 30:  # Need sufficient history for comparison
        return False
    curr_avg = sum(dist_arr) / len(dist_arr)  # Calculate average of recent distances
    return abs(distance - curr_avg) >= MOVEMENT_THRESHOLD  # Check for significant difference


def calculate_distance(center_x, center_y):
    """
    Calculates the Euclidean distance between the ball and the hole.

    Args:
        center_x: x-coordinate of the ball's center.
        center_y: y-coordinate of the ball's center.

    Returns:
        The distance between the ball and the hole.
    """
    hole_center_x = HOLE[0] + HOLE[2] // 2
    hole_center_y = HOLE[1] + HOLE[3] // 2
    return math.sqrt((hole_center_x - center_x) ** 2 + (hole_center_y - center_y) ** 2)


def process_and_upload_video(video_file, user_id):
    """
    Processes a video to track the golf ball, detect shots, and upload data to BigQuery.

    Args:
        video_file: The path to the video file.
        user_id: The ID of the user who uploaded the video.
    """
    cap = cv2.VideoCapture(video_file)  # Open the video
    tracker = cv2.legacy.TrackerCSRT_create()  # Create a CSRT tracker
    ret, frame = cap.read()  # Read the first frame
    if ret:
        # Generate a unique filename for the image
        image_filename = f"BG_{user_id}.jpg"

        # Save the first frame as a JPEG image
        cv2.imwrite(f"/tmp/{image_filename}", frame)
        
        # Upload the image to the bucket
        bucket = storage_client.get_bucket(BG_BUCKET)
        blob = bucket.blob(image_filename)
        blob.upload_from_filename(f"/tmp/{image_filename}")
        
        # Clean up temporary image file
        os.remove(f"/tmp/{image_filename}")

    tracker.init(frame, BALL)  # Initialize the tracker with the ball's initial position

    frame_number = 0
    num_shots = 0
    dist_history = deque(maxlen=30)  # Store recent distances for movement detection
    status_history = deque(maxlen=30)  # Store recent movement statuses (True/False)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break  # End of video

        success, bbox = tracker.update(frame)

        if success:
            frame_number += 1
            x, y, w, h = bbox
            center_x, center_y = x + w // 2, y + h // 2
            time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            distance = calculate_distance(center_x, center_y)
            is_moving = check_if_moving(dist_history, distance)
            dist_history.append(distance)

            # Detect a new shot when movement starts after a stationary period
            if not any(status_history) and is_moving:
                num_shots += 1

            status_history.append(is_moving)

            # Prepare tracking data for BigQuery
            tracking_data = {
                "created_time": time_now,
                "user_id": user_id,
                "frame_number": frame_number,
                "x": int(center_x),
                "y": int(center_y),
                "distance": f"{distance:.2f}",
                "is_moving": is_moving,
                "shot_number": num_shots,
            }
            insert_errors = bq_client.insert_rows_json(tracking_table_ref, [tracking_data])
            ERRORS.extend(insert_errors)

    if ERRORS:
        print(f"Errors during streaming inserts: {ERRORS}")

    cap.release()  # Release video capture resources
    cv2.destroyAllWindows()


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

    # Create BigQuery table if it doesn't exist
    try:
        bq_client.get_table(tracking_table_ref)
    except:
        print("Creating 'tracking' table in BigQuery...")
        bq_client.create_table(bigquery.Table(tracking_table_ref, schema=TRACKING_SCHEMA))
        print("Table created successfully.")

    temp_file = f"/tmp/{file_name}"

    # Download the video to a temporary file
    with open(temp_file, "wb") as temp_file_handle:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)
        blob.download_to_filename(temp_file)

    # Process the video and upload tracking data
    process_and_upload_video(temp_file, user_id)

    # Clean up the temporary file
    if os.path.isfile(temp_file):
        os.remove(temp_file)
    else:
        print(f"Downloaded file not found: {temp_file}")

    end_time = datetime.now()
    elapsed_time = (end_time - start_time).total_seconds()
    print(f"Function execution time: {elapsed_time:.2f} seconds")
