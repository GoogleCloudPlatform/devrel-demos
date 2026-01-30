#!/bin/bash
set -e

# Configuration
PROJECT_ID="daniela-genai-sandbox"
BUCKET_NAME="${PROJECT_ID}_tenkai_artifacts"

# Verify bucket exists, if not create (idempotent-ish)
if ! gsutil ls -b "gs://$BUCKET_NAME" > /dev/null 2>&1; then
    echo "Creating bucket gs://$BUCKET_NAME..."
    gsutil mb -p "$PROJECT_ID" "gs://$BUCKET_NAME"
fi

echo "Uploading Scenarios..."
gsutil -m rsync -r scenarios "gs://$BUCKET_NAME/scenarios"

echo "Uploading Templates..."
gsutil -m rsync -r experiments/templates "gs://$BUCKET_NAME/templates"

echo "Assets Uploaded."
