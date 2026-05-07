#!/bin/bash
# 05_deploy_prefill.sh - Deploy Frontend and Prefill Worker on Node 0

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Deploying Frontend and Prefill Worker on Node 0..."
echo " Head Node IP: $HEAD_NODE_IP"
echo " Model Path: $MODEL_PATH"
echo " Served Model: $SERVED_MODEL_NAME"
echo "===================================================="

VLLM_IMAGE="vllm/vllm-openai:gemma4-0505-cu130"

# Retrieve internal GVNIC IP dynamically on Node 0
NODE_0_IP=$(gcloud compute instances describe disagg-node-0 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].networkIP)' \
    --project="$PROJECT_ID")

SSH_COMMANDS=$(cat <<EOF
set -ex

# Clean up existing containers
sudo docker rm -f gemma4-native disagg-prefill disagg-decode disagg-frontend || true

# Launch native Prefill API Server
echo "Launching native vLLM Prefill Server..."
sudo docker run -d \
    --name disagg-prefill \
    --init \
    --net=host \
    --gpus all \
    --ipc=host \
    -v /data/model:/data/model \
    -e HF_TOKEN="$HF_TOKEN" \
    --entrypoint bash \
    "$VLLM_IMAGE" \
    -c "pip install msgpack && vllm serve /data/model --port 8001 --tensor-parallel-size 8 --max-model-len 32768 --gpu-memory-utilization 0.90 --kv-transfer-config '{\"kv_connector\":\"P2pNcclConnector\",\"kv_role\":\"kv_producer\",\"kv_ip\":\"${NODE_0_IP}\",\"kv_port\":14579}'"

# Check status
sleep 5
sudo docker ps
sudo docker logs disagg-prefill --tail 20
EOF
)

echo "SSHing into disagg-node-0 to deploy containers..."
gcloud compute ssh disagg-node-0 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="$SSH_COMMANDS"

echo "===================================================="
echo " Native Prefill Server deployed on Node 0."
echo " Please run the next script: ./06_deploy_decode.sh"
echo "===================================================="
