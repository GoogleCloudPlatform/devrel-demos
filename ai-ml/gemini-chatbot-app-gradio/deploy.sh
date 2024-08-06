#!/bin/bash

# Purpose: To deploy the App to Cloud Run.

# @TODO Replace <YOUR-PROJECT-ID> with your Google Cloud Project ID
PROJECT=<YOUR-PROJECT-ID>

# Google Cloud Region
LOCATION=us-east1

# Depolying app from source code
gcloud run deploy gradio-app --source=. --port=8080 --region=$LOCATION --project=$PROJECT --allow-unauthenticated