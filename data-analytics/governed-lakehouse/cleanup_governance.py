import os
from google.cloud import datacatalog_v1
from google.cloud import bigquery_datapolicies_v1

project_id = os.environ.get("PROJECT_ID")
region = os.environ.get("REGION", "us-central1")

catalog_client = datacatalog_v1.PolicyTagManagerClient()
dp_client = bigquery_datapolicies_v1.DataPolicyServiceClient()
parent_loc = f"projects/{project_id}/locations/{region}"

# 1. Delete Data Policy
try:
    data_policy_name = f"{parent_loc}/dataPolicies/mask_financial_null"
    dp_client.delete_data_policy(name=data_policy_name)
    print("🗑️ Deleted Data Policy (Masking Rule).")
except Exception as e:
    print(f"Skipping Data Policy deletion: {e}")

# 2. Find and Delete Taxonomy (This auto-deletes child Policy Tags)
try:
    taxonomies = catalog_client.list_taxonomies(parent=parent_loc)
    taxonomy_id = next((t.name for t in taxonomies if t.display_name == "BusinessCritical"), None)
    
    if taxonomy_id:
        catalog_client.delete_taxonomy(name=taxonomy_id)
        print("🗑️ Deleted Taxonomy and Policy Tags.")
    else:
        print("Taxonomy not found. Skipping.")
except Exception as e:
    print(f"Skipping Taxonomy deletion: {e}")