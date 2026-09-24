from google.api_core.exceptions import AlreadyExists
from google.cloud import dataplex_v1
from google.cloud.dataplex_v1.types import AspectType, EntryGroup, EntryType

from schemas import (
    ENTRY_GROUP_ID,
    ENTRY_TYPE_ID,
    EXTRACTED_ASPECT_TYPE_ID,
    GOVERNANCE_ASPECT_TYPE_ID,
    PROJECT_ID,
    REGION,
    extracted_aspect_template,
    governance_aspect_template,
)

catalog_client = dataplex_v1.CatalogServiceClient()
parent_location = f"projects/{PROJECT_ID}/locations/{REGION}"

entry_group_resource_name = f"{parent_location}/entryGroups/{ENTRY_GROUP_ID}"
entry_type_resource_name = f"{parent_location}/entryTypes/{ENTRY_TYPE_ID}"
extracted_aspect_type_name = f"{parent_location}/aspectTypes/{EXTRACTED_ASPECT_TYPE_ID}"
governance_aspect_type_name = f"{parent_location}/aspectTypes/{GOVERNANCE_ASPECT_TYPE_ID}"

# 1. Provision EntryGroup
try:
    eg_op = catalog_client.create_entry_group(
        parent=parent_location,
        entry_group_id=ENTRY_GROUP_ID,
        entry_group=EntryGroup(
            name=entry_group_resource_name,
            display_name="Unstructured Dark Data Fileset Group",
            description="Governed logical container for unstructured Cloud Storage PDF manuals and SOP filesets.",
        ),
    )
    if hasattr(eg_op, "result"):
        eg_op.result()
    print(f"Created EntryGroup: {entry_group_resource_name}")
except AlreadyExists:
    print(f"EntryGroup already exists; retrieving live resource: {entry_group_resource_name}")

live_entry_group = catalog_client.get_entry_group(name=entry_group_resource_name)

# 2. Provision EntryType
try:
    et_op = catalog_client.create_entry_type(
        parent=parent_location,
        entry_type_id=ENTRY_TYPE_ID,
        entry_type=EntryType(
            name=entry_type_resource_name,
            display_name="Unstructured PDF Fileset Asset",
            description="Logical fileset grouping unstructured PDF manuals and SOP documents in Cloud Storage.",
        ),
    )
    if hasattr(et_op, "result"):
        et_op.result()
    print(f"Created EntryType : {entry_type_resource_name}")
except AlreadyExists:
    print(f"EntryType already exists; retrieving live resource : {entry_type_resource_name}")

live_entry_type = catalog_client.get_entry_type(name=entry_type_resource_name)

# 3. Provision AspectType 1: dark-data-extracted-metadata
try:
    at1_op = catalog_client.create_aspect_type(
        parent=parent_location,
        aspect_type_id=EXTRACTED_ASPECT_TYPE_ID,
        aspect_type=AspectType(
            name=extracted_aspect_type_name,
            display_name="Dark Data Multimodal Extracted Metadata",
            description="Structured domain ontology, operational hazard level, and provenance extracted by Gemini.",
            metadata_template=extracted_aspect_template,
        ),
    )
    if hasattr(at1_op, "result"):
        at1_op.result()
    print(f"Created AspectType: {extracted_aspect_type_name}")
except AlreadyExists:
    print(f"AspectType already exists; retrieving live resource: {extracted_aspect_type_name}")

live_extracted_aspect_type = catalog_client.get_aspect_type(name=extracted_aspect_type_name)

# 4. Provision AspectType 2: document-governance-aspect
try:
    at2_op = catalog_client.create_aspect_type(
        parent=parent_location,
        aspect_type_id=GOVERNANCE_ASPECT_TYPE_ID,
        aspect_type=AspectType(
            name=governance_aspect_type_name,
            display_name="Document Governance & Inventory Cross-Reference Aspect",
            description="Compliance standards, stewardship ownership, and structured SKU inventory cross-references.",
            metadata_template=governance_aspect_template,
        ),
    )
    if hasattr(at2_op, "result"):
        at2_op.result()
    print(f"Created AspectType: {governance_aspect_type_name}")
except AlreadyExists:
    print(f"AspectType already exists; retrieving live resource: {governance_aspect_type_name}")

live_governance_aspect_type = catalog_client.get_aspect_type(name=governance_aspect_type_name)
print("✓ All Knowledge Catalog namespaces and AspectType blueprints are active.")
