import json
import time
from google.api_core.exceptions import (
    AlreadyExists,
    NotFound,
    PermissionDenied,
)
from google.cloud import bigquery, dataplex_v1
from google.protobuf import field_mask_pb2, struct_pb2
from schemas import (
    ASPECT_TYPE_ID,
    COLUMN_GOVERNANCE_RULES,
    DATAPLEX_LOCATION,
    DATASET_ID,
    PROJECT_ID,
    STATE_FILE,
    pii_aspect_template,
)

bq_client = bigquery.Client(project=PROJECT_ID)
catalog_client = dataplex_v1.CatalogServiceClient()

# 1. Provision BigQuery dataset and copy 4 public e-commerce tables
dataset_ref = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
dataset_ref.location = "US"
bq_client.create_dataset(dataset_ref, exists_ok=True)
print(f"BigQuery dataset ready: {PROJECT_ID}.{DATASET_ID} (US)")

PUBLIC_SOURCE = "bigquery-public-data.thelook_ecommerce"
TABLES = ["users", "orders", "order_items", "products"]
copy_config = bigquery.CopyJobConfig(
    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
)
for table_name in TABLES:
    src_table = f"{PUBLIC_SOURCE}.{table_name}"
    dst_table = f"{PROJECT_ID}.{DATASET_ID}.{table_name}"
    copy_job = bq_client.copy_table(
        src_table, dst_table, job_config=copy_config
    )
    copy_job.result()
    print(f"Copied public table: {DATASET_ID}.{table_name}")

# 2. Create or retrieve global AspectType (pii-governance)
parent_global = f"projects/{PROJECT_ID}/locations/global"
aspect_type_path = f"{parent_global}/aspectTypes/{ASPECT_TYPE_ID}"

try:
    create_op = catalog_client.create_aspect_type(
        parent=parent_global,
        aspect_type_id=ASPECT_TYPE_ID,
        aspect_type=dataplex_v1.AspectType(
            description="Column-level PII sensitivity and SQL governance.",
            metadata_template=pii_aspect_template,
        ),
    )
    create_op.result()
    print(f"Created AspectType ID: {ASPECT_TYPE_ID} (global)")
except AlreadyExists:
    print(f"AspectType ready: {ASPECT_TYPE_ID} (global)")

# 3. Poll Knowledge Catalog search until auto-ingested users entry is ready
search_scope = f"projects/{PROJECT_ID}/locations/global"
users_query = f"name:users AND system=BIGQUERY AND parent:{DATASET_ID}"
users_entry = None
for attempt in range(1, 16):
    hits = list(
        catalog_client.search_entries(
            request=dataplex_v1.SearchEntriesRequest(
                name=search_scope,
                query=users_query,
                page_size=5,
            )
        )
    )
    if hits:
        users_entry = hits[0].dataplex_entry
        break
    time.sleep(4)

if users_entry is None:
    raise RuntimeError(f"Timed out waiting for catalog entry: {users_query}")

# Extract numeric PROJECT_NUMBER from canonical entry resource name
project_number = users_entry.name.split("/")[1]
aspect_key_prefix = f"{project_number}.global.{ASPECT_TYPE_ID}"

# 4. Build and attach 7 column-level aspects (Schema.fields.<col>)
aspects_map = {}
aspect_keys = []
for col_name, payload in COLUMN_GOVERNANCE_RULES.items():
    aspect_key = f"{aspect_key_prefix}@Schema.fields.{col_name}"
    aspect_keys.append(aspect_key)
    aspect_struct = struct_pb2.Struct()
    aspect_struct.update(payload)
    aspects_map[aspect_key] = dataplex_v1.Aspect(
        aspect_type=aspect_type_path,
        path=f"Schema.fields.{col_name}",
        data=aspect_struct,
    )

updated_entry = None
for sync_attempt in range(1, 12):
    try:
        updated_entry = catalog_client.update_entry(
            request=dataplex_v1.UpdateEntryRequest(
                entry=dataplex_v1.Entry(
                    name=users_entry.name,
                    aspects=aspects_map,
                ),
                update_mask=field_mask_pb2.FieldMask(paths=["aspects"]),
                aspect_keys=aspect_keys,
            )
        )
        break
    except (PermissionDenied, NotFound):
        if sync_attempt == 11:
            raise
        time.sleep(5)

print(f"Resolved Entry ID: {updated_entry.name.split('/')[-1]}")
print(f"Aspect Key Prefix: {aspect_key_prefix}")
print(f"Attached Column Aspects: {len(aspect_keys)} columns on users")

# 5. Wait for all 4 tables to appear in search index and save state
for poll_idx in range(1, 12):
    table_hits = list(
        catalog_client.search_entries(
            request=dataplex_v1.SearchEntriesRequest(
                name=search_scope,
                query=f"system=BIGQUERY AND parent:{DATASET_ID}",
                page_size=10,
            )
        )
    )
    if len(table_hits) >= 4:
        break
    time.sleep(4)

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(
        {
            "project_id": PROJECT_ID,
            "project_number": project_number,
            "dataplex_location": DATAPLEX_LOCATION,
            "dataset_id": DATASET_ID,
            "aspect_type_id": ASPECT_TYPE_ID,
            "aspect_type_path": aspect_type_path,
            "aspect_key_prefix": aspect_key_prefix,
            "users_entry_name": updated_entry.name,
        },
        f,
        indent=2,
    )
print(f"Saved state manifest: {STATE_FILE} ({len(table_hits)} tables)")
