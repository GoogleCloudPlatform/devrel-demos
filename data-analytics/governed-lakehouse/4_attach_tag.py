import os
from google.cloud import datacatalog_v1
from google.cloud import bigquery

project_id = os.environ.get("PROJECT_ID")
region = os.environ.get("REGION", "us-central1")
dataset_id = os.environ.get("DATASET_ID", "lakehouse_retail_demo")

# 1. Dynamically lookup the Policy Tag ID
catalog_client = datacatalog_v1.PolicyTagManagerClient()
parent_loc = f"projects/{project_id}/locations/{region}"

taxonomies = catalog_client.list_taxonomies(parent=parent_loc)
taxonomy_id = next((t.name for t in taxonomies if t.display_name == "BusinessCritical"), None)
policy_tags = catalog_client.list_policy_tags(parent=taxonomy_id)
policy_tag_id = next((p.name for p in policy_tags if p.display_name == "RestrictedFinancial"), None)

# 2. Update BigQuery Schema
bq_client = bigquery.Client(project=project_id)
table_id = f"{project_id}.{dataset_id}.transactions"
table = bq_client.get_table(table_id)

new_schema =[]
for field in table.schema:
    if field.name == 'amount':
        policy_tags_list = bigquery.PolicyTagList(names=[policy_tag_id])
        new_field = bigquery.SchemaField(
            name=field.name, field_type=field.field_type, mode=field.mode,
            description=field.description, policy_tags=policy_tags_list
        )
        new_schema.append(new_field)
    else:
        new_schema.append(field)

table.schema = new_schema
bq_client.update_table(table, ["schema"])

print("✅ Policy tag successfully attached to the 'amount' column in BigQuery!")