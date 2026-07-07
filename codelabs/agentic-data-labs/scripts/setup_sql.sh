#!/usr/bin/env bash
# Background Cloud SQL deployer for the DAK Cymbal Pets codelab.
# Launched by setup.sh to provision and configure Cloud SQL in the background.

set -euo pipefail

# --- Configuration (Must match setup.sh) ---
TARGET_DATASET="cymbal_pets"
REGION="us-central1"
CLOUDSQL_INSTANCE="cymbal-pets-ops"
CLOUDSQL_TIER="db-f1-micro"
CLOUDSQL_DB="cymbal_pets_ops"
BQ_CONNECTION="cymbal-pets-cloudsql"

# --- Colors for Logging ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${RED}[ERROR]${NC} $1"; }

# --- Helpers ---
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
          log_warn "IAM propagation delay encountered. Retrying in ${delay}s (Attempt $attempt/$max_attempts)..."
          sleep $delay
          ((attempt++))
        else
          log_error "Failed to grant $role after $max_attempts attempts."
          return 1
        fi
    fi
  done
}

# --- Config & Environment ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Load environment from .env if it exists
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Determine Project ID (env/gcloud config/arguments)
PROJECT_ID="${1:-${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}}"
if [[ -z "$PROJECT_ID" ]]; then
  log_error "No project ID provided. Background setup aborted."
  exit 1
fi

if [[ -z "${CLOUDSQL_PASSWORD:-}" ]]; then
  log_error "No CLOUDSQL_PASSWORD provided in .env. Background setup aborted."
  exit 1
fi

GCS_BUCKET="gs://${PROJECT_ID}-cymbal-pets-raw"

log_info "Background setup started for project: ${PROJECT_ID}"

# =============================================================================
# PHASE 1: Provision Cloud SQL Postgres (with pre-configured parameters)
# =============================================================================
log_info "Starting Cloud SQL instance creation (takes ~5 minutes)..."

# Check if instance already exists
if gcloud sql instances describe "$CLOUDSQL_INSTANCE" --project="$PROJECT_ID" &>/dev/null; then
  log_warn "Cloud SQL instance ${CLOUDSQL_INSTANCE} already exists. Skipping creation."
else
  if ! gcloud beta sql instances create "$CLOUDSQL_INSTANCE" \
    --project="$PROJECT_ID" \
    --database-version=POSTGRES_15 \
    --tier="$CLOUDSQL_TIER" \
    --region="$REGION" \
    --database-flags=cloudsql.iam_authentication=on \
    --data-api-access=ALLOW_DATA_API \
    --storage-auto-increase \
    --quiet > /dev/null 2>&1; then
    
    log_error "Cloud SQL instance creation failed!"
    exit 1
  fi
  log_ok "Cloud SQL instance ${CLOUDSQL_INSTANCE} created successfully."
fi

# =============================================================================
# PHASE 2: Configure Users and Database
# =============================================================================
log_info "Configuring Postgres superuser password..."
gcloud sql users set-password postgres \
  --instance="$CLOUDSQL_INSTANCE" \
  --project="$PROJECT_ID" \
  --password="$CLOUDSQL_PASSWORD" \
  --quiet > /dev/null 2>&1 || true

log_info "Creating database ${CLOUDSQL_DB}..."
gcloud sql databases create "$CLOUDSQL_DB" \
  --instance="$CLOUDSQL_INSTANCE" \
  --project="$PROJECT_ID" \
  --quiet > /dev/null 2>&1 \
  || log_warn "Database ${CLOUDSQL_DB} may already exist."

log_ok "Database ${CLOUDSQL_DB} ready."

# Create IAM database user for developer
CURRENT_USER_EMAIL=$(gcloud config get-value account 2>/dev/null)
if [[ -n "$CURRENT_USER_EMAIL" ]]; then
  log_info "Creating IAM database user for ${CURRENT_USER_EMAIL}..."
  gcloud sql users create "$CURRENT_USER_EMAIL" \
    --instance="$CLOUDSQL_INSTANCE" \
    --project="$PROJECT_ID" \
    --type=CLOUD_IAM_USER \
    --quiet > /dev/null 2>&1 \
    || log_info "IAM user already exists."
  log_ok "IAM database user created."
else
  log_warn "Current user email not found. Direct IAM authentication may require manual setup."
fi

# =============================================================================
# PHASE 3: Initialize Schema and Import Data
# =============================================================================
# Grant Cloud SQL Service Account GCS access (needed for SQL/CSV imports)
CLOUDSQL_SA=$(gcloud sql instances describe "$CLOUDSQL_INSTANCE" \
  --project="$PROJECT_ID" \
  --format="value(serviceAccountEmailAddress)" 2>/dev/null)

if [[ -n "$CLOUDSQL_SA" ]]; then
  gcloud storage buckets add-iam-policy-binding "$GCS_BUCKET" \
    --member="serviceAccount:${CLOUDSQL_SA}" \
    --role="roles/storage.objectViewer" \
    --quiet > /dev/null 2>&1
  log_ok "Granted objectViewer on ${GCS_BUCKET} to Cloud SQL service account."
fi

# Wait for GCS CSV exports to be fully completed by the foreground script
log_info "Waiting for GCS CSV exports to complete..."
MAX_WAIT_ATTEMPTS=100
WAIT_ATTEMPT=0
while ! gcloud storage ls "${GCS_BUCKET}/export/products.csv" &>/dev/null; do
  ((WAIT_ATTEMPT++))
  if [ $WAIT_ATTEMPT -ge $MAX_WAIT_ATTEMPTS ]; then
    log_error "Timed out waiting for CSV exports in GCS after $((MAX_WAIT_ATTEMPTS * 3))s. Did setup.sh complete successfully?"
    exit 1
  fi
  sleep 3
done
log_ok "GCS CSV files detected. Proceeding with database loading."

# Create Consolidated init_db.sql (Schemas + IAM developer grants)
log_info "Generating consolidated DB initialization SQL script..."
cat > /tmp/_init_db.sql <<EOF
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS pet_profiles;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY,
  first_name VARCHAR(100), last_name VARCHAR(200), email VARCHAR(200),
  gender VARCHAR(10), address_city VARCHAR(200), address_state VARCHAR(100),
  loyalty_member BOOLEAN, customer_type VARCHAR(50), signup_date DATE
);

CREATE TABLE pet_profiles (
  pet_id INTEGER PRIMARY KEY,
  customer_id INTEGER, pet_name VARCHAR(100), pet_type VARCHAR(50),
  age INTEGER, weight INTEGER, activity_level VARCHAR(50), dietary_needs VARCHAR(100)
);

CREATE TABLE products (
  product_id INTEGER PRIMARY KEY,
  product_name VARCHAR(300), category VARCHAR(100), subcategory VARCHAR(100),
  brand VARCHAR(100), price DECIMAL(10,2), description TEXT,
  inventory_level INTEGER, supplier_id INTEGER, average_rating DECIMAL(3,1), cost DECIMAL(10,2)
);
EOF

if [[ -n "${CURRENT_USER_EMAIL:-}" ]]; then
  cat >> /tmp/_init_db.sql <<EOF
-- Grant permissions to IAM user (role created by gcloud sql users create --type=CLOUD_IAM_USER)
DO \$\$
BEGIN
  GRANT USAGE ON SCHEMA public TO "${CURRENT_USER_EMAIL}";
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO "${CURRENT_USER_EMAIL}";
  GRANT cloudsqlsuperuser TO "${CURRENT_USER_EMAIL}";
EXCEPTION WHEN undefined_object THEN
  RAISE NOTICE 'IAM user role not found, skipping grants';
END \$\$;
EOF
fi

gcloud storage cp /tmp/_init_db.sql "${GCS_BUCKET}/temp/_init_db.sql" --quiet > /dev/null 2>&1
log_info "Executing schema DDL and user grant scripts..."
if ! gcloud sql import sql "$CLOUDSQL_INSTANCE" \
  "${GCS_BUCKET}/temp/_init_db.sql" \
  --project="$PROJECT_ID" \
  --database="$CLOUDSQL_DB" \
  --user=postgres \
  --quiet > /dev/null 2>&1; then
  log_error "Failed to initialize schema and permissions in Cloud SQL."
  exit 1
fi
rm -f /tmp/_init_db.sql
log_ok "Cloud SQL tables and permissions initialized."

# Import CSV files
COLS_customers="customer_id,first_name,last_name,email,gender,address_city,address_state,loyalty_member,customer_type,signup_date"
COLS_pet_profiles="pet_id,customer_id,pet_name,pet_type,age,weight,activity_level,dietary_needs"
COLS_products="product_id,product_name,category,subcategory,brand,price,description,inventory_level,supplier_id,average_rating,cost"

for table in customers pet_profiles products; do
  eval "COLUMNS=\$COLS_${table}"
  log_info "Importing ${table} CSV data into Cloud SQL..."
  if ! gcloud sql import csv "$CLOUDSQL_INSTANCE" \
    "${GCS_BUCKET}/export/${table}.csv" \
    --project="$PROJECT_ID" \
    --database="$CLOUDSQL_DB" \
    --table="$table" \
    --columns="$COLUMNS" \
    --quiet > /dev/null 2>&1; then
    log_error "Failed to import ${table} CSV data."
    exit 1
  fi
  log_ok "${table} data successfully loaded."
done

# =============================================================================
# PHASE 4: Establish BigQuery Federated Connection
# =============================================================================
log_info "Creating BigQuery federated connection to Cloud SQL..."
CLOUDSQL_CONNECTION=$(gcloud sql instances describe "$CLOUDSQL_INSTANCE" \
  --project="$PROJECT_ID" \
  --format="value(connectionName)" 2>/dev/null)

bq mk --connection \
  --project_id="$PROJECT_ID" \
  --location=US \
  --connection_type=CLOUD_SQL \
  --properties="{\"instanceId\":\"${CLOUDSQL_CONNECTION}\",\"database\":\"${CLOUDSQL_DB}\",\"type\":\"POSTGRES\"}" \
  --connection_credential="{\"username\":\"postgres\",\"password\":\"${CLOUDSQL_PASSWORD}\"}" \
  "$BQ_CONNECTION" > /dev/null 2>&1 \
  || log_warn "BQ Connection may already exist."

# Grant Connection Service Account Cloud SQL Client permissions
BQ_CONN_SA=$(bq show --connection --format=json "${PROJECT_ID}.US.${BQ_CONNECTION}" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['cloudSql']['serviceAccountId'])" 2>/dev/null)

if [[ -n "$BQ_CONN_SA" ]]; then
  grant_iam_role_with_retry "$PROJECT_ID" "serviceAccount:${BQ_CONN_SA}" "roles/cloudsql.client"
fi

# Allow IAM permission to propagate
log_info "Waiting 5s for federated query permissions to propagate..."
sleep 5

# =============================================================================
# PHASE 5: Verify Ingestion and Clean Up BigQuery
# =============================================================================
log_info "Verifying Cloud SQL data via BigQuery Connection..."
CUSTOMER_COUNT=$(bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --format=csv --quiet \
  "SELECT * FROM EXTERNAL_QUERY('${PROJECT_ID}.us.${BQ_CONNECTION}', 'SELECT COUNT(*) FROM customers;')" 2>/dev/null \
  | tail -n 1 | grep -oE '[0-9]+' || echo "")

if [[ -z "$CUSTOMER_COUNT" || "$CUSTOMER_COUNT" -lt 1000 ]]; then
  log_error "Cloud SQL verification failed (got ${CUSTOMER_COUNT:-0} customers). Not dropping BigQuery tables."
  exit 1
fi
log_ok "Cloud SQL verified successfully: ${CUSTOMER_COUNT} customers active in database."

# Safe to drop operational tables from BigQuery
for table in customers pet_profiles products; do
  log_info "Dropping operational table ${TARGET_DATASET}.${table} from BigQuery..."
  bq rm --force --project_id="$PROJECT_ID" "${PROJECT_ID}:${TARGET_DATASET}.${table}" > /dev/null 2>&1
done

# Clean up GCS temp and export files
gcloud storage rm -r "${GCS_BUCKET}/export/" > /dev/null 2>&1 || true
gcloud storage rm -r "${GCS_BUCKET}/temp/" > /dev/null 2>&1 || true
log_ok "Cleaned up temporary extraction files in GCS."

log_info "===================================================="
log_ok " Cloud SQL Background Setup Successfully Completed!"
log_info "===================================================="
