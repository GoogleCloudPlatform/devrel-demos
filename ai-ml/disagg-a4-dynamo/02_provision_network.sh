#!/bin/bash
# 02_provision_network.sh - Network Provisioning (Optimized 9-NIC RoCE)

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run env setup first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Provisioning RoCE Network for A4 (9-NIC)..."
echo " Project: $PROJECT_ID"
echo " Region: $REGION"
echo " Zone: $ZONE"
echo " Using pre-existing 'default' network for GVNIC (nic0)"
echo "===================================================="

set -x

# 1. Create the RoCE VPC using the Zone-Specific Network Profile (MTU 8896 is automatic)
NETWORK_PROFILE="${ZONE}-vpc-roce"
echo "Using RoCE Network Profile: $NETWORK_PROFILE"

# Check if roce-network already exists to avoid errors
if ! gcloud compute networks describe roce-network --project="$PROJECT_ID" &>/dev/null; then
    gcloud compute networks create roce-network \
        --subnet-mode=custom \
        --network-profile="$NETWORK_PROFILE" \
        --project="$PROJECT_ID"
else
    echo "roce-network already exists, skipping creation."
fi

# Create 8 subnets in the RoCE VPC (one for each MRDMA NIC)
for i in {0..7}; do
    if ! gcloud compute networks subnets describe "roce-subnet-$i" --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
        gcloud compute networks subnets create "roce-subnet-$i" \
            --network=roce-network \
            --region="$REGION" \
            --range="10.10.$i.0/24" \
            --project="$PROJECT_ID"
    else
        echo "roce-subnet-$i already exists, skipping creation."
    fi
done

# 2. Create RoCE Network Firewall Policy (Regional Network Firewall Policy required for RoCE)
echo "Creating Regional Network Firewall Policy for RoCE..."
if ! gcloud compute network-firewall-policies describe roce-firewall-policy --region="$REGION" --project="$PROJECT_ID" &>/dev/null; then
    gcloud compute network-firewall-policies create roce-firewall-policy \
        --region="$REGION" \
        --policy-type=RDMA_ROCE_POLICY \
        --project="$PROJECT_ID"

    # Create stateless allow rule for all internal RoCE traffic (ingress, 0.0.0.0/0 required for RoCE)
    gcloud compute network-firewall-policies rules create 1000 \
        --firewall-policy=roce-firewall-policy \
        --firewall-policy-region="$REGION" \
        --action=allow \
        --direction=INGRESS \
        --src-ip-ranges=0.0.0.0/0 \
        --layer4-configs=all \
        --project="$PROJECT_ID"

    # Associate the policy with roce-network
    gcloud compute network-firewall-policies associations create \
        --firewall-policy=roce-firewall-policy \
        --firewall-policy-region="$REGION" \
        --network=roce-network \
        --name=roce-association \
        --project="$PROJECT_ID"
else
    echo "roce-firewall-policy already exists, skipping creation."
fi

# 3. Create standard VPC Firewall Rules for vLLM Peer-to-Peer NCCL communications on 'default' network
echo "Creating standard VPC Firewall rules for vLLM P2P socket transport..."
if ! gcloud compute firewall-rules describe default-allow-vllm-p2p --project="$PROJECT_ID" &>/dev/null; then
    gcloud compute firewall-rules create default-allow-vllm-p2p \
        --network=default \
        --allow=tcp:14579-14589,tcp:8000-8001,tcp:2379,tcp:4222 \
        --source-ranges=10.180.0.0/20 \
        --project="$PROJECT_ID"
else
    echo "default-allow-vllm-p2p firewall rule already exists, skipping..."
fi

# 4. Ensure IAP firewall rule exists for SSH access
echo "Ensuring default-allow-iap firewall rule exists..."
if ! gcloud compute firewall-rules describe default-allow-iap --project="$PROJECT_ID" &>/dev/null; then
    gcloud compute firewall-rules create default-allow-iap \
        --network=default \
        --allow=tcp:22 \
        --source-ranges=35.235.240.0/20 \
        --project="$PROJECT_ID"
else
    echo "default-allow-iap firewall rule already exists, skipping..."
fi

set +x

echo "===================================================="
echo " RoCE Networking provisioned successfully."
echo " Please run the next script: ./02b_create_gcs_cache.sh"
echo "===================================================="
