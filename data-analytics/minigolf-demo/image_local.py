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
This code is for the Raspberry Pi, to set the ROI of the ball and the hole.
Also, using process_video() function, check if the tracker is properly working.
"""

import cv2
import math
from google.cloud import storage
from collections import deque

PREFIX = "/Users/hyunuklim/video/GX01"
SUFFIX = "ALTA787042484087914200.MP4"

def get_video_name(num):
    return f"{PREFIX}{num:04d}_{SUFFIX}"

# VIDEO = {
#     55: "GX010055_{SUFFIX}", # 3 shots, not hole in
#     56: "GX010056_{SUFFIX}", # 6 shots, not hole in
#     57: "GX010057_{SUFFIX}", # not good
#     58: "GX010058_{SUFFIX}", # 6 shots, hole in
# }

BALL = {
    55: (226, 611, 8, 7),
    56: (226, 611, 8, 7),
    57: (223, 609, 8, 8),
    58: (221, 609, 8, 8),
}

HOLE = (1428, 568, 32, 26)

MOVEMENT_THRESHOLD = 5

def set_roi(num):
    cap = cv2.VideoCapture(get_video_name(num))
    _, frame = cap.read()
    bbox = cv2.selectROI('Select Ball', frame, False) # select the range of interest manually
    print(f'The position of the ball is : {bbox}')
    hole = cv2.selectROI('Select Hole', frame, False) # select the range of interest manually
    print(f'The position of the hole is : {hole}')
    cap.release()
    cv2.destroyAllWindows()

def calculate_distance(center_x, center_y):
    """Calculates the distance between the ball's center and the hole."""
    hole_center = ((HOLE[0] + HOLE[2] // 2), (HOLE[1] + HOLE[3] // 2))
    return math.sqrt((hole_center[0] - center_x) ** 2 + (hole_center[1] - center_y) ** 2)

def check_if_moving(dist_arr, distance):
    if len(dist_arr) < 10:
        return False
    curr_avg = sum(dist_arr) / len(dist_arr)
    return abs(distance - curr_avg) >= MOVEMENT_THRESHOLD

def process_video(num):
    cap = cv2.VideoCapture(get_video_name(num))
    tracker = cv2.legacy.TrackerCSRT_create()

    ret, frame = cap.read()
    tracker.init(frame, BALL[num])

    # Initialize list to store tracking data across frames
    tracking_data = []
    shot_data = []
    frame_number = 0
    num_shots = 0
    dist_history = deque(maxlen=10)
    status_history = deque(maxlen=10)
    output_video = cv2.VideoWriter('output_video.avi', cv2.VideoWriter_fourcc(*'MJPG'), 30, (frame.shape[1], frame.shape[0]))


    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print(frame_number, success, bbox)
            break
        
        success, bbox = tracker.update(frame)
        
        if success:
            frame_number += 1
            x, y, w, h = bbox  # Extract coordinates and dimensions from bounding box
            center_x, center_y = int(x + w//2), int(y + h//2)
            cv2.rectangle(frame, (int(x), int(y)), (int(x+w), int(y+h)), (0, 0, 255), 2)  # Color = Red, Thickness = 2
            if frame_number % 2 == 0:
                output_video.write(frame)
            distance = calculate_distance(center_x, center_y)
            is_moving = check_if_moving(dist_history, distance)
            dist_history.append(distance)
            if not any(status_history) and is_moving:
                num_shots += 1
                shot_data.append({
                    "user_id": "test",
                    "shot_number": num_shots,
                    "frame_number": frame_number,
                    "distance": f"{distance:.2f}"
                })

            status_history.append(is_moving)
            # Store data for the current frame
            print({
                    "user_id": "test",
                    "frame_number": frame_number,
                    "x": int(center_x),
                    "y": int(center_y),
                    "distance": f"{distance:.2f}",
                    "is_moving" : is_moving,
                    "shot_number": num_shots,
                })

            # print(f"Ball Coordinates: ({center_x}, {center_y})") 
            # print(f"frame: {frame_number} Dist: ({total_distance:.2f})")
            cv2.imshow("Tracking", frame)
            if cv2.waitKey(1) == ord('q'):
                break
    print(shot_data)
    # Release resources once processing is complete
    cap.release()
    cv2.destroyAllWindows()
    output_video.release()

set_roi(55)
# process_video(66)
