from google.api_core.exceptions import AlreadyExists, Conflict
from google.cloud import dataplex_v1, storage
from google.cloud.dataplex_v1.types import Entry, EntrySource

from schemas import (
    BUCKET_NAME,
    ENTRY_GROUP_ID,
    ENTRY_TYPE_ID,
    FILESET_ENTRY_ID,
    LOCAL_PDF_PATH,
    PROJECT_ID,
    REGION,
    VIRTUAL_STORAGE_URI,
    ensure_sample_pdf,
)

# 1. Verify pre-packaged PDF manual and upload to Cloud Storage bucket
ensure_sample_pdf(LOCAL_PDF_PATH)
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)
if not bucket.exists():
    try:
        bucket = storage_client.create_bucket(bucket, location=REGION)
        print(f"Created Cloud Storage bucket: gs://{BUCKET_NAME} in {REGION}")
    except Conflict:
        bucket = storage_client.bucket(BUCKET_NAME)

blob = bucket.blob("sop-pdfs/LUM-LIG-DES-8G8J_manual.pdf")
blob.upload_from_filename(LOCAL_PDF_PATH, content_type="application/pdf")
print(f"Uploaded unstructured PDF manual to: {VIRTUAL_STORAGE_URI}")

# 2. Register governed Fileset Entry in Knowledge Catalog
catalog_client = dataplex_v1.CatalogServiceClient()
parent_location = f"projects/{PROJECT_ID}/locations/{REGION}"
entry_group_resource_name = f"{parent_location}/entryGroups/{ENTRY_GROUP_ID}"
entry_type_resource_name = f"{parent_location}/entryTypes/{ENTRY_TYPE_ID}"

fileset_entry_name = f"{entry_group_resource_name}/entries/{FILESET_ENTRY_ID}"
fully_qualified_fileset_uri = f"gcs:{BUCKET_NAME}"

fileset_entry_spec = Entry(
    name=fileset_entry_name,
    entry_type=entry_type_resource_name,
    fully_qualified_name=fully_qualified_fileset_uri,
    entry_source=EntrySource(
        resource=VIRTUAL_STORAGE_URI,
        system="Cloud Storage",
        platform="Google Cloud",
        display_name="LUM-LIG-DES-8G8J Unstructured SOP & Technical Manual Fileset",
        description="Logical fileset grouping unstructured product operating procedures and electrical safety PDFs.",
        location=REGION,
    ),
)

try:
    create_entry_op = catalog_client.create_entry(
        parent=entry_group_resource_name,
        entry_id=FILESET_ENTRY_ID,
        entry=fileset_entry_spec,
    )
    print(f"Registered governed Fileset Entry: {create_entry_op.name}")
except AlreadyExists:
    print(f"Fileset Entry already exists; retrieving live entry: {fileset_entry_name}")

registered_fileset_entry = catalog_client.get_entry(name=fileset_entry_name)
print(f"  -> Fully Qualified Name : {registered_fileset_entry.fully_qualified_name}")
print(f"  -> Physical Resource URI: {registered_fileset_entry.entry_source.resource}")
print(f"  -> Source System        : {registered_fileset_entry.entry_source.system}")
