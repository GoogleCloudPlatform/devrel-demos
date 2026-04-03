#!/bin/bash

echo "================================================================="
echo "02: Loading Data to BigQuery from Cloud Storage"
echo "================================================================="
echo "This script creates the model_dev dataset and loads the raw data"
echo "hosted in your Cloud Storage bucket into native BigQuery tables."

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

USER_BUCKET="cymbal-autos-${PROJECT_ID}"

if [ -z "$DATASET_ID" ]; then
  DATASET_ID="model_dev"
fi
if [ -z "$LOCATION" ]; then
  LOCATION="US"
fi

# Ensure dataset exists
echo "Ensuring dataset $DATASET_ID exists..."
bq --location=$LOCATION mk -d \
  --project_id=$PROJECT_ID \
  $DATASET_ID 2>/dev/null || echo "Dataset $DATASET_ID already exists."

echo "------------------------------------------------"
echo "Loading synthetic_cars table into BigQuery from gs://${USER_BUCKET}/data/synthetic_car_data.csv..."
bq load \
  --source_format=CSV \
  --skip_leading_rows=1 \
  --replace \
  --schema=data/schemas/synthetic_cars_schema.json \
  $PROJECT_ID:$DATASET_ID.synthetic_cars \
  gs://${USER_BUCKET}/data/synthetic_car_data.csv

echo "------------------------------------------------"
echo "Loading vehicle_metadata table into BigQuery from gs://${USER_BUCKET}/data/vehicle_metadata_bq.jsonl..."
bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --replace \
  --schema=data/schemas/vehicle_metadata_schema.json \
  $PROJECT_ID:$DATASET_ID.vehicle_metadata \
  gs://${USER_BUCKET}/data/vehicle_metadata_bq.jsonl

echo "------------------------------------------------"
echo "Loading seller_risk_profiles table into BigQuery from gs://${USER_BUCKET}/data/seller_risk_profiles.jsonl..."
bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  --replace \
  --schema=data/schemas/seller_risk_profiles_schema.json \
  $PROJECT_ID:$DATASET_ID.seller_risk_profiles \
  gs://${USER_BUCKET}/data/seller_risk_profiles.jsonl

echo "------------------------------------------------"
echo "Updating vehicle_metadata URIs to point to your new bucket gs://${USER_BUCKET}/..."
bq query --use_legacy_sql=false \
"UPDATE \`${PROJECT_ID}.${DATASET_ID}.vehicle_metadata\`
SET images = ARRAY(
  SELECT REPLACE(uri, 'sample-data-and-media', 'cymbal-autos-${PROJECT_ID}')
  FROM UNNEST(images) AS uri
)
WHERE TRUE;"

echo "================================================================="
echo "BigQuery load complete!"
echo "================================================================="
