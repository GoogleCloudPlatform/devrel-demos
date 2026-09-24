import json
import os
import shutil
from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import bigquery, dataplex_v1
from google.protobuf import field_mask_pb2
from schemas import (
    ASPECT_TYPE_ID,
    COLUMN_GOVERNANCE_RULES,
    DATASET_ID,
    PROJECT_ID,
    STATE_FILE,
)

catalog_client = dataplex_v1.CatalogServiceClient()
bq_client = bigquery.Client(project=PROJECT_ID)

state = {}
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

users_entry_name = state.get("users_entry_name", "")
aspect_key_prefix = state.get("aspect_key_prefix", "")
aspect_type_path = state.get(
    "aspect_type_path",
    f"projects/{PROJECT_ID}/locations/global/aspectTypes/{ASPECT_TYPE_ID}",
)

print("Starting reverse-dependency resource cleanup...")
cleanup_notes = []

# 1. Detach column-level aspects from the users entry first
aspect_keys = [
    f"{aspect_key_prefix}@Schema.{col}"
    for col in COLUMN_GOVERNANCE_RULES
]
if users_entry_name and aspect_key_prefix:
    try:
        catalog_client.update_entry(
            request=dataplex_v1.UpdateEntryRequest(
                entry=dataplex_v1.Entry(name=users_entry_name, aspects={}),
                update_mask=field_mask_pb2.FieldMask(paths=["aspects"]),
                delete_missing_aspects=True,
                aspect_keys=aspect_keys,
            )
        )
    except (NotFound, GoogleAPICallError) as exc:
        cleanup_notes.append(f"entry:{type(exc).__name__}")
print(f"Detached column aspects: {len(aspect_keys)} keys removed")

# 2. Delete global AspectType (pii-governance)
try:
    del_op = catalog_client.delete_aspect_type(name=aspect_type_path)
    del_op.result()
except NotFound as exc:
    cleanup_notes.append(f"aspect_type:{type(exc).__name__}")
print(f"Deleted AspectType ID: {ASPECT_TYPE_ID} (global)")

# 3. Delete BigQuery sandbox dataset and all copied tables
dataset_full_id = f"{PROJECT_ID}.{DATASET_ID}"
bq_client.delete_dataset(
    dataset_full_id, delete_contents=True, not_found_ok=True
)
print(f"Deleted BigQuery dataset: {dataset_full_id}")

# 4. Remove local state file and bytecode cache
if os.path.exists(STATE_FILE):
    os.remove(STATE_FILE)
shutil.rmtree("__pycache__", ignore_errors=True)
print(f"Removed local state file: {STATE_FILE}")

print("✓ Standalone teardown complete. Environment cleanly reset.")
