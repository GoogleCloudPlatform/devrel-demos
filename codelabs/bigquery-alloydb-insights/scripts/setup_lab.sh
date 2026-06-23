#!/bin/bash
# Lab 2: Setup Script
# Creates all infrastructure and seeds data so attendees can jump straight
# into running AI queries. Run from the repository root directory.
#
# Usage: bash lab2/scripts/setup_lab.sh

set -euo pipefail

# ---------------------------------------------------------------
# Config
# ---------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Load environment from .env if it exists
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# || -z "$line" ]] && continue
        export "$line"
    done < "$ENV_FILE"
fi

# Determine Project ID (env/gcloud config/prompt)
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "$PROJECT_ID" ]]; then
    read -p "Enter your Google Cloud Project ID: " PROJECT_ID
fi
if [[ -z "$PROJECT_ID" ]]; then
    echo "❌ ERROR: Google Cloud Project ID cannot be empty."
    exit 1
fi

# Determine Region
REGION="${REGION:-us-central1}"

# Save to .env file
echo "Writing environment variables to $ENV_FILE..."
echo "PROJECT_ID=$PROJECT_ID" > "$ENV_FILE"
echo "REGION=$REGION" >> "$ENV_FILE"

# Configure gcloud CLI
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1

BUCKET="gs://${PROJECT_ID}-lab2"
SOURCE_BUCKET="gs://sample-data-and-media/data-cloud-roadshow-26/lab2"

echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Bucket:   $BUCKET"
echo ""

# Quick credential check (catches expired Cloud Shell tokens)
if ! gcloud auth print-access-token &>/dev/null; then
  echo "ERROR: Your credentials have expired. Run 'gcloud auth login' and try again."
  exit 1
fi

# Helper function to run IAM policy binding with retries to handle propagation delay
function grant_iam_role_with_retry() {
  local project=$1
  local member=$2
  local role=$3
  local max_attempts=4
  local attempt=1
  local delay=5

  echo "      Granting $role to $member..."
  while [ $attempt -le $max_attempts ]; do
    if gcloud projects add-iam-policy-binding "$project" --format=none \
      --member="$member" --role="$role" --quiet &>/dev/null; then
        echo "      ✅ Successfully granted $role."
        return 0
    else
        if [ $attempt -lt $max_attempts ]; then
          echo "      ⚠️ IAM propagation delay encountered. Retrying in ${delay}s (Attempt $attempt/$max_attempts)..."
          sleep $delay
          ((attempt++))
        else
          echo "      ❌ Error: Failed to grant $role after $max_attempts attempts."
          return 1
        fi
    fi
  done
}

# ---------------------------------------------------------------
# [1/8] Enable required APIs
# ---------------------------------------------------------------
echo "[1/8] Enabling required Google Cloud APIs (BigQuery, Vertex AI, Gemini Data Analytics, AlloyDB, Storage)..."
gcloud services enable \
  bigquery.googleapis.com \
  aiplatform.googleapis.com \
  geminidataanalytics.googleapis.com \
  alloydb.googleapis.com \
  storage.googleapis.com \
  --quiet
echo "      Done."
echo ""

# ---------------------------------------------------------------
# [2/8] Create BigQuery dataset
# ---------------------------------------------------------------
echo "[2/8] Creating BigQuery dataset 'lost_cargo_dataset'..."
bq --location="$REGION" mk --dataset "$PROJECT_ID:lost_cargo_dataset" 2>/dev/null || true
echo "      Done."

# ---------------------------------------------------------------
# [3/8] Create Cloud Resource connection + IAM grants
# ---------------------------------------------------------------
echo "[3/8] Creating Cloud Resource connection and granting permissions..."
bq mk --connection --location=$REGION --connection_type=CLOUD_RESOURCE lost_cargo_conn 2>/dev/null || true

SA_EMAIL=$(bq show --format=prettyjson --connection $REGION.lost_cargo_conn \
  | grep "serviceAccountId" | cut -d '"' -f 4)
echo "      Connection service account: $SA_EMAIL"

# Grant permissions using the retry helper to gracefully handle propagation delay
grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:$SA_EMAIL" "roles/storage.objectViewer"
grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:$SA_EMAIL" "roles/aiplatform.user"
echo "      Done."


# ---------------------------------------------------------------
# [4/8] Create AlloyDB BigQuery connection (for reverse ETL)
# ---------------------------------------------------------------
echo "[4/8] Creating AlloyDB BigQuery connection for reverse ETL..."
echo "      (This connection will be used later to export data directly to AlloyDB.)"
echo "      Note: If AlloyDB is not ready yet, this step may fail."
echo "      You can re-run this step later with: bq mk --connection ..."
# Note: BigQuery treats AlloyDB as a PostgreSQL Cloud SQL connection under the hood via the REST API.
curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  -H "Content-Type: application/json" \
  "https://bigqueryconnection.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/connections?connectionId=lost_cargo_alloydb_conn" \
  -d '{
    "cloudSql": {
      "instanceId": "'${PROJECT_ID}':'${REGION}':lost-cargo-cluster",
      "database": "postgres",
      "type": "POSTGRES",
      "credential": {
        "username": "postgres",
        "password": "lost-cargo"
      }
    }
  }' > /dev/null || true

# Grant the connection's service account access to AlloyDB
SA_EMAIL_ALLOYDB=$(bq show --format=prettyjson --connection "$REGION.lost_cargo_alloydb_conn" | grep "serviceAccountId" | cut -d '"' -f 4)
if [[ -n "$SA_EMAIL_ALLOYDB" ]]; then
  grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:$SA_EMAIL_ALLOYDB" "roles/alloydb.client"
fi
echo "      Done."

# ---------------------------------------------------------------
# [5/8] Create GCS bucket, copy assets, and grant AlloyDB access
# ---------------------------------------------------------------
echo "[5/8] Creating GCS bucket, copying lab assets, and granting AlloyDB permissions..."
if gcloud storage buckets describe "$BUCKET" &>/dev/null; then
    echo "      Bucket already exists: $BUCKET"
else
    echo "      Creating bucket $BUCKET..."
    gcloud storage buckets create "$BUCKET" --location=$REGION
fi

echo "      Copying images from central bucket..."
gcloud storage cp -r "${SOURCE_BUCKET}/images/*" "${BUCKET}/images/"

echo "      Copying data from central bucket..."
gcloud storage cp -r "${SOURCE_BUCKET}/data/*" "${BUCKET}/data/"

echo "      Done."



# ---------------------------------------------------------------
# [6/8] Load telemetry data into BigQuery
# ---------------------------------------------------------------
echo "[6/8] Loading telemetry data into BigQuery..."
bq load --replace --source_format=NEWLINE_DELIMITED_JSON \
  "$PROJECT_ID:lost_cargo_dataset.telemetry_data" \
  "${BUCKET}/data/telemetry_data.jsonl" \
  shipment_id:STRING,telemetry_string:STRING
echo "      Done."

# ---------------------------------------------------------------
# [7/8] Create thermal baseline (thermal_history)
# ---------------------------------------------------------------
echo "[7/8] Creating thermal sensor baseline data..."
bq query --use_legacy_sql=false --quiet \
"CREATE OR REPLACE TABLE \`${PROJECT_ID}.lost_cargo_dataset.thermal_history\` AS
SELECT
  TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR), INTERVAL (n * 15) MINUTE) AS reading_time,
  'SENS-99' AS sensor_id,
  ROUND(75.0 + (RAND() * 3.0), 1) AS thermal_reading
FROM UNNEST(GENERATE_ARRAY(51, 150)) AS n;"
echo "      Done."

# ---------------------------------------------------------------
# [8/8] Create current thermal readings (thermal_current)
# ---------------------------------------------------------------
echo "[8/8] Creating current thermal readings data..."
bq query --use_legacy_sql=false --quiet \
"CREATE OR REPLACE TABLE \`${PROJECT_ID}.lost_cargo_dataset.thermal_current\` AS
SELECT
  TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR), INTERVAL (n * 15) MINUTE) AS reading_time,
  'SENS-99' AS sensor_id,
  CASE
    WHEN n = 25 THEN 148.4
    ELSE ROUND(75.0 + (RAND() * 3.0), 1)
  END AS thermal_reading
FROM UNNEST(GENERATE_ARRAY(1, 50)) AS n;"
echo "      Done."

# ---------------------------------------------------------------
# [Done] Summary
# ---------------------------------------------------------------
echo ""
echo "============================================"
echo " Lab 2 Setup Complete!"
echo "============================================"
echo ""
echo " Created resources:"
echo "   - BigQuery dataset:    lost_cargo_dataset"
echo "   - BQ connection:       $REGION.lost_cargo_conn (Cloud Resource)"
echo "   - BQ connection:       $REGION.lost_cargo_alloydb_conn (AlloyDB)"
echo "   - GCS bucket:          $BUCKET"
echo "     - images/:           Port security images"
echo "     - data/:             Telemetry data"
echo "   - Table:               telemetry_data"
echo "   - Table:               thermal_history"
echo "   - Table:               thermal_current"
echo ""
echo " Next: Return to the codelab and continue with"
echo "       setting up the Data Agent Kit."
echo ""

