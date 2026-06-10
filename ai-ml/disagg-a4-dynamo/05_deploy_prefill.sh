#!/bin/bash
# 05_deploy_prefill.sh - Deploy Prefill Worker on Node 0

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run env setup first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Deploying Dynamo Prefill Worker on Node 0..."
echo " Head Node IP (etcd): $HEAD_NODE_IP"
echo " Model Path: $MODEL_PATH"
echo " Served Model: $SERVED_MODEL_NAME"
echo "===================================================="

VLLM_IMAGE="nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.2.0-deepseek-v4-cuda13-dev.3"

SSH_COMMANDS=$(cat <<EOF
set -ex

# Clean up existing containers
sudo docker rm -f dynamo-prefill dynamo-decode dynamo-frontend || true

# Dynamically discover RoCE interfaces
ROCE_DEVS=\$(ls /sys/class/net | grep '^roce' | sed 's/\$/:1/' | paste -sd, -)

# Launch Dynamo Prefill Worker
echo "Launching Dynamo Prefill Worker..."
sudo docker run -d \
    --name dynamo-prefill \
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
        --is-prefill-worker \
        --kv-events-config '{"enable_kv_cache_events": true}' \
        --kv-transfer-config '{"kv_connector":"NixlConnector","kv_role":"kv_producer"}'

# Check status
sleep 5
sudo docker ps
sudo docker logs dynamo-prefill --tail 20
EOF
)

# Build conditional SSH arguments for corporate environment compliance
SSH_ARGS=""
IAP_FLAG="--tunnel-through-iap"
if [ "$USE_INTERNAL_SSH_OVERRIDE" = "true" ]; then
    echo "Enabling Google Corporate Internal SSH Hostname override..."
    SSH_ARGS="-- -o Hostname=nic0.dynamo-node-0.${ZONE}.c.${PROJECT_ID}.internal.gcpnode.com"
    IAP_FLAG=""
fi

echo "SSHing into dynamo-node-0 to deploy Prefill Worker..."
gcloud compute ssh dynamo-node-0 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    $IAP_FLAG \
    --command="$SSH_COMMANDS" \
    $SSH_ARGS

echo "===================================================="
echo " Dynamo Prefill Worker deployed on Node 0."
echo " Please run the next script: ./06_deploy_decode.sh"
echo "===================================================="
