#!/usr/bin/env bash
# Teardown script to clean up all GCP resources created for the codelab.
# Reads configuration from .env (created by setup.sh).

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

# --- Load .env (created by setup.sh) ---
ENV_FILE="$SCRIPT_DIR/../.env"

if [ ! -f "$ENV_FILE" ]; then
    log_error "Missing .env file at ${ENV_FILE}. Cannot teardown without knowing what was provisioned."
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

# --- Validate required vars ---
if [[ -z "${PROJECT_ID:-}" ]]; then
    log_error "PROJECT_ID is not set. Check your .env file."
    exit 1
fi
if [[ -z "${REGION:-}" ]]; then
    log_error "REGION is not set. Check your .env file."
    exit 1
fi

# --- Derived resource names (with defaults matching setup.sh) ---
COMPOSER_ENVIRONMENT="${COMPOSER_ENVIRONMENT:-cymbal-airflow}"
COMPOSER_SA_NAME="${COMPOSER_SA_NAME:-composer-worker-sa}"
SPANNER_INSTANCE="${SPANNER_INSTANCE:-cymbal-fraud}"
DATASET_NAME="${DATASET_NAME:-transactions_dataset_evals}"
RAW_BUCKET="${RAW_BUCKET:-${PROJECT_ID}-fin-clearing-raw}"
MODELS_BUCKET="${MODELS_BUCKET:-${PROJECT_ID}-models}"
ICEBERG_CATALOG="${RAW_BUCKET}"
COMPOSER_SA_EMAIL="${COMPOSER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║   Teardown: Deleting All Codelab Resources           ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
log_warn "This will delete the following resources in project '${PROJECT_ID}':"
log_warn "  - GCS Bucket:          gs://${RAW_BUCKET}"
log_warn "  - GCS Bucket:          gs://${MODELS_BUCKET}"
log_warn "  - Iceberg Catalog:     ${ICEBERG_CATALOG}"
log_warn "  - BigQuery Dataset:    ${DATASET_NAME}"
log_warn "  - Spanner Instance:    ${SPANNER_INSTANCE}"
log_warn "  - Composer Env:        ${COMPOSER_ENVIRONMENT} in ${REGION}"
log_warn "  - Worker Serv. Acct:   ${COMPOSER_SA_EMAIL}"
echo ""

read -rp "Are you sure you want to proceed? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    log_info "Teardown cancelled."
    exit 0
fi

# =============================================================================
# 1. Delete Managed Airflow Environment
# =============================================================================
if gcloud composer environments describe "$COMPOSER_ENVIRONMENT" --project="$PROJECT_ID" --location="$REGION" &>/dev/null; then
    log_info "Deleting Managed Airflow Environment '${COMPOSER_ENVIRONMENT}' (takes 10-15 minutes)..."
    gcloud composer environments delete "$COMPOSER_ENVIRONMENT" \
        --project="$PROJECT_ID" \
        --location="$REGION" \
        --quiet
    log_ok "Managed Airflow environment deleted."
else
    log_warn "Managed Airflow environment '${COMPOSER_ENVIRONMENT}' not found. Skipping."
fi

# =============================================================================
# 2. Delete Cloud Spanner Instance
# =============================================================================
if gcloud spanner instances describe "$SPANNER_INSTANCE" --project="$PROJECT_ID" &>/dev/null; then
    log_info "Deleting Cloud Spanner Instance '${SPANNER_INSTANCE}'..."
    gcloud spanner instances delete "$SPANNER_INSTANCE" \
        --project="$PROJECT_ID" \
        --quiet
    log_ok "Cloud Spanner instance deleted."
else
    log_warn "Spanner instance '${SPANNER_INSTANCE}' not found. Skipping."
fi

# =============================================================================
# 3. Delete BigLake Iceberg Catalog (namespace + catalog)
# =============================================================================
# Detect which gcloud track has working biglake commands (mirrors setup.sh)
if gcloud biglake iceberg catalogs list --project="$PROJECT_ID" &>/dev/null 2>&1; then
  BIGLAKE_CMD="gcloud biglake"
elif gcloud alpha biglake iceberg catalogs list --project="$PROJECT_ID" &>/dev/null 2>&1; then
  BIGLAKE_CMD="gcloud alpha biglake"
else
  BIGLAKE_CMD="gcloud biglake"
fi

# Delete namespace first, then catalog
if $BIGLAKE_CMD iceberg namespaces describe "$DATASET_NAME" \
    --catalog="$ICEBERG_CATALOG" --project="$PROJECT_ID" 2>/dev/null; then
    log_info "Deleting Iceberg namespace '${DATASET_NAME}'..."
    # Delete all tables in the namespace first
    TABLES=$($BIGLAKE_CMD iceberg tables list \
      --namespace="$DATASET_NAME" --catalog="$ICEBERG_CATALOG" \
      --project="$PROJECT_ID" --format="value(name)" 2>/dev/null || echo "")
    for table_path in $TABLES; do
      table_name=$(basename "$table_path")
      log_info "  Deleting Iceberg table '${table_name}'..."
      $BIGLAKE_CMD iceberg tables delete "$table_name" \
        --namespace="$DATASET_NAME" --catalog="$ICEBERG_CATALOG" \
        --project="$PROJECT_ID" --quiet 2>/dev/null || true
    done
    $BIGLAKE_CMD iceberg namespaces delete "$DATASET_NAME" \
      --catalog="$ICEBERG_CATALOG" --project="$PROJECT_ID" --quiet 2>/dev/null || true
    log_ok "Iceberg namespace deleted."
else
    log_warn "Iceberg namespace '${DATASET_NAME}' not found. Skipping."
fi

if $BIGLAKE_CMD iceberg catalogs describe "$ICEBERG_CATALOG" --project="$PROJECT_ID" 2>/dev/null; then
    log_info "Deleting Iceberg catalog '${ICEBERG_CATALOG}'..."
    $BIGLAKE_CMD iceberg catalogs delete "$ICEBERG_CATALOG" \
      --project="$PROJECT_ID" --quiet 2>/dev/null || true
    log_ok "Iceberg catalog deleted."
else
    log_warn "Iceberg catalog '${ICEBERG_CATALOG}' not found. Skipping."
fi

# =============================================================================
# 4. Delete BigQuery Dataset
# =============================================================================
if bq show --project_id="$PROJECT_ID" "$DATASET_NAME" &>/dev/null; then
    log_info "Deleting BigQuery Dataset '${DATASET_NAME}' and all tables..."
    bq --project_id="$PROJECT_ID" rm -r -f -d "$DATASET_NAME"
    log_ok "BigQuery dataset deleted."
else
    log_warn "BigQuery dataset '${DATASET_NAME}' not found. Skipping."
fi

# =============================================================================
# 5. Delete Cloud Storage Buckets
# =============================================================================
for bucket in "$RAW_BUCKET" "$MODELS_BUCKET"; do
  if gcloud storage buckets describe "gs://${bucket}" --project="$PROJECT_ID" &>/dev/null; then
      log_info "Deleting Cloud Storage Bucket gs://${bucket}..."
      gcloud storage rm -r "gs://${bucket}" --quiet
      log_ok "GCS Bucket gs://${bucket} deleted."
  else
      log_warn "GCS Bucket gs://${bucket} not found. Skipping."
  fi
done

# =============================================================================
# 6. Delete Service Account
# =============================================================================
if gcloud iam service-accounts describe "$COMPOSER_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
    log_info "Deleting Service Account ${COMPOSER_SA_EMAIL}..."
    
    # Remove project policy bindings
    log_info "Removing project IAM policy bindings for the service account..."
    ROLES=(
      roles/composer.worker
      roles/bigquery.admin
      roles/dataproc.editor
      roles/dataproc.worker
      roles/spanner.admin
      roles/storage.admin
      roles/iam.serviceAccountUser
    )
    for role in "${ROLES[@]}"; do
        gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:${COMPOSER_SA_EMAIL}" \
            --role="$role" --quiet &>/dev/null || true
    done
    
    # Delete SA
    gcloud iam service-accounts delete "$COMPOSER_SA_EMAIL" --project="$PROJECT_ID" --quiet
    log_ok "Service account deleted."
else
    log_warn "Service account ${COMPOSER_SA_EMAIL} not found. Skipping."
fi

# =============================================================================
# 7. Delete Local Data and Env
# =============================================================================
log_info "Cleaning up local files..."
rm -rf "$SCRIPT_DIR/data"
rm -f "$ENV_FILE"

log_ok "Teardown complete! All project resources cleaned up successfully."
