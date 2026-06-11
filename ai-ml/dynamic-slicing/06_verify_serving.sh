#!/usr/bin/env bash
# ==============================================================================
#  Step 6: 06_verify_serving.sh - Verify Gemma-3 and Llama-3 Serving APIs
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

# Helper to run curl via port-forward
verify_model() {
  local service_name=$1
  local model_path=$2
  local port=$3
  
  echo "----------------------------------------------------"
  echo " Verifying Service: ${service_name} for Model: ${model_path}"
  echo "----------------------------------------------------"
  
  # Start port-forward in background
  kubectl port-forward "svc/${service_name}" "${port}:${port}" -n "${NAMESPACE}" &
  PF_PID=$!
  
  # Clean up port-forward on exit/error
  trap 'kill $PF_PID 2>/dev/null || true' EXIT
  
  # Wait for port-forward to be ready
  echo "Waiting for port-forward on port ${port}..."
  python3 -c "
  import socket, time
  for _ in range(30):
      try:
          s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          s.connect(('127.0.0.1', ${port}))
          s.close()
          break
      except:
          time.sleep(1)
  "
  
  echo "Sending test request..."
  curl -s "http://localhost:${port}/v1/completions" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"${model_path}\",
        \"prompt\": \"The future of AI on GKE TPUs is\",
        \"max_tokens\": 20,
        \"temperature\": 0.7
      }" | python3 -m json.tool
      
  echo ""
  # Kill port-forward for this model
  kill $PF_PID 2>/dev/null || true
  trap - EXIT
}

# 1. Verify Gemma-3 Serving
verify_model "gemma3-serving-api" "${GEMMA3_MODEL_PATH}" 8000

# 2. Verify Llama-3 Serving
# We use port 8001 to avoid conflicts if anything is lingering
verify_model "llama3-serving-api" "${LLAMA3_MODEL_PATH}" 8001

echo "===================================================="
# Force a newline
echo " Verification completed!"
echo "===================================================="
