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

# 1. Delete benchmark jobs
echo "Deleting benchmark jobs..."
kubectl delete job vllm-benchmark-job -n "${NAMESPACE}" --ignore-not-found || true

# 2. Delete Envoy load balancer proxy resources
echo "Deleting Envoy proxy load balancer deployment, service and ConfigMap..."
kubectl delete deployment envoy-router -n "${NAMESPACE}" --ignore-not-found || true
kubectl delete service vllm-router-service -n "${NAMESPACE}" --ignore-not-found || true
kubectl delete configmap envoy-config -n "${NAMESPACE}" --ignore-not-found || true

# 3. Delete JAX prefill/decode serving deployments and headless services
echo "Deleting Prefill and Decode Deployments and headless services..."
kubectl delete deployment vllm-prefill -n "${NAMESPACE}" --ignore-not-found || true
kubectl delete service vllm-prefill-service -n "${NAMESPACE}" --ignore-not-found || true
kubectl delete deployment vllm-decode -n "${NAMESPACE}" --ignore-not-found || true
kubectl delete service vllm-decode-service -n "${NAMESPACE}" --ignore-not-found || true
kubectl delete ResourceClaimTemplate tpu-netdev-claim-template -n "${NAMESPACE}" --ignore-not-found || true

# 4. Delete GKE TPU Node Pool to release reservation chips cleanly!
echo "Deleting GKE TPU Node Pool tpu7-gemma-pool..."
REGION=$(echo "${ZONE}" | cut -d'-' -f1-2)
gcloud container node-pools delete tpu7-gemma-pool \
  --cluster "${CLUSTER_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
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

echo "===================================================="
echo " TEARDOWN CLEANUP SUCCESSFULLY COMPLETED!"
echo " All disaggregated resources, GKE cluster, and VPC networks have been purged cleanly!"
echo "===================================================="
