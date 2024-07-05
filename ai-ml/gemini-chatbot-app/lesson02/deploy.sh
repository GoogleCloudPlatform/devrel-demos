#!/bin/bash

# Purpose: To deploy the App to Cloud Run.

# Google Cloud Project
PROJECT=my-cloud-project

# Google Cloud Region
LOCATION=europe-north1

# Depolying app from source code
gcloud run deploy simple-app --source . --region=$LOCATION --project=$PROJECT --allow-unauthenticated
