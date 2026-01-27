#!/bin/bash
set -e

# Configuration
PROJECT_ID=$(gcloud config get-value project)
REGION=${GOOGLE_CLOUD_LOCATION:-"us-central1"}
REPO_NAME="godoctor-repo"
IMAGE_NAME="godoctor"
TAG="latest"
IMAGE_URI="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$TAG"
SERVICE_NAME="godoctor"
SECRET_NAME="GEMINI_API_KEY"

# Usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --with-gemini    Deploy with Gemini API support (requires '$SECRET_NAME' in Secret Manager)"
    echo "  --with-vertex    Deploy with Vertex AI support (uses project/location from gcloud config)"
    echo "  --help           Show this help message"
    echo ""
    echo "Note: If no AI flags are provided, godoctor will run without the code_review tool."
    exit 1
}

# Parse arguments
DEPLOY_MODE="standard"
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --with-gemini) DEPLOY_MODE="gemini"; shift ;;
        --with-vertex) DEPLOY_MODE="vertex"; shift ;;
        --help) usage ;;
        *) echo "Unknown parameter: $1"; usage ;;
    esac
done

echo "Deployment Mode: $DEPLOY_MODE"
echo "Project: $PROJECT_ID, Region: $REGION"

echo "Building and pushing Docker image using Cloud Build..."
# Using Cloud Build avoids dependency on local Docker installation
gcloud builds submit --tag "$IMAGE_URI" .

# Build the deployment command
DEPLOY_CMD=(gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_URI" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated)

# Handle deployment modes
case $DEPLOY_MODE in
    gemini)
        echo "Configuring Gemini API support via Secret Manager..."
        # Verify secret exists
        if ! gcloud secrets describe "$SECRET_NAME" &>/dev/null; then
            echo "ERROR: Secret '$SECRET_NAME' not found in Secret Manager."
            echo "Please create it first: echo -n 'your-api-key' | gcloud secrets create $SECRET_NAME --data-file=-"
            exit 1
        fi
        DEPLOY_CMD+=(--set-secrets "GEMINI_API_KEY=$SECRET_NAME:latest")
        ;;
    vertex)
        echo "Configuring Vertex AI support..."
        VARS="GOOGLE_GENAI_USE_VERTEXAI=true"
        VARS="$VARS,GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
        VARS="$VARS,GOOGLE_CLOUD_LOCATION=$REGION"
        DEPLOY_CMD+=(--set-env-vars "$VARS")
        ;;
    *)
        echo "Running in standard mode (AI features disabled)..."
        ;;
esac

echo "Running deployment..."
"${DEPLOY_CMD[@]}"

echo "Deployment complete."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"
echo "MCP Endpoint (Streamable HTTP): $SERVICE_URL"


