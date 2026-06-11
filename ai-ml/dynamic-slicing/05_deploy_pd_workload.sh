#!/usr/bin/env bash
# ==============================================================================
#  Step 5: 05_deploy_pd_workload.sh - Deploy TPU Prefill/Decode Workloads
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

if [ ! -d "llm-d" ]; then
    echo "Error: llm-d directory not found. Please run 03_setup_llm_d.sh first."
    exit 1
fi

echo "===================================================="
echo " Project ID: ${PROJECT_ID}"
echo " Namespace: ${NAMESPACE}"
echo " Guide Name: ${GUIDE_NAME}"
echo "===================================================="

# Apply Kustomize overlays for TPU vLLM and convert to JobSet
echo "Applying TPU Model Server manifests via Kustomize (converted to JobSet)..."
kubectl kustomize llm-d/guides/${GUIDE_NAME}/modelserver/tpu/vllm/ | python3 scratch/convert_sfs_to_jobset.py | kubectl apply -n ${NAMESPACE} -f -

echo "Waiting for Prefill JobSet to be created..."
until kubectl get jobset -n ${NAMESPACE} pd-disaggregation-tpu-vllm-prefill >/dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo ""

echo "Waiting for Decode JobSet to be created..."
until kubectl get jobset -n ${NAMESPACE} pd-disaggregation-tpu-vllm-decode >/dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo ""

wait_for_pods_ready() {
  local role=$1
  local expected_count=$2
  local timeout=$3
  local start_time=$(date +%s)
  local expected_ready_containers=$((expected_count * 2))
  
  echo "Waiting for ${role} pods to be ready (${expected_count} pods, timeout ${timeout}s)..."
  while true; do
    # Get all container ready statuses for pods of this role
    local ready_statuses=$(kubectl get pods -n ${NAMESPACE} -l llm-d.ai/role=${role} -o jsonpath='{.items[*].status.containerStatuses[*].ready}' 2>/dev/null || true)
    local ready_count=0
    for status in ${ready_statuses}; do
      if [ "${status}" = "true" ]; then
        ready_count=$((ready_count + 1))
      fi
    done
    
    if [ "${ready_count}" -eq "${expected_ready_containers}" ] && [ "${ready_count}" -gt 0 ]; then
      echo "${role} pods are ready!"
      return 0
    fi
    
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))
    if [ "${elapsed}" -gt "${timeout}" ]; then
      echo "Timeout waiting for ${role} pods to be ready!"
      return 1
    fi
    
    local pending_count=$(kubectl get pods -n ${NAMESPACE} -l llm-d.ai/role=${role} --no-headers 2>/dev/null | grep -c "Pending" || true)
    local running_count=$(kubectl get pods -n ${NAMESPACE} -l llm-d.ai/role=${role} --no-headers 2>/dev/null | grep -c "Running" || true)
    echo "Pods status: Running=${running_count}, Pending=${pending_count} | Ready containers: ${ready_count}/${expected_ready_containers} | Elapsed: ${elapsed}s"
    
    sleep 15
  done
}

echo "Waiting for Prefill pods to be ready..."
wait_for_pods_ready "prefill" 16 600

echo "Waiting for Decode pods to be ready..."
wait_for_pods_ready "decode" 16 600

echo "===================================================="
echo " TPU P/D Workloads deployed successfully!"
echo "===================================================="
echo "You can monitor the logs with:"
echo "  kubectl logs -f -l llm-d.ai/modelservice-role=prefill -c modelserver -n ${NAMESPACE}"
echo "  kubectl logs -f -l llm-d.ai/modelservice-role=decode -c modelserver -n ${NAMESPACE}"
echo "===================================================="
