#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

echo "🚀 Starting Petverse System Setup..."

# 1. Check for Project ID & Region in environment, otherwise prompt
if [ -z "$PROJECT_ID" ]; then
    read -p "Enter your Google Cloud Project ID: " PROJECT_ID
fi
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID cannot be empty."
    return 1 2>/dev/null || exit 1
fi

if [ -z "$REGION" ]; then
    read -p "Enter your Location Region (e.g., us-central1) [default: us-central1]: " REGION
fi
REGION=${REGION:-us-central1}
LOCATION=$REGION

# Write to .env file in project root
ENV_FILE="$(dirname "$0")/../.env"
echo "Writing environment variables to $ENV_FILE..."
echo "PROJECT_ID=$PROJECT_ID" > "$ENV_FILE"
echo "REGION=$REGION" >> "$ENV_FILE"

echo "Configuring environment..."
gcloud config set project $PROJECT_ID > /dev/null 2>&1
export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
export LOCATION=$LOCATION

DATASET="petverse_kg"
TABLE_NODES="Nodes"
TABLE_EDGES="Edges"
CONNECTION_NAME="petverse-embeddings"

echo "✅ Environment loaded successfully: $GOOGLE_CLOUD_PROJECT in $LOCATION."

echo "⚠️⚠️⚠️ ATTENTION ⚠️⚠️⚠️ "
echo " This script will take a few minutes to complete"
echo " Please leave this tab open and continue with the lab"
echo "☝️☝️☝️ ATTENTION ☝️☝️☝️"

# =========================================================
# CRITICAL: ENCAPSULATE API OPERATIONS IN A SAFE SUBSHELL
# This guarantees that if any `bq` or `gcloud` step fails, `set -e` forces
# instant termination of the SUB-TASK without killing your
# active interactive terminal window session!
# =========================================================
(
  set -e # Enable strict instant-fail inside this wrapper ONLY
  echo "🛠️  Initializing serverless resources inside isolated subtask..."

  # 1. Enable Required APIs
  echo "🛠️ Step 1: Enabling Required APIs..."
  gcloud services enable \
      aiplatform.googleapis.com \
      bigquery.googleapis.com \
      artifactregistry.googleapis.com \
      container.googleapis.com \
      pubsub.googleapis.com

  # Force-provision Vertex AI Service Agent and grant storage permissions to avoid lazy-provisioning race conditions
  echo "🛠️ Step 1b: Force-provisioning Vertex AI Service Agent..."
  gcloud beta services identity create \
      --service=aiplatform.googleapis.com \
      --project="${PROJECT_ID}"

  PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
  VERTEX_AI_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-aiplatform.iam.gserviceaccount.com"

  echo "🔐 Granting Storage Object Viewer role to Vertex AI Service Agent..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${VERTEX_AI_SERVICE_AGENT}" \
      --role="roles/storage.objectViewer" >/dev/null

  # 1c. Create Project-Specific GCS Bucket & Copy Sample Data
  BUCKET_NAME="${PROJECT_ID}-petverse"
  echo "🛠️ Step 1c: Creating project-specific GCS bucket 'gs://${BUCKET_NAME}'..."
  if gcloud storage buckets describe "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
      echo "✅ GCS Bucket 'gs://${BUCKET_NAME}' already exists."
  else
      echo "Creating bucket 'gs://${BUCKET_NAME}'..."
      gcloud storage buckets create "gs://${BUCKET_NAME}" \
          --location="${LOCATION}" \
          --uniform-bucket-level-access
      
      echo "📦 Copying sample dataset into GCS bucket..."
      gcloud storage cp -r gs://sample-data-and-media/petverse/* "gs://${BUCKET_NAME}/"
  fi

  # 2. Create Artifact Registry Repository
  echo "🛠️ Step 2: Creating Artifact Registry Repository..."
  gcloud artifacts repositories create gke-cats-repo \
      --repository-format=docker \
      --location=$REGION \
      --description="Processor Registry" 2>/dev/null || echo "ℹ️ Repository may already exist."

  # 3. Build and Push Images
  echo "🛠️ Step 3a: Building and Pushing GKE Producer Container Image..."
  gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/gke-cats-repo/petverse-producer:latest ./producer

  echo "🛠️ Step 3b: Building and Pushing GKE Worker Container Image..."
  gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/gke-cats-repo/petverse-worker:latest ./worker

  # 4. Create BigQuery Dataset
  echo "🛠️ Step 4: Creating BigQuery Dataset..."
  if bq show --dataset "$PROJECT_ID:$DATASET" > /dev/null 2>&1; then
      echo "✅ Dataset '$DATASET' already exists."
  else
      echo "Creating dataset '$DATASET' in $LOCATION..."
      bq mk --dataset --location=$LOCATION "$PROJECT_ID:$DATASET"
  fi

  # Apply the required label
  echo "Applying deployment labeling to dataset..."
  bq update --set_label dev-tutorial:stabby-unicorn "$PROJECT_ID:$DATASET" > /dev/null 2>&1

  # 5. Connection & Permissions
  echo "🛠️ Step 5: Provisioning Serverless BigQuery Connection and Granting Permissions via SQL..."
  bq query --use_legacy_sql=false "
  CREATE CONNECTION IF NOT EXISTS \`$PROJECT_ID.$LOCATION.$CONNECTION_NAME\`
  OPTIONS (
    connection_type = 'CLOUD_RESOURCE',
    friendly_name = 'Petverse Embedded Vectors API'
  );"

  echo "🔐 Applying Project-level Direct IAM Delegation to Connection..."
  bq query --location=$LOCATION --use_legacy_sql=false "
  GRANT \`roles/aiplatform.user\`
  ON PROJECT \`$PROJECT_ID\`
  TO \"connection:$PROJECT_ID.$LOCATION.$CONNECTION_NAME\";"

  # # 6. Infrastructure Tables
  # echo "🛠️ Step 6: Constructing Knowledge Tables with Autonomous Vector Generators..."
  # echo "✨ Creating Table '$TABLE_NODES' with Literal Explicit Embedding Source Columns..."
  # bq query --use_legacy_sql=false "
  # CREATE TABLE IF NOT EXISTS \`$PROJECT_ID.$DATASET.$TABLE_NODES\` (
  #   entity_id STRING NOT NULL,
  #   entity_type STRING,
  #   name STRING,
  #   pet_bio STRING,
  #   properties JSON,
  #   bio_embedding STRUCT<result ARRAY<FLOAT64>, status STRING> GENERATED ALWAYS AS (
  #     AI.EMBED(
  #       pet_bio,
  #       connection_id => '$PROJECT_ID.$LOCATION.$CONNECTION_NAME',
  #       endpoint => 'text-embedding-005'
  #     )
  #   ) STORED OPTIONS(asynchronous = TRUE)
  # );"

  # echo "✨ Creating Table '$TABLE_EDGES'..."
  # bq query --use_legacy_sql=false "
  # CREATE TABLE IF NOT EXISTS \`$PROJECT_ID.$DATASET.$TABLE_EDGES\` (
  #   source_id STRING,
  #   target_id STRING,
  #   relationship STRING,
  #   properties JSON
  # );"

  # 7. Pub/Sub Resources
  echo "🛠️ Step 7: Creating Pub/Sub Topic and Subscription..."
  TOPIC="petverse-topic"
  SUBSCRIPTION="petverse-sub"

  if gcloud pubsub topics describe "$TOPIC" > /dev/null 2>&1; then
      echo "✅ Topic '$TOPIC' already exists."
  else
      echo "Creating topic '$TOPIC'..."
      gcloud pubsub topics create "$TOPIC"
  fi

  if gcloud pubsub subscriptions describe "$SUBSCRIPTION" > /dev/null 2>&1; then
      echo "✅ Subscription '$SUBSCRIPTION' already exists."
  else
      echo "Creating subscription '$SUBSCRIPTION'..."
      gcloud pubsub subscriptions create "$SUBSCRIPTION" --topic="$TOPIC" --ack-deadline=600
  fi

  echo "🦄 Setup Complete for project $PROJECT_ID!"
  echo "📊 Dataset, Dynamic Embeddings Connection, and Federated Roles fully online."
)

# Grab response condition from subshell to gracefully catch failure silently without crash
if [ $? -ne 0 ]; then
    echo "❌ Pipeline Script encountered an unrecoverable error and halted safety checks."
    echo "🔍 Check above for specific BigQuery fault details."
else
    echo " 🎉 🦄  Setup successfully finished! 🎉 🦄"

    echo "📝 Generating job-producer.yaml..."
    if [ -f "templates/job-producer-template.yaml" ]; then
        sed -e "s/\${PROJECT_ID}/$PROJECT_ID/g" \
            -e "s/\${REGION}/$REGION/g" \
            templates/job-producer-template.yaml > job-producer.yaml
        echo "✅ job-producer.yaml generated."
    else
        echo "⚠️ templates/job-producer-template.yaml not found, skipping."
    fi

    echo "📝 Generating job-worker.yaml..."
    if [ -f "templates/job-worker-template.yaml" ]; then
        sed -e "s/\${PROJECT_ID}/$PROJECT_ID/g" \
            -e "s/\${REGION}/$REGION/g" \
            templates/job-worker-template.yaml > job-worker.yaml
        echo "✅ job-worker.yaml generated."
    else
        echo "⚠️ templates/job-worker-template.yaml not found, skipping."
    fi
    echo "📝 Replacing region placeholder in SQL..."
    if [ -f "templates/job-worker-template.yaml" ]; then
        sed -i "s/\${PROJECT_ID}/$PROJECT_ID/g; s/\${REGION}/$REGION/g" scripts/create_tables.sql
        echo "✅ Replaced REGION in create_tables.sql."
    else
        echo "⚠️ create_tables.sql not found"
    fi
fi
