#!/bin/bash
# 03_provision_vms.sh - Provision A4 VMs with 10 NICs (Default + aw-gvnic-main)

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run ./01_set_env.sh first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Provisioning A4 VMs (a4-highgpu-8g) with 10 NICs..."
echo " Project: $PROJECT_ID"
echo " Zone: $ZONE"
echo " Reservation: ${RESERVATION_ID:-None}"
echo " Using 'default' network for nic0 (GVNIC)"
echo " Using 'aw-gvnic-main' network for nic1 (GVNIC)"
echo "===================================================="

# 1. Create compact placement policy
PLACEMENT_POLICY="disagg-placement"
echo "Creating compact placement policy: $PLACEMENT_POLICY"
gcloud compute resource-policies create group-placement "$PLACEMENT_POLICY" \
    --region="$REGION" \
    --collocation=COLLOCATED \
    --project="$PROJECT_ID" || echo "Placement policy might already exist, continuing..."

# 2. Determine Reservation Flags
RESERVATION_FLAGS=""
if [ -n "$RESERVATION_ID" ]; then
    echo "Using reservation: $RESERVATION_ID"
    RESERVATION_FLAGS="--reservation-affinity=specific --reservation=$RESERVATION_ID"
else
    echo "No reservation provided, attempting on-demand allocation."
fi

# 3. Build Network Interface Arguments
# We need:
# - 1 GVNIC interface (nic0 on default)
# - 8 MRDMA interfaces (nic1-8 on roce-subnet-0 to roce-subnet-7)
NIC_ARGS="--network-interface=network=default,subnet=default,nic-type=GVNIC"

for i in {0..7}; do
    NIC_ARGS="$NIC_ARGS --network-interface=subnet=roce-subnet-$i,nic-type=MRDMA,no-address"
done

IMAGE_FAMILY="common-cu129-ubuntu-2204-nvidia-580"

# 4. Provision Node 0 (Head / Prefill)
echo "Provisioning disagg-node-0..."
# Delete existing instance if any
gcloud compute instances delete disagg-node-0 --zone="$ZONE" --project="$PROJECT_ID" --quiet || true

set -x
gcloud compute instances create disagg-node-0 \
    --zone="$ZONE" \
    --machine-type=a4-highgpu-8g \
    --image-family="$IMAGE_FAMILY" \
    --image-project=deeplearning-platform-release \
    $NIC_ARGS \
    --accelerator=type=nvidia-b200,count=8 \
    --maintenance-policy=TERMINATE --restart-on-failure \
    --resource-policies="$PLACEMENT_POLICY" \
    $RESERVATION_FLAGS \
    --project="$PROJECT_ID"
set +x

# 5. Provision Node 1 (Decode)
echo "Provisioning disagg-node-1..."
gcloud compute instances delete disagg-node-1 --zone="$ZONE" --project="$PROJECT_ID" --quiet || true

set -x
gcloud compute instances create disagg-node-1 \
    --zone="$ZONE" \
    --machine-type=a4-highgpu-8g \
    --image-family="$IMAGE_FAMILY" \
    --image-project=deeplearning-platform-release \
    $NIC_ARGS \
    --accelerator=type=nvidia-b200,count=8 \
    --maintenance-policy=TERMINATE --restart-on-failure \
    --resource-policies="$PLACEMENT_POLICY" \
    $RESERVATION_FLAGS \
    --project="$PROJECT_ID"
set +x

echo "===================================================="
echo " A4 VMs provisioned successfully with 10 NICs."
echo " Please run the next script: ./04_setup_infrastructure.sh"
echo "===================================================="
