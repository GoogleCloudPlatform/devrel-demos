#!/bin/bash -x

# Load variables
. ./env.sh

echo "--- Starting Kubernetes and GKE Resource Cleanup ---"

# 1. Delete LeaderWorkerSet and Helm release
kubectl delete leaderworkerset qwen-simple-anywhere-cache --ignore-not-found
helm uninstall lws --namespace lws-system 2>/dev/null
kubectl delete namespace lws-system --ignore-not-found

# 2. Delete GKE Node Pools
# Note: Usually deleting the cluster deletes the node pools, 
# but explicit deletion ensures it's gone before the cluster teardown begins.
for i in {1..8}
do
	gcloud container node-pools delete "tpu-v6e-single-$i" \
	    --cluster="${CLUSTER_NAME}" \
	    --region="${REGION}" \
	    --project="${PROJECT_ID}" --quiet

done

# 3. Delete GKE Cluster
gcloud container clusters delete "${CLUSTER_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" --quiet

echo "--- Starting IAM and Service Account Cleanup ---"

# 1. Define the full Service Account email for clarity
SA_EMAIL="tpu-reader-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# 2. Remove Storage Bucket IAM Binding
# This removes the 'objectViewer' role from the specific bucket
gcloud storage buckets remove-iam-policy-binding gs://inf-demo-model-storage \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectViewer" --quiet

# 3. Remove Workload Identity Binding
# This severs the link between the GKE KSA and the GCP SA
gcloud iam service-accounts remove-iam-policy-binding "${SA_EMAIL}" \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:${PROJECT_ID}.svc.id.goog[default/default]" --quiet

# 4. Delete the Service Account
gcloud iam service-accounts delete "${SA_EMAIL}" --project="${PROJECT_ID}" --quiet

echo "IAM cleanup complete!"

echo "--- Starting Network and Firewall Cleanup ---"

# 4. Delete Firewall Rules (Must go before the Network)
gcloud compute firewall-rules delete \
    "${GVNIC_NETWORK_PREFIX}-allow-ssh" \
    "${GVNIC_NETWORK_PREFIX}-allow-icmp" \
    "${GVNIC_NETWORK_PREFIX}-allow-internal" \
    "ray-allow-internal" \
    --project="${PROJECT_ID}" --quiet

# 5. Delete Subnets (Must go before the Network)
gcloud compute networks subnets delete "${GVNIC_NETWORK_PREFIX}-tpu" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" --quiet

gcloud compute networks subnets delete "${GVNIC_NETWORK_PREFIX}-proxy-sub" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" --quiet

gcloud compute networks subnets delete "proxy-only-subnet" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" --quiet

# 6. Finally, delete the VPC Network
gcloud compute networks delete "${GVNIC_NETWORK_PREFIX}-main" \
    --project="${PROJECT_ID}" --quiet

echo "Cleanup complete!"
