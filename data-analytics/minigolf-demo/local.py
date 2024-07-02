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
from monitor import download_data
from google.cloud import bigquery, storage


storage_client = storage.Client()
bq_client = bigquery.Client()

PATH = "./"
LANE = "b"
PROJECT_ID = "gml-seoul-2024-demo-00"
BACKGROUND_IMAGE_BUCKET = f"image_gml_{LANE}"
COMMENTARY = f"{PROJECT_ID}.minigolf_{LANE}.commentary"

def download_data(full_path, user_id):
    bucket = storage_client.get_bucket(BACKGROUND_IMAGE_BUCKET)
    blob = bucket.blob(f"{user_id}.png")
    blob.download_to_filename(os.path.join(full_path, "result.png"))

    commentary_query = f'SELECT commentary FROM {COMMENTARY} WHERE user_id="{user_id}"'
    commentary_df = bq_client.query(commentary_query).to_dataframe()
    commentary_string = commentary_df['commentary'].iloc[0]["commentary"]

    textPath = os.path.join(full_path,'result.txt')
    with open(textPath, 'w', encoding='utf-8') as file:
        file.write(commentary_string)
    print(f"Commentary saved to {full_path}/result.txt")


while True:
    user_id = input("Enter user_id like '0001': ")

    if len(user_id) == 4 and user_id.isdigit():
        download_data(PATH, f"minigolf_{user_id}")
    else:
        print("Invalid input. Please enter exactly four digits.") 

