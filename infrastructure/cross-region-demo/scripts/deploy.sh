#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: ./deploy.sh <PROJECT_ID>"
  exit 1
fi

PROJECT_ID=$1
REGION="us-central1"

echo "Using Project ID: $PROJECT_ID"

# Build images using Google Cloud Build (no local Docker needed)
echo "Building Backend Image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/two-tier-backend ./backend --project $PROJECT_ID

echo "Building Frontend Image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/two-tier-frontend ./frontend --project $PROJECT_ID

# Generate a unique revision ID to force a new Cloud Run revision
REVISION_ID=$(date +%s)
echo "Revision ID: $REVISION_ID"

# Deploy Infrastructure
cd terraform
terraform init
terraform apply -auto-approve \
  -var="project_id=$PROJECT_ID" \
  -var="region=$REGION" \
  -var="backend_image=gcr.io/$PROJECT_ID/two-tier-backend" \
  -var="frontend_image=gcr.io/$PROJECT_ID/two-tier-frontend" \
  -var="revision_id=$REVISION_ID"

FRONTEND_URL=$(terraform output -raw frontend_url)
echo "------------------------------------------------"
echo "Deployment Complete!"
echo "Frontend URL: $FRONTEND_URL"
echo "------------------------------------------------"
