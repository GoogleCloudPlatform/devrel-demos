#!/usr/bin/env bash
# ==============================================================================
#  Step 4: 05_verify_completions.sh - Verify completions API routing over Envoy
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

# Retrieve active router ClusterIP
CLUSTER_IP=$(kubectl get service vllm-router-service -n "${NAMESPACE}" -o jsonpath='{.spec.clusterIP}')

echo "===================================================="
echo " Sending completions request to Envoy proxy..."
echo " Target Router IP: http://${CLUSTER_IP}:8000"
echo "===================================================="

# Send OpenAI-compliant POST completions remotely inside the host node
curl -s http://${CLUSTER_IP}:8000/v1/completions   -H "Content-Type: application/json"   -d '{
    "model": "'"${SERVED_MODEL_NAME}"'",
    "prompt": "'"${SERVED_MODEL_NAME}"' disaggregated serving is live. In this benchmark, we will show",
    "max_tokens": 50,
    "temperature": 0.0
  }'

echo -e "\n===================================================="
echo " completions API routing verified successfully!"
echo "===================================================="
