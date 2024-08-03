#!/bin/bash

# Purpose: To deploy the App to Cloud Run.

# Google Cloud Project
PROJECT=emanuel-ai

# Google Cloud Region
LOCATION=us-east1

# Depolying app from source code
gcloud run deploy gradio-app --source=. --port=8080 --region=$LOCATION --project=$PROJECT --allow-unauthenticated