#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION=${GOOGLE_CLOUD_LOCATION:-"us-central1"}
REPO_NAME="godoctor-repo"

echo "Using Project: $PROJECT_ID"
echo "Using Region: $REGION"

# Enable APIs
echo "Enabling APIs..."
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com



# Create Artifact Registry
if ! gcloud artifacts repositories describe $REPO_NAME --location=$REGION &>/dev/null; then
    echo "Creating Artifact Registry repository '$REPO_NAME'..."
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="Docker repository for GoDoctor"
else
    echo "Artifact Registry repository '$REPO_NAME' already exists."
fi

echo "Setup complete."
