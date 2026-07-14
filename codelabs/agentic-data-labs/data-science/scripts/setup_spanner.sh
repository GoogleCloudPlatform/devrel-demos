#!/usr/bin/env bash
# Setup script for Cloud Spanner.
# Provisions a Cloud Spanner instance, database, and target review table.
# The SparkEvalFraudReviewQueue table schema matches the enriched fields
# that the batch inference notebook writes after scoring gold-layer data.
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
SPANNER_INSTANCE="${SPANNER_INSTANCE:-cymbal-fraud}"
SPANNER_DATABASE="${SPANNER_DATABASE:-fraud-db}"

if [[ -z "${PROJECT_ID:-}" ]]; then
    log_error "PROJECT_ID is not set. Check your .env file."
    exit 1
fi
if [[ -z "${REGION:-}" ]]; then
    log_error "REGION is not set. Check your .env file."
    exit 1
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Cloud Spanner Setup                                ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""
log_info "Project ID:       ${PROJECT_ID}"
log_info "Region:           ${REGION}"
log_info "Spanner Instance: ${SPANNER_INSTANCE}"
log_info "Spanner Database: ${SPANNER_DATABASE}"
echo ""

# Translate Region to Spanner Config
# e.g., us-west1 -> regional-us-west1
SPANNER_CONFIG="regional-${REGION}"

# =============================================================================
# STEP 1: Provision Spanner Instance
# =============================================================================
log_step "1" "Provisioning Spanner Instance"

if gcloud spanner instances describe "$SPANNER_INSTANCE" --project="$PROJECT_ID" &>/dev/null; then
    log_warn "Spanner instance '${SPANNER_INSTANCE}' already exists. Reusing it."
else
    log_info "Creating Spanner instance '${SPANNER_INSTANCE}' config '${SPANNER_CONFIG}' (typically takes 1-2 minutes)..."
    if ! gcloud spanner instances create "$SPANNER_INSTANCE" \
        --project="$PROJECT_ID" \
        --config="$SPANNER_CONFIG" \
        --description="Cymbal Fraud Review Instance" \
        --processing-units=100 \
        --quiet; then
        log_error "Failed to create Spanner instance '${SPANNER_INSTANCE}'."
        exit 1
    fi
    log_ok "Spanner instance '${SPANNER_INSTANCE}' created successfully."
fi

# =============================================================================
# STEP 2: Create Spanner Database and Tables
# =============================================================================
log_step "2" "Creating Spanner Database & Schema"

if gcloud spanner databases describe "$SPANNER_DATABASE" --instance="$SPANNER_INSTANCE" --project="$PROJECT_ID" &>/dev/null; then
    log_warn "Spanner database '${SPANNER_DATABASE}' already exists. Reusing it."
else
    log_info "Creating Spanner database '${SPANNER_DATABASE}'..."
    if ! gcloud spanner databases create "$SPANNER_DATABASE" \
        --instance="$SPANNER_INSTANCE" \
        --project="$PROJECT_ID" \
        --quiet; then
        log_error "Failed to create Spanner database '${SPANNER_DATABASE}'."
        exit 1
    fi
    log_ok "Spanner database '${SPANNER_DATABASE}' created."
fi

# Create the fraud review queue table.
# This schema matches the enriched gold-layer data plus prediction outputs
# that the batch inference notebook (03_inference.ipynb) writes via Spark JDBC.
log_info "Checking/Creating SparkEvalFraudReviewQueue table..."

DDL_STMT="CREATE TABLE SparkEvalFraudReviewQueue (
    transaction_id              STRING(36) NOT NULL,
    amount                      FLOAT64,
    currency                    STRING(10),
    device_id                   STRING(20),
    ip_address                  STRING(45),
    merchant_mcc                INT64,
    payee_id                    STRING(36),
    payment_method              STRING(50),
    payor_id                    STRING(36),
    status                      STRING(20),
    timestamp                   STRING(50),
    payor_name                  STRING(255),
    payor_country               STRING(10),
    payor_risk_score            FLOAT64,
    payee_name                  STRING(255),
    payee_country               STRING(10),
    payee_risk_score            FLOAT64,
    payee_category              STRING(50),
    is_fraud                    INT64,
    prediction                  FLOAT64
) PRIMARY KEY (transaction_id)"

# Check if table exists
if gcloud spanner databases ddl describe "$SPANNER_DATABASE" \
    --instance="$SPANNER_INSTANCE" --project="$PROJECT_ID" 2>/dev/null | grep -i -q "SparkEvalFraudReviewQueue"; then
    log_warn "Table SparkEvalFraudReviewQueue already exists. Updating schema..."
    if ! gcloud spanner databases ddl update "$SPANNER_DATABASE" \
        --instance="$SPANNER_INSTANCE" \
        --project="$PROJECT_ID" \
        --ddl="DROP TABLE SparkEvalFraudReviewQueue" \
        --quiet; then
        log_error "Failed to drop table 'SparkEvalFraudReviewQueue'."
        exit 1
    fi
fi

log_info "Applying DDL to create SparkEvalFraudReviewQueue table..."
if ! gcloud spanner databases ddl update "$SPANNER_DATABASE" \
    --instance="$SPANNER_INSTANCE" \
    --project="$PROJECT_ID" \
    --ddl="$DDL_STMT" \
    --quiet; then
    log_error "Failed to apply DDL to database '${SPANNER_DATABASE}'."
    exit 1
fi
log_ok "DDL schema successfully applied."

log_ok "Cloud Spanner setup completed successfully!"
