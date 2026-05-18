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

echo "🚀 Starting Petverse Deployment..."

# Load environment variables from .env file if it exists
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE..."
    export $(cat "$ENV_FILE" | xargs)
fi

# Check for Project ID & Region in environment, otherwise prompt
if [ -z "$PROJECT_ID" ]; then
    read -p "Enter your Google Cloud Project ID: " PROJECT_ID
fi
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID cannot be empty."
    exit 1
fi

if [ -z "$REGION" ]; then
    read -p "Enter your Region (e.g., us-central1) [default: us-central1]: " REGION
fi
REGION=${REGION:-us-central1}

if [ ! -f "job-producer.yaml" ] || [ ! -f "job-worker.yaml" ]; then
    echo "❌ job-producer.yaml or job-worker.yaml not found. Please run scripts/setup.sh first."
    exit 1
fi

echo "🔐 Configuring Cloud IAM Service Account..."
gcloud iam service-accounts create petverse-gke-sa 2>/dev/null || echo "ℹ️ Cloud IAM service account petverse-gke-sa already exists."

echo "🔐 Granting IAM roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:petverse-gke-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:petverse-gke-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:petverse-gke-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.user" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:petverse-gke-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:petverse-gke-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher" >/dev/null

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:petverse-gke-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/pubsub.subscriber" >/dev/null

echo "🔐 Binding IAM Service Account to K8S Service Account..."
gcloud iam service-accounts add-iam-policy-binding \
    petverse-gke-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="serviceAccount:$PROJECT_ID.svc.id.goog[default/petverse-gke-sa]" >/dev/null

echo "🔐 Configuring K8s Service Account..."
kubectl create serviceaccount petverse-gke-sa 2>/dev/null || echo "ℹ️ Service account petverse-gke-sa already exists."

kubectl annotate serviceaccount petverse-gke-sa \
    iam.gke.io/gcp-service-account=petverse-gke-sa@$PROJECT_ID.iam.gserviceaccount.com --overwrite

echo "📊 Loading sample data into BigQuery..."
bq mk --dataset --location=$REGION $PROJECT_ID:petverse_kg 2>/dev/null || echo "ℹ️ Dataset petverse_kg already exists."

bq load --source_format=CSV --autodetect --replace petverse_kg.pets gs://sample-data-and-media/petverse/pets.csv
bq load --source_format=CSV --autodetect --replace petverse_kg.pet_urls gs://sample-data-and-media/petverse/pet_urls.csv

echo "🎉 🦄 👉 Deployment configured successfully!"
echo "👉 You can now run the jobs manually:"
echo "   1. Populate the queue:  kubectl apply -f job-producer.yaml"
echo "   2. Process in parallel: kubectl apply -f job-worker.yaml"
