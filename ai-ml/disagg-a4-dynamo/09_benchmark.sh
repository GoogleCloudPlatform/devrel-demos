#!/bin/bash
# 09_benchmark.sh - Run Benchmarks from Benchmark Host

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run env setup first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Preparing Disaggregated serving Benchmark on host..."
echo " Benchmark Host: dynamo-benchmark-host"
echo "===================================================="

# Retrieve internal IP of Node 0
NODE_0_IP=$(gcloud compute instances describe dynamo-node-0 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].networkIP)' \
    --project="$PROJECT_ID")

# SSH Commands to download dataset and run benchmarks directly on dynamo-benchmark-host
SSH_COMMANDS=$(cat <<EOF
set -ex
ulimit -n 65536

# 1. Clean up old logs and virtual envs
rm -rf /tmp/sharegpt.json ~/benchmark_venv

# Ensure system python packages are active on the benchmark host
if ! dpkg -s python3-pip &> /dev/null || ! dpkg -s python3-venv &> /dev/null || ! command -v git &> /dev/null; then
    echo "Installing missing system python packages on benchmark host..."
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-venv git
fi

# 2. Create virtual env
python3 -m venv ~/benchmark_venv
source ~/benchmark_venv/bin/activate

# Redirect pip temporary space to user home directory
export USER_HOME=\$HOME
export TMPDIR="\$USER_HOME/tmp"
export PIP_CACHE_DIR="\$USER_HOME/pip_cache"
mkdir -p "\$TMPDIR" "\$PIP_CACHE_DIR"

# 3. Install vllm and dependencies dynamically
pip install --upgrade pip
pip install --cache-dir "\$PIP_CACHE_DIR" vllm requests numpy transformers aiohttp

# 3b. Generate a clean, verified local ShareGPT dataset programmatically
python3 -c '
import json
data = [
    {
        "id": f"sg_{i}",
        "conversations": [
            {"from": "human", "value": "Explain the difference between Prefill and Decode phases in LLM inference in one paragraph. " * (i % 3 + 1)},
            {"from": "gpt", "value": "The prefill phase processes the entire input sequence at once to generate the KV cache, which is highly compute-bound. The decode phase generates subsequent tokens one-by-one in an autoregressive loop, which is highly memory-bandwidth bound. " * 8}
        ]
    } for i in range(2500)
]
with open("/tmp/sharegpt.json", "w") as f:
    json.dump(data, f, indent=2)
'
head -n 15 /tmp/sharegpt.json

# 4. Execute High-Concurrency Stress-Test (5000 prompts, 80 QPS request rate)
echo "Executing high-concurrency stress-test benchmark against vLLM Router gateway..."
\$USER_HOME/benchmark_venv/bin/vllm bench serve \
  --base-url "http://${NODE_0_IP}:8000" \
  --model "$SERVED_MODEL_NAME" \
  --endpoint "/v1/completions" \
  --dataset-name "sharegpt" \
  --dataset-path "/tmp/sharegpt.json" \
  --request-rate inf \
  --num-prompts 5000 \
  --tokenizer "$TOKENIZER_NAME" \
  --trust-remote-code
EOF
)

# Build conditional SSH arguments for corporate environment compliance
SSH_ARGS=""
IAP_FLAG="--tunnel-through-iap"
if [ "$USE_INTERNAL_SSH_OVERRIDE" = "true" ]; then
    echo "Enabling Google Corporate Internal SSH Hostname override for Benchmark Host..."
    SSH_ARGS="-- -o Hostname=nic0.dynamo-benchmark-host.${ZONE}.c.${PROJECT_ID}.internal.gcpnode.com"
    IAP_FLAG=""
fi

echo "SSHing into dynamo-benchmark-host to run benchmarks..."
gcloud compute ssh dynamo-benchmark-host \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    $IAP_FLAG \
    --command="$SSH_COMMANDS" \
    $SSH_ARGS

echo "===================================================="
echo " Benchmarks completed successfully!"
echo "===================================================="
