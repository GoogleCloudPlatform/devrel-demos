#!/bin/bash

echo "================================================================="
echo "TEARDOWN: Cleaning up Cymbal Autos Demo Resources"
echo "================================================================="
echo "WARNING: This will delete BigQuery datasets, Cloud Storage data,"
echo "and Cloud Run services. Press Ctrl+C within 5 seconds to abort."
sleep 5

# Source .env if it exists
if [ -f ../../.env ]; then
  source ../../.env
elif [ -f .env ]; then
  source .env
fi

# Determine PROJECT_ID and USER_BUCKET dynamically
if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID is not set and could not be determined."
  exit 1
fi

USER_BUCKET="cymbal-autos-${PROJECT_ID}"

if [ -z "$DATASET_ID" ]; then
  DATASET_ID="model_dev"
fi
if [ -z "$LOCATION" ]; then
  LOCATION="US"
fi

if [ -z "$USER_BUCKET" ]; then
  echo "Error: USER_BUCKET is not set. Cannot clean up Cloud Storage."
else
  echo -e "\n1. Emptying Google Cloud Storage Bucket ($USER_BUCKET)..."
  gcloud storage rm -r gs://${USER_BUCKET}/* 2>/dev/null || echo "Bucket already empty or doesn't exist."
fi

echo -e "\n2. Deleting Cloud Run Service (cymbal-autos-frontend)..."
gcloud run services delete cymbal-autos-frontend \
  --region us-central1 \
  --project=$PROJECT_ID \
  --quiet 2>/dev/null || echo "Cloud Run service not found."

echo -e "\n3. Removing Connection Service Account IAM bindings..."
# Attempt to get the connection SA email before we delete the connection
SERVICE_ACCT_EMAIL=$(bq show --format=prettyjson --connection "$PROJECT_ID.$LOCATION.conn" 2>/dev/null | jq -r '.serviceAccountId')

if [ ! -z "$SERVICE_ACCT_EMAIL" ]; then
    echo "Removing roles for $SERVICE_ACCT_EMAIL..."
    gcloud projects remove-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SERVICE_ACCT_EMAIL}" \
        --role="roles/storage.objectViewer" --condition=None --quiet >/dev/null 2>&1 || true
    
    gcloud projects remove-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SERVICE_ACCT_EMAIL}" \
        --role="roles/aiplatform.user" --condition=None --quiet >/dev/null 2>&1 || true
else
    echo "Connection SA not found or could not be parsed."
fi

echo -e "\n4. Deleting BigQuery Cloud Resource Connection..."
bq rm --connection --force --location=$LOCATION $PROJECT_ID.$LOCATION.conn 2>/dev/null || echo "Connection not found."

echo -e "\n5. Deleting BigQuery Dataset & All Tables ($DATASET_ID)..."
bq rm -r -f -d $PROJECT_ID:$DATASET_ID 2>/dev/null || echo "Dataset not found."

# Try to remove compute SA roles if they were added for Cloud Run builds
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
if [ ! -z "$PROJECT_NUMBER" ]; then
    COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
    echo -e "\n6. Removing Cloud Run build roles from default compute service account..."
    for ROLE in "roles/storage.admin" "roles/artifactregistry.admin" "roles/cloudbuild.builds.builder"; do
        gcloud projects remove-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:${COMPUTE_SA}" \
            --role="$ROLE" --condition=None --quiet >/dev/null 2>&1 || true
    done
fi

echo -e "\n================================================================="
echo "Teardown Complete!"
echo "Note: The Cloud Storage bucket itself was emptied but not deleted."
echo "================================================================="
