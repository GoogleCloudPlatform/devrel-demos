#!/usr/bin/env bash
# ==============================================================================
#  Step 11: 11_verify_serving.sh - Verify Qwen P/D Serving API via Temp Pod
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

run_curl_pod() {
  local pod_name=$1
  local url=$2
  local data=$3
  
  # Delete pod if it already exists from a previous failed run
  kubectl delete pod "${pod_name}" -n ${NAMESPACE} --grace-period=0 --force >/dev/null 2>&1 || true

  kubectl run "${pod_name}" \
      --image=cfmanteiga/alpine-bash-curl-jq \
      --restart=Never \
      -n ${NAMESPACE} \
      -- sh -c "
for i in {1..15}; do
  res_code=\$(curl --connect-timeout 5 --max-time 10 -s -o /tmp/res.json -w \"%{http_code}\" -X POST ${url} -H 'Content-Type: application/json' -d '${data}' || echo \"000\")
  if [ \"\$res_code\" = \"200\" ]; then
    cat /tmp/res.json
    exit 0
  fi
  sleep 10
done
exit 1
" >/dev/null

  # Wait for pod to start running or complete
  local phase="Unknown"
  for _ in {1..60}; do
    phase=$(kubectl get pod "${pod_name}" -n ${NAMESPACE} -o jsonpath='{.status.phase}' 2>/dev/null || echo "Unknown")
    if [ "$phase" = "Running" ] || [ "$phase" = "Succeeded" ] || [ "$phase" = "Failed" ]; then
      break
    fi
    sleep 1
  done

  if [ "$phase" = "Pending" ] || [ "$phase" = "Unknown" ]; then
     echo "Error: Pod ${pod_name} failed to start. Current phase: ${phase}" >&2
     kubectl describe pod "${pod_name}" -n ${NAMESPACE} >&2
     kubectl delete pod "${pod_name}" -n ${NAMESPACE} --wait=false >/dev/null 2>&1
     return 1
  fi

  # Stream logs (blocks until container exits)
  local response=$(kubectl logs -f "${pod_name}" -n ${NAMESPACE} 2>/dev/null || true)
  
  # Clean up pod
  kubectl delete pod "${pod_name}" -n ${NAMESPACE} --wait=false >/dev/null 2>&1
  
  if [ -z "$response" ]; then
    echo "Error: Empty response or timeout from ${pod_name}." >&2
    return 1
  fi
  
  echo "$response"
  return 0
}

verify_serving_pod() {
  local model_path=$1
  
  echo "----------------------------------------------------"
  echo " Verifying Model: ${model_path} via Temp Pod"
  echo "----------------------------------------------------"
  
  # retrieve internal IP for the Gateway
  local ip=$(kubectl get gateway llm-d-inference-gateway -n ${NAMESPACE} -o jsonpath='{.status.addresses[0].value}')
  echo "Gateway IP: ${ip}"
  
  if [ -z "$ip" ]; then
    echo "Error: Gateway IP not found."
    return 1
  fi

  # 1. Send a completion request via a temporary pod
  echo "Sending a completion request..."
  local response
  if response=$(run_curl_pod "curl-debug-comp" "http://${ip}/v1/completions" "{\"model\": \"${model_path}\", \"prompt\": \"How are you today?\"}"); then
     echo "$response" | python3 -m json.tool || echo "Raw Response: $response"
  else
     echo "$response"
  fi

  echo ""

  # 2. Send a chat request via a temporary pod
  echo "Sending a chat request..."
  local chat_response
  if chat_response=$(run_curl_pod "curl-debug-chat" "http://${ip}/v1/chat/completions" "{\"model\": \"${model_path}\", \"messages\": [{\"role\": \"user\", \"content\": \"How are you today?\"}], \"max_tokens\": 200}"); then
     echo "$chat_response" | python3 -m json.tool || echo "Raw Response: $chat_response"
  else
     echo "$chat_response"
  fi
}

verify_serving_pod "${MODEL_NAME}"

echo "===================================================="
echo " Verification completed!"
echo "===================================================="
