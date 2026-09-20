import json
import pandas as pd
from google.cloud import dataplex_v1
from google.cloud.dataplex_v1.types import Aspect, Entry

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

# Load validated payloads produced by Step 4
with open("extracted_metadata.json", "r", encoding="utf-8") as f_ext:
    extracted_data = json.load(f_ext)

with open("governance_metadata.json", "r", encoding="utf-8") as f_gov:
    governance_data = json.load(f_gov)

catalog_client = dataplex_v1.CatalogServiceClient()
parent_location = f"projects/{PROJECT_ID}/locations/{REGION}"

entry_group_resource_name = f"{parent_location}/entryGroups/{ENTRY_GROUP_ID}"
entry_type_resource_name = f"{parent_location}/entryTypes/{ENTRY_TYPE_ID}"
extracted_aspect_type_name = f"{parent_location}/aspectTypes/{EXTRACTED_ASPECT_TYPE_ID}"
governance_aspect_type_name = f"{parent_location}/aspectTypes/{GOVERNANCE_ASPECT_TYPE_ID}"

fileset_entry_name = f"{entry_group_resource_name}/entries/{FILESET_ENTRY_ID}"
fully_qualified_fileset_uri = f"gcs:{BUCKET_NAME}"

extracted_aspect_key = f"{PROJECT_ID}.{REGION}.{EXTRACTED_ASPECT_TYPE_ID}"
governance_aspect_key = f"{PROJECT_ID}.{REGION}.{GOVERNANCE_ASPECT_TYPE_ID}"

updated_entry_payload = Entry(
    name=fileset_entry_name,
    entry_type=entry_type_resource_name,
    fully_qualified_name=fully_qualified_fileset_uri,
    aspects={
        extracted_aspect_key: Aspect(
            aspect_type=extracted_aspect_type_name,
            data=extracted_data,
        ),
        governance_aspect_key: Aspect(
            aspect_type=governance_aspect_type_name,
            data=governance_data,
        ),
    },
)

update_op = catalog_client.update_entry(
    request=dataplex_v1.UpdateEntryRequest(
        entry=updated_entry_payload,
        update_mask={"paths": ["aspects"]},
        aspect_keys=[extracted_aspect_key, governance_aspect_key],
    )
)

# Retrieve authoritative Entry with EntryView.ALL to verify live bound aspects
live_governed_entry = catalog_client.get_entry(
    request=dataplex_v1.GetEntryRequest(
        name=fileset_entry_name,
        view=dataplex_v1.EntryView.ALL,
    )
)

print(f"Successfully bound {len(live_governed_entry.aspects)} Aspect(s) to Entry: {live_governed_entry.name}\n")

for key, aspect_obj in live_governed_entry.aspects.items():
    aspect_short_name = key.split(".")[-1]
    print(f"=== Live Attached Aspect: {aspect_short_name} (Full Key: {key}) ===")
    df_live_aspect = pd.DataFrame(
        list(dict(aspect_obj.data).items()),
        columns=["Catalog Field", "Authoritative Stored Value"],
    )
    print(df_live_aspect.to_string(index=False))
    print()
