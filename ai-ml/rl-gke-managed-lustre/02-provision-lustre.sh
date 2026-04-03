#!/bin/bash
# 02 - Script to manage Google Cloud Managed Service for Lustre instances for GPU.

. ./env.sh

# The default throughput tier logic from original script
THROUGHPUT_TIER=1000 # MBps per TiB
FILESYSTEM_NAME="lustre"

echo "Creating Lustre instance '${LUSTRE_INSTANCE_ID}' in ${ZONE}..."

# Network must be fully qualified
FULL_NETWORK_PATH="projects/${PROJECT_ID}/global/networks/${NETWORK_NAME}"

PEERING_ADDRESS_NAME="google-managed-services-${NETWORK_NAME}"

echo "Checking if Service Networking Peering address exists..."
if ! gcloud compute addresses describe "${PEERING_ADDRESS_NAME}" --global --project="${PROJECT_ID}" > /dev/null 2>&1; then
    echo "Allocating a global IP range for Google Managed Services..."
    gcloud compute addresses create "${PEERING_ADDRESS_NAME}" \
        --global \
        --purpose=VPC_PEERING \
        --prefix-length=24 \
        --network="${NETWORK_NAME}" \
        --project="${PROJECT_ID}"
fi

echo "Checking if VPC Peering is established..."
if ! gcloud services vpc-peerings list --network="${NETWORK_NAME}" --project="${PROJECT_ID}" --format="value(service)" | grep -q "servicenetworking.googleapis.com"; then
    echo "Connecting VPC to Service Networking..."
    gcloud services vpc-peerings connect \
        --service=servicenetworking.googleapis.com \
        --ranges="${PEERING_ADDRESS_NAME}" \
        --network="${NETWORK_NAME}" \
        --project="${PROJECT_ID}" || \
    (echo "Connect failed, attempting to update existing peering connection instead..." && \
     gcloud services vpc-peerings update \
        --service=servicenetworking.googleapis.com \
        --ranges="${PEERING_ADDRESS_NAME}" \
        --network="${NETWORK_NAME}" \
        --project="${PROJECT_ID}" \
        --force)
fi

gcloud lustre instances create "${LUSTRE_INSTANCE_ID}" \
    --project="${PROJECT_ID}" \
    --location="${ZONE}" \
    --capacity-gib="${LUSTRE_CAPACITY}" \
    --per-unit-storage-throughput="${THROUGHPUT_TIER}" \
    --filesystem="${FILESYSTEM_NAME}" \
    --network="${FULL_NETWORK_PATH}" \
    --gke-support-enabled \
    --async

echo "Creation initiated. Note: This can take some time to come fully online."
echo "Check status manually with: gcloud lustre instances describe ${LUSTRE_INSTANCE_ID} --project ${PROJECT_ID} --location ${ZONE} --format=\"value(state)\""
