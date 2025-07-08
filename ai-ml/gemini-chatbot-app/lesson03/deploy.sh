#!/bin/bash
# Purpose: To deploy the App to Cloud Run.

# Google Vertex AI
GOOGLE_GENAI_USE_VERTEXAI=true

# Google Cloud Project
GOOGLE_CLOUD_PROJECT=go-zeroth

# Google Cloud Region
GOOGLE_CLOUD_LOCATION=europe-north1

# Cloud Run Instance Environment Variables
CLOUD_RUN_INSTANCE_ENV_VARS="GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION"

# Deploying app from source code
gcloud run deploy simple-app --source . \
  --region=$GOOGLE_CLOUD_LOCATION \
  --project=$GOOGLE_CLOUD_PROJECT \
  --set-env-vars=$CLOUD_RUN_INSTANCE_ENV_VARS \
  --allow-unauthenticated
