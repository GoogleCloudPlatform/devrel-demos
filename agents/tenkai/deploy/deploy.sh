#!/bin/bash
set -e

# Robustly capture Project ID
RAW_PROJECT=$(gcloud config get-value project)
PROJECT_ID=$(echo "$RAW_PROJECT" | grep -oE '[a-z][a-z0-9-]{5,29}' | tail -n 1)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Could not determine Google Cloud Project ID."
    echo "Raw output from gcloud: $RAW_PROJECT"
    exit 1
fi

REGION="us-central1"
REPO_NAME="tenkai-repo"
IMAGE_NAME="tenkai-server"
IMAGE_TAG="latest"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"
SERVICE_ACCOUNT="tenkai-runner@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Building and Pushing Image to ${IMAGE_URI}..."
# Copy Dockerfile to root temporarily because gcloud builds submit prefers it in the context root
cp deploy/Dockerfile .
trap "rm Dockerfile" EXIT

# Submit build to Cloud Build
gcloud builds submit --tag ${IMAGE_URI} .

echo "Deploying Cloud Run Service (Orchestrator)..."
gcloud run deploy tenkai-server \
    --image ${IMAGE_URI} \
    --platform managed \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --allow-unauthenticated \
    --set-env-vars TENKAI_MODE=cloud \
    --set-env-vars GOOGLE_CLOUD_PROJECT=${PROJECT_ID} \
    --set-env-vars TENKAI_JOB_IMAGE=${IMAGE_URI}

# Note: We use the SAME image for the Orchestrator (Server) and the Workers (Jobs).
# When running as a Job, the entrypoint/cmd will be overridden by the Runner (orchestrator).

echo "Deployment validation..."
SERVICE_URL=$(gcloud run services describe tenkai-server --region ${REGION} --format 'value(status.url)')
echo "Tenkai Server deployed at: ${SERVICE_URL}"

# Create the Job definition (Base Job) that the orchestrator will trigger/override
echo "Creating/Updating Tenkai Worker Job..."
gcloud run jobs deploy tenkai-worker \
    --image ${IMAGE_URI} \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --set-env-vars TENKAI_MODE=worker \
    --tasks 1 \
    --max-retries 0

echo "Done! To verify, visit ${SERVICE_URL}"
