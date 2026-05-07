#!/bin/bash
# 02_provision_network.sh - Network Provisioning (Optimized 9-NIC RoCE)

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
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

set +x

echo "===================================================="
echo " RoCE Networking provisioned successfully."
echo " Please run the next script: ./03_provision_vms.sh"
echo "===================================================="
