#!/bin/bash
# 04b_mount_and_download.sh - Mount GCS FUSE and Download Model

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run env setup first."
    exit 1
fi

. ./env.sh

IAP_FLAG="--tunnel-through-iap"
if [ "$USE_INTERNAL_SSH_OVERRIDE" = "true" ]; then
    IAP_FLAG=""
fi

echo "===================================================="
echo " Setting up GCS FUSE and downloading model..."
echo " Bucket: gs://$BUCKET_NAME"
echo " Model: $MODEL_NAME"
echo "===================================================="

# Verify GCS bucket exists
if ! gcloud storage buckets describe "gs://$BUCKET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "Error: GCS bucket gs://$BUCKET_NAME not found. Please run 02b_create_gcs_cache.sh first."
    exit 1
fi

# Retrieve Node 1 internal IP dynamically
NODE_1_IP=$(gcloud compute instances describe dynamo-node-1 \
    --zone="$ZONE" \
    --format='get(networkInterfaces[0].networkIP)' \
    --project="$PROJECT_ID")

# Script to install and mount GCS FUSE (runs on both nodes)
MOUNT_SCRIPT=$(cat <<EOF
set -ex

# Install GCS FUSE
if ! command -v gcsfuse &> /dev/null; then
    echo "Installing GCS FUSE..."
    sudo apt-get update
    sudo apt-get install -y lsb-release gnupg curl
    export gcsFuseRepo=gcsfuse-\$(lsb_release -c -s)
    echo "deb https://packages.cloud.google.com/apt \${gcsFuseRepo} main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
    sudo apt-get update
    sudo apt-get install -y gcsfuse
fi

# Configure FUSE to allow other users (important for Docker)
sudo sed -i 's/#user_allow_other/user_allow_other/g' /etc/fuse.conf

# Create mount directory
sudo mkdir -p /data/model
sudo chown -R \$USER:\$USER /data/model

# Unmount if already mounted
sudo umount /data/model || true

# Mount the bucket
CURRENT_UID=\$(id -u)
CURRENT_GID=\$(id -g)
gcsfuse -o allow_other --uid=\$CURRENT_UID --gid=\$CURRENT_GID "$BUCKET_NAME" /data/model

# Verify mount
ls -la /data/model
EOF
)

# 1. Deploy mount script on Node 0
echo "Mounting GCS Bucket on dynamo-node-0..."
SSH_ARGS_0=""
if [ "$USE_INTERNAL_SSH_OVERRIDE" = "true" ]; then
    echo "Enabling Google Corporate Internal SSH Hostname override for Node 0..."
    SSH_ARGS_0="-- -o Hostname=nic0.dynamo-node-0.${ZONE}.c.${PROJECT_ID}.internal.gcpnode.com"
fi
gcloud compute ssh dynamo-node-0 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    $IAP_FLAG \
    --command="$MOUNT_SCRIPT" \
    $SSH_ARGS_0

# 2. Deploy mount script on Node 1
echo "Mounting GCS Bucket on dynamo-node-1..."
SSH_ARGS_1=""
if [ "$USE_INTERNAL_SSH_OVERRIDE" = "true" ]; then
    echo "Enabling Google Corporate Internal SSH Hostname override for Node 1..."
    SSH_ARGS_1="-- -o Hostname=nic0.dynamo-node-1.${ZONE}.c.${PROJECT_ID}.internal.gcpnode.com"
fi
gcloud compute ssh dynamo-node-1 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    $IAP_FLAG \
    --command="$MOUNT_SCRIPT" \
    $SSH_ARGS_1

# 3. Download model on Node 0 (since it's mounted to GCS, Node 1 will see it automatically)
DOWNLOAD_COMMANDS=$(cat <<EOF
set -ex

# Create local temporary directory for download (native write performance)
sudo mkdir -p /data/local_model

# Format and Mount the first local NVMe SSD (375 GB) for fast temporary storage
if ! mountpoint -q /data/local_model; then
    echo "Formatting and mounting NVMe SSD (/dev/nvme0n1)..."
    sudo mkfs.ext4 -F -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/nvme0n1
    sudo mount -o discard,defaults /dev/nvme0n1 /data/local_model
fi
sudo chown -R \$USER:\$USER /data/local_model

echo "Starting model download using Docker into local directory..."
sudo docker run --rm \
  -v /data/local_model:/data/model \
  -e HF_TOKEN="$HF_TOKEN" \
  -e HF_HOME=/data/model/.hf_cache \
  -e MODEL_NAME="$MODEL_NAME" \
  python:3.10-slim \
  bash -c "pip install -U huggingface_hub && pip uninstall -y hf-xet && python3 -c \"
import os
from huggingface_hub import snapshot_download
print('Starting authenticated native Python snapshot download...')
snapshot_download(
    repo_id=os.environ['MODEL_NAME'],
    local_dir='/data/model',
    token=os.environ['HF_TOKEN'],
    ignore_patterns=['*.bin', '*.pth']
)
print('Download completed successfully!')
\""

echo "Model download complete locally. Copying files to GCS FUSE mount (/data/model)..."
cp -r /data/local_model/* /data/model/

echo "Cleaning up local temporary directory..."
sudo umount /data/local_model || true
sudo rm -rf /data/local_model

echo "Contents of GCS FUSE mount (/data/model):"
ls -lh /data/model
EOF
)

echo "Triggering model download on dynamo-node-0..."
gcloud compute ssh dynamo-node-0 \
    --zone="$ZONE" \
    --project="$PROJECT_ID" \
    $IAP_FLAG \
    --command="$DOWNLOAD_COMMANDS" \
    $SSH_ARGS_0

echo "===================================================="
echo " GCS FUSE mounted on both nodes."
echo " Model downloaded successfully to GCS."
echo " Please run the next script: ./05_deploy_prefill.sh"
echo "===================================================="
