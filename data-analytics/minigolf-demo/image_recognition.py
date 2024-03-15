"""
This is the code for Cloud function.
"""

import functions_framework
import cv2
import math
import os
from time import time
from google.cloud import bigquery, storage

# Pre-defined position of the golf ball.
BALL = (945, 910, 47, 45)
# Pre-defined position of the hole.
HOLE = (1013, 3052, 35, 56)

BIGQUERY_DATASET_ID = "ball_track"
BIGQUERY_TABLE_ID = "test_table"

def calculate_distance(center_x, center_y):
    """Calculates the distance between the ball's center and the hole."""
    hole_center = ((HOLE[0] + HOLE[2] // 2), (HOLE[1] + HOLE[3] // 2))
    return math.sqrt((hole_center[0] - center_x) ** 2 + (hole_center[1] - center_y) ** 2)

def process_video(video_file, user_id):
    """Processes a video file to extract ball tracking data.

    Args:
        video_file: The path to the video file.

    Returns:
        A list of dictionaries, where each dictionary represents a frame's
        tracking data containing: user_id, frame_number, x, y, distance
    """

    # Initialize video capture object 
    cap = cv2.VideoCapture(video_file)
    # Create a CSRT tracker object
    tracker = cv2.legacy.TrackerCSRT_create()

    # Read the first frame and initialize the tracker with the bounding box
    ret, frame = cap.read()
    tracker.init(frame, BALL)

    # Initialize list to store tracking data across frames
    tracking_data = []
    frame_number = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        success, bbox = tracker.update(frame)

        if success:
            frame_number += 1
            x, y, w, h = bbox  # Extract coordinates and dimensions from bounding box
            center_x, center_y = x + w//2, y + h//2

            # Calculate distance to the hole
            total_distance = calculate_distance(center_x, center_y)
            
            # Store data for the current frame
            tracking_data.append(
                {
                    "user_id": user_id,
                    "frame_number": frame_number,
                    "x": int(center_x),
                    "y": int(center_y),
                    "distance": f"{total_distance:.2f}"
                }
            )

    # Release resources once processing is complete
    cap.release()
    cv2.destroyAllWindows()

    return tracking_data

def upload_data(data):
    """Uploads ball tracking data to a BigQuery table.

    Args:
        data: A list of dictionaries containing the tracking data. 
    """

    # Create a BigQuery client object
    client = bigquery.Client()

    # Get references to the BigQuery dataset and table
    dataset_ref = client.dataset(BIGQUERY_DATASET_ID)
    table_ref = dataset_ref.table(BIGQUERY_TABLE_ID)

    # Define the schema for the BigQuery table
    job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("frame_number", "INTEGER"),
            bigquery.SchemaField("x", "INTEGER"),
            bigquery.SchemaField("y", "INTEGER"),
            bigquery.SchemaField("distance", "FLOAT"),
        ]
    )

    # Load the data into the BigQuery table
    job = client.load_table_from_json(data, table_ref, job_config=job_config)

    # Handle potential errors during the upload process
    try:
        job.result()
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
        tracking_data = process_video(temp_file, user_id)

    # Upload the extracted data to BigQuery
    upload_data(tracking_data)

    # Clean up temporary file
    if os.path.isfile(temp_file):
      os.remove(temp_file)
    else:
      print(f"Downloaded file not found: {temp_file}")

    end_time = time()
    # Print elapsed time
    print(f"Function execution time: {end_time - start_time:.2f} seconds")
