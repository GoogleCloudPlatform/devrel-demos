#!/usr/bin/env bash
# ==============================================================================
#  Step 12: 12_teardown_cleanup.sh - Tear down all disaggregated resources,
#            GKE cluster, and VPC networks.
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
echo " Cluster: ${CLUSTER_NAME}"
echo "===================================================="

if [[ "$1" != "-y" ]]; then
    read -p "Are you sure you want to proceed with teardown? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Teardown cancelled."
        exit 0
    fi
fi

# Derive region from ZONE
REGION=$(echo "${ZONE}" | cut -d'-' -f1-2)

# 1. Delete model server workloads (Kustomize)
if [ -d "llm-d" ]; then
  echo "Deleting TPU Model Server workloads..."
  kubectl delete -n ${NAMESPACE} -k llm-d/guides/${GUIDE_NAME}/modelserver/tpu/vllm/ --ignore-not-found || true
fi

# 2. Uninstall LLM-D Router (Helm)
echo "Uninstalling LLM-D Router..."
helm uninstall ${GUIDE_NAME} -n ${NAMESPACE} || true

# 3. Delete Namespace (this also deletes secrets, gateways, routes)
echo "Deleting Namespace ${NAMESPACE}..."
kubectl delete namespace ${NAMESPACE} --ignore-not-found || true

# 4. Delete GAIE CRDs
echo "Uninstalling Gateway API Inference Extension CRDs..."
export GAIE_VERSION="v1.5.0"
kubectl delete -k "https://github.com/kubernetes-sigs/gateway-api-inference-extension/config/crd?ref=${GAIE_VERSION}" --ignore-not-found || true

# 5. Delete GKE TPU Node Pools
echo "Deleting GKE TPU Node Pools..."
for i in {1..2}; do
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

# 6. Delete Workload Policy
echo "Deleting Workload Policy superslice-policy..."
gcloud compute resource-policies delete superslice-policy \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --quiet || true

# 7. Delete GKE Cluster
echo "Deleting GKE Cluster ${CLUSTER_NAME}..."
gcloud container clusters delete "${CLUSTER_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --quiet || true

# 8. Delete VPC Networks and Subnets
echo "Deleting VPC networks and subnetworks..."
# Delete subnets first
gcloud compute networks subnets delete "${GVNIC_NETWORK_PREFIX}-tpu" --region="${REGION}" --project="${PROJECT_ID}" --quiet || true
gcloud compute networks subnets delete "${GVNIC_NETWORK_PREFIX}-proxy" --region="${REGION}" --project="${PROJECT_ID}" --quiet || true

# Delete firewall rules
gcloud compute firewall-rules delete "${GVNIC_NETWORK_PREFIX}-allow-internal" --project="${PROJECT_ID}" --quiet || true

# Finally delete network
gcloud compute networks delete "${GVNIC_NETWORK_PREFIX}-main" --project="${PROJECT_ID}" --quiet || true

# 9. Clean up local files
echo "Cleaning up local config files..."
rm -f env.sh

echo "===================================================="
echo " TEARDOWN CLEANUP SUCCESSFULLY COMPLETED!"
echo " All resources have been purged cleanly!"
echo "===================================================="
