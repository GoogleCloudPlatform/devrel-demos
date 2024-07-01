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
import re
from google.cloud import bigquery, storage
from cloud_function.firestore_utils import get_firestore_client

LANE = "a"
MONITORING_INTERVAL = 5
BACKGROUND_IMAGE_BUCKET = "image_gml_test_a"
PROJECT_ID = "gml-seoul-2024-demo-01"
BIGQUERY_A = f"{PROJECT_ID}.minigolf_a.tracking"
BIGQUERY_B = f"{PROJECT_ID}.minigolf_b.tracking"
COMMENTARY = f"{PROJECT_ID}.minigolf_a.commentary" # MAKE SURE TO SELECT A RIGHT LANE!
BASE_PATH = "C:/Users/pc/desktop/Google_Share_Sample/"
TOTALS_PATH = os.path.join(BASE_PATH, "totals")
LIST_FILE_PATH = os.path.join(BASE_PATH, "list.txt")
PERSONAL_DATA_PATH = os.path.join(BASE_PATH, "personalData")

client = bigquery.Client()
storage_client = storage.Client()
db = get_firestore_client()

def create_totals_directory(totals_path):
    """Creates the totals directory if it doesn't exist."""
    if not os.path.exists(totals_path):
        os.makedirs(totals_path)
        print(f"폴더가 생성되었습니다 : {totals_path}")

def query_data(dataset):
    """Fetches data from BigQuery, filters it, and calculates statistics."""
    query = f"SELECT * FROM {dataset}"
    df = client.query(query).to_dataframe()
    last_frame_per_user = df.groupby('user_id')['frame_number'].transform(max)
    df_filtered = df[df['frame_number'] == last_frame_per_user]
    df_filtered = df_filtered[df_filtered['distance'] < 30]
    user_shot_counts = df_filtered.groupby('user_id')['shot_number'].first()
    user_shot_counts = user_shot_counts[user_shot_counts > 0]
    num_users = df_filtered['user_id'].nunique()
    average_shots = user_shot_counts.mean()
    return num_users, average_shots

def update_stats(totals_path, num_users, average_shots_per_user):
    """Writes the calculated results to a text file."""
    REStxt = f"\n총유저:{num_users}\n평균 타수:{average_shots_per_user}"
    textPath = os.path.join(totals_path, 'totals.txt')
    with open(textPath, 'w') as file:
        file.write(REStxt)


def check_user_status(lane, user_id):
    """Checks the status of a user in Firestore."""
    users_ref = db.collection(f'users_{lane}').document(f"minigolf_{user_id}")
    user_doc = users_ref.get()
    if user_doc.exists:
        status = user_doc.to_dict().get('status')
        print(f"USER_ID {user_id} status: {status}")
        return status
    else:
        print(f"USER_ID {user_id} not found in Firestore.")
        return None
    

if __name__ == "__main__":
    create_totals_directory(TOTALS_PATH)

    while True:
        USER_ID = input("Enter USER_ID (four digits, e.g., 0001, or type 'exit'): ")
        if USER_ID.lower() == 'exit':
            break
        if not re.match(r'^\d{4}$', USER_ID): 
            print("Invalid USER_ID. Please enter exactly four digits.")
            continue
        
        num_users_a, average_shots_per_user_a = query_data(BIGQUERY_A)
        num_users_b, average_shots_per_user_b = query_data(BIGQUERY_B)

        num_users = num_users_a + num_users_b
        average_shots_per_user = ((average_shots_per_user_a * num_users_a) + 
                                (average_shots_per_user_b * num_users_b)) / num_users

        update_stats(TOTALS_PATH, num_users, average_shots_per_user)

        # --- Check USER_ID Status in Firestore ---
        status = check_user_status(LANE, USER_ID)
        if status == "completed":
            print(f"{USER_ID} is completed. Find the user folder.")
            user_folder_name = None
            with open(LIST_FILE_PATH, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line:
                        parts = line.split('_')
                        if len(parts) >= 5:
                            print(parts[5])  # Log the third value
                            if parts[5] == USER_ID:
                                user_folder_name = f"{parts[0]}_{parts[1]}"
                                break
            if not user_folder_name:
                raise ValueError(f"USER_ID {USER_ID} not found in the list file.")
        elif status == "processing":
            print(f"{USER_ID} is currently being processed. Please wait.")
            continue  # Skip to the next user 

        full_path = os.path.join(PERSONAL_DATA_PATH, user_folder_name)
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            print(f"Folder created: {full_path}")
        else:
            print(f"Folder already exists: {full_path}")
        
        bucket = storage_client.get_bucket(BACKGROUND_IMAGE_BUCKET)
        blob = bucket.blob(f"minigolf_{USER_ID}.png")
        blob.download_to_filename(os.path.join(full_path, "result.png"))

        commentary_query = f'SELECT commentary FROM {COMMENTARY} WHERE user_id="minigolf_{USER_ID}"'
        commentary_df = client.query(commentary_query).to_dataframe()
        commentary_string = commentary_df['commentary'].iloc[0]["commentary"]

        textPath = os.path.join(full_path,'result.txt')
        with open(textPath, 'w', encoding='utf-8') as file:
            file.write(commentary_string)

        print("Content saved to /tmp/result.txt")

