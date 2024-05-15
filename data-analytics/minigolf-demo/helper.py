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
This script defines regions of interest (ROIs) for the golf ball and hole within a video. 
It also includes a process_video() function that utilizes a tracker to monitor the ball's movement,
providing a way to assess the tracker's performance.

Usage:
    python3 image_local.py <command> <file_path>

Commands:
    roi: Sets the ROIs for the ball and hole in the specified video.
    process: Processes the video, tracking the ball's movement and print it to the terminal.

Example: If the video is located in "/Users/hyunuklim/video/minigolf_0481.mp4", you would use:
    python3 image_local.py process /Users/hyunuklim/video/minigolf_0481.mp4
"""

import cv2
import math
import os
import sys

from collections import deque

# Initial ROI values (can be adjusted using the 'roi' command)
BALL = (212, 602, 26, 20)
HOLE = (1411, 558, 46, 42)

MOVEMENT_THRESHOLD = 5  # Threshold for detecting ball movement


def set_roi(file):
    """Allows the user to manually set the ROIs for the ball and hole in a video."""
    cap = cv2.VideoCapture(file)
    _, frame = cap.read()
    if not _:
        print(f"Error: {file} is not loaded.")
        return

    ball_roi = cv2.selectROI('Select Ball', frame, False)
    print(f'The position of the ball is: {ball_roi}')
    hole_roi = cv2.selectROI('Select Hole', frame, False)
    print(f'The position of the hole is: {hole_roi}')
    cap.release()
    cv2.destroyAllWindows()


def calculate_distance(center_x, center_y):
    """Calculates the distance between the ball's center and the hole's center."""
    hole_center = ((HOLE[0] + HOLE[2] // 2), (HOLE[1] + HOLE[3] // 2))
    return math.sqrt((hole_center[0] - center_x) ** 2 + (hole_center[1] - center_y) ** 2)


def check_if_moving(dist_arr, distance):
    """Determines if the ball is moving based on recent distance values."""
    if len(dist_arr) < 30:
        return False
    curr_avg = sum(dist_arr) / len(dist_arr)
    return abs(distance - curr_avg) >= MOVEMENT_THRESHOLD


def process_video(file):
    """Processes a video, tracking the ball's movement and printing relevant data."""
    cap = cv2.VideoCapture(file)
    tracker = cv2.legacy.TrackerCSRT_create()  # Create a CSRT tracker

    ret, frame = cap.read()  # Read the first frame
    tracker.init(frame, BALL)  # Initialize the tracker with the ball's ROI

    shot_data = []  # List to store shot data
    frame_number = 0
    num_shots = 0

    # Initialize deques to store recent distances and movement statuses
    dist_history = deque(maxlen=30)
    status_history = deque(maxlen=30)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        success, bbox = tracker.update(frame)

        if success:
            frame_number += 1
            x, y, w, h = bbox
            center_x, center_y = int(x + w // 2), int(y + h // 2)

            # Draw ROIs for the ball and hole
            cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 255), 2)
            cv2.rectangle(frame, (HOLE[0], HOLE[1]), (HOLE[0] + HOLE[2], HOLE[1] + HOLE[3]), (0, 0, 255), 2)
            distance = calculate_distance(center_x, center_y)
            is_moving = check_if_moving(dist_history, distance)
            dist_history.append(distance)

            # Detect new shots based on movement
            if not any(status_history) and is_moving:
                num_shots += 1
                shot_data.append({
                    "user_id": "test",
                    "shot_number": num_shots,
                    "frame_number": frame_number,
                    "distance": f"{distance:.2f}"
                })

            status_history.append(is_moving)
            
            # Print tracking data for the current frame
            print({
                "user_id": "test",
                "frame_number": frame_number,
                "x": int(center_x),
                "y": int(center_y),
                "distance": f"{distance:.2f}",
                "is_moving": is_moving,
                "shot_number": num_shots,
            })
            cv2.imshow("Tracking", frame)
            if cv2.waitKey(1) == ord('q'):
                break

    print(shot_data)  # Print shot data at the end

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] not in ["roi", "process"]:
        print("Usage: python3 helper.py roi(or process) /path/to/folder")
        sys.exit(1)
    instruction, file_path = sys.argv[1], sys.argv[2]
    if not os.path.isfile(file_path):
        print(f"Error: Invalid file path '{file_path}'.")
        sys.exit(1)  # Exit with an error code

    if instruction == "roi":
        set_roi(file_path)
    elif instruction == "process":
        process_video(file_path)
