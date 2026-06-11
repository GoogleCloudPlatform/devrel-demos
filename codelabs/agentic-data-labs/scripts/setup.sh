#!/usr/bin/env bash
# Setup script for the DAK Cymbal Pets Investigation codelab.
# Provisions BigQuery, Cloud SQL, and GCS resources. Usage: ./setup.sh

set -euo pipefail

cd "$(dirname "$0")"

# --- Configuration ---
SOURCE_BUCKET="gs://sample-data-and-media/cymbal-pets/parquet"
TARGET_DATASET="cymbal_pets"
REGION="us-central1"
CLOUDSQL_INSTANCE="cymbal-pets-ops"
CLOUDSQL_TIER="db-f1-micro"
CLOUDSQL_DB="cymbal_pets_ops"
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

log_step() {
  echo ""
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}  Step $1: $2${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# --- Config & Environment ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

# Load environment from .env if it exists
if [ -f "$ENV_FILE" ]; then
    log_info "Loading environment variables from $ENV_FILE..."
    set -a
    source "$ENV_FILE"
    set +a
fi

# Determine Project ID (env/gcloud config/prompt)
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "$PROJECT_ID" ]]; then
    log_warn "No active project detected in gcloud config or environment."
    read -rp "Enter your Google Cloud Project ID: " PROJECT_ID
fi
if [[ -z "$PROJECT_ID" ]]; then
    log_error "Google Cloud Project ID cannot be empty."
    exit 1
fi

# Determine Cloud SQL Password
if [[ -z "${CLOUDSQL_PASSWORD:-}" ]]; then
    CLOUDSQL_PASSWORD=$(openssl rand -hex 8)
    log_ok "Auto-generated secure Cloud SQL password."
fi

# Save to .env file
log_info "Writing environment variables to $ENV_FILE..."
echo "PROJECT_ID=$PROJECT_ID" > "$ENV_FILE"
echo "REGION=$REGION" >> "$ENV_FILE"
echo "CLOUDSQL_PASSWORD=$CLOUDSQL_PASSWORD" >> "$ENV_FILE"

# Configure gcloud CLI
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1

GCS_BUCKET="gs://${PROJECT_ID}-cymbal-pets-raw"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   DAK Codelab: The Cymbal Pets Investigation         ║${NC}"
echo -e "${GREEN}║   Setting up environment...                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Project:       ${PROJECT_ID}"
log_info "Region:        ${REGION}"
log_info "Source data:   ${SOURCE_BUCKET}"
log_info "GCS bucket:    ${GCS_BUCKET}"
echo ""

# =============================================================================
# STEP 1: Enable APIs
# =============================================================================
log_step "1" "Enabling required APIs"

APIS=(
  bigquery.googleapis.com
  sqladmin.googleapis.com
  storage.googleapis.com
  dataplex.googleapis.com
  bigqueryconnection.googleapis.com
)

for api in "${APIS[@]}"; do
  log_info "Enabling ${api}..."
  gcloud services enable "$api" --project="$PROJECT_ID" --quiet 2>/dev/null || true
done
log_ok "All APIs enabled."

# =============================================================================
# STEP 2: Create GCS bucket for learner's working data
# =============================================================================
log_step "2" "Creating GCS bucket"

if gcloud storage ls "$GCS_BUCKET" &>/dev/null; then
  log_warn "Bucket ${GCS_BUCKET} already exists. Reusing it."
else
  gcloud storage buckets create "$GCS_BUCKET" --project="$PROJECT_ID" --location="$REGION" --quiet
  log_ok "Created bucket ${GCS_BUCKET}"
fi

# =============================================================================
# STEP 3: Create BigQuery dataset and load base tables from Parquet
# =============================================================================
log_step "3" "Creating BigQuery dataset and loading base tables from Parquet"

# Create the dataset
bq --project_id="$PROJECT_ID" mk --dataset \
  --location=US \
  --description="Cymbal Pets analytics dataset for DAK Codelab" \
  "${PROJECT_ID}:${TARGET_DATASET}" 2>/dev/null || log_warn "Dataset may already exist."

log_ok "Dataset ${TARGET_DATASET} ready."

# Load tables from public PARQUET files
# Source: gs://sample-data-and-media/cymbal-pets/tables/{table}/*.parquet

log_info "Loading customers from PARQUET..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "LOAD DATA INTO \`${PROJECT_ID}.${TARGET_DATASET}.customers\`
   OPTIONS(description='Cymbal Pets customers table')
   FROM FILES (
     uris = ['${SOURCE_BUCKET}/customers/*.parquet'],
     format = 'parquet'
   )"
log_ok "customers loaded."

log_info "Loading orders from PARQUET..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "LOAD DATA INTO \`${PROJECT_ID}.${TARGET_DATASET}.orders\`
   OPTIONS(description='Cymbal Pets orders table')
   FROM FILES (
     uris = ['${SOURCE_BUCKET}/orders/*.parquet'],
     format = 'parquet'
   )"
log_ok "orders loaded."

log_info "Loading order_items from PARQUET..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "LOAD DATA INTO \`${PROJECT_ID}.${TARGET_DATASET}.order_items\`
   OPTIONS(description='Cymbal Pets order items table')
   FROM FILES (
     uris = ['${SOURCE_BUCKET}/order_items/*.parquet'],
     format = 'parquet'
   )"
log_ok "order_items loaded."

log_info "Loading products from PARQUET..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "LOAD DATA INTO \`${PROJECT_ID}.${TARGET_DATASET}.products\`
   OPTIONS(description='Cymbal Pets products table')
   FROM FILES (
     uris = ['${SOURCE_BUCKET}/products/*.parquet'],
     format = 'parquet'
   )"
log_ok "products loaded."

log_info "Loading pet_profiles from PARQUET..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "LOAD DATA INTO \`${PROJECT_ID}.${TARGET_DATASET}.pet_profiles\`
   OPTIONS(description='Cymbal Pets pet profiles table')
   FROM FILES (
     uris = ['${SOURCE_BUCKET}/pet_profiles/*.parquet'],
     format = 'parquet'
   )"
log_ok "pet_profiles loaded."

log_ok "All base tables loaded."

# =============================================================================
# STEP 4: Start Cloud SQL background deployment worker
# =============================================================================
log_step "4" "Starting Cloud SQL instance provisioning (background)"
log_info "Spawning background worker process (setup_sql.sh)..."

# Launch setup_sql.sh in the background and redirect all output to a log file
nohup bash ./setup_sql.sh "$PROJECT_ID" > /tmp/cloudsql_setup.log 2>&1 &
CLOUDSQL_PID=$!

log_info "Cloud SQL background setup started (PID: ${CLOUDSQL_PID}). Logs are written to /tmp/cloudsql_setup.log"

# =============================================================================
# STEP 5: Augment data with B2B mystery (while Cloud SQL provisions)
# =============================================================================
log_step "5" "Augmenting data with B2B mystery narrative"

# 5a. Add new columns
log_info "Adding new columns to tables..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "ALTER TABLE \`${PROJECT_ID}.${TARGET_DATASET}.customers\`
   ADD COLUMN IF NOT EXISTS customer_type STRING,
   ADD COLUMN IF NOT EXISTS signup_date DATE"

bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "ALTER TABLE \`${PROJECT_ID}.${TARGET_DATASET}.orders\`
   ADD COLUMN IF NOT EXISTS promo_code STRING"

bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "ALTER TABLE \`${PROJECT_ID}.${TARGET_DATASET}.products\`
   ADD COLUMN IF NOT EXISTS cost FLOAT64"

log_info "Adding column descriptions to clarify line vs unit price..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "ALTER TABLE \`${PROJECT_ID}.${TARGET_DATASET}.order_items\`
   ALTER COLUMN price SET OPTIONS(description='The total price for this line item (unit_price * quantity), with any applicable discounts already applied'),
   ALTER COLUMN quantity SET OPTIONS(description='The number of units purchased for this line item')"

log_ok "Columns and descriptions added."

# 5b. Backfill existing customer data
log_info "Backfilling existing customers as 'Individual'..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "UPDATE \`${PROJECT_ID}.${TARGET_DATASET}.customers\`
   SET
     customer_type = 'Individual',
     signup_date = DATE_SUB('2025-01-01', INTERVAL CAST(FLOOR(RAND() * 730) AS INT64) DAY)
   WHERE customer_type IS NULL"

# 5c. Set product costs
log_info "Setting product costs (55-70% of price)..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "UPDATE \`${PROJECT_ID}.${TARGET_DATASET}.products\`
   SET cost = ROUND(price * (0.55 + RAND() * 0.15), 2)
   WHERE cost IS NULL"

# 5d. Fix dietary_needs in pet_profiles
log_info "Fixing pet dietary needs with realistic values..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "UPDATE \`${PROJECT_ID}.${TARGET_DATASET}.pet_profiles\`
   SET dietary_needs = CASE
     WHEN pet_type = 'Dog' AND MOD(pet_id, 5) = 0 THEN 'grain-free'
     WHEN pet_type = 'Dog' AND MOD(pet_id, 5) = 1 THEN 'high-protein'
     WHEN pet_type = 'Dog' AND MOD(pet_id, 5) = 2 THEN 'weight-management'
     WHEN pet_type = 'Dog' AND MOD(pet_id, 5) = 3 THEN 'sensitive-stomach'
     WHEN pet_type = 'Dog' AND MOD(pet_id, 5) = 4 THEN 'puppy-formula'
     WHEN pet_type = 'Cat' AND MOD(pet_id, 5) = 0 THEN 'indoor-formula'
     WHEN pet_type = 'Cat' AND MOD(pet_id, 5) = 1 THEN 'hairball-control'
     WHEN pet_type = 'Cat' AND MOD(pet_id, 5) = 2 THEN 'grain-free'
     WHEN pet_type = 'Cat' AND MOD(pet_id, 5) = 3 THEN 'senior-formula'
     WHEN pet_type = 'Cat' AND MOD(pet_id, 5) = 4 THEN 'urinary-health'
     WHEN pet_type = 'Fish' AND MOD(pet_id, 3) = 0 THEN 'tropical-flakes'
     WHEN pet_type = 'Fish' AND MOD(pet_id, 3) = 1 THEN 'bottom-feeder-pellets'
     WHEN pet_type = 'Fish' AND MOD(pet_id, 3) = 2 THEN 'color-enhancing'
     WHEN pet_type = 'Bird' AND MOD(pet_id, 3) = 0 THEN 'seed-mix'
     WHEN pet_type = 'Bird' AND MOD(pet_id, 3) = 1 THEN 'pellet-diet'
     WHEN pet_type = 'Bird' AND MOD(pet_id, 3) = 2 THEN 'fruit-supplement'
     WHEN pet_type = 'Reptile' AND MOD(pet_id, 3) = 0 THEN 'calcium-enriched'
     WHEN pet_type = 'Reptile' AND MOD(pet_id, 3) = 1 THEN 'insect-based'
     WHEN pet_type = 'Reptile' AND MOD(pet_id, 3) = 2 THEN 'vitamin-supplement'
     ELSE 'standard'
   END
   WHERE TRUE"

log_ok "Pet dietary needs fixed."

# 5e. Insert B2B customers
log_info "Inserting 100 B2B customers..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "INSERT INTO \`${PROJECT_ID}.${TARGET_DATASET}.customers\`
     (customer_id, first_name, last_name, email, gender, address_city, address_state,
      loyalty_member, customer_type, signup_date)
   SELECT
     100000 + num AS customer_id,
     CASE MOD(num, 10)
       WHEN 0 THEN 'James' WHEN 1 THEN 'Maria' WHEN 2 THEN 'Robert'
       WHEN 3 THEN 'Linda' WHEN 4 THEN 'David' WHEN 5 THEN 'Sarah'
       WHEN 6 THEN 'Michael' WHEN 7 THEN 'Jennifer' WHEN 8 THEN 'William'
       WHEN 9 THEN 'Patricia'
     END AS first_name,
     CASE MOD(num, 12)
       WHEN 0 THEN 'Pet Supply Co' WHEN 1 THEN 'Animal Care LLC'
       WHEN 2 THEN 'Happy Paws Inc' WHEN 3 THEN 'Furry Friends Wholesale'
       WHEN 4 THEN 'PetMart Distribution' WHEN 5 THEN 'Critter Commerce'
       WHEN 6 THEN 'Tail Waggers Supply' WHEN 7 THEN 'Paw Palace Wholesale'
       WHEN 8 THEN 'Pet Paradise Group' WHEN 9 THEN 'Bark & Meow Trading'
       WHEN 10 THEN 'Four Legs Wholesale' WHEN 11 THEN 'Companion Care Dist'
     END AS last_name,
     CONCAT('contact', CAST(num AS STRING), '@petsupply.biz') AS email,
     CASE WHEN MOD(num, 2) = 0 THEN 'm' ELSE 'f' END AS gender,
     CASE MOD(num, 8)
       WHEN 0 THEN 'Houston' WHEN 1 THEN 'Phoenix' WHEN 2 THEN 'San Antonio'
       WHEN 3 THEN 'Dallas' WHEN 4 THEN 'Denver' WHEN 5 THEN 'Portland'
       WHEN 6 THEN 'Charlotte' WHEN 7 THEN 'Nashville'
     END AS address_city,
     CASE MOD(num, 8)
       WHEN 0 THEN 'Texas' WHEN 1 THEN 'Arizona' WHEN 2 THEN 'Texas'
       WHEN 3 THEN 'Texas' WHEN 4 THEN 'Colorado' WHEN 5 THEN 'Oregon'
       WHEN 6 THEN 'North Carolina' WHEN 7 THEN 'Tennessee'
     END AS address_state,
     FALSE AS loyalty_member,
     'Business' AS customer_type,
     DATE_ADD('2025-01-01', INTERVAL CAST(FLOOR(RAND() * 28) AS INT64) DAY) AS signup_date
   FROM UNNEST(GENERATE_ARRAY(1, 100)) AS num"

log_ok "B2B customers inserted."

# 5f. Insert B2B orders
log_info "Inserting ~25,000 B2B-Wholesale orders..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "INSERT INTO \`${PROJECT_ID}.${TARGET_DATASET}.orders\`
     (order_id, customer_id, order_date, order_type, payment_method,
      shipping_address_city, store_id, promo_code)
   SELECT
     2000000 + ROW_NUMBER() OVER () AS order_id,
     100000 + CAST(FLOOR(RAND() * 100) + 1 AS INT64) AS customer_id,
     DATE_ADD('2025-01-01', INTERVAL CAST(FLOOR(RAND() * 31) AS INT64) DAY) AS order_date,
     'B2B-Wholesale' AS order_type,
     CASE WHEN RAND() < 0.7 THEN 'Invoice' ELSE 'Credit Card' END AS payment_method,
     CAST(NULL AS STRING) AS shipping_address_city,
     CAST(NULL AS INT64) AS store_id,
     CASE WHEN RAND() < 0.92 THEN 'BIGORDER25' ELSE NULL END AS promo_code
   FROM UNNEST(GENERATE_ARRAY(1, 25000)) AS num"

log_ok "B2B orders inserted."

# 5g. Insert B2B order items
log_info "Inserting B2B order line items (2 items per order)..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "INSERT INTO \`${PROJECT_ID}.${TARGET_DATASET}.order_items\`
     (order_item_id, order_id, product_id, quantity, price)
   WITH b2b_products AS (
     SELECT product_id, price, ROUND(price * 0.75, 2) AS discounted_price,
            ROW_NUMBER() OVER (ORDER BY product_id) AS prod_row
     FROM \`${PROJECT_ID}.${TARGET_DATASET}.products\`
     WHERE category IN ('Food', 'Health & Wellness')
   ),
   b2b_orders_expanded AS (
     SELECT o.order_id, item_num,
            1 + MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(o.order_id AS STRING), CAST(item_num AS STRING)))),
                    (SELECT COUNT(*) FROM b2b_products)) AS prod_idx,
            CAST(1 + MOD(ABS(FARM_FINGERPRINT(CONCAT(CAST(o.order_id AS STRING), CAST(item_num AS STRING)))), 4) AS INT64) AS quantity
     FROM \`${PROJECT_ID}.${TARGET_DATASET}.orders\` o
     CROSS JOIN UNNEST(GENERATE_ARRAY(1, 2)) AS item_num
     WHERE o.order_type = 'B2B-Wholesale'
   )
   SELECT
     5000000 + ROW_NUMBER() OVER () AS order_item_id,
     e.order_id,
     p.product_id,
     e.quantity,
     p.discounted_price * e.quantity AS price
   FROM b2b_orders_expanded e
   JOIN b2b_products p ON p.prod_row = e.prod_idx"

log_ok "B2B order items inserted."

# 5h. Verify the AOV impact
log_info "Verifying AOV impact for January 2025..."
bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
  "SELECT
     order_type,
     COUNT(DISTINCT o.order_id) AS order_count,
     ROUND(SUM(oi.price) / COUNT(DISTINCT o.order_id), 2) AS aov
   FROM \`${PROJECT_ID}.${TARGET_DATASET}.orders\` o
   JOIN \`${PROJECT_ID}.${TARGET_DATASET}.order_items\` oi ON o.order_id = oi.order_id
   WHERE o.order_date >= '2025-01-01' AND o.order_date < '2025-02-01'
   GROUP BY order_type
   ORDER BY order_type" > /dev/null 2>&1
# ---- Define column lists (used for both BQ export and Cloud SQL import) ----
COLS_customers="customer_id,first_name,last_name,email,gender,address_city,address_state,loyalty_member,customer_type,signup_date"
COLS_pet_profiles="pet_id,customer_id,pet_name,pet_type,age,weight,activity_level,dietary_needs"
COLS_products="product_id,product_name,category,subcategory,brand,price,description,inventory_level,supplier_id,average_rating,cost"

# ---- Export each table from BQ to GCS as CSV in parallel with Cloud SQL creation ----
log_info "Exporting customer/pet/product data from BigQuery to GCS..."
for table in customers pet_profiles products; do
  eval "COLUMNS=\$COLS_${table}"

  log_info "Exporting ${table} from BigQuery to GCS..."
  if ! bq query --project_id="$PROJECT_ID" --use_legacy_sql=false --quiet \
    --destination_table="${PROJECT_ID}:${TARGET_DATASET}._export_${table}" \
    --replace \
    "SELECT ${COLUMNS} FROM \`${PROJECT_ID}.${TARGET_DATASET}.${table}\`" > /dev/null 2>&1; then
    log_error "Failed to create export table for ${table}."
    exit 1
  fi

  if ! bq extract --project_id="$PROJECT_ID" \
    --destination_format=CSV \
    --print_header=false \
    "${PROJECT_ID}:${TARGET_DATASET}._export_${table}" \
    "${GCS_BUCKET}/export/${table}.csv" > /dev/null 2>&1; then
    log_error "Failed to extract ${table} to CSV."
    exit 1
  fi

  bq rm -f --project_id="$PROJECT_ID" "${PROJECT_ID}:${TARGET_DATASET}._export_${table}" 2>/dev/null || true
  log_ok "${table} exported to GCS."
done

# =============================================================================
# STEP 6: Upload promo data to GCS
# =============================================================================
log_step "6" "Uploading promotional event data to GCS"

gcloud storage cp ../data/promo_events.json "${GCS_BUCKET}/promo_events.json"
log_ok "Promotional data uploaded to ${GCS_BUCKET}/promo_events.json"

# =============================================================================
# DONE
# =============================================================================
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Base Setup complete!                               ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Your core BigQuery and GCS assets are ready."
echo -e "Cloud SQL is currently provisioning in the background and will be fully ready by Step 4."
echo ""
echo -e "  ${BLUE}BigQuery:${NC}   ${PROJECT_ID}.${TARGET_DATASET}"
echo -e "            ├── orders"
echo -e "            └── order_items"
echo ""
echo -e "  ${BLUE}GCS:${NC}        ${GCS_BUCKET}"
echo -e "            └── promo_events.json"
echo ""
echo -e "Next: Open the Antigravity IDE and connect to project ${BLUE}${PROJECT_ID}${NC} to start the lab immediately!"
echo ""
echo -e "You can monitor the background database setup by running:"
echo -e "  ${YELLOW}tail -f /tmp/cloudsql_setup.log${NC}"
echo ""
echo -e "To clean up when done: ${YELLOW}./teardown.sh ${PROJECT_ID}${NC}"

