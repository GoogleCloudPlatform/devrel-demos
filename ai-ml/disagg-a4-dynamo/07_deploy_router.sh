#!/bin/bash
# 07_deploy_router.sh - Deploy Dynamo Frontend (Router) on Node 0

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run env setup first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Deploying Dynamo Frontend (Router) on Node 0..."
echo " Listening Port: 8000"
echo " etcd Endpoints: $ETCD_ENDPOINTS"
echo " NATS Server: $NATS_SERVER"
echo "===================================================="

VLLM_IMAGE="nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.2.0-deepseek-v4-cuda13-dev.3"

SSH_COMMANDS=$(cat <<EOF
set -ex

# Clean up existing frontend container if any
sudo docker rm -f dynamo-frontend || true

# Launch Dynamo Frontend
echo "Launching Dynamo Frontend..."
sudo docker run -d \
    --name dynamo-frontend \
    --init \
    --net=host \
    --ulimit nofile=65536:65536 \
    -v /data/model:/data/model \
    -e HF_TOKEN="$HF_TOKEN" \
    -e ETCD_ENDPOINTS="$ETCD_ENDPOINTS" \
    -e NATS_SERVER="$NATS_SERVER" \
    -e DYN_EVENT_PLANE="nats" \
    "$VLLM_IMAGE" \
    python3 -m dynamo.frontend \
        --http-port 8000 \
        --model-name "$SERVED_MODEL_NAME" \
        --model-path /data/model

# Check status
sleep 3
sudo docker ps
sudo docker logs dynamo-frontend --tail 20
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

echo "SSHing into dynamo-node-0 to deploy Frontend..."
gcloud compute ssh dynamo-node-0 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    $IAP_FLAG \
    --command="$SSH_COMMANDS" \
    $SSH_ARGS

echo "===================================================="
echo " Dynamo Frontend (Router) deployed on Node 0."
echo " Please run the next script: ./08_verify.sh"
echo "===================================================="
