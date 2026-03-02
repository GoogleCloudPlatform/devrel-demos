import os
from google.cloud import datacatalog_v1

project_id = os.environ.get("PROJECT_ID")
region = os.environ.get("REGION", "us-central1")
parent = f"projects/{project_id}/locations/{region}"

client = datacatalog_v1.PolicyTagManagerClient()

# 1. Create Taxonomy
taxonomy = datacatalog_v1.Taxonomy(
    display_name="BusinessCritical",
    description="Business critical data taxonomy",
    activated_policy_types=[datacatalog_v1.Taxonomy.PolicyType.FINE_GRAINED_ACCESS_CONTROL]
)
created_taxonomy = client.create_taxonomy(parent=parent, taxonomy=taxonomy)

# 2. Create Policy Tag
policy_tag = datacatalog_v1.PolicyTag(display_name="RestrictedFinancial")
created_policy_tag = client.create_policy_tag(
    parent=created_taxonomy.name, 
    policy_tag=policy_tag
)

print(f"✅ Taxonomy created: {created_taxonomy.name}")
print(f"✅ Policy Tag created: {created_policy_tag.name}")