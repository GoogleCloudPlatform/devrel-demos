#!/usr/bin/env bash
# Master setup script for the Data Agent Kit Codelab.
# Bootstraps the GCS buckets, BigLake Iceberg catalog, BigQuery datasets,
# mock data, and triggers background creation of Cloud Spanner and
# Managed Airflow.
#
# Prerequisites (run in Cloud Shell before this script):
#   gcloud config set project <<YOUR_PROJECT_ID>>
#   export PROJECT_ID=$(gcloud config get-value project)
#   export REGION=us-west1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helpers ---
log_info()  { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${RED}[ERROR]${NC} $1"; }

log_step() {
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}  Step $1: $2${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# --- Config & Environment ---
ENV_FILE="$SCRIPT_DIR/../.env"

# Auto-detect or use exported env vars
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-west1}"

if [[ -z "${PROJECT_ID:-}" ]]; then
    log_error "PROJECT_ID is not set. Run: gcloud config set project <<YOUR_PROJECT_ID>>"
    exit 1
fi

# Set the active project in gcloud
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1

# --- Derived resource names ---
COMPOSER_ENVIRONMENT="${COMPOSER_ENVIRONMENT:-cymbal-airflow}"
SPANNER_INSTANCE="${SPANNER_INSTANCE:-cymbal-fraud}"
SPANNER_DATABASE="${SPANNER_DATABASE:-fraud-db}"
DATASET_NAME="${DATASET_NAME:-transactions_dataset_evals}"
RAW_BUCKET="${RAW_BUCKET:-${PROJECT_ID}-fin-clearing-raw}"
MODELS_BUCKET="${MODELS_BUCKET:-${PROJECT_ID}-models}"
ICEBERG_CATALOG="${RAW_BUCKET}"
COMPOSER_SA_NAME="${COMPOSER_SA_NAME:-composer-worker-sa}"

# --- Write all config to .env ---
# This is the single source of truth for all sub-scripts.
update_env_var() {
  local key=$1
  local value=$2
  touch "$ENV_FILE"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "$ENV_FILE" && rm -f "${ENV_FILE}.bak"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

update_env_var "PROJECT_ID" "$PROJECT_ID"
update_env_var "REGION" "$REGION"
update_env_var "RAW_BUCKET" "$RAW_BUCKET"
update_env_var "MODELS_BUCKET" "$MODELS_BUCKET"
update_env_var "DATASET_NAME" "$DATASET_NAME"
update_env_var "ICEBERG_CATALOG" "$ICEBERG_CATALOG"
update_env_var "SPANNER_INSTANCE" "$SPANNER_INSTANCE"
update_env_var "SPANNER_DATABASE" "$SPANNER_DATABASE"
update_env_var "COMPOSER_ENVIRONMENT" "$COMPOSER_ENVIRONMENT"
update_env_var "COMPOSER_SA_NAME" "$COMPOSER_SA_NAME"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Cymbal Pay Fraud Codelab: Bootstrapping            ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Project ID:            ${PROJECT_ID}"
log_info "Region:                ${REGION}"
log_info "GCS Ingestion Bucket:  gs://${RAW_BUCKET}"
log_info "GCS Models Bucket:     gs://${MODELS_BUCKET}"
log_info "BigQuery Dataset:      ${DATASET_NAME}"
log_info "Iceberg Catalog:       ${ICEBERG_CATALOG}"
log_info "Spanner Instance:      ${SPANNER_INSTANCE}"
log_info "Composer Environment:  ${COMPOSER_ENVIRONMENT}"
echo ""

# =============================================================================
# STEP 1: Enable Required APIs
# =============================================================================
log_step "1" "Enabling required Google Cloud APIs"

APIS=(
  storage.googleapis.com
  bigquery.googleapis.com
  biglake.googleapis.com
  bigqueryconnection.googleapis.com
  dataproc.googleapis.com
  composer.googleapis.com
  compute.googleapis.com
  spanner.googleapis.com
  iam.googleapis.com
  cloudresourcemanager.googleapis.com
)

for api in "${APIS[@]}"; do
  log_info "Enabling ${api}..."
  gcloud services enable "$api" --project="$PROJECT_ID" --quiet 2>/dev/null || true
done
log_ok "Core APIs enabled."

# =============================================================================
# STEP 2: Create Cloud Storage Buckets
# =============================================================================
log_step "2" "Creating Cloud Storage Buckets"

# Raw ingestion bucket
if gcloud storage buckets describe "gs://${RAW_BUCKET}" --project="$PROJECT_ID" &>/dev/null; then
  log_warn "GCS Bucket gs://${RAW_BUCKET} already exists."
else
  log_info "Creating bucket gs://${RAW_BUCKET} in ${REGION}..."
  gcloud storage buckets create "gs://${RAW_BUCKET}" --project="$PROJECT_ID" --location="$REGION" --quiet
  log_ok "GCS Bucket gs://${RAW_BUCKET} created."
fi

# ML models bucket (used by training notebook: gs://${PROJECT_ID}-models/fraud_model)
if gcloud storage buckets describe "gs://${MODELS_BUCKET}" --project="$PROJECT_ID" &>/dev/null; then
  log_warn "GCS Bucket gs://${MODELS_BUCKET} already exists."
else
  log_info "Creating bucket gs://${MODELS_BUCKET} in ${REGION}..."
  gcloud storage buckets create "gs://${MODELS_BUCKET}" --project="$PROJECT_ID" --location="$REGION" --quiet
  log_ok "GCS Bucket gs://${MODELS_BUCKET} created."
fi

# =============================================================================
# STEP 3: Copy Pre-Generated Datasets from Source Bucket
# =============================================================================
log_step "3" "Copying pre-generated datasets"

DATA_DIR="$SCRIPT_DIR/data"
SOURCE_BUCKET="gs://sample-data-and-media/cymbal-financial-fraud"

# Copy logs.json directly between buckets (avoids downloading 276MB locally)
log_info "Copying logs.json → gs://${RAW_BUCKET}/logs.json..."
gcloud storage cp "${SOURCE_BUCKET}/logs.json" "gs://${RAW_BUCKET}/logs.json" --quiet
log_ok "Raw logs copied to gs://${RAW_BUCKET}/logs.json"

# Download dimension tables locally for BigQuery loading in Step 5
mkdir -p "$DATA_DIR"
log_info "Downloading dimension tables for BigQuery loading..."
gcloud storage cp "${SOURCE_BUCKET}/payers.csv" "$DATA_DIR/payers.csv" --quiet
gcloud storage cp "${SOURCE_BUCKET}/payees.csv" "$DATA_DIR/payees.csv" --quiet
log_ok "Dimension tables downloaded to ${DATA_DIR}/"

# =============================================================================
# STEP 4: Create BigLake Iceberg Catalog & Namespace
# =============================================================================
log_step "4" "Provisioning BigLake Iceberg Catalog"

# Determine which gcloud track has working biglake iceberg commands.
# The flags may live under 'gcloud alpha biglake' or 'gcloud biglake' depending
# on the SDK version installed in Cloud Shell.
if gcloud biglake iceberg catalogs list --project="$PROJECT_ID" &>/dev/null 2>&1; then
  BIGLAKE_CMD="gcloud biglake"
elif gcloud alpha biglake iceberg catalogs list --project="$PROJECT_ID" &>/dev/null 2>&1; then
  BIGLAKE_CMD="gcloud alpha biglake"
else
  # Last resort: try GA and let errors surface
  BIGLAKE_CMD="gcloud biglake"
fi
log_info "Using: ${BIGLAKE_CMD} iceberg ..."

# Check if catalog already exists
if $BIGLAKE_CMD iceberg catalogs describe "$ICEBERG_CATALOG" \
    --project="$PROJECT_ID" &>/dev/null; then
  log_warn "BigLake Iceberg catalog '${ICEBERG_CATALOG}' already exists."
else
  log_info "Creating BigLake Iceberg catalog '${ICEBERG_CATALOG}'..."
  $BIGLAKE_CMD iceberg catalogs create "$ICEBERG_CATALOG" \
    --catalog-type=gcs-bucket \
    --project="$PROJECT_ID" \
    --quiet
  log_ok "Iceberg catalog '${ICEBERG_CATALOG}' created."
fi

# Create namespace for our transaction tables
if $BIGLAKE_CMD iceberg namespaces describe "$DATASET_NAME" \
    --catalog="$ICEBERG_CATALOG" --project="$PROJECT_ID" &>/dev/null; then
  log_warn "Iceberg namespace '${DATASET_NAME}' already exists."
else
  log_info "Creating Iceberg namespace '${DATASET_NAME}'..."
  $BIGLAKE_CMD iceberg namespaces create "$DATASET_NAME" \
    --catalog="$ICEBERG_CATALOG" \
    --project="$PROJECT_ID" \
    --quiet
  log_ok "Iceberg namespace '${DATASET_NAME}' created."
fi

# =============================================================================
# STEP 5: Create BigQuery Dataset and Load Directory Tables
# =============================================================================
log_step "5" "Provisioning BigQuery Dataset and Directory Tables"

# Create BigQuery Dataset if not exists
if bq show --project_id="$PROJECT_ID" "$DATASET_NAME" &>/dev/null; then
    log_warn "BigQuery dataset '${DATASET_NAME}' already exists."
else
    log_info "Creating BigQuery dataset '${DATASET_NAME}' in location '${REGION}'..."
    bq --project_id="$PROJECT_ID" mk --dataset --location="$REGION" "$DATASET_NAME"
    log_ok "BigQuery dataset '${DATASET_NAME}' created."
fi

# Load Payers directory table
log_info "Loading dim_payers table..."
bq --project_id="$PROJECT_ID" load --autodetect --source_format=CSV \
  --location="$REGION" --replace \
  "${DATASET_NAME}.dim_payers" "$DATA_DIR/payers.csv"
log_ok "Loaded dim_payers."

# Load Payees directory table
log_info "Loading dim_payees table..."
bq --project_id="$PROJECT_ID" load --autodetect --source_format=CSV \
  --location="$REGION" --replace \
  "${DATASET_NAME}.dim_payees" "$DATA_DIR/payees.csv"
log_ok "Loaded dim_payees."

# =============================================================================
# STEP 6: Trigger Long-Running Deployments in Background
# =============================================================================
log_step "6" "Triggering background infrastructure provisioning"

COMPOSER_LOG="/tmp/composer_setup.log"
SPANNER_LOG="/tmp/spanner_setup.log"

log_info "Launching Cloud Spanner setup in background..."
log_info "Logging Spanner setup output to: ${SPANNER_LOG}"
nohup ./setup_spanner.sh > "$SPANNER_LOG" 2>&1 &
SPANNER_PID=$!

log_info "Launching Managed Airflow setup in background (takes 15-25 minutes)..."
log_info "Logging Composer setup output to: ${COMPOSER_LOG}"
nohup ./setup_composer.sh > "$COMPOSER_LOG" 2>&1 &
COMPOSER_PID=$!

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Bootstrap Completed!                               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Your primary BigQuery dataset, GCS buckets, and Iceberg catalog are ready."
echo -e "You can now begin Codelab steps (Pages 3, 4, 5, and 6) inside the IDE."
echo ""
echo -e "Cloud Spanner and Managed Airflow are provisioning in the background:"
echo -e "  • Spanner PID:  ${SPANNER_PID} (takes ~2-3 mins)"
echo -e "  • Composer PID: ${COMPOSER_PID} (takes ~20-25 mins)"
echo ""
echo -e "To monitor progress of background services, run these commands in a separate terminal:"
echo -e "  ${YELLOW}tail -f /tmp/spanner_setup.log${NC}"
echo -e "  ${YELLOW}tail -f /tmp/composer_setup.log${NC}"
echo ""
echo -e "Configuration written to: ${ENV_FILE}"
echo ""
