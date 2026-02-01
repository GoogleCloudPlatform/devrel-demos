#!/bin/bash
set -e

# Ensure we are in the project root
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."
echo "Working directory: $(pwd)"

# Configuration
PROJECT_ID=${PROJECT_ID:-"daniela-genai-sandbox"}

BUCKET_NAME="tenkai-artifacts-${PROJECT_ID}"

echo "Target Bucket: gs://$BUCKET_NAME"

# Verify bucket exists, if not create (idempotent-ish)
if ! gsutil ls -b "gs://$BUCKET_NAME" > /dev/null 2>&1; then
    echo "Creating bucket gs://$BUCKET_NAME..."
    gsutil mb -p "$PROJECT_ID" -l "us-central1" "gs://$BUCKET_NAME"
fi

echo "Uploading Scenarios..."
gsutil -m rsync -r scenarios "gs://$BUCKET_NAME/scenarios"

echo "Uploading Templates..."
# Upload contents of templates to gs://BUCKET/templates
gsutil -m rsync -r templates "gs://$BUCKET_NAME/templates"

echo "Assets Uploaded."


