#!/bin/bash
# 06_deploy_decode.sh - Deploy Decode Worker on Node 1

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Deploying Decode Worker on Node 1..."
echo " Head Node IP (etcd): $HEAD_NODE_IP"
echo " Model Path: $MODEL_PATH"
echo "===================================================="

# Retrieve Node 1 internal IP dynamically
NODE_1_IP=$(gcloud compute instances describe disagg-node-1 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].networkIP)' \
    --project="$PROJECT_ID")

VLLM_IMAGE="vllm/vllm-openai:gemma4-0505-cu130"

SSH_COMMANDS=$(cat <<EOF
set -ex

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker not found, installing..."
    sudo apt-get update
    sudo apt-get install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker
fi

# Clean up existing containers
sudo docker rm -f gemma4-native disagg-decode || true

# Launch native Decode Server
echo "Launching native vLLM Decode Server..."
sudo docker run -d \
    --name disagg-decode \
    --init \
    --net=host \
    --gpus all \
    --ipc=host \
    -v /data/model:/data/model \
    --entrypoint bash \
    "$VLLM_IMAGE" \
    -c "pip install msgpack && vllm serve /data/model --port 8001 --tensor-parallel-size 8 --max-model-len 32768 --gpu-memory-utilization 0.90 --kv-transfer-config '{\"kv_connector\":\"P2pNcclConnector\",\"kv_role\":\"kv_consumer\",\"kv_ip\":\"${HEAD_NODE_IP}\",\"kv_port\":14579}'"

# Check status
sleep 5
sudo docker ps
sudo docker logs disagg-decode --tail 20
EOF
)

echo "SSHing into disagg-node-1 to deploy containers..."
gcloud compute ssh disagg-node-1 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="$SSH_COMMANDS" \
    -- -o Hostname=nic0.disagg-node-1.$ZONE.c.$PROJECT_ID.internal.gcpnode.com


echo "===================================================="
echo " Decode Worker deployed on Node 1."
echo " Please run the next script to deploy the router: ./07_deploy_router.sh"
echo "===================================================="
