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

import cv2
import math
from collections import deque
from datetime import datetime
from bigquery_utils import insert_data

# Constants for ball and hole positions (assuming fixed locations in the video)
BALL = (1700, 520, 40, 40)
HOLE = (725, 536, 7, 6)
MOVEMENT_THRESHOLD = 5

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


def process_video(video_file, user_id):
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

            insert_data("tracking", tracking_data)

    cap.release()  # Release video capture resources
    cv2.destroyAllWindows()