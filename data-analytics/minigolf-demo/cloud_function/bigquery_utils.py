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

from google.cloud import bigquery


bq_client = bigquery.Client()
dataset_ref = bq_client.dataset(f"minigolf")
tracking_table_ref = dataset_ref.table("tracking")
commentary_table_ref = dataset_ref.table("commentary")

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
    bigquery.SchemaField("user_id", "STRING"),
    bigquery.SchemaField("commentary", "STRING"),
]


def initialize_bq_tables():
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
    return


def insert_data(table, data):
    if table == "tracking":
        bq_client.insert_rows_json(tracking_table_ref, [data])
    elif table == "commentary":
        bq_client.insert_rows_json(commentary_table_ref, [data])
    return


def query_data_to_dataframe(project_id, user_id):
    BIGQUERY = f"{project_id}.minigolf.tracking"
    query = f'SELECT * FROM {BIGQUERY} WHERE user_id = "{user_id}" AND shot_number > 0'
    df = bq_client.query(query).to_dataframe()
    return df
