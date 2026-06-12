#!/usr/bin/env bash
# ==============================================================================
#  Step 5: 05_deploy_simple_superslicing.sh - Deploy Simple Superslicing Workload
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

echo "========================================================================"
echo " Deploying a JobSet through Kueue using super slicing with high priority"
echo " Project ID: ${PROJECT_ID}"
echo " Namespace: ${NAMESPACE}"
echo "========================================================================"

# Apply JobSet manifests
echo "Applying TPU JobSet manifests..."
kubectl apply -f kueue-jobset-simple-superslicing.yaml -n ${NAMESPACE}

echo "Waiting for JobSet to be created..."
until kubectl get jobset -n ${NAMESPACE} kueue-jobset-simple-superslicing >/dev/null 2>&1; do
  echo -n "."
  sleep 2
done
echo ""

# Get expected pods from jobset spec.parallelism (default to 1 if not set)
expected_pods=$(kubectl get jobset -n ${NAMESPACE} kueue-jobset-simple-superslicing -o jsonpath='{.spec.replicatedJobs[*].template.spec.parallelism}' 2>/dev/null || echo 1)
if [ -z "${expected_pods}" ]; then
  expected_pods=1
fi

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
wait_for_pods_ready "jobset.sigs.k8s.io/jobset-name=kueue-jobset-simple-superslicing" ${expected_pods} 600

echo "===================================================="
echo " TPU Simple Superslicing Workload deployed successfully!"
echo "===================================================="
