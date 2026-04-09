#!/bin/bash
export PATH=$PATH:/usr/local/bin:/opt/homebrew/bin:/Users/jasondavenport/google-cloud-sdk/bin
set -e

# Configuration
if [ -z "$1" ]; then
  PROJECT_ID=$(gcloud config get-value project)
  if [ -z "$PROJECT_ID" ]; then
    echo "Usage: ./scripts/setup.sh <PROJECT_ID>"
    exit 1
  fi
else
  PROJECT_ID=$1
fi

USER_EMAIL=$(gcloud config get-value account)

echo "Setting up project: $PROJECT_ID for user: $USER_EMAIL"

# APIs to enable
APIS=(
    "run.googleapis.com"
    "iam.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
    "compute.googleapis.com"
    "geminicloudassist.googleapis.com"
    "recommender.googleapis.com"
    "monitoring.googleapis.com"
    "cloudasset.googleapis.com"
    "appoptimize.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "cloudaiservices.googleapis.com"
)

echo "Enabling necessary APIs..."
for api in "${APIS[@]}"; do
    echo "Enabling $api..."
    gcloud services enable "$api" --project "$PROJECT_ID"
done

echo "Granting roles to $USER_EMAIL in project $PROJECT_ID..."

ROLES=(
  "roles/run.admin"
  "roles/iam.serviceAccountAdmin"
  "roles/iam.serviceAccountUser"
  "roles/resourcemanager.projectIamAdmin"
  "roles/cloudbuild.builds.editor"
  "roles/artifactregistry.admin"
  "roles/serviceusage.serviceUsageAdmin"
)

for ROLE in "${ROLES[@]}"; do
  echo "Adding $ROLE..."
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="user:$USER_EMAIL" \
    --role="$ROLE" \
    --condition=None > /dev/null
done

echo "------------------------------------------------"
echo "Setup Complete!"
echo "Note: It may take several minutes for APIs and roles to propagate across the GCP console."
echo "------------------------------------------------"
