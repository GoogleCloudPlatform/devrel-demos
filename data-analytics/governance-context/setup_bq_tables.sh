#!/bin/bash
# ==============================================================================
# setup_bq_tables.sh
# Sets up the BigQuery datasets, tables, and sample data for the
# Governance-Aware GenAI Agent Codelab.
# ==============================================================================
set -e

# --- Configuration ---
export PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "${PROJECT_ID}" ]; then
  echo "❌ Error: Google Cloud Project ID is not set. Run 'gcloud config set project [PROJECT_ID]' first."
  exit 1
fi

export REGION="${REGION:-us-central1}"
echo "🚀 [Start] Setting up BigQuery Datasets and Tables in Project: ${PROJECT_ID}, Region: ${REGION}"

# --- 1. Create BigQuery Datasets ---
echo "📊 Creating BigQuery Datasets..."
for dataset in finance_mart marketing_prod analyst_sandbox; do
  if ! bq show --dataset "${PROJECT_ID}:${dataset}" >/dev/null 2>&1; then
    echo "  -> Creating dataset ${dataset}..."
    bq mk --dataset --location="${REGION}" "${PROJECT_ID}:${dataset}"
  else
    echo "  -> Dataset ${dataset} already exists."
  fi
done

# --- 2. Create BigQuery Tables ---
echo "📝 Creating BigQuery Tables..."

# finance_mart.fin_monthly_closing_internal
if ! bq show "${PROJECT_ID}:finance_mart.fin_monthly_closing_internal" >/dev/null 2>&1; then
  echo "  -> Creating table finance_mart.fin_monthly_closing_internal..."
  bq mk --table "${PROJECT_ID}:finance_mart.fin_monthly_closing_internal" \
    closing_date:DATE,revenue_amt:FLOAT,cost_amt:FLOAT,profit_amt:FLOAT,status:STRING
else
  echo "  -> Table finance_mart.fin_monthly_closing_internal already exists."
fi

# finance_mart.fin_quarterly_public_report
if ! bq show "${PROJECT_ID}:finance_mart.fin_quarterly_public_report" >/dev/null 2>&1; then
  echo "  -> Creating table finance_mart.fin_quarterly_public_report..."
  bq mk --table "${PROJECT_ID}:finance_mart.fin_quarterly_public_report" \
    quarter_name:STRING,public_revenue:FLOAT,public_operating_income:FLOAT,disclosure_date:DATE
else
  echo "  -> Table finance_mart.fin_quarterly_public_report already exists."
fi

# marketing_prod.mkt_realtime_campaign_performance
if ! bq show "${PROJECT_ID}:marketing_prod.mkt_realtime_campaign_performance" >/dev/null 2>&1; then
  echo "  -> Creating table marketing_prod.mkt_realtime_campaign_performance..."
  bq mk --table "${PROJECT_ID}:marketing_prod.mkt_realtime_campaign_performance" \
    event_time:TIMESTAMP,campaign_id:STRING,estimated_revenue:FLOAT
else
  echo "  -> Table marketing_prod.mkt_realtime_campaign_performance already exists."
fi

# analyst_sandbox.tmp_data_dump_v2_final_real
if ! bq show "${PROJECT_ID}:analyst_sandbox.tmp_data_dump_v2_final_real" >/dev/null 2>&1; then
  echo "  -> Creating table analyst_sandbox.tmp_data_dump_v2_final_real..."
  bq mk --table "${PROJECT_ID}:analyst_sandbox.tmp_data_dump_v2_final_real" \
    col1:STRING,val:FLOAT
else
  echo "  -> Table analyst_sandbox.tmp_data_dump_v2_final_real already exists."
fi

# --- 3. Populate Tables with Sample Data ---
echo "📥 Loading sample data into BigQuery tables..."

# finance_mart.fin_monthly_closing_internal
bq query --use_legacy_sql=false "
  INSERT INTO \`${PROJECT_ID}.finance_mart.fin_monthly_closing_internal\` (closing_date, revenue_amt, cost_amt, profit_amt, status)
  VALUES
    ('2024-01-31', 1500000.00, 900000.00, 600000.00, 'FINALIZED'),
    ('2024-02-29', 1450000.00, 850000.00, 600000.00, 'FINALIZED'),
    ('2024-03-31', 1600000.00, 950000.00, 650000.00, 'FINALIZED');
"

# finance_mart.fin_quarterly_public_report
bq query --use_legacy_sql=false "
  INSERT INTO \`${PROJECT_ID}.finance_mart.fin_quarterly_public_report\` (quarter_name, public_revenue, public_operating_income, disclosure_date)
  VALUES
    ('2024-Q1', 4550000.00, 1850000.00, '2024-04-15');
"

# marketing_prod.mkt_realtime_campaign_performance
bq query --use_legacy_sql=false "
  INSERT INTO \`${PROJECT_ID}.marketing_prod.mkt_realtime_campaign_performance\` (event_time, campaign_id, estimated_revenue)
  VALUES
    (TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE), 'CMP_SUMMER_EARLY', 120.50),
    (TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE), 'CMP_SUMMER_EARLY', 350.00),
    (CURRENT_TIMESTAMP(), 'CMP_BRAND_AWARENESS', 50.00);
"

# analyst_sandbox.tmp_data_dump_v2_final_real
bq query --use_legacy_sql=false "
  INSERT INTO \`${PROJECT_ID}.analyst_sandbox.tmp_data_dump_v2_final_real\` (col1, val)
  VALUES
    ('2024-01 data maybe?', 1500000),
    ('2024-01 data maybe?', 1500000),
    ('test_row', 99999999);
"

echo "✨ [Success] BigQuery Datasets and Tables setup completed successfully!"
