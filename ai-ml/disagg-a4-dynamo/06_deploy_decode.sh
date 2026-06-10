#!/bin/bash
# 06_deploy_decode.sh - Deploy Decode Worker on Node 1

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run env setup first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Deploying Dynamo Decode Worker on Node 1..."
echo " Head Node IP (etcd): $HEAD_NODE_IP"
echo " Model Path: $MODEL_PATH"
echo "===================================================="

# Retrieve Node 1 internal IP dynamically
NODE_1_IP=$(gcloud compute instances describe dynamo-node-1 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].networkIP)' \
    --project="$PROJECT_ID")

VLLM_IMAGE="nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.2.0-deepseek-v4-cuda13-dev.3"

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
sudo docker rm -f dynamo-decode || true

# Dynamically discover RoCE interfaces
ROCE_DEVS=\$(ls /sys/class/net | grep '^roce' | sed 's/\$/:1/' | paste -sd, -)

# Launch Dynamo Decode Worker
echo "Launching Dynamo Decode Worker..."
sudo docker run -d \
    --name dynamo-decode \
    --init \
    --net=host \
    --gpus all \
    --privileged \
    --device /dev/infiniband \
    --ulimit nofile=65536:65536 \
    --ulimit memlock=-1:-1 \
    --ipc=host \
    -v /data/model:/data/model \
    -e HF_TOKEN="$HF_TOKEN" \
    -e ETCD_ENDPOINTS="$ETCD_ENDPOINTS" \
    -e NATS_SERVER="$NATS_SERVER" \
    -e DYN_EVENT_PLANE="nats" \
    -e DYN_SYSTEM_PORT=8001 \
    -e VLLM_NIXL_SIDE_CHANNEL_PORT=5600 \
    -e UCX_NET_DEVICES="\$ROCE_DEVS" \
    -e UCX_TLS=rc,self,sm,cuda_copy,cuda_ipc,gdr_copy \
    -e UCX_IB_GID_INDEX=3 \
    -e UCX_IB_ODP_MEM_TYPES=cuda \
    -e UCX_GGA_ODP_MEM_TYPES=cuda \
    -e UCX_REG_NONBLOCK_FALLBACK=n \
    -e UCX_WARN_UNUSED_ENV_VARS=n \
    -e UCX_RCACHE_MAX_UNRELEASED=1024 \
    -e NCCL_IB_DISABLE=0 \
    -e CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 \
    "$VLLM_IMAGE" \
    python3 -m dynamo.vllm \
        --model /data/model \
        --served-model-name "$SERVED_MODEL_NAME" \
        --tensor-parallel-size 8 \
        --max-model-len 32768 \
        --gpu-memory-utilization 0.90 \
        --is-decode-worker \
        --kv-transfer-config '{"kv_connector":"NixlConnector","kv_role":"kv_consumer"}'

# Check status
sleep 5
sudo docker ps
sudo docker logs dynamo-decode --tail 20
EOF
)

# Build conditional SSH arguments for corporate environment compliance
SSH_ARGS=""
IAP_FLAG="--tunnel-through-iap"
if [ "$USE_INTERNAL_SSH_OVERRIDE" = "true" ]; then
    echo "Enabling Google Corporate Internal SSH Hostname override for Node 1..."
    SSH_ARGS="-- -o Hostname=nic0.dynamo-node-1.${ZONE}.c.${PROJECT_ID}.internal.gcpnode.com"
    IAP_FLAG=""
fi

echo "SSHing into dynamo-node-1 to deploy Decode Worker..."
gcloud compute ssh dynamo-node-1 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    $IAP_FLAG \
    --command="$SSH_COMMANDS" \
    $SSH_ARGS

echo "===================================================="
echo " Dynamo Decode Worker deployed on Node 1."
echo " Please run the next script: ./07_deploy_router.sh"
echo "===================================================="
