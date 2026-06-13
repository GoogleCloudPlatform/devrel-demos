#!/usr/bin/env bash
# ==============================================================================
#  Step 7: 07_deploy_ss_pd_workload.sh - Deploy TPU Prefill/Decode Workloads (LWS)
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

echo "======================================================================"
echo " Deploying two LWS through Kueue using subslicing with high priority"
echo " Project ID: ${PROJECT_ID}"
echo " Namespace: ${NAMESPACE}"
echo "======================================================================"

# Create Service Account if not exists (should be created by 04, but double check)
kubectl create serviceaccount gcs-fuse-ksa -n "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

# configure role binding
gcloud storage buckets add-iam-policy-binding gs://${GCS_BUCKET_NAME} \
    --member="principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PROJECT_ID}.svc.id.goog/subject/ns/${NAMESPACE}/sa/gcs-fuse-ksa" \
    --role="roles/storage.bucketViewer"
gcloud storage buckets add-iam-policy-binding gs://$GCS_BUCKET_NAME \
    --member="principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${PROJECT_ID}.svc.id.goog/subject/ns/${NAMESPACE}/sa/gcs-fuse-ksa" \
    --role="roles/storage.objectUser"

# Apply LWS manifests
echo "Applying TPU Model Server manifests (LWS)..."
sed "s/MODEL_WEIGHT_BUCKET/${GCS_BUCKET_NAME}/g" kueue-lws-prefill-model-streamer.yaml | kubectl apply -n ${NAMESPACE} -f -
sed "s/MODEL_WEIGHT_BUCKET/${GCS_BUCKET_NAME}/g" kueue-lws-decode-model-streamer.yaml | kubectl apply -n ${NAMESPACE} -f -

echo "Waiting for Prefill LWS to be created..."
until kubectl get leaderworkerset -n ${NAMESPACE} kueue-vllm-prefill-model-streamer >/dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo ""

echo "Waiting for Decode LWS to be created..."
until kubectl get leaderworkerset -n ${NAMESPACE} kueue-vllm-decode-model-streamer >/dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo ""

wait_for_pods_ready() {
  local role=$1
  local expected_pods=$2
  local timeout=$3
  local start_time=$(date +%s)
  
  echo "Waiting for ${role} pods to be Running (${expected_pods} pods, timeout ${timeout}s)..."
  while true; do
    # Get all pod phases for pods of this role
    local pod_phases=$(kubectl get pods -n ${NAMESPACE} -l llm-d.ai/role=${role} -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    local running_count=0
    for phase in ${pod_phases}; do
      if [ "${phase}" = "Running" ]; then
        running_count=$((running_count + 1))
      fi
    done
    
    if [ "${running_count}" -eq "${expected_pods}" ] && [ "${running_count}" -gt 0 ]; then
      echo "${role} pods are Running!"
      return 0
    fi
    
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))
    if [ "${elapsed}" -gt "${timeout}" ]; then
      echo "Timeout waiting for ${role} pods to be Running!"
      return 1
    fi
    
    local pending_count=$(kubectl get pods -n ${NAMESPACE} -l llm-d.ai/role=${role} --no-headers 2>/dev/null | grep -c "Pending" || true)
    echo "Pods status: Running=${running_count}, Pending=${pending_count} | Elapsed: ${elapsed}s"
    
    sleep 15
  done
}

echo "Waiting for Prefill pods to be ready..."
# 4 replica * size 2 = 8 pods.
wait_for_pods_ready "prefill" 8 600

echo "Waiting for Decode pods to be ready..."
# 4 replica * size 2 = 8 pods.
wait_for_pods_ready "decode" 8 600

echo "===================================================="
echo " TPU P/D Workloads deployed successfully!"
echo "===================================================="
echo "You can monitor the logs with:"
echo "  kubectl logs -f kueue-vllm-prefill-model-streamer-0 -c vllm-leader -n ${NAMESPACE}"
echo "  kubectl logs -f kueue-vllm-decode-model-streamer-0 -c vllm-leader -n ${NAMESPACE}"
echo "===================================================="
