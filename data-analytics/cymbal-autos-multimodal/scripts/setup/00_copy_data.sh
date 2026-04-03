#!/bin/bash
set -e

echo "================================================================="
echo "00: Copying Demo Data Assets to your bucket"
echo "================================================================="
echo "This script copies the raw data (CSVs, JSONLs, Images) from the"
echo "public demonstration bucket into your personal Google Cloud Storage."

# Source environment variables if .env exists
if [ -f .env ]; then
  source .env
fi

# Get Project ID from environment or gcloud config
if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID is not set and could not be determined."
  echo "Please run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

USER_BUCKET="cymbal-autos-${PROJECT_ID}"

# Create the bucket if it doesn't exist
if ! gcloud storage ls gs://$USER_BUCKET > /dev/null 2>&1; then
  echo "Creating bucket gs://$USER_BUCKET..."
  gcloud storage buckets create gs://$USER_BUCKET --location=US
else
  echo "Bucket gs://$USER_BUCKET already exists."
fi

# Make the bucket publicly readable for frontend image rendering
echo "Making bucket gs://$USER_BUCKET publicly readable..."
gsutil iam ch allUsers:objectViewer "gs://$USER_BUCKET"

SOURCE_BUCKET="gs://sample-data-and-media/cymbal-autos"

echo "Copying images from $SOURCE_BUCKET to gs://$USER_BUCKET..."
if ! gcloud storage cp -r $SOURCE_BUCKET/* gs://$USER_BUCKET/; then
  echo -e "\nERROR: Failed to copy data from $SOURCE_BUCKET."
  echo "Please ensure the central bucket is public or you have the requisite Viewer permissions."
  exit 1
fi

echo "Copying local dataset from workspace to gs://$USER_BUCKET/data/..."
if ! gcloud storage cp -r data/* gs://$USER_BUCKET/data/; then
  echo -e "\nERROR: Failed to copy local data to gs://$USER_BUCKET/data/."
  exit 1
fi

echo "Data copy complete!"
