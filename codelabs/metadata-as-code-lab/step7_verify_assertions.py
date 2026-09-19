import json
from google.cloud import dataplex_v1

from schemas import (
    ENTRY_GROUP_ID,
    ENTRY_TYPE_ID,
    EXTRACTED_ASPECT_TYPE_ID,
    FILESET_ENTRY_ID,
    GOVERNANCE_ASPECT_TYPE_ID,
    PROJECT_ID,
    REGION,
)

with open("extracted_metadata.json", "r", encoding="utf-8") as f_ext:
    expected_extraction = json.load(f_ext)

catalog_client = dataplex_v1.CatalogServiceClient()
parent_location = f"projects/{PROJECT_ID}/locations/{REGION}"

entry_group_resource_name = f"{parent_location}/entryGroups/{ENTRY_GROUP_ID}"
entry_type_resource_name = f"{parent_location}/entryTypes/{ENTRY_TYPE_ID}"
extracted_aspect_type_name = f"{parent_location}/aspectTypes/{EXTRACTED_ASPECT_TYPE_ID}"
governance_aspect_type_name = f"{parent_location}/aspectTypes/{GOVERNANCE_ASPECT_TYPE_ID}"
fileset_entry_name = f"{entry_group_resource_name}/entries/{FILESET_ENTRY_ID}"

print("Running substantive end-to-end verification assertions...")

# 1. Verify EntryGroup exists
verify_eg = catalog_client.get_entry_group(name=entry_group_resource_name)
assert verify_eg.name == entry_group_resource_name, "EntryGroup resource name mismatch."

# 2. Verify EntryType exists
verify_et = catalog_client.get_entry_type(name=entry_type_resource_name)
assert verify_et.name == entry_type_resource_name, "EntryType resource name mismatch."

# 3. Verify both custom AspectTypes exist
verify_at1 = catalog_client.get_aspect_type(name=extracted_aspect_type_name)
assert verify_at1.name == extracted_aspect_type_name, "Extracted AspectType missing."

verify_at2 = catalog_client.get_aspect_type(name=governance_aspect_type_name)
assert verify_at2.name == governance_aspect_type_name, "Governance AspectType missing."

# 4. Verify live Fileset Entry and bound Aspect payloads
verify_entry = catalog_client.get_entry(
    request=dataplex_v1.GetEntryRequest(
        name=fileset_entry_name,
        view=dataplex_v1.EntryView.ALL,
    )
)
bound_extracted = next(
    (asp for k, asp in verify_entry.aspects.items() if k.endswith(f".{REGION}.{EXTRACTED_ASPECT_TYPE_ID}")),
    None,
)
bound_governance = next(
    (asp for k, asp in verify_entry.aspects.items() if k.endswith(f".{REGION}.{GOVERNANCE_ASPECT_TYPE_ID}")),
    None,
)

assert bound_extracted is not None, f"Aspect '{EXTRACTED_ASPECT_TYPE_ID}' not found on live Entry."
assert bound_governance is not None, f"Aspect '{GOVERNANCE_ASPECT_TYPE_ID}' not found on live Entry."
assert bound_extracted.data.get("document_title") == expected_extraction["document_title"], "Extracted title mismatch."
assert 0.0 <= float(bound_extracted.data.get("confidence_score", -1.0)) <= 1.0, "Invalid confidence score in catalog."
assert "lakehouse" in str(bound_governance.data.get("lakehouse_cross_ref_table", "")).lower(), "Missing Lakehouse cross-reference."

# 5. Verify search index discoverability
search_query = f"entrygroup={entry_group_resource_name} name:{FILESET_ENTRY_ID}"
search_results = list(
    catalog_client.search_entries(
        request=dataplex_v1.SearchEntriesRequest(
            name=parent_location,
            query=search_query,
        )
    )
)
assert len(search_results) >= 1, "Expected at least 1 search result in Knowledge Catalog."

print("✓ All 5 substantive verification assertions passed against live Google Cloud control plane state!")
