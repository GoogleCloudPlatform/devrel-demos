#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

echo "===================================================="
echo "Initializing Lost Cargo Investigation Environment..."
echo "===================================================="

# Ensure active project is identified
if [ -z "${PROJECT_ID}" ]; then
  echo "Error: No active Google Cloud project configured."
  echo "Please run: gcloud config set project <YOUR_PROJECT_ID>"
  exit 1
fi

# Ensure a region is identified
if [ -z "${REGION}" ]; then
  echo "Error: No Google Cloud region specified."
  echo "Please run: export REGION=<YOUR_REGION>"
  exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
USER_ACCOUNT=$(gcloud config get-value account)

BUCKET_NAME="${PROJECT_ID}-lost-cargo-lake"
DATASET="lost_cargo_dataset"
NAMESPACE="lost_cargo_namespace"
CATALOG_NAME="cargo_catalog"
TAXONOMY_NAME="LostCargo"

echo "Project ID:      ${PROJECT_ID}"
echo "Project Number:  ${PROJECT_NUMBER}"
echo "User Account:    ${USER_ACCOUNT}"
echo "Region:          ${REGION}"
echo "Bucket Name:     ${BUCKET_NAME}"
echo "===================================================="

# 1. GCS Bucket Creation & Data Ingestion
echo "Creating Cloud Storage bucket: gs://${BUCKET_NAME}..."
gcloud storage buckets create "gs://${BUCKET_NAME}" --location="${REGION}" || true

echo "Populating bucket with sample logistics data..."
# gcloud storage cp -r gs://sample-data-and-media/shipping_manifests/ "gs://${BUCKET_NAME}/shipping_manifests" || true
# gcloud storage cp -r gs://sample-data-and-media/raw_logs "gs://${BUCKET_NAME}/raw_logs" || true

# TEMPORARY FOR TESTING
gcloud storage cp ./data/manifests.jsonl gs://${BUCKET_NAME}/shipping_manifests/
gcloud storage cp ./data/maritime_logs.txt gs://${BUCKET_NAME}/raw_logs/

# 2. BigQuery Dataset Creation
echo "Creating BigQuery dataset: ${DATASET}..."
bq mk --location="${REGION}" "${DATASET}" || true

# 3. Lakehouse Catalog & Namespace Creation
echo "Provisioning Lakehouse Iceberg REST Catalog..."
gcloud alpha biglake iceberg catalogs create "${BUCKET_NAME}" \
  --catalog-type=gcs-bucket \
  --credential-mode=vended-credentials \
  --primary-location="${REGION}" || true

echo "Creating Iceberg Namespace: ${NAMESPACE}..."
gcloud biglake iceberg namespaces create "${NAMESPACE}" \
  --catalog="${BUCKET_NAME}" || true

CATALOG_SA=$(gcloud biglake iceberg catalogs describe "${BUCKET_NAME}" --format="value(biglake-service-account)")
echo "Catalog Service Account: ${CATALOG_SA}"

# 4. Creating the GCS Connection (Cloud Resource Connection)
# Note: Created using bq CLI as standard for BigQuery connection administration
echo "Creating BigQuery Cloud Resource Connection (${REGION}.conn)..."
bq mk --connection --location=${REGION} --connection_type=CLOUD_RESOURCE \
  --display_name="lakehouse-connection" \
  --description="Create a lakehouse connection for advanced management" \
  conn && sleep 10 || true

CONNECTION_SA=$(bq show --connection --format=json ${REGION}.conn | jq -r '.cloudResource.serviceAccountId')
echo "Connection Service Account: ${CONNECTION_SA}"

# 5. IAM Permission Assignments
echo "Granting Catalog SA storage access on bucket..."
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${CATALOG_SA}" \
  --role="roles/storage.objectUser" --quiet

echo "Granting Connection SA storage access on project..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CONNECTION_SA}" \
  --role="roles/storage.objectUser" --quiet

COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "Granting Compute Default SA permissions for Managed Spark execution..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/dataproc.worker" --quiet

echo "Granting Compute SA Data Editor access to BigQuery"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/bigquery.dataEditor" --quiet

echo "Granting Compute SA editor access to Lakehouse"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/biglake.editor" --quiet

echo "Granting User Masked Reader role for Governance validation..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="user:${USER_ACCOUNT}" \
  --role="roles/bigquerydatapolicy.maskedReader" --quiet

# 6. Nudge Knowledge Catalog to speed up Insights generation
echo "Warming up Knowledge Catalog..."
gcloud beta services identity create --service=dataplex.googleapis.com --project=${PROJECT_NUMBER}

# 7. Generating .env File
ENV_FILE=".env"
echo "Generating ${ENV_FILE} configuration file..."

cat <<EOF > "${ENV_FILE}"
PROJECT_ID="${PROJECT_ID}"
PROJECT_NUMBER="${PROJECT_NUMBER}"
USER_ACCOUNT="${USER_ACCOUNT}"
REGION="${REGION}"
BUCKET_NAME="${BUCKET_NAME}"
DATASET="${DATASET}"
NAMESPACE="${NAMESPACE}"
CATALOG_NAME="${CATALOG_NAME}"
CATALOG_SA="${CATALOG_SA}"
COMPUTE_SA="${COMPUTE_SA}"
CONNECTION_ID="${REGION}.conn"
CONNECTION_SA="${CONNECTION_SA}"
TAXONOMY_NAME="${TAXONOMY_NAME}"
EOF

# 8. Set environment variables
echo "Setting environment variables from .env configuration file"
bash ./set_env.sh

echo "===================================================="
echo "Environment Setup Complete!"
echo "===================================================="
