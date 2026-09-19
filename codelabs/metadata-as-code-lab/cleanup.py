import os
import time
from google.api_core.exceptions import NotFound, ResourceExhausted
from google.cloud import dataplex_v1, storage

from schemas import (
    BUCKET_NAME,
    ENTRY_GROUP_ID,
    ENTRY_TYPE_ID,
    EXTRACTED_ASPECT_TYPE_ID,
    FILESET_ENTRY_ID,
    GOVERNANCE_ASPECT_TYPE_ID,
    PROJECT_ID,
    REGION,
)

print("Starting reverse-dependency resource cleanup in Knowledge Catalog...")

catalog_client = dataplex_v1.CatalogServiceClient()
active_parent = f"projects/{PROJECT_ID}/locations/{REGION}"

# 1. Delete Fileset Entry
target_entry_path = f"{active_parent}/entryGroups/{ENTRY_GROUP_ID}/entries/{FILESET_ENTRY_ID}"
for attempt in range(3):
    try:
        catalog_client.delete_entry(name=target_entry_path)
        print(f"Deleted Fileset Entry: {target_entry_path}")
        break
    except NotFound:
        print(f"Fileset Entry already deleted: {target_entry_path}")
        break
    except ResourceExhausted:
        print("Rate limit encountered; waiting 5s before retry...")
        time.sleep(5)

# 2. Delete EntryGroup
target_eg_path = f"{active_parent}/entryGroups/{ENTRY_GROUP_ID}"
for attempt in range(3):
    try:
        del_eg_op = catalog_client.delete_entry_group(name=target_eg_path)
        if hasattr(del_eg_op, "result"):
            del_eg_op.result()
        print(f"Deleted EntryGroup   : {target_eg_path}")
        break
    except NotFound:
        print(f"EntryGroup already deleted   : {target_eg_path}")
        break
    except ResourceExhausted:
        print("Rate limit encountered; waiting 5s before retry...")
        time.sleep(5)

# 3. Delete EntryType
target_et_path = f"{active_parent}/entryTypes/{ENTRY_TYPE_ID}"
for attempt in range(3):
    try:
        del_et_op = catalog_client.delete_entry_type(name=target_et_path)
        if hasattr(del_et_op, "result"):
            del_et_op.result()
        print(f"Deleted EntryType    : {target_et_path}")
        break
    except NotFound:
        print(f"EntryType already deleted    : {target_et_path}")
        break
    except ResourceExhausted:
        print("Rate limit encountered; waiting 5s before retry...")
        time.sleep(5)

# 4. Delete Custom AspectTypes
for aspect_id_val in (EXTRACTED_ASPECT_TYPE_ID, GOVERNANCE_ASPECT_TYPE_ID):
    target_at_path = f"{active_parent}/aspectTypes/{aspect_id_val}"
    for attempt in range(3):
        try:
            del_at_op = catalog_client.delete_aspect_type(name=target_at_path)
            if hasattr(del_at_op, "result"):
                del_at_op.result()
            print(f"Deleted AspectType   : {target_at_path}")
            break
        except NotFound:
            print(f"AspectType already deleted   : {target_at_path}")
            break
        except ResourceExhausted:
            print("Rate limit encountered; waiting 5s before retry...")
            time.sleep(5)

# 5. Delete Cloud Storage object and bucket
storage_client = storage.Client(project=PROJECT_ID)
try:
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob("sop-pdfs/LUM-LIG-DES-8G8J_manual.pdf")
    if blob.exists():
        blob.delete()
        print(f"Deleted Cloud Storage object : gs://{BUCKET_NAME}/sop-pdfs/LUM-LIG-DES-8G8J_manual.pdf")
    if bucket.exists():
        bucket.delete(force=True)
        print(f"Deleted Cloud Storage bucket : gs://{BUCKET_NAME}")
except NotFound:
    print(f"Cloud Storage bucket already deleted: gs://{BUCKET_NAME}")
except ResourceExhausted:
    print("Cloud Storage rate limit encountered; skipping bucket deletion.")

# 6. Remove temporary generated JSON artifacts
for temp_file in ("extracted_metadata.json", "governance_metadata.json"):
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
            print(f"Removed local temporary file : {temp_file}")
        except OSError as err:
            print(f"File cleanup note: {err}")

print("✓ Standalone teardown complete. Environment cleanly reset.")
