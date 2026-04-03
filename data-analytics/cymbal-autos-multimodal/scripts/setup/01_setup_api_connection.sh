#!/bin/bash

# ==============================================================================
# ONE-TIME SETUP SCRIPT: BigQuery ObjectRef & ML Connections
# ==============================================================================
# This script configures your Google Cloud environment so BigQuery can read
# unstructured data (images) directly from Cloud Storage using ObjectRef
# and run foundation models via Vertex AI (for the ML.PREDICT functions etc).

# Source .env for project configuration if it exists, otherwise define defaults
if [ -f ../../.env ]; then
  source ../../.env
elif [ -f .env ]; then
  source .env
fi

if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID is not set and could not be determined."
  echo "Please run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi
if [ -z "$LOCATION" ]; then
  LOCATION="US"
fi

echo -e "\n================================================================="
echo "Creating BigQuery Cloud Resource Connection (conn)..."
echo "================================================================="
# This creates a special service account that BigQuery will use to access GCS
bq mk --connection \
    --location=$LOCATION \
    --project_id=$PROJECT_ID \
    --connection_type=CLOUD_RESOURCE \
    conn 2>/dev/null || echo "Connection might already exist. Proceeding..."


echo -e "\n================================================================="
echo "Retrieving connection service account email..."
echo "================================================================="
# Extract the auto-generated service account email for the connection
SERVICE_ACCT_EMAIL=$(bq show --format=prettyjson --connection $PROJECT_ID.$LOCATION.conn | grep "serviceAccountId" | cut -d '"' -f 4)

if [ -z "$SERVICE_ACCT_EMAIL" ]; then
    echo "Error: Could not retrieve service account email for the connection."
    echo "Please check if the connection was created successfully."
    exit 1
fi
echo "Service Account: $SERVICE_ACCT_EMAIL"


echo -e "\n================================================================="
echo "Granting IAM roles to service account..."
echo "================================================================="
echo "-> Granting roles/storage.objectViewer (for ObjectRef)"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCT_EMAIL}" \
    --role="roles/storage.objectViewer" \
    --format=none

echo "-> Granting roles/aiplatform.user (for Vertex AI integration)"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCT_EMAIL}" \
    --role="roles/aiplatform.user" \
    --format=none

echo -e "\n================================================================="
echo "Waiting ~60 seconds for IAM updates to propagate..."
echo "(Otherwise, subsequent steps might fail due to cache delays)"
echo "================================================================="
sleep 60

echo -e "\nEnvironment setup complete! Your BigQuery connection is ready."
