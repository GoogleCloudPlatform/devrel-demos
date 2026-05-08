#!/bin/bash
set -e

# SCRIPT: 07_deploy_router.sh
# PURPOSE: Launch the centralized vLLM Router on Node 0 on port 8000
#          using the standard Mooncake HTTP routing parameters.

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
    exit 1
fi

. ./env.sh

# Retrieve Node 1 internal IP dynamically
NODE_1_IP=$(gcloud compute instances describe disagg-node-1 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].networkIP)' \
    --project="$PROJECT_ID")

echo "===================================================="
echo " Deploying Centralized vLLM Router on Node 0..."
echo " Listening Port: 8000"
echo " Prefill Target: http://localhost:8001"
echo " Decode Target: http://${NODE_1_IP}:8001"
echo "===================================================="

SSH_COMMANDS=$(cat <<EOF
set -ex

# 1. Kill any existing vllm-router process cleanly
sudo pkill vllm-router || true

# 1b. Elevate file descriptor limits to 65536 to prevent too many open files (os error 24)
ulimit -n 65536

# 2. Launch vllm-router in background on port 8000 changing metrics port to 9095
nohup bash -c "ulimit -n 65536 && exec /data/local_model/router_venv/bin/vllm-router --policy round_robin \
  --vllm-pd-disaggregation \
  --prefill http://localhost:8001 \
  --decode http://${NODE_1_IP}:8001 \
  --host 0.0.0.0 \
  --port 8000 \
  --prometheus-port 9099 \
  --kv-connector mooncake" > /tmp/vllm_router.log 2>&1 &

echo "vLLM Router successfully launched in background on Node 0!"
sleep 3
ps aux | grep vllm-router
cat /tmp/vllm_router.log | tail -n 20
EOF
)

# Build conditional SSH arguments for corporate environment compliance
SSH_ARGS=""
if [ "$USE_INTERNAL_SSH_OVERRIDE" = "true" ]; then
    echo "Enabling Google Corporate Internal SSH Hostname override..."
    SSH_ARGS="-- -o Hostname=nic0.disagg-node-0.${ZONE}.c.${PROJECT_ID}.internal.gcpnode.com"
fi

echo "SSHing into disagg-node-0 to deploy vLLM Router..."
gcloud compute ssh disagg-node-0 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="$SSH_COMMANDS" \
    $SSH_ARGS

echo "===================================================="
echo " vLLM Router successfully deployed on Node 0."
echo " Please run the next script to verify: ./08_verify.sh"
echo "===================================================="
