#!/bin/bash

# Load environment variables from .env if present
if [ -f ~/.env ]; then
  source ~/.env
elif [ -f .env ]; then
  source .env
fi

export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-$(gcloud config get-value compute/region 2>/dev/null)}"

echo "Environment configured:"
echo "  PROJECT_ID: $PROJECT_ID"
echo "  REGION:     $REGION"
