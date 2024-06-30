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

import cv2
import firebase_admin
import functions_framework
import math
import os
import pandas

from collections import deque
from datetime import datetime
from firebase_admin import firestore
from google.cloud import bigquery, storage
import matplotlib.pyplot as plt

import vertexai
from vertexai.generative_models import GenerativeModel, Image, Part
import vertexai.preview.generative_models as generative_models

# Constants for ball and hole positions (assuming fixed locations in the video)
BALL = (1700, 520, 40, 40)
HOLE = (725, 536, 7, 6)

PROJECT_ID = "summit-seoul-2024-demo-01"
VIDEO_BUCKET = "video_summit_real"
BACKGROUND_IMAGE_BUCKET = ""

# Threshold for considering distance change as significant movement
MOVEMENT_THRESHOLD = 5

# BigQuery configuration
BIGQUERY_DATASET_ID = "minigolf"
BIGQUERY_TRACKING_TABLE_ID = "tracking"
BIGQUERY_COMMENTARY_TABLE_ID = "commentary"
BIGQUERY = f"{PROJECT_ID}.{BIGQUERY_DATASET_ID}.{BIGQUERY_TRACKING_TABLE_ID}"

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
COMMENTARY_SCHEMA = [
    bigquery.SchemaField("commentary", "STRING"),
]

GEMINI_MODEL = "gemini-1.5-pro-001"
GENERATION_CONFIG = {
    "max_output_tokens": 8192,
    "temperature": 0,
    "top_p": 1,
}

SAFETY_SETTINGS = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

TITLE = ""
VENUE = ""
LANGUAGE = "English"

SYSTEM_INSTRUCTION = f"""
You are a team of two professional golf broadcasters covering the final hole of the {TITLE} at the {VENUE}. Use {LANGUAGE} to display result.
Each Announcer and Commentator's line must start on a new line. Once the announcer's or the commentator's dialogue has ended, use line breaks to clearly separate.
You will receive precise shot information for the final hole. This information is extracted from video analysis and is 100% accurate. You MUST base your commentary strictly on this data, especially the number of shots taken and the outcome of each shot.
**IMPORTANT - Never say "Hole in one" if the number of shot is greater than one.
Also use provided raw video and a photo. The photo shows the player's ball trajectory and shot sequence.
- Use markdown syntax appropriately.
- Refer to the player as "player" or "they".
- Avoid commentary on the player's appearance.
- Focus on the commentary; do not include sound effects.

Background:
- The competitor has already finished their round and is currently ahead.
- The player needs to finish this hole at par or better (three shots or less) to win the championship.
- If they score a bogey or worse (four shots or more), the competitor will win.
- Don't reveal the exact score difference, just emphasize that the player needs a good performance on this final hole to secure victory.

Announcer (Play-by-Play):
- Your role is to create excitement and capture the energy of the moment.
- Focus on describing the action as it unfolds, using vivid language and a dynamic tone.
- Don't just state what happened, describe the shot's trajectory in detail.
- Highlight the stakes of the final hole and React to the player's shots with enthusiasm.
- **Engage with the commentator, asking questions and prompting further analysis.**
- Paint a picture for the viewers so they feel like they are right there on the green.

Commentator (Analyst):
- Your role is to provide expert insights and analysis.
- Discuss the player's strategy: "Interesting choice to play it safe on this shot. They must be feeling the pressure."
- Evaluate the quality of the shots: "That was a textbook putt, perfectly executed. They read the green like a pro."
- Offer extended context about the tournament, the player's history, and the significance of this final hole.
- Share relevant statistics or historical data: "No player has ever won this tournament with a hole-in-one on the final hole. Could we witness history in the making?"
- Don't just provide facts, weave them into a compelling narrative.
- **Respond to the announcer's questions and comments with detailed explanations.**

## Example Interaction - This is just some examples, do not directly use this example but use it as a reference:
**IMPORTANT - Prioritize the image provided**

Before the Shots:
Announcer: Welcome back to the {TITLE} final! The tension is palpable here at the {VENUE} as we head to the final hole!
Commentator: Absolutely, the atmosphere is electric! This is it, the moment of truth. Can the player hold their nerve and claim the championship title? All eyes are on them!

Shot 1:
Announcer: The player takes a deep breath and lines up their first putt.
Commentator: This first putt is crucial. It's a tricky distance, requiring a delicate touch and a strategic approach.
Announcer: And here comes the putt! Oh, just a bit strong! The ball rolls past the hole.
Commentator: Not the ideal start, but the player has plenty of opportunities to recover.

Shot 2:
Announcer: The first putt may not have gone as planned, but the player remains composed.
Commentator: Yes, the player has shown incredible mental fortitude throughout this tournament. I expect them to bounce back from this.
Announcer: Here comes the second putt. It's rolling nicely towards the hole…
Commentator: Oh, so close! Just a hair to the left! But it's right next to the hole!

Shot 3 (Success):
Announcer: It's right there! One putt for glory!
Commentator: This is a pressure-packed moment. Can the player hold their nerve and sink this putt?
Announcer: This is it! The final putt! The player takes aim… It's in! An incredible finish! The player wins the title!
Commentator: What a performance! The player remained calm under pressure and sank the winning putt! A new champion is crowned!

Shot 3 (Failure):
Announcer: It all comes down to this! One putt to decide the championship!
Commentator: The tension is almost unbearable! Can the player pull off this clutch putt?
Announcer: Here it comes, the final putt… Oh no! It misses!
Commentator: What a heartbreaking finish! Unfortunately, victory will have to wait for another day. But let's give the player a round of applause for their incredible effort.
"""

bq_client = bigquery.Client()
storage_client = storage.Client()

dataset_ref = bq_client.dataset(BIGQUERY_DATASET_ID)
tracking_table_ref = dataset_ref.table(BIGQUERY_TRACKING_TABLE_ID)
commentary_table_ref = dataset_ref.table(BIGQUERY_COMMENTARY_TABLE_ID)

# List to store any errors during BigQuery inserts
ERRORS = []


def get_firestore_client():
    try:
        app = firebase_admin.get_app()
    except ValueError:
        app = firebase_admin.initialize_app()
    finally:
        return firestore.client(app)


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
        # bucket = storage_client.get_bucket(BACKGROUND_IMAGE_BUCKET)
        # blob = bucket.blob(image_filename)
        # blob.upload_from_filename(f"/tmp/{image_filename}")
        
        # Clean up temporary image file
        # os.remove(f"/tmp/{image_filename}")

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


def helper_shot_information(df):
    filtered_df = df[df['shot_number'] > 0].sort_values(by='frame_number')

    # Group by shot_number
    grouped = filtered_df.groupby('shot_number')
    shot_number_dict = {1: "1st", 2: "2nd", 3: "3rd"}

    shot_details = []
    # Iterate over each group
    for shot_number, group_df in grouped:
        # Get the last row for the current shot_number
        row = group_df.iloc[-1]

        if shot_number < 4:
            shot_details.append(f"The {shot_number_dict[shot_number]} ")
        else:
            shot_details.append(f"The {shot_number}th ")
        shot_details.append(f"shot was ")

        if row['distance'] < 30:
            shot_details.append(f"hole-in!\n")
        else:
            shot_details.append(f"not hole-in.\n")
    shot_details = ''.join(shot_details)

    # Check if last shot distance is less than 50 (made a hole-in)
    result = "didn't make" if filtered_df['distance'].iloc[-1] > 50 else "made"
    last_shot_distance = filtered_df['distance'].iloc[-1]
    shot_number = filtered_df['shot_number'].iloc[-1]
    shot_dict = {1: "Hole-in-one!",
                 2: "birdie!",
                 3: "par!",
                 4: "bogey.",
                 5: "double bogey.",
                 6: "triple bogey.",
                 7: "quadruple bogey.",
                 8: "double par."}
    if last_shot_distance <= 30:
        result = f"made with {shot_number} shot/shots! {shot_dict[shot_number]}"
        if shot_number > 3:
            result += " The player loses."
        else:
            result += " The player wins!"

    commentary = f"""
    {shot_details}
    The ball {result}
    """
    return commentary


def generate(content):
    vertexai.init(project=PROJECT_ID, location="us-central1")
    model = GenerativeModel(
        GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    
    responses = model.generate_content(
        content,        
        generation_config=GENERATION_CONFIG,
        safety_settings=SAFETY_SETTINGS,
    )
    return responses.text


# Cloud Function entry point
@functions_framework.cloud_event
def image_recognition(cloud_event):
    """
    Cloud Function triggered by a new video upload to Cloud Storage.

    Processes the video and uploads tracking data to BigQuery.
    """
    start_time = datetime.now()
    db = get_firestore_client()

    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]
    user_id = file_name.split(".")[0]
    user = {
        "user_id": user_id,
        "status": "processing",  # Initial status is 'waiting'
    }
    # Create 'users' collection if it doesn't exist
    if not db.collection('users').get():
        db.collection('users').document().set({})
    
    # Save user information to Firestore
    users_ref = db.collection('users').document(user_id)  # Use user_number as document ID
    users_ref.set(user)

    # Create BigQuery table if it doesn't exist
    try:
        bq_client.get_table(tracking_table_ref)
    except:
        print("Creating 'tracking' table in BigQuery...")
        bq_client.create_table(bigquery.Table(tracking_table_ref, schema=TRACKING_SCHEMA))
        print("Table created successfully.")

    try:
        bq_client.get_table(commentary_table_ref)
    except:
        print("Creating 'commentary' table in BigQuery...")
        bq_client.create_table(bigquery.Table(commentary_table_ref, schema=COMMENTARY_SCHEMA))
        print("Table created successfully.")

    temp_file = f"/tmp/{file_name}"

    # Download the video to a temporary file
    with open(temp_file, "wb") as temp_file_handle:
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)
        blob.download_to_filename(temp_file)

    # Process the video and upload tracking data
    process_and_upload_video(temp_file, user_id)

    query = f'SELECT * FROM {BIGQUERY} WHERE user_id = "{user_id}" AND shot_number > 0'

    df = bq_client.query(query).to_dataframe()

    URI = f"gs://{bucket_name}/{user_id}.mp4"
    img = plt.imread(f"/tmp/BG_{user_id}.jpg")
    fig, ax = plt.subplots(figsize=(19.20, 10.80))
    # Define your custom color palette
    custom_palette = {
        1: "#4285F4", # Google Core scheme
        2: "#34A853",
        3: "#FBBC04",
        4: "#EA4335",
        5: "#63BDFD", # Google Highlight scheme
        6: "#18D363",
        7: "#FFE000",
        8: "#FF8080",
        9: "#4285F4", # Google Core scheme
        10: "#34A853",
        11: "#FBBC04",
        12: "#EA4335",
        13: "#63BDFD", # Google Highlight scheme
        14: "#18D363",
        15: "#FFE000",
        16: "#FF8080",
    }

    color_palette = [custom_palette[shot_number] for shot_number in df['shot_number'].unique()]
    # df['x'], df['y'] = 1080 - df['y'], df['x']
    # color_palette = sns.color_palette("tab10", n_colors=len(df['shot_number'].unique()))

    shot_groups = df.groupby('shot_number')
    for i, (shot_number, data) in enumerate(shot_groups):
        ax.scatter(data['x'], data['y'], label=f"Shot {shot_number}", color=color_palette[i], s=15, marker='o', edgecolors='white', linewidths=0.25)
    ax.legend()

    # invert y-axis
    plt.gca().invert_yaxis()
    # plt.gca().invert_xaxis()

    # Remove axis labels and ticks
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')

    ax.imshow(img)
    plt.savefig('/tmp/result.png')
    
    VIDEO = Part.from_uri(uri=URI, mime_type="video/mp4")
    PHOTO = Part.from_image(Image.load_from_file("/tmp/result.png"))

    RES = generate([VIDEO, PHOTO, helper_shot_information(df)])
    insert_errors = bq_client.insert_rows_json(tracking_table_ref, [{"commentary": RES}])

    # Clean up the temporary file
    if os.path.isfile(temp_file):
        os.remove(temp_file)
    else:
        print(f"Downloaded file not found: {temp_file}")

    # Update user status to 'completed' in 'users' collection
    user_ref = db.collection('users').document(user_id)
    user_ref.update({'status': 'completed'})

    end_time = datetime.now()    
    elapsed_time = (end_time - start_time).total_seconds()
    print(f"Processing {file_name} is completed. Execution time: {elapsed_time:.2f} seconds.")
