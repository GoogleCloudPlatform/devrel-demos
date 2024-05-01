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

Assumptions:
    - You have a recorded video using a GoPro camera. If not, you need to change constants such as PREFIX/SUFFIX.
    - The video is stored in the user's video folder (e.g., /Users/{USERNAME}/video/).

Usage:
    python3 image_local.py <command> <video_number>

Commands:
    roi: Sets the ROIs for the ball and hole in the specified video.
    process: Processes the video, tracking the ball's movement and print it to the terminal.
    background: Get the first frame of the video, upload it to the Cloud so that it can work as a background image.
    cp: Copies a video file from the GoPro storage to the user's video folder.

Example: To process video number 481, you would use:
    python3 image_local.py process 481
"""

import argparse
import cv2
import math
import os
import platform
import shutil

from collections import deque
from google.cloud import storage

# Constants
BACKGROUND_IMAGE_BUCKET = "background_image_storage"  # Cloud Storage bucket for background images
USERNAME = os.environ.get('USER', os.environ.get('USERNAME'))
PIXEL_FOLDER = "/media/pixel/Internal shared storage/DCIM/GoPro-Exports"  # GoPro storage path
PREFIX = f"/home/{USERNAME}/video/GX01"  # User's video folder path
if platform.system() == 'Darwin':  # Adjust paths for macOS
    PIXEL_FOLDER = f"/Users/{USERNAME}" + PIXEL_FOLDER
    PREFIX = f"/Users/{USERNAME}/video/GX01"
SUFFIX = ".MP4"  # Video file extension

# Initial ROI values (can be adjusted using the 'roi' command)
BALL = (1434, 495, 15, 15)
HOLE = (752, 586, 11, 8)
MOVEMENT_THRESHOLD = 5  # Threshold for detecting ball movement


def get_video_name(num):
    """Constructs the video file name based on the video number."""
    return f"{PREFIX}{num:04d}{SUFFIX}"


def copy_file(num):
    """Copies a video file from the GoPro storage to the user's video folder."""
    video_name = f"GX01{num:04d}"
    GOPRO_SUFFIX = "_ALTA787042484087914200.MP4"
    source_file = os.path.join(PIXEL_FOLDER[:-5], video_name + GOPRO_SUFFIX)
    destination_file = os.path.join(PREFIX[:-5], video_name + ".MP4")

    try:
        shutil.copyfile(source_file, destination_file)
        print(f"File '{video_name}' copied successfully!")
    except Exception as e:
        print(f"Error copying file '{video_name}': {e}")


def set_roi(num):
    """Allows the user to manually set the ROIs for the ball and hole in a video."""
    cap = cv2.VideoCapture(get_video_name(num))
    _, frame = cap.read()
    if not _:
        print(f"Error: {get_video_name(num)} is not loaded.")
        return

    ball_roi = cv2.selectROI('Select Ball', frame, False)
    print(f'The position of the ball is: {ball_roi}')
    hole_roi = cv2.selectROI('Select Hole', frame, False)
    print(f'The position of the hole is: {hole_roi}')
    cap.release()
    cv2.destroyAllWindows()


def set_background(num):
    """Extracts the first frame of a video and uploads it to Cloud Storage as a background image."""
    cap = cv2.VideoCapture(get_video_name(num))
    ret, frame = cap.read()
    if not ret:
        print(f"Error: {get_video_name(num)} is not a valid file.")
        return

    cv2.imwrite('output_image.jpg', frame)

    # Upload the image to Cloud Storage
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(BACKGROUND_IMAGE_BUCKET)
    blob = bucket.blob('output_image.jpg')
    blob.upload_from_filename('output_image.jpg')
    cap.release()


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


def process_video(num):
    """Processes a video, tracking the ball's movement and printing relevant data."""
    cap = cv2.VideoCapture(get_video_name(num))
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


def main():
    """Parses command-line arguments and executes the corresponding functions."""
    parser = argparse.ArgumentParser(description='Process video or set ROI for ball and hole')
    subparsers = parser.add_subparsers(dest='command')

    # Subparsers for different commands
    set_roi_parser = subparsers.add_parser('roi')
    set_roi_parser.add_argument('video_number', type=int, help='The video number to process')
    process_video_parser = subparsers.add_parser('process')
    process_video_parser.add_argument('video_number', type=int, help='The video number to process')
    get_bg_parser = subparsers.add_parser('bg')
    get_bg_parser.add_argument('video_number', type=int, help='The video number to process')
    copy_file_parser = subparsers.add_parser('copy')
    copy_file_parser.add_argument('video_number', type=int, help='The video number to process')

    args = parser.parse_args()

    if args.command == 'roi':
        set_roi(args.video_number)
    elif args.command == 'process':
        process_video(args.video_number)
    elif args.command == 'bg':
        set_background(args.video_number)
    elif args.command == 'copy':
        copy_file(args.video_number)
    else:
        print("Invalid command. Please use either of following commands: roi, process, bg, copy")


if __name__ == '__main__':
    main()
