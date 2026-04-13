#!/bin/bash
set -e

# Get script directory and change to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load configuration from .env
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo "ERROR: .env file not found. Please create one with PROJECT_ID."
    exit 1
fi

if [ -z "$PROJECT_ID" ]; then
    echo "ERROR: PROJECT_ID is not set in .env file."
    exit 1
fi

REGION="us-central1"
CLUSTER_ID="rma-cluster"
INSTANCE_ID="rma-instance-1"
SA_NAME="auth-demo-sa"
SERVICE_NAME="auth-issue-demo"

echo "--- Terraform Setup for Auth Demo ---"
echo "Using Project: $PROJECT_ID"

# Get current Cloud Run image
echo "Fetching current Cloud Run image..."
IMAGE=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(spec.template.spec.containers[0].image)" 2>/dev/null || true)

if [ -z "$IMAGE" ]; then
    echo "WARNING: Could not find existing Cloud Run service image."
    echo "Using a placeholder image (gcr.io/cloudrun/hello) for initial Terraform apply."
    IMAGE="gcr.io/cloudrun/hello"
fi

echo "Found Image: $IMAGE"

cd terraform

# Initialize Terraform
echo "Initializing Terraform..."
terraform init

echo "Formatting Terraform files..."
terraform fmt

echo "Validating Terraform configuration..."
terraform validate

echo "------------------------------------------------"
echo "Applying changes..."
echo "------------------------------------------------"

terraform apply -var="project_id=$PROJECT_ID" -var="cloud_run_image=$IMAGE" -auto-approve

echo "------------------------------------------------"
echo "Building and deploying updated Cloud Run service..."
echo "------------------------------------------------"

gcloud run deploy $SERVICE_NAME \
  --source ../auth_issue_demo \
  --region $REGION \
  --project $PROJECT_ID \
  --service-account $SA_NAME@$PROJECT_ID.iam.gserviceaccount.com \
  --quiet
