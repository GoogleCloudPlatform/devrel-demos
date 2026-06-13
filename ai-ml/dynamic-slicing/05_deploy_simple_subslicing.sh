#!/usr/bin/env bash
# ==============================================================================
#  Step 5: 05_deploy_simple_subslicing.sh - Deploy Simple Subslicing Workload
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

echo "=================================================================="
echo " Deploying a Jobset through Kueue using subslicing with low priority"
echo " Project ID: ${PROJECT_ID}"
echo " Namespace: ${NAMESPACE}"
echo "=================================================================="

# Apply Jobset manifests
echo "Applying TPU Model Server manifests ..."
kubectl apply -f kueue-jobset-simple-subslicing.yaml -n ${NAMESPACE}

echo "Waiting for Jobset to be created..."
until kubectl get jobset -n ${NAMESPACE} kueue-jobset-simple-subslicing >/dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo ""

wait_for_pods_ready() {
  local selector=$1
  local expected_pods=$2
  local timeout=$3
  local start_time=$(date +%s)
  
  echo "Waiting for pods with selector '${selector}' to be Running (${expected_pods} pods, timeout ${timeout}s)..."
  while true; do
    # Get all pod phases for pods matching selector
    local pod_phases=$(kubectl get pods -n ${NAMESPACE} -l ${selector} -o jsonpath='{.items[*].status.phase}' 2>/dev/null || true)
    local running_count=0
    for phase in ${pod_phases}; do
      if [ "${phase}" = "Running" ]; then
        running_count=$((running_count + 1))
      fi
    done
    
    if [ "${running_count}" -eq "${expected_pods}" ] && [ "${running_count}" -gt 0 ]; then
      echo "Pods are Running!"
      return 0
    fi
    
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))
    if [ "${elapsed}" -gt "${timeout}" ]; then
      echo "Timeout waiting for pods to be Running!"
      return 1
    fi
    
    local pending_count=$(kubectl get pods -n ${NAMESPACE} -l ${selector} --no-headers 2>/dev/null | grep -c "Pending" || true)
    echo "Pods status: Running=${running_count}, Pending=${pending_count} | Elapsed: ${elapsed}s"
    
    sleep 15
  done
}

echo "Waiting for pods to be ready..."
# 6 replicas * size 2 = 12 pods.
wait_for_pods_ready "jobset.sigs.k8s.io/jobset-name=kueue-jobset-simple-subslicing" 12 600

echo "===================================================="
echo " TPU Simple Subslicing Workload deployed successfully!"
echo "===================================================="
