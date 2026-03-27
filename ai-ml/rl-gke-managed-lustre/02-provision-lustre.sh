#!/bin/bash
# 02 - Script to manage Google Cloud Managed Service for Lustre instances for GPU.

. ./env.sh

# The default throughput tier logic from original script
THROUGHPUT_TIER=1000 # MBps per TiB
FILESYSTEM_NAME="lustre"

echo "Creating Lustre instance '${LUSTRE_INSTANCE_ID}' in ${ZONE}..."

# Network must be fully qualified
FULL_NETWORK_PATH="projects/${PROJECT_ID}/global/networks/${NETWORK_NAME}"

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
