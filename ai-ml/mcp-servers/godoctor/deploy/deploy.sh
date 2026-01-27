#!/bin/bash
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION=${GOOGLE_CLOUD_LOCATION:-"us-central1"}
REPO_NAME="godoctor-repo"
IMAGE_NAME="godoctor"
TAG="latest"
IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$TAG"
SERVICE_NAME="godoctor"

echo "Building Docker image..."
# Configure Docker auth for Artifact Registry
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# Force linux/amd64 for Cloud Run compatibility
docker build --platform linux/amd64 -t $IMAGE_URI .


echo "Pushing image to Artifact Registry..."
docker push $IMAGE_URI

echo "Deploying to Cloud Run..."
# Construct env vars arguments
ENV_VARS=""

# Check for GEMINI_API_KEY
if [ -n "$GEMINI_API_KEY" ]; then
    ENV_VARS="GEMINI_API_KEY=$GEMINI_API_KEY"
fi

# Check for Vertex AI config
if [ -n "$GOOGLE_GENAI_USE_VERTEXAI" ]; then
    if [ -n "$ENV_VARS" ]; then ENV_VARS="$ENV_VARS,"; fi
    ENV_VARS="${ENV_VARS}GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI"
    
    # Also pass project/location if using Vertex
    if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
         ENV_VARS="${ENV_VARS},GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
    else
         ENV_VARS="${ENV_VARS},GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
    fi
    
    if [ -n "$GOOGLE_CLOUD_LOCATION" ]; then
         ENV_VARS="${ENV_VARS},GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION"
    else
         ENV_VARS="${ENV_VARS},GOOGLE_CLOUD_LOCATION=$REGION"
    fi
fi

# Build the deployment command
DEPLOY_CMD=(gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URI" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated)

if [ -n "$ENV_VARS" ]; then
    DEPLOY_CMD+=(--set-env-vars "$ENV_VARS")
fi

echo "Running deployment..."
"${DEPLOY_CMD[@]}"

echo "Deployment complete."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"
echo "SSE Endpoint: $SERVICE_URL/sse"
