#!/bin/bash
# Lab 2: Setup Script
# Creates all infrastructure and seeds data so attendees can jump straight
# into running AI queries. Run from the repository root directory.
#
# Usage: bash lab2/scripts/setup_lab.sh

set -euo pipefail

# --- Set Logging Config ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_info()  { echo -e "${CYAN}ℹ️  ${BOLD}$1${NC}"; }
print_ok()    { echo -e "${GREEN}✅ $1${NC}"; }
print_warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# ---------------------------------------------------------------
# Config
# ---------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Load environment from .env if it exists
if [ -f "$ENV_FILE" ]; then
    print_info "Loading environment variables from $ENV_FILE..."
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
    print_error "Google Cloud Project ID cannot be empty."
    exit 1
fi

# Determine Region
if [ -z "${REGION:-}" ]; then
    print_warn "REGION environment variable is not set."
    while [ -z "${REGION:-}" ]; do
        read -p "Please explicitly enter your assigned Google Cloud region (e.g., us-central1, europe-west1): " REGION
    done
fi

# Save to .env file
print_info "Writing environment variables to $ENV_FILE..."
echo "PROJECT_ID=$PROJECT_ID" > "$ENV_FILE"
echo "REGION=$REGION" >> "$ENV_FILE"

# Configure gcloud CLI
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1

BUCKET="gs://${PROJECT_ID}-lab2"
SOURCE_BUCKET="gs://sample-data-and-media/data-cloud-roadshow-26/lab2"

print_info "Project:  $PROJECT_ID"
print_info "Region:   $REGION"
print_info "Bucket:   $BUCKET"
echo ""

# Quick credential check (catches expired Cloud Shell tokens)
if ! gcloud auth print-access-token &>/dev/null; then
  print_error "Your credentials have expired. Run 'gcloud auth login' and try again."
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

  print_info "      Granting $role to $member..."
  while [ $attempt -le $max_attempts ]; do
    if gcloud projects add-iam-policy-binding "$project" --format=none \
      --member="$member" --role="$role" --quiet &>/dev/null; then
        print_ok "      Successfully granted $role."
        return 0
    else
        if [ $attempt -lt $max_attempts ]; then
          print_warn "      IAM propagation delay encountered. Retrying in ${delay}s (Attempt $attempt/$max_attempts)..."
          sleep $delay
          ((attempt++))
        else
          print_error "      Failed to grant $role after $max_attempts attempts."
          return 1
        fi
    fi
  done
}

# ---------------------------------------------------------------
# [1/8] Enable required APIs
# ---------------------------------------------------------------
print_info "[1/8] Enabling required Google Cloud APIs (BigQuery, Vertex AI, Gemini Data Analytics, AlloyDB, Storage)..."
gcloud services enable \
  aiplatform.googleapis.com \
  alloydb.googleapis.com \
  bigquery.googleapis.com \
  bigqueryconnection.googleapis.com \
  cloudaicompanion.googleapis.com \
  geminidataanalytics.googleapis.com \
  storage.googleapis.com \
  --quiet
print_ok "      Done."
echo ""

# ---------------------------------------------------------------
# [2/8] Create BigQuery dataset
# ---------------------------------------------------------------
print_info "[2/8] Creating BigQuery dataset 'lost_cargo_dataset'..."
bq --location=$REGION mk --dataset "$PROJECT_ID:lost_cargo_dataset" 2>/dev/null || true
print_ok "      Done."

# ---------------------------------------------------------------
# [3/8] Create Cloud Resource connection + IAM grants
# ---------------------------------------------------------------
print_info "[3/8] Creating Cloud Resource connection and granting permissions..."
bq mk --connection --location=$REGION --connection_type=CLOUD_RESOURCE lost_cargo_conn 2>/dev/null || true

SA_EMAIL=$(bq show --format=prettyjson --connection ${REGION}.lost_cargo_conn \
  | grep "serviceAccountId" | cut -d '"' -f 4)
print_info "      Connection service account: $SA_EMAIL"

# Grant permissions using the retry helper to gracefully handle propagation delay
grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:$SA_EMAIL" "roles/storage.objectViewer"
grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:$SA_EMAIL" "roles/aiplatform.user"
print_ok "      Done."


# ---------------------------------------------------------------
# [4/8] Create AlloyDB BigQuery connection (for reverse ETL)
# ---------------------------------------------------------------
print_info "[4/8] Creating AlloyDB BigQuery connection for reverse ETL..."
print_info "      (This connection will be used later to export data directly to AlloyDB.)"
print_info "      Note: If AlloyDB is not ready yet, this step may fail."
print_info "      You can re-run this step later with: bq mk --connection ..."
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
SA_EMAIL_ALLOYDB=$(bq show --format=prettyjson --connection ${REGION}.lost_cargo_alloydb_conn | grep "serviceAccountId" | cut -d '"' -f 4)
if [[ -n "$SA_EMAIL_ALLOYDB" ]]; then
  grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:$SA_EMAIL_ALLOYDB" "roles/alloydb.client"
fi
print_ok "      Done."

# ---------------------------------------------------------------
# [5/8] Create GCS bucket, copy assets, and grant AlloyDB access
# ---------------------------------------------------------------
print_info "[5/8] Creating GCS bucket, copying lab assets, and granting AlloyDB permissions..."
if gcloud storage buckets describe "$BUCKET" &>/dev/null; then
    print_info "      Bucket already exists: $BUCKET"
else
    print_info "      Creating bucket $BUCKET..."
    gcloud storage buckets create "$BUCKET" --location=$REGION
fi

print_info "      Copying images from central bucket..."
gcloud storage cp -r "${SOURCE_BUCKET}/images/*" "${BUCKET}/images/"

print_info "      Copying data from central bucket..."
gcloud storage cp -r "${SOURCE_BUCKET}/data/*" "${BUCKET}/data/"

print_ok "      Done."



# ---------------------------------------------------------------
# [6/8] Load telemetry data into BigQuery
# ---------------------------------------------------------------
print_info "[6/8] Loading telemetry data into BigQuery..."
bq load --replace --source_format=NEWLINE_DELIMITED_JSON \
  "$PROJECT_ID:lost_cargo_dataset.telemetry_data" \
  "${BUCKET}/data/telemetry_data.jsonl" \
  shipment_id:STRING,telemetry_string:STRING
print_ok "      Done."

# ---------------------------------------------------------------
# [7/8] Create thermal baseline (thermal_history)
# ---------------------------------------------------------------
print_info "[7/8] Creating thermal sensor baseline data..."
bq query --use_legacy_sql=false --quiet --location="$REGION" \
"CREATE OR REPLACE TABLE \`${PROJECT_ID}.lost_cargo_dataset.thermal_history\` AS
SELECT
  TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR), INTERVAL (n * 15) MINUTE) AS reading_time,
  'SENS-99' AS sensor_id,
  ROUND(75.0 + (RAND() * 3.0), 1) AS thermal_reading
FROM UNNEST(GENERATE_ARRAY(51, 150)) AS n;"
print_ok "      Done."

# ---------------------------------------------------------------
# [8/8] Create current thermal readings (thermal_current)
# ---------------------------------------------------------------
print_info "[8/8] Creating current thermal readings data..."
bq query --use_legacy_sql=false --quiet --location="$REGION" \
"CREATE OR REPLACE TABLE \`${PROJECT_ID}.lost_cargo_dataset.thermal_current\` AS
SELECT
  TIMESTAMP_SUB(TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR), INTERVAL (n * 15) MINUTE) AS reading_time,
  'SENS-99' AS sensor_id,
  CASE
    WHEN n = 25 THEN 148.4
    ELSE ROUND(75.0 + (RAND() * 3.0), 1)
  END AS thermal_reading
FROM UNNEST(GENERATE_ARRAY(1, 50)) AS n;"
print_ok "      Done."

# ---------------------------------------------------------------
# [Done] Summary
# ---------------------------------------------------------------
echo ""
print_ok "============================================"
print_ok " Lab 2 Setup Complete!"
print_ok "============================================"
echo ""
print_info " Created resources:"
print_info "   - BigQuery dataset:    lost_cargo_dataset"
print_info "   - BQ connection:       ${REGION}.lost_cargo_conn (Cloud Resource)"
print_info "   - BQ connection:       ${REGION}.lost_cargo_alloydb_conn (AlloyDB)"
print_info "   - GCS bucket:          $BUCKET"
print_info "     - images/:           Port security images"
print_info "     - data/:             Telemetry data"
print_info "   - Table:               telemetry_data"
print_info "   - Table:               thermal_history"
print_info "   - Table:               thermal_current"
echo ""
print_info " Next: Return to the codelab and continue with"
print_info "       the next steps!"
echo ""
