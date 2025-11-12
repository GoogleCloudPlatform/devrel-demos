#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status

# ====================================================
# Environment Configuration
# ====================================================
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"
ENTRY_GROUP="@bigquery"

# ====================================================
# Function to apply governance aspects
# ====================================================
apply_governance() {
    local DATASET=$1
    local TABLE=$2
    local YAML_FILE=$3
    # Dataplex Entry ID format
    local ENTRY_ID="bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/${DATASET}/tables/${TABLE}"

    echo "👉 Processing: ${DATASET}.${TABLE}..."
    
    # Execute update via gcloud command
    gcloud dataplex entries update "${ENTRY_ID}" \
        --project="${PROJECT_ID}" \
        --location="${REGION}" \
        --entry-group="${ENTRY_GROUP}" \
        --update-aspects="./aspect_payloads/${YAML_FILE}" \
        --quiet

    echo "   -> ✅ Success!"
}

echo "🚀 [Start] Applying governance aspects via gcloud..."

# ====================================================
# Execute application for each scenario
# ====================================================

# Scenario A: CFO Internal
apply_governance "finance_mart" "fin_monthly_closing_internal" "fin_internal.yaml"

# Scenario B: Public Report
apply_governance "finance_mart" "fin_quarterly_public_report" "fin_public.yaml"

# Scenario C: Marketing Realtime
apply_governance "marketing_prod" "mkt_realtime_campaign_performance" "mkt_realtime.yaml"

# Scenario D: Analyst Sandbox (The Trap)
apply_governance "analyst_sandbox" "tmp_data_dump_v2_final_real" "sandbox_dump.yaml"

echo "✨ All governance aspects applied successfully!"