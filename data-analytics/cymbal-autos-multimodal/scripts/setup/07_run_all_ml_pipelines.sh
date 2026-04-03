#!/bin/bash
set -e

# Source environment variables if .env exists
if [ -f ../../.env ]; then
  source ../../.env
elif [ -f .env ]; then
  source .env
fi

if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
fi

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID is not set and could not be determined."
  echo "Please run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi
if [ -z "$LOCATION" ]; then
  LOCATION="US"
fi

echo "================================================================="
echo "OPTIONAL: Running All Machine Learning SQL Pipelines sequentially"
echo "================================================================="
echo "This script executes all BigQuery SQL files to create the AI pipelines."
echo "You can also run these manually in the BigQuery UI if you prefer."

echo "------------------------------------------------"
echo "Step 3: Vision Extraction (Gemini Vision)..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/setup/03_vision_extraction.sql

echo "------------------------------------------------"
echo "Step 4: Predictive Pricing (XGBoost)..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/setup/04_predictive_pricing.sql

echo "------------------------------------------------"
echo "Step 5: Semantic Scam Detection (Embeddings + Vector Search)..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/setup/05_semantic_scam_detection.sql

echo "------------------------------------------------"
echo "Step 6: Generative Deal Scoring (AI.SCORE)..."
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/setup/06_generative_deal_score.sql

echo "================================================================="
echo "All ML pipelines executed successfully!"
echo "================================================================="
