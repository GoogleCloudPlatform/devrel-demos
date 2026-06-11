#!/usr/bin/env bash
# ==============================================================================
#  Step 1.5: 01b_enable_apis_and_features.sh - Enable APIs and AI Zone features
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

echo "===================================================="
# Force a newline after input if this was run interactively, but it shouldn't be.
echo " Project ID: ${PROJECT_ID}"
echo " Enabling APIs and AI Zone features..."
echo "===================================================="

# 1. Enable required APIs
APIS=(
  "container.googleapis.com"
  "compute.googleapis.com"
  "iam.googleapis.com"
  "cloudresourcemanager.googleapis.com"
)

for api in "${APIS[@]}"; do
  echo "Enabling API: ${api}..."
  gcloud services enable "${api}" --project="${PROJECT_ID}"
done

# 2. Enable AI Zone features (visibility) for the project
echo "Enabling AI Zone visibility feature for project ${PROJECT_ID}..."
gcloud compute preview-features update ai-zones-visibility \
  --activation-status=enabled \
  --rollout-plan=fast-rollout \
  --project="${PROJECT_ID}" \
  --quiet

# Wait a few seconds for propagation
echo "Waiting for API propagation..."
sleep 10

echo "===================================================="
# Force a newline
echo " APIs and AI Zone features enabled successfully!"
echo "===================================================="
