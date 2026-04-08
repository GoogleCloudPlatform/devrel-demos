#!/bin/bash
# setup_env.sh
# Prepares the GCP environment for the Event-Driven Data Agent

cd "$(dirname "$0")"

# -------------------------------------------------------------
# Configuration Variables
# -------------------------------------------------------------
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"
export DATASET_NAME="cymbal_bank"

# Set the active project
gcloud config set project $PROJECT_ID

echo "Setting up environment for project: $PROJECT_ID in region: $REGION"

# -------------------------------------------------------------
# 1. Enable APIs
# -------------------------------------------------------------
echo "Enabling necessary APIs..."
gcloud services enable \
    pubsub.googleapis.com \
    bigquery.googleapis.com \
    aiplatform.googleapis.com \
    cloudresourcemanager.googleapis.com \
    iam.googleapis.com

# Create a Cloud Storage bucket for ADK staging
gcloud storage buckets create gs://$PROJECT_ID-adk-staging --location=$REGION || true

# -------------------------------------------------------------
# 2. Configure BigQuery Data
# -------------------------------------------------------------
echo "Configuring BigQuery data..."

# Create dataset
bq mk --dataset ${PROJECT_ID}:${DATASET_NAME} || true

# Load customer_profiles table from local CSV
echo "Loading customer_profiles data into BigQuery..."

bq load \
  --autodetect \
  --replace \
  --source_format=CSV \
  ${PROJECT_ID}:${DATASET_NAME}.customer_profiles \
  customer_profiles.csv

# Create an empty retail_transactions table with schema
echo "Creating retail_transactions table..."
bq mk \
  -t \
  --schema "transaction_id:STRING,transaction_time:TIMESTAMP,user_id:STRING,amount:FLOAT,merchant_name:STRING,merchant_category_code:STRING,location_country:STRING,is_international:BOOLEAN,is_trusted_device:BOOLEAN" \
  ${PROJECT_ID}:${DATASET_NAME}.retail_transactions || true

# --- Load some historical analysis data into the retail_transactions table ---
echo "Generating historical transaction data locally..."
python load_historical_data.py

echo "Loading historical data into BigQuery..."
bq load \
  --source_format=NEWLINE_DELIMITED_JSON \
  ${PROJECT_ID}:${DATASET_NAME}.retail_transactions \
  historical_events.json \
  transaction_id:STRING,transaction_time:TIMESTAMP,user_id:STRING,amount:FLOAT,merchant_name:STRING,merchant_category_code:STRING,location_country:STRING,is_international:BOOLEAN,is_trusted_device:BOOLEAN

echo "Cleaning up local file..."
rm historical_events.json

# Create an empty agent_decisions table with schema for explicit agent logging
echo "Creating agent_decisions table..."
bq mk \
  -t \
  --schema "session_id:STRING,timestamp:TIMESTAMP,app_name:STRING,user_id:STRING,merchant:STRING,decision:STRING,summary:STRING" \
  ${PROJECT_ID}:${DATASET_NAME}.agent_decisions || true

# Configure Continuous Query Environment
echo "Configuring Continuous Query Environment..."

# Create an Enterprise reservation for continuous queries with 0 baseline slots but autoscaling up to 50 slots
bq mk \
  --project_id=$PROJECT_ID \
  --location=US \
  --reservation \
  --slots=0 \
  --autoscale_max_slots=50 \
  --ignore_idle_slots=false \
  --edition=ENTERPRISE \
  my-continuous-reservation || true

# Assign the project to use this reservation for continuous queries
bq mk \
  --project_id=$PROJECT_ID \
  --location=US \
  --reservation_assignment \
  --reservation_id=my-continuous-reservation \
  --assignee_id=$PROJECT_ID \
  --job_type=CONTINUOUS \
  --assignee_type=PROJECT || true

# 3. Configure IAM Permissions
echo "Configuring IAM permissions..."

export SA_NAME="adk-agent-sa"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Creating Service Account: $SA_EMAIL"
gcloud iam service-accounts create $SA_NAME \
    --description="Service Account for ADK Agent" \
    --display-name="ADK Agent SA" 2>/dev/null || true

echo "Binding roles/aiplatform.admin..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.admin" > /dev/null

echo "Binding roles/bigquery.dataEditor..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.dataEditor" > /dev/null

echo "Binding roles/bigquery.user..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.user" > /dev/null

echo "Binding roles/serviceusage.serviceUsageConsumer..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/serviceusage.serviceUsageConsumer" > /dev/null

echo "Binding roles/pubsub.publisher..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/pubsub.publisher" > /dev/null

echo "Binding roles/pubsub.viewer..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/pubsub.viewer" > /dev/null

echo "Environment setup complete!"
