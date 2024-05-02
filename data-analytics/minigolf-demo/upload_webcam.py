import cv2
from datetime import datetime
import os
from google.cloud import storage

"""
This script captures video from a webcam, allows the user to start and stop recording, 
and provides options to save the recorded video locally or upload it to Google Cloud Storage. 
For Google Cloud Storage upload, ensure you have set up authentication and have a bucket created. 
"""


# Constants for bucket name and subfolder
BUCKET_NAME = ""
# Get the current working directory
VIDEO_SUBFOLDER = os.path.join(os.getcwd(), "video")
# Create the video subfolder if it doesn't exist
os.makedirs(VIDEO_SUBFOLDER, exist_ok=True)

# Function to upload a file to Google Cloud Storage
def upload_blob(bucket_name, source, destination):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination)
    blob.upload_from_filename(source)
    print(f"File {source} uploaded to {destination}.")


# Initialize video capture
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
cap.set(cv2.CAP_PROP_FPS, 60)

# Get video properties
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
print(f"Capture Resolution: {width} x {height}, FPS: {fps}")
actual_fps = cap.get(cv2.CAP_PROP_FPS)
print("Actual Capture FPS:", actual_fps)

# Video writer settings
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
recording = False
out = None

# Instructions for the user
print("Press '1' to start recording.")
print("Press 'q' or 'Esc' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    cv2.imshow('Webcam', frame)
    key = cv2.waitKey(1)

    # Start recording when '1' is pressed
    if key & 0xFF == ord('1'):
        if recording:
            continue
        recording = True
        now = datetime.now()
        filename = f"minigolf_{now.strftime('%Y%m%d_%H%M%S')}.mp4"
        full_video_path = os.path.join(VIDEO_SUBFOLDER, filename)

        out = cv2.VideoWriter(full_video_path, fourcc, 60.0, (width, height))
        print("Recording started...")
        print("Press '2' to stop recording and upload to cloud storage.")
        print("Press '3' to stop recording and save locally.")

    # Upload and save to subfolder when '2' is pressed
    elif key & 0xFF == ord('2') and recording:
        recording = False
        out.release()
        print("Recording stopped. The video will be uploaded to the Cloud storage")
        upload_blob(BUCKET_NAME, full_video_path, filename)  # Upload to subfolder
        print("Press '1' to start recording.")
        print("Press 'q' or 'Esc' to quit.")

    # Save to subfolder without uploading when '3' is pressed
    elif key & 0xFF == ord('3') and recording:
        recording = False
        out.release()
        print("Recording stopped. The video will NOT be uploaded to the Cloud storage")
        print("Press '1' to start recording.")
        print("Press 'q' or 'Esc' to quit.")

    # Quit when 'q' or 'Esc' is pressed
    elif key & 0xFF == ord('q') or key == 27:
        break

    # Write frame to video file if recording
    if recording:
        out.write(frame)

# Release resources
cap.release()
if out is not None:
    out.release()
cv2.destroyAllWindows()
