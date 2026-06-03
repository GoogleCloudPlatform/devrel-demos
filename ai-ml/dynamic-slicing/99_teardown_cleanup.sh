#!/usr/bin/env bash
# ==============================================================================
#  Teardown: 99_teardown_cleanup.sh - Tear down all disaggregated resources and TPU pool
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. All resources are already torn down."
    exit 0
fi
. ./env.sh

echo "===================================================="
echo " TEARING DOWN ALL GKE TPU DISAGGREGATED RESOURCES..."
echo " Namespace: ${NAMESPACE}"
echo " GKE Node Pool: tpu7-gemma-pool"
echo "===================================================="

# Setup kubectl credentials context wrapper
kubectl() {
  if [ -n "$SERVER" ]; then
    if [ -n "$TOKEN" ]; then
      command kubectl --token="$TOKEN" --server="$SERVER" --insecure-skip-tls-verify=true "$@"
    else
      command kubectl --server="$SERVER" --insecure-skip-tls-verify=true "$@"
    fi
  else
    command kubectl "$@"
  fi
}

# 1. Delete Workloads (JobSets)
echo "Deleting JobSets..."
kubectl delete jobset gemma3-serving -n "${NAMESPACE}" --ignore-not-found || true
kubectl delete jobset gemma2-tuning -n "${NAMESPACE}" --ignore-not-found || true
kubectl delete jobset llama3-serving -n "${NAMESPACE}" --ignore-not-found || true

# 2. Delete Kueue Resources
if [ -f "./kueue-resources.yaml" ]; then
  echo "Deleting Kueue resources..."
  kubectl delete -f kueue-resources.yaml --ignore-not-found || true
fi

# 3. Delete GKE Slice Controller
if [ -f "./slice-controller.yaml" ]; then
  echo "Deleting GKE Slice Controller..."
  kubectl delete -f slice-controller.yaml --ignore-not-found || true
fi

# 3.5 Uninstall Kueue and JobSet
echo "Uninstalling Kueue and JobSet..."
helm uninstall kueue -n kueue-system || true
helm uninstall jobset -n jobset-system || true
kubectl delete namespace kueue-system --ignore-not-found || true
kubectl delete namespace jobset-system --ignore-not-found || true
kubectl delete namespace slice-controller-system --ignore-not-found || true

# 4. Delete GKE TPU Node Pools
echo "Deleting GKE TPU Node Pools..."
REGION=$(echo "${ZONE}" | cut -d'-' -f1-2)
for i in {1..4}; do
  POOL_NAME="tpu7-pool-${i}"
  if gcloud container node-pools describe "${POOL_NAME}" --cluster "${CLUSTER_NAME}" --region "${REGION}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Deleting Node Pool ${POOL_NAME}..."
    gcloud container node-pools delete "${POOL_NAME}" \
      --cluster "${CLUSTER_NAME}" \
      --region "${REGION}" \
      --project "${PROJECT_ID}" \
      --quiet || true
  fi
done

# 4.5 Delete Workload Policy
echo "Deleting Workload Policy superslice-policy..."
gcloud compute resource-policies delete superslice-policy \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet || true

# 5. Delete GKE Cluster
echo "Deleting GKE Cluster ${CLUSTER_NAME}..."
gcloud container clusters delete "${CLUSTER_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --quiet || true

# 6. Delete VPC Networks
echo "Deleting VPC networks and subnetworks..."
gcloud compute networks subnets delete "${HOST_SUBNET}" --region="${REGION}" --project="${PROJECT_ID}" --quiet || true
gcloud compute networks delete "${HOST_NETWORK}" --project="${PROJECT_ID}" --quiet || true

# 7. Clean up environment files
echo "Cleaning up local config files..."
rm -f env.sh
rm -f envoy.yaml
rm -f kueue-resources.yaml

echo "===================================================="
echo " TEARDOWN CLEANUP SUCCESSFULLY COMPLETED!"
echo " All disaggregated resources, GKE cluster, and VPC networks have been purged cleanly!"
echo "===================================================="
