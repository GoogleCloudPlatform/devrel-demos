#!/bin/bash
set -e

# Configuration
# Robustly capture Project ID, ignoring environment noise/warnings
RAW_PROJECT=$(gcloud config get-value project)
# Extract the last valid-looking project ID (lowercase, digits, hyphens, 6-30 chars)
PROJECT_ID=$(echo "$RAW_PROJECT" | grep -oE '[a-z][a-z0-9-]{5,29}' | tail -n 1)

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Could not determine Google Cloud Project ID."
    echo "Raw output from gcloud: $RAW_PROJECT"
    exit 1
fi

REGION="us-central1"
REPO_NAME="tenkai-repo"
SERVICE_ACCOUNT="tenkai-runner@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Using Project: ${PROJECT_ID}"
echo "Region: ${REGION}"

# 1. Enable APIs
echo "Enabling APIs..."
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    iam.googleapis.com

# 2. Create Artifact Registry
echo "Creating Artifact Registry..."
if ! gcloud artifacts repositories describe ${REPO_NAME} --location=${REGION} >/dev/null 2>&1; then
    gcloud artifacts repositories create ${REPO_NAME} \
        --repository-format=docker \
        --location=${REGION} \
        --description="Tenkai Images"
fi

# 3. Create Service Account for Tenkai Runner
echo "Creating Service Account..."
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT} >/dev/null 2>&1; then
    gcloud iam service-accounts create tenkai-runner \
        --display-name="Tenkai Runner"
fi

# 4. Grant Permissions to SA
# Needs to create Cloud Run Jobs
echo "Granting permissions..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.developer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/iam.serviceAccountUser"

# 5. Allow it to write logs
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/logging.logWriter"

echo "Setup Complete!"
echo "Artifact Registry: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}"
echo "Service Account: ${SERVICE_ACCOUNT}"
