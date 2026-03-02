import os
from google.cloud import datacatalog_v1
from google.cloud import bigquery_datapolicies_v1
from google.iam.v1 import iam_policy_pb2

project_id = os.environ.get("PROJECT_ID")
region = os.environ.get("REGION", "us-central1")
analyst_email = os.environ.get("EMAIL_ANALYST")

# 1. Lookup the Policy Tag ID
catalog_client = datacatalog_v1.PolicyTagManagerClient()
parent_loc = f"projects/{project_id}/locations/{region}"

taxonomies = catalog_client.list_taxonomies(parent=parent_loc)
taxonomy_id = next((t.name for t in taxonomies if t.display_name == "BusinessCritical"), None)

if not taxonomy_id:
    raise ValueError("Taxonomy not found! Please run step 1 first.")

policy_tags = catalog_client.list_policy_tags(parent=taxonomy_id)
policy_tag_id = next((p.name for p in policy_tags if p.display_name == "RestrictedFinancial"), None)

print(f"🔍 Found Policy Tag: {policy_tag_id}")

# 2. Create Data Masking Policy (Always Null)
dp_client = bigquery_datapolicies_v1.DataPolicyServiceClient()
data_policy = bigquery_datapolicies_v1.DataPolicy(
    data_policy_id="mask_financial_null",
    policy_tag=policy_tag_id,
    data_policy_type=bigquery_datapolicies_v1.DataPolicy.DataPolicyType.DATA_MASKING_POLICY,
    data_masking_policy=bigquery_datapolicies_v1.DataMaskingPolicy(
        predefined_expression=bigquery_datapolicies_v1.DataMaskingPolicy.PredefinedExpression.ALWAYS_NULL
    )
)
created_policy = dp_client.create_data_policy(
    parent=parent_loc, 
    data_policy=data_policy
)

# 3. Bind the Masked Reader role to the Analyst
iam_req = iam_policy_pb2.GetIamPolicyRequest(resource=created_policy.name)
iam_policy = dp_client.get_iam_policy(request=iam_req)
iam_policy.bindings.add(role="roles/bigquerydatapolicy.maskedReader", members=[f"serviceAccount:{analyst_email}"])
dp_client.set_iam_policy(request=iam_policy_pb2.SetIamPolicyRequest(resource=created_policy.name, policy=iam_policy))

print("✅ Masking rule created and applied to the Analyst.")