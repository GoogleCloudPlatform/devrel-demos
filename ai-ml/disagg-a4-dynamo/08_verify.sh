#!/bin/bash
# 08_verify.sh - Verify Disaggregated Serving Flow

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run env setup first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Verifying Disaggregated Serving..."
echo " Project: $PROJECT_ID"
echo " Zone: $ZONE"
echo " Served Model: $SERVED_MODEL_NAME"
echo "===================================================="

# Get public IP of Node 0
echo "Retrieving public IP of dynamo-node-0..."
NODE_0_PUBLIC_IP=$(gcloud compute instances describe dynamo-node-0 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)' \
    --project="$PROJECT_ID" || echo "")

if [ -n "$NODE_0_PUBLIC_IP" ]; then
    echo "Node 0 Public IP: $NODE_0_PUBLIC_IP"
    ENDPOINT="http://${NODE_0_PUBLIC_IP}:8000/v1/completions"
else
    echo "Could not retrieve public IP. We will run the verification curl locally on dynamo-node-0 via SSH."
    ENDPOINT="http://localhost:8000/v1/completions"
fi

VERIFY_COMMAND=$(cat <<'EOF'
set -ex
curl -s -X POST "$ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"$SERVED_MODEL_NAME\",
    \"prompt\": \"User: Explain the difference between Prefill and Decode phases in LLM inference in one paragraph.\\nAssistant:\",
    \"temperature\": 0.7,
    \"max_tokens\": 150
  }" | python3 -m json.tool
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

if [ -n "$NODE_0_PUBLIC_IP" ]; then
    echo "Sending test request to public endpoint..."
    # Try locally first, if it fails (e.g. due to firewall), fallback to SSH
    if ! eval "$VERIFY_COMMAND"; then
        echo "Public access failed (possibly due to firewall). Falling back to running curl locally on dynamo-node-0 via SSH..."
        gcloud compute ssh dynamo-node-0 \
            --zone="$ZONE" \
            --project="$PROJECT_ID" \
            $IAP_FLAG \
            --command="export ENDPOINT='http://localhost:8000/v1/completions' && export SERVED_MODEL_NAME='$SERVED_MODEL_NAME' && $VERIFY_COMMAND" \
            $SSH_ARGS
    fi
else
    gcloud compute ssh dynamo-node-0 \
        --zone="$ZONE" \
        --project="$PROJECT_ID" \
        $IAP_FLAG \
        --command="export ENDPOINT='http://localhost:8000/v1/completions' && export SERVED_MODEL_NAME='$SERVED_MODEL_NAME' && $VERIFY_COMMAND" \
        $SSH_ARGS
fi

echo ""
echo "===================================================="
echo " Verification completed."
echo " To confirm disaggregated serving (Prefill -> NIXL Transfer -> Decode):"
echo " 1. Check Prefill logs on Node 0:"
echo "    gcloud compute ssh dynamo-node-0 --zone=$ZONE $IAP_FLAG --command='sudo docker logs dynamo-prefill' $SSH_ARGS"
echo " 2. Check Decode logs on Node 1:"
echo "    gcloud compute ssh dynamo-node-1 --zone=$ZONE $IAP_FLAG --command='sudo docker logs dynamo-decode' -- -o Hostname=nic0.dynamo-node-1.${ZONE}.c.${PROJECT_ID}.internal.gcpnode.com"
echo " Please run the next script: ./09_benchmark.sh"
echo "===================================================="
