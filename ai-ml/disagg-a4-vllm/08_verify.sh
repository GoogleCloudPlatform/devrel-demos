#!/bin/bash
# 08_verify.sh - Verify Disaggregated Serving Flow

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Verifying Disaggregated Serving..."
echo " Project: $PROJECT_ID"
echo " Zone: $ZONE"
echo "===================================================="

VERIFY_COMMAND=$(cat <<'EOF'
set -ex
curl -s -X POST "http://localhost:8000/v1/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"/data/model\",
    \"prompt\": \"Explain the difference between Prefill and Decode phases in LLM inference in one paragraph.\",
    \"temperature\": 0.7,
    \"max_tokens\": 150
  }" | python3 -m json.tool
EOF
)

echo "Sending test request locally on Node 0 via SSH..."
gcloud compute ssh disagg-node-0 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    --command="$VERIFY_COMMAND" \
    -- -o Hostname=nic0.disagg-node-0.$ZONE.c.$PROJECT_ID.internal.gcpnode.com

echo ""
echo "===================================================="
echo " Verification completed."
echo " To confirm disaggregated serving (Prefill -> NCCL GVNIC Transfer -> Decode):"
echo " 1. Check Prefill logs on Node 0:"
echo "    gcloud compute ssh disagg-node-0 --zone=$ZONE --command='sudo docker logs disagg-prefill --tail 50'"
echo "    Look for: '[PyNcclConnector] Save KV layer' or similar."
echo " 2. Check Decode logs on Node 1:"
echo "    gcloud compute ssh disagg-node-1 --zone=$ZONE --command='sudo docker logs disagg-decode --tail 50'"
echo "    Look for: '[PyNcclConnector] Load KV layer' and autoregressive generation."
echo " "
echo " Please run the next script to benchmark: ./09_benchmark.sh"
echo "===================================================="
