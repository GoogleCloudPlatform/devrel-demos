#!/bin/bash
set -ex

# SCRIPT: 09_benchmark.sh
# PURPOSE: Transfer and run the official vLLM stress-test benchmarks against the
#          active disaggregated served cluster on Node 0 from dev-host-dmc.

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Preparing Disaggregated serving Benchmark on devhost..."
echo " Devhost: dev-host-dmc"
echo "===================================================="

# Retrieve internal GVNIC IP dynamically on Node 0
NODE_0_IP=$(gcloud compute instances describe disagg-node-0 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].networkIP)' \
    --project="$PROJECT_ID")

# SSH Commands to download dataset and run benchmarks directly on dev-host-dmc
SSH_COMMANDS=$(cat <<EOF
set -ex

# 1. Clean up old logs and virtual envs
rm -rf /tmp/sharegpt.json ~/benchmark_venv

# Ensure system python packages are active on the devhost
if ! dpkg -s python3-pip &> /dev/null || ! dpkg -s python3-venv &> /dev/null; then
    echo "Installing missing system python packages..."
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-venv
fi

# 2. Create virtual env on massive home directory
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

# 3b. Generate a clean, verified local ShareGPT dataset programmatically to completely bypass Git LFS issues
python3 -c '
import json
data = [
    {
        "id": f"sg_{i}",
        "conversations": [
            {"from": "human", "value": "Explain the difference between Prefill and Decode phases in LLM inference in one paragraph. " * (i % 3 + 1)},
            {"from": "gpt", "value": "The prefill phase processes the entire input sequence at once to generate the KV cache, which is highly compute-bound. The decode phase generates subsequent tokens one-by-one in an autoregressive loop, which is highly memory-bandwidth bound."}
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
  --model "/data/model" \
  --endpoint "/v1/completions" \
  --dataset-name "sharegpt" \
  --dataset-path "/tmp/sharegpt.json" \
  --request-rate 80.0 \
  --num-prompts 5000 \
  --tokenizer "google/gemma-4-31B-it" \
  --trust-remote-code

EOF
)

echo "SSHing into dev-host-dmc to run benchmarks..."
gcloud compute ssh dev-host-dmc \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="$SSH_COMMANDS"

echo "===================================================="
echo " Benchmarks completed successfully on devhost!"
echo "===================================================="
