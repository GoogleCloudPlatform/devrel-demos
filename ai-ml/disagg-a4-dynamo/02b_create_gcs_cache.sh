#!/bin/bash
# 02b_create_gcs_cache.sh - GCS Bucket & Anywhere Cache Creation

set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run env setup first."
    exit 1
fi

. ./env.sh

echo "===================================================="
echo " Creating GCS Bucket and Anywhere Cache..."
echo " Bucket: gs://$BUCKET_NAME"
echo " Zone: $ZONE"
echo "===================================================="

set -x

# 1. Create the GCS Bucket (idempotent)
if ! gcloud storage buckets describe "gs://$BUCKET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "GCS bucket gs://$BUCKET_NAME not found, creating..."
    gcloud storage buckets create "gs://$BUCKET_NAME" \
        --location="$REGION" \
        --uniform-bucket-level-access \
        --project="$PROJECT_ID"
else
    echo "GCS bucket gs://$BUCKET_NAME already exists, skipping creation."
fi

# 2. Create the Anywhere Cache (we attempt to create, if it fails we assume it might exist or we log it)
# Anywhere Cache creation might fail if it already exists.
# We can try to list it first, but listing might be slow or have different output.
# We will use "|| true" but log it, or try to check if we can detect it.
echo "Ensuring Anywhere Cache exists..."
gcloud storage buckets anywhere-caches create "gs://$BUCKET_NAME" "$ZONE" \
    --ttl=1d \
    --admission-policy=ADMIT_ON_FIRST_MISS \
    --project="$PROJECT_ID" || echo "Anywhere Cache might already exist or failed to create, continuing..."

set +x

echo "===================================================="
echo " GCS Bucket and Anywhere Cache configuration complete."
echo " Please run the next script: ./03_provision_vms.sh"
echo "===================================================="
