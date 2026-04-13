#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: ./destroy.sh <PROJECT_ID>"
  exit 1
fi

PROJECT_ID=$1
REGION="us-central1"

echo "Using Project ID: $PROJECT_ID"

# Determine the directory of the script for reliable paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Navigate to terraform directory
cd "$PROJECT_ROOT/terraform"

echo "Destroying Infrastructure..."

# Initialize and Destroy Infrastructure
terraform init
terraform destroy -auto-approve \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="backend_image=gcr.io/$PROJECT_ID/two-tier-backend" \
  -var="frontend_image=gcr.io/$PROJECT_ID/two-tier-frontend"

echo "------------------------------------------------"
echo "Destruction Complete!"
echo "------------------------------------------------"
