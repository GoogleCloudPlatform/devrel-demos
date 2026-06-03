#!/usr/bin/env bash
# ==============================================================================
#  Step 7: 07_monitor_tuning.sh - Monitor Gemma-2 Fine-Tuning Workload
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

# Setup kubectl context wrapper
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

echo "===================================================="
# Force a newline
echo " Monitoring Gemma-2 Fine-Tuning Job..."
echo " Namespace: ${NAMESPACE}"
echo "===================================================="

# 1. Check JobSet status
echo "JobSet Status:"
kubectl get jobset gemma2-tuning -n "${NAMESPACE}"
echo ""

# 2. Get Pods
echo "Pods associated with tuning job:"
kubectl get pods -n "${NAMESPACE}" -l jobset.x-k8s.io/jobset-name=gemma2-tuning
echo ""

# 3. Print logs from Pod 0
POD_NAME=$(kubectl get pods -n "${NAMESPACE}" -l jobset.x-k8s.io/jobset-name=gemma2-tuning,jobset.x-k8s.io/pod-index=0 -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

if [ -n "${POD_NAME}" ]; then
  echo "Recent logs from leader pod ${POD_NAME}:"
  echo "----------------------------------------------------"
  kubectl logs "${POD_NAME}" -n "${NAMESPACE}" --tail=50
  echo "----------------------------------------------------"
  echo ""
  echo "To stream all logs, run:"
  echo "  kubectl logs ${POD_NAME} -n ${NAMESPACE} -f"
else
  echo "No pods found yet. The job might be queued in Kueue."
  echo "Check workload status:"
  kubectl describe workload -l jobset.x-k8s.io/jobset-name=gemma2-tuning -n "${NAMESPACE}"
fi

echo "===================================================="
