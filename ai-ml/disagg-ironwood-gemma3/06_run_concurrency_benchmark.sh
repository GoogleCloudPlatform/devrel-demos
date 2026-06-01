#!/usr/bin/env bash
# ==============================================================================
#  Step 5: 06_run_concurrency_benchmark.sh - Deploy stress-test GKE Benchmark Job
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh
export CONCURRENCY=32
export NUM_PROMPTS=1000

echo "===================================================="
echo " Deploying GKE Serving Stress-Test Job..."
echo " Namespace: ${NAMESPACE}"
echo " Target: http://vllm-router-service:8000"
echo " Concurrency: ${CONCURRENCY}"
echo " Total Prompts: ${NUM_PROMPTS}"
echo "===================================================="

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

# Delete old benchmark job
kubectl delete job vllm-benchmark-job -n "${NAMESPACE}" --ignore-not-found

# Deploy declarative GKE Job manifest
cat <<EOF | kubectl apply -n "${NAMESPACE}" -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: vllm-benchmark-job
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        app: vllm-benchmark
    spec:
      restartPolicy: Never
      containers:
      - name: benchmark
        image: vllm/vllm-tpu:gemma4
        imagePullPolicy: IfNotPresent
        command:
        - bash
        - -c
        - |
          echo "Downloading real ShareGPT dataset..."
          wget -q https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json -O /tmp/sharegpt.json
          
          echo "Executing GKE 8-Replica Proxy Router stress-test benchmark..."
          vllm bench serve \
            --base-url "http://vllm-router-service:8000" \
            --model "${SERVED_MODEL_NAME}" \
            --endpoint "/v1/completions" \
            --dataset-name "sharegpt" \
            --dataset-path "/tmp/sharegpt.json" \
            --request-rate inf \
            --num-prompts ${NUM_PROMPTS} \
            --max-concurrency ${CONCURRENCY} \
            --tokenizer "${SERVED_MODEL_NAME}" \
            --trust-remote-code
        env:
        - name: HF_TOKEN
          value: "${HF_TOKEN}"
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
EOF

echo "===================================================="
echo " Benchmark Job successfully deployed!"
echo " Check logs using:"
echo "   kubectl logs -n ${NAMESPACE} -l app=vllm-benchmark -f"
echo "===================================================="
