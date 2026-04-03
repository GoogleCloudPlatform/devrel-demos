import os
from google.cloud import datacatalog_v1
from google.iam.v1 import iam_policy_pb2

project_id = os.environ.get("PROJECT_ID")
region = os.environ.get("REGION", "us-central1")
manager_email = os.environ.get("EMAIL_MANAGER")
current_user = os.environ.get("CURRENT_USER")

# 1. Lookup the Policy Tag ID
catalog_client = datacatalog_v1.PolicyTagManagerClient()
parent_loc = f"projects/{project_id}/locations/{region}"

taxonomies = catalog_client.list_taxonomies(parent=parent_loc)
taxonomy_id = next((t.name for t in taxonomies if t.display_name == "BusinessCritical"), None)
policy_tags = catalog_client.list_policy_tags(parent=taxonomy_id)
policy_tag_id = next((p.name for p in policy_tags if p.display_name == "RestrictedFinancial"), None)

# 2. Grant original data read access
iam_req = iam_policy_pb2.GetIamPolicyRequest(resource=policy_tag_id)
iam_policy = catalog_client.get_iam_policy(request=iam_req)

iam_policy.bindings.add(
    role="roles/datacatalog.categoryFineGrainedReader",
    members=[f"serviceAccount:{manager_email}", f"user:{current_user}"]
)
catalog_client.set_iam_policy(request=iam_policy_pb2.SetIamPolicyRequest(resource=policy_tag_id, policy=iam_policy))

print("✅ Fine-Grained Reader access granted to Manager and You.")