#!/usr/bin/env bash
# Teardown script for the DAK Cymbal Pets codelab.
# Deletes all GCP resources created by setup.sh. Usage: ./teardown.sh

set -euo pipefail

cd "$(dirname "$0")"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Helpers ---
log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Config & Environment ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Load environment from .env if it exists
if [ -f "$ENV_FILE" ]; then
    log_info "Loading environment variables from $ENV_FILE..."
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# || -z "$line" ]] && continue
        export "$line"
    done < "$ENV_FILE"
fi

PROJECT_ID="${1:-${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}}"
if [[ -z "${PROJECT_ID}" ]]; then
  log_warn "No active project detected in gcloud config or environment."
  read -rp "Please enter your Google Cloud Project ID: " PROJECT_ID
  if [[ -z "${PROJECT_ID}" ]]; then
    log_error "Project ID is required to perform the teardown."
    exit 1
  fi
fi

echo ""
echo -e "${YELLOW}This will delete all DAK Codelab resources in project: ${PROJECT_ID}${NC}"
echo ""
read -rp "Are you sure? [y/N]: " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
  echo "Cancelled."
  exit 0
fi
echo ""

log_info "Deleting BigQuery dataset cymbal_pets..."
if bq rm --recursive --force --dataset "${PROJECT_ID}:cymbal_pets" 2>/dev/null; then
  log_ok "BigQuery dataset cymbal_pets deleted."
else
  log_warn "BigQuery dataset cymbal_pets not found or already deleted."
fi

log_info "Deleting BigQuery dataset dbt_marts..."
if bq rm --recursive --force --dataset "${PROJECT_ID}:dbt_marts" 2>/dev/null; then
  log_ok "BigQuery dataset dbt_marts deleted."
else
  log_warn "BigQuery dataset dbt_marts not found or already deleted."
fi

log_info "Deleting GCS bucket..."
if gcloud storage rm -r "gs://${PROJECT_ID}-cymbal-pets-raw" 2>/dev/null; then
  log_ok "GCS bucket deleted."
else
  log_warn "GCS bucket not found or already deleted."
fi

log_info "Deleting BigQuery connection cymbal-pets-cloudsql..."
if bq rm --connection --force "${PROJECT_ID}.us.cymbal-pets-cloudsql" 2>/dev/null; then
  log_ok "BQ connection deleted."
else
  log_warn "BQ connection not found or already deleted."
fi

log_info "Deleting Cloud SQL instance cymbal-pets-ops (this takes a few minutes)..."
if gcloud sql instances delete cymbal-pets-ops --project="${PROJECT_ID}" --quiet 2>/dev/null; then
  log_ok "Cloud SQL instance deleted."
else
  log_warn "Cloud SQL instance not found or already deleted."
fi

log_info "Cleaning up local environment files..."
if rm -f "$ENV_FILE"; then
  log_ok "Removed .env file."
fi
if rm -f /tmp/cloudsql_setup.log; then
  log_ok "Removed /tmp/cloudsql_setup.log."
fi

echo ""
log_ok "Teardown complete."