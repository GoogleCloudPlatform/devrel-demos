#!/bin/bash
set -e
set -x # Enable debug mode to see every command

# Ensure we are in the project root
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd "$DIR/.."
echo "Working directory: $(pwd)"

# Configuration
PROJECT_ID=${PROJECT_ID:-"daniela-genai-sandbox"}
REGION=${REGION:-"us-central1"}
REPO_NAME="tenkai-repo"
IMAGE_TAG=${IMAGE_TAG:-"latest"}
DB_INSTANCE_NAME="tenkai-db" # Cloud SQL Instance Name
BUCKET_NAME="tenkai-artifacts-${PROJECT_ID}"
DB_NAME="tenkai" # Use the specific tenkai database

# Get DB Connection Name



DB_CONNECTION_NAME=$(gcloud sql instances describe "$DB_INSTANCE_NAME" --project="$PROJECT_ID" --format='value(connectionName)')

# Load env vars from .env if present
if [ -f .env ]; then
    export $(cat .env | xargs)
fi
# Prompt for DB Password if not set
if [ -z "$DB_PASS" ]; then
    read -s -p "Enter DB Password for 'tenkai' user: " DB_PASS
    echo ""
fi

# URLs
SERVER_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/tenkai-server:$IMAGE_TAG"
WORKER_IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/tenkai-runner:$IMAGE_TAG"

echo "Deploying to Project: $PROJECT_ID"

# 1. Build and Push Images using Cloud Build
echo "--- Step 1: Building Server ---"
cat > cloudbuild_server.yaml <<'EOF'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: [ 'build', '-t', '$_IMAGE', '-f', 'Dockerfile.server', '.' ]
images:
  - '$_IMAGE'
EOF
# Use --stream-logs to see build progress in real-time
gcloud builds submit --config cloudbuild_server.yaml --substitutions _IMAGE="$SERVER_IMAGE" --project "$PROJECT_ID" .
rm -f cloudbuild_server.yaml

echo "--- Step 2: Building Runner ---"
cat > cloudbuild_runner.yaml <<'EOF'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: [ 'build', '-t', '$_IMAGE', '-f', 'Dockerfile.runner', '.' ]
images:
  - '$_IMAGE'
EOF
# Use --stream-logs to see build progress in real-time
gcloud builds submit --config cloudbuild_runner.yaml --substitutions _IMAGE="$WORKER_IMAGE" --project "$PROJECT_ID" .
rm -f cloudbuild_runner.yaml

echo "--- Step 3: Ensuring IAM Permissions ---"
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:tenkai-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.developer"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:tenkai-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:tenkai-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

echo "--- Step 5: Deploying Tenkai Server ---"
gcloud run deploy tenkai-server \
    --image "$SERVER_IMAGE" \
    --platform managed \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --allow-unauthenticated \
    --port 8080 \
    --add-cloudsql-instances "$DB_CONNECTION_NAME" \
    --add-volume "name=assets,type=cloud-storage,bucket=$BUCKET_NAME" \
    --add-volume-mount "volume=assets,mount-path=/app/assets" \
    --set-env-vars "DB_DRIVER=pgx" \
    --set-env-vars "DB_DSN=postgres://tenkai:$DB_PASS@/$DB_NAME?host=/cloudsql/$DB_CONNECTION_NAME" \
    --set-env-vars "GCS_BUCKET=$BUCKET_NAME" \
    --set-env-vars "RUNNER_IMAGE=$WORKER_IMAGE" \
    --set-env-vars "TENKAI_JOB_NAME=tenkai-runner" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
    --set-env-vars "GOOGLE_CLOUD_LOCATION=$REGION" \
    --service-account "tenkai-sa@$PROJECT_ID.iam.gserviceaccount.com"

# Get API URL
API_URL=$(gcloud run services describe tenkai-server --platform managed --region "$REGION" --project "$PROJECT_ID" --format 'value(status.url)')
echo "API URL: $API_URL"

echo "--- Step 6: Updating Runner Job Definition ---"
gcloud run jobs deploy tenkai-runner \
    --image "$WORKER_IMAGE" \
    --region "$REGION" \
    --project "$PROJECT_ID" \
    --tasks 1 \
    --max-retries 0 \
    --memory 2Gi \
    --set-cloudsql-instances "$DB_CONNECTION_NAME" \
    --add-volume "name=assets,type=cloud-storage,bucket=$BUCKET_NAME" \
    --add-volume-mount "volume=assets,mount-path=/app/assets" \
    --set-env-vars "DB_DRIVER=pgx" \
    --set-env-vars "DB_DSN=postgres://tenkai:$DB_PASS@/$DB_NAME?host=/cloudsql/$DB_CONNECTION_NAME" \
        --set-env-vars "GCS_BUCKET=$BUCKET_NAME" \
        --set-env-vars "MODE=worker" \
        --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
    --set-env-vars "GOOGLE_CLOUD_LOCATION=$REGION" \
    --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY" \
    --service-account "tenkai-sa@$PROJECT_ID.iam.gserviceaccount.com"

echo "--- Step 7: Deployment Complete ---"
echo "Server URL: $API_URL"
