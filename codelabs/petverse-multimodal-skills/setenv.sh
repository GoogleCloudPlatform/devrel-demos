#!/bin/bash

# Load environment variables from .env if present
if [ -f ~/.env ]; then
  source ~/.env
elif [ -f .env ]; then
  source .env
fi

export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-$(gcloud config get-value compute/region 2>/dev/null)}"
export AGY_ADC_AUTH=true
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export GOOGLE_CLOUD_QUOTA_PROJECT="$PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="global"
export AGY_CLI_DISABLE_AUTO_UPDATE=true

gcloud config set project "$PROJECT_ID" >/dev/null 2>&1
gcloud config set compute/region "$REGION" >/dev/null 2>&1

echo "Environment configured:"
echo "  PROJECT_ID: $PROJECT_ID"
echo "  REGION:     $REGION"
