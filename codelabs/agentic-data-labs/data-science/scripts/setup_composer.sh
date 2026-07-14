#!/usr/bin/env bash
# Setup script for Managed Airflow (Cloud Composer) on Google Cloud.
# Provisions a minimal Managed Airflow environment with access to
# BigQuery, Spark / Dataproc, Spanner, Cloud Storage, and Cloud SQL.
#
# NOTE: This script is called by setup.sh which creates .env first.
#       It can also be run standalone if .env exists.

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

grant_iam_role_with_retry() {
  local project=$1
  local member=$2
  local role=$3
  local max_attempts=4
  local attempt=1
  local delay=5

  log_info "Granting $role to $member..."
  while [ $attempt -le $max_attempts ]; do
    if gcloud projects add-iam-policy-binding "$project" --format=none \
      --member="$member" --role="$role" --quiet &>/dev/null; then
        log_ok "Successfully granted $role."
        return 0
    else
        if [ $attempt -lt $max_attempts ]; then
          log_warn "IAM propagation delay. Retrying in ${delay}s (Attempt $attempt/$max_attempts)..."
          sleep $delay
          ((++attempt))
        else
          log_error "Failed to grant $role after $max_attempts attempts."
          return 1
        fi
    fi
  done
}

# --- Load .env (created by setup.sh) ---
ENV_FILE="$SCRIPT_DIR/../.env"

if [ ! -f "$ENV_FILE" ]; then
    log_error "Missing .env file at ${ENV_FILE}. Run setup.sh first."
    exit 1
fi

set -a
source "$ENV_FILE"
set +a

# --- Validate required vars ---
COMPOSER_ENVIRONMENT="${COMPOSER_ENVIRONMENT:-cymbal-airflow}"
COMPOSER_SA_NAME="${COMPOSER_SA_NAME:-composer-worker-sa}"
IMAGE_VERSION="${IMAGE_VERSION:-}"

if [[ -z "${PROJECT_ID:-}" ]]; then
    log_error "PROJECT_ID is not set. Check your .env file."
    exit 1
fi
if [[ -z "${REGION:-}" ]]; then
    log_error "REGION is not set. Check your .env file."
    exit 1
fi

# Configure gcloud CLI
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1


COMPOSER_SA_EMAIL="${COMPOSER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Managed Airflow Setup                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Project ID:           ${PROJECT_ID}"
log_info "Region:               ${REGION}"
log_info "Composer Environment: ${COMPOSER_ENVIRONMENT}"
log_info "Service Account:      ${COMPOSER_SA_EMAIL}"
log_info "Environment Size:     small (minimal cost footprint)"
echo ""

# =============================================================================
# STEP 2: Provision Service Account & Grant IAM Roles
# =============================================================================
log_step "1" "Provisioning dedicated Service Account for Composer workers"

# Create Service Account if it does not exist
if gcloud iam service-accounts describe "$COMPOSER_SA_EMAIL" --project="$PROJECT_ID" &>/dev/null; then
  log_warn "Service account ${COMPOSER_SA_EMAIL} already exists. Reusing it."
else
  log_info "Creating service account ${COMPOSER_SA_NAME}..."
  gcloud iam service-accounts create "$COMPOSER_SA_NAME" \
    --project="$PROJECT_ID" \
    --display-name="Managed Airflow Worker Service Account" \
    --quiet 2>/dev/null
  log_ok "Created service account ${COMPOSER_SA_EMAIL}."
fi

log_info "Granting IAM roles for BigQuery, Spark/Dataproc, Spanner, GCS, and Composer..."

# NOTE: These roles are intentionally broad for codelab simplicity.
# In production, prefer least-privilege roles such as
# roles/bigquery.dataEditor + roles/bigquery.jobUser,
# roles/spanner.databaseUser, roles/storage.objectAdmin, etc.
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
  grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:${COMPOSER_SA_EMAIL}" "$role"
done

# Grant ServiceAgentV2Ext to Managed Airflow Service Agent on the project
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null)
COMPOSER_SERVICE_AGENT="service-${PROJECT_NUMBER}@cloudcomposer-accounts.iam.gserviceaccount.com"

# The Composer service agent is not auto-created by enabling the API.
# Explicitly provision it before granting roles.
log_info "Provisioning Managed Airflow service agent..."
gcloud beta services identity create --service=composer.googleapis.com \
  --project="$PROJECT_ID" &>/dev/null

log_info "Granting Managed Airflow Service Agent (${COMPOSER_SERVICE_AGENT}) required extension role..."
grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:${COMPOSER_SERVICE_AGENT}" "roles/composer.ServiceAgentV2Ext"

log_ok "All Service Account permissions successfully configured."

# =============================================================================
# STEP 2: Create Managed Airflow Environment (Smallest Instance)
# =============================================================================
log_step "2" "Creating Managed Airflow Environment (size=small)"

if gcloud composer environments describe "$COMPOSER_ENVIRONMENT" --project="$PROJECT_ID" --location="$REGION" &>/dev/null; then
  log_warn "Managed Airflow environment ${COMPOSER_ENVIRONMENT} already exists in ${REGION}. Skipping creation."
else
  log_info "Provisioning Managed Airflow environment '${COMPOSER_ENVIRONMENT}' in ${REGION} (this typically takes 15-25 minutes)..."
  
  CREATE_CMD=(
    gcloud composer environments create "$COMPOSER_ENVIRONMENT"
    --project="$PROJECT_ID"
    --location="$REGION"
    --image-version="${IMAGE_VERSION:-composer-3-airflow-2.11.1}"
    --environment-size=small
    --service-account="${COMPOSER_SA_EMAIL}"
    --quiet
  )

  if ! "${CREATE_CMD[@]}"; then
      log_error "Managed Airflow environment creation failed!"
      exit 1
  fi
  log_ok "Managed Airflow environment '${COMPOSER_ENVIRONMENT}' created successfully."
fi

# =============================================================================
# STEP 4: Install Required PyPI Packages
# =============================================================================
log_step "3" "Installing PyPI packages for dbt and orchestration"

log_info "Installing dbt-bigquery and orchestration-pipelines..."
gcloud composer environments update "$COMPOSER_ENVIRONMENT" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --update-pypi-packages-from-file=/dev/stdin --quiet <<'PYPI'
dbt-bigquery
orchestration-pipelines
PYPI
log_ok "PyPI packages installed."

# =============================================================================
# STEP 5: Retrieve Metadata & Update Local Environment Configuration
# =============================================================================
log_step "4" "Retrieving environment metadata and updating .env"

COMPOSER_DAGS_BUCKET=$(gcloud composer environments describe "$COMPOSER_ENVIRONMENT" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --format="value(config.dagGcsPrefix)" 2>/dev/null || echo "")

AIRFLOW_URI=$(gcloud composer environments describe "$COMPOSER_ENVIRONMENT" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --format="value(config.airflowUri)" 2>/dev/null || echo "")

log_info "DAGs GCS Bucket: ${COMPOSER_DAGS_BUCKET}"
log_info "Airflow Web UI:  ${AIRFLOW_URI}"

# Append runtime-discovered values to .env.
# Only these two are new — everything else was already written by setup.sh.
# No race condition: this runs ~20 min after setup.sh finishes writing .env.
update_env_var() {
  local key=$1
  local value=$2
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "$ENV_FILE" && rm -f "${ENV_FILE}.bak"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

update_env_var "COMPOSER_DAGS_BUCKET" "$COMPOSER_DAGS_BUCKET"
update_env_var "AIRFLOW_URI" "$AIRFLOW_URI"

log_ok "Updated ${ENV_FILE} with Composer DAGs bucket and Airflow URI."

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Managed Airflow Setup Complete!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Your Managed Airflow environment is ready."
echo ""
echo -e "  ${BLUE}Project ID:           ${NC}${PROJECT_ID}"
echo -e "  ${BLUE}Region:               ${NC}${REGION}"
echo -e "  ${BLUE}Environment:          ${NC}${COMPOSER_ENVIRONMENT}"
echo -e "  ${BLUE}Worker Service Acct:  ${NC}${COMPOSER_SA_EMAIL}"
echo -e "  ${BLUE}DAGs GCS Bucket:      ${NC}${COMPOSER_DAGS_BUCKET}"
echo -e "  ${BLUE}Airflow Web UI:       ${NC}${AIRFLOW_URI}"
echo ""
echo -e "Included Service Access (IAM Roles):"
echo -e "  • BigQuery          (roles/bigquery.admin)"
echo -e "  • Spark / Dataproc  (roles/dataproc.editor, roles/dataproc.worker)"
echo -e "  • Cloud Spanner     (roles/spanner.admin)"
echo -e "  • Cloud Storage     (roles/storage.admin)"
echo ""
echo -e "To upload DAGs to this Airflow environment, copy your Python DAG files to:"
echo -e "  ${YELLOW}gcloud storage cp path/to/dag.py ${COMPOSER_DAGS_BUCKET}/${NC}"
echo ""


