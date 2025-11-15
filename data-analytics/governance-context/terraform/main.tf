provider "google" {
  project = var.project_id
  region  = var.region
}

# ==================================================================
# 1. Dataplex Aspect Type (The Governance Template)
# ==================================================================
resource "google_dataplex_aspect_type" "product_spec" {
  aspect_type_id = "official-data-product-spec"
  project        = var.project_id
  location       = var.region
  description    = "Defines the comprehensive profile of a data product for governance agents."

  metadata_template = <<EOF
{
  "name": "OfficialDataProductSpec",
  "type": "record",
  "recordFields": [
    {
      "name": "product_tier",
      "type": "enum",
      "annotations": { "displayName": "1. Criticality Tier", "description": "How critical is this data?" },
      "index": 1,
      "constraints": { "required": true },
      "enumValues": [
        { "name": "GOLD_CRITICAL", "index": 1 },
        { "name": "SILVER_STANDARD", "index": 2 },
        { "name": "BRONZE_ADHOC", "index": 3 }
      ]
    },
    {
      "name": "data_domain",
      "type": "enum",
      "annotations": { "displayName": "2. Owner Domain", "description": "Business domain responsible." },
      "index": 2,
      "constraints": { "required": true },
      "enumValues": [
        { "name": "FINANCE", "index": 1 },
        { "name": "MARKETING", "index": 2 },
        { "name": "LOGISTICS", "index": 3 }
      ]
    },
    {
      "name": "usage_scope",
      "type": "enum",
      "annotations": { "displayName": "3. Usage Scope", "description": "Who can see this outside?" },
      "index": 3,
      "constraints": { "required": true },
      "enumValues": [
        { "name": "INTERNAL_ONLY", "index": 1 },
        { "name": "EXTERNAL_READY", "index": 2 }
      ]
    },
    {
      "name": "update_frequency",
      "type": "enum",
      "annotations": { "displayName": "4. Freshness", "description": "How often it updates." },
      "index": 4,
      "constraints": { "required": true },
      "enumValues": [
        { "name": "REALTIME_STREAMING", "index": 1 },
        { "name": "DAILY_BATCH", "index": 2 },
        { "name": "QUARTERLY_CLOSING", "index": 3 }
      ]
    },
    {
      "name": "is_certified",
      "type": "bool",
      "annotations": { "displayName": "5. Certified?", "description": "Officially stamped by Data Governance Council." },
      "index": 5,
      "constraints": { "required": true }
    }
  ]
}
EOF
}

# ==================================================================
# 2. BigQuery Infrastructure (The Data Lake)
# ==================================================================

# --- Dataset 1: Finance Mart (Highly governed) ---
resource "google_bigquery_dataset" "finance_mart" {
  dataset_id                 = "finance_mart"
  location                   = var.region
  delete_contents_on_destroy = true
}

resource "google_bigquery_table" "monthly_closing" {
  dataset_id          = google_bigquery_dataset.finance_mart.dataset_id
  table_id            = "fin_monthly_closing_internal"
  deletion_protection = false
  schema = <<EOF
[
  { "name": "closing_date", "type": "DATE", "mode": "REQUIRED" },
  { "name": "revenue_amt", "type": "FLOAT", "mode": "NULLABLE" },
  { "name": "cost_amt", "type": "FLOAT", "mode": "NULLABLE" },
  { "name": "profit_amt", "type": "FLOAT", "mode": "NULLABLE" },
  { "name": "status", "type": "STRING", "mode": "NULLABLE" }
]
EOF
}

resource "google_bigquery_table" "quarterly_public" {
  dataset_id          = google_bigquery_dataset.finance_mart.dataset_id
  table_id            = "fin_quarterly_public_report"
  deletion_protection = false
  schema = <<EOF
[
  { "name": "quarter_name", "type": "STRING", "mode": "REQUIRED" },
  { "name": "public_revenue", "type": "FLOAT", "mode": "NULLABLE" },
  { "name": "public_operating_income", "type": "FLOAT", "mode": "NULLABLE" },
  { "name": "disclosure_date", "type": "DATE", "mode": "NULLABLE" }
]
EOF
}

# --- Dataset 2: Marketing Prod (Fast moving) ---
resource "google_bigquery_dataset" "marketing_prod" {
  dataset_id                 = "marketing_prod"
  location                   = var.region
  delete_contents_on_destroy = true
}

resource "google_bigquery_table" "realtime_campaign" {
  dataset_id          = google_bigquery_dataset.marketing_prod.dataset_id
  table_id            = "mkt_realtime_campaign_performance"
  deletion_protection = false
  schema = <<EOF
[
  { "name": "event_time", "type": "TIMESTAMP" },
  { "name": "campaign_id", "type": "STRING" },
  { "name": "estimated_revenue", "type": "FLOAT" }
]
EOF
}

# --- Dataset 3: Analyst Sandbox (The trap) ---
resource "google_bigquery_dataset" "analyst_sandbox" {
  dataset_id                 = "analyst_sandbox"
  location                   = var.region
  delete_contents_on_destroy = true
}

resource "google_bigquery_table" "temp_dump" {
  dataset_id          = google_bigquery_dataset.analyst_sandbox.dataset_id
  table_id            = "tmp_data_dump_v2_final_real"
  deletion_protection = false
  schema = <<EOF
[
  { "name": "col1", "type": "STRING" },
  { "name": "val", "type": "FLOAT" }
]
EOF
}

# ==================================================================
# 4. Data Loading (DML Jobs)
# ==================================================================
# These jobs automatically insert data after table creation.
# They replace the need for 'tables.sql' and manual 'bq query' execution.

resource "google_bigquery_job" "load_fin_monthly" {
  job_id   = "tf_job_load_fin_monthly_${formatdate("YYMMDDhhmmss", timestamp())}"
  project  = var.project_id
  location = var.region

  query {
    query = <<EOF
      INSERT INTO `${var.project_id}.${google_bigquery_dataset.finance_mart.dataset_id}.${google_bigquery_table.monthly_closing.table_id}`
      (closing_date, revenue_amt, cost_amt, profit_amt, status)
      VALUES
        ('2024-01-31', 1500000.00, 900000.00, 600000.00, 'FINALIZED'),
        ('2024-02-29', 1450000.00, 850000.00, 600000.00, 'FINALIZED'),
        ('2024-03-31', 1600000.00, 950000.00, 650000.00, 'FINALIZED');
    EOF
    create_disposition = ""
    write_disposition = ""
    use_legacy_sql = false
  }
  depends_on = [google_bigquery_table.monthly_closing]
}

resource "google_bigquery_job" "load_fin_quarterly" {
  job_id   = "tf_job_load_fin_quarterly_${formatdate("YYMMDDhhmmss", timestamp())}"
  project  = var.project_id
  location = var.region

  query {
    query = <<EOF
      INSERT INTO `${var.project_id}.${google_bigquery_dataset.finance_mart.dataset_id}.${google_bigquery_table.quarterly_public.table_id}`
      (quarter_name, public_revenue, public_operating_income, disclosure_date)
      VALUES
        ('2024-Q1', 4550000.00, 1850000.00, '2024-04-15');
    EOF
    create_disposition = ""
    write_disposition = ""
    use_legacy_sql = false
  }
  depends_on = [google_bigquery_table.quarterly_public]
}

resource "google_bigquery_job" "load_mkt_realtime" {
  job_id   = "tf_job_load_mkt_realtime_${formatdate("YYMMDDhhmmss", timestamp())}"
  project  = var.project_id
  location = var.region

  query {
    query = <<EOF
      INSERT INTO `${var.project_id}.${google_bigquery_dataset.marketing_prod.dataset_id}.${google_bigquery_table.realtime_campaign.table_id}`
      (event_time, campaign_id, estimated_revenue)
      VALUES
        (TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE), 'CMP_SUMMER_EARLY', 120.50),
        (TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE), 'CMP_SUMMER_EARLY', 350.00),
        (CURRENT_TIMESTAMP(), 'CMP_BRAND_AWARENESS', 50.00);
    EOF
    create_disposition = ""
    write_disposition = ""
    use_legacy_sql = false
  }
  depends_on = [google_bigquery_table.realtime_campaign]
}

resource "google_bigquery_job" "load_analyst_sandbox" {
  job_id   = "tf_job_load_sandbox_${formatdate("YYMMDDhhmmss", timestamp())}"
  project  = var.project_id
  location = var.region

  query {
    query = <<EOF
      INSERT INTO `${var.project_id}.${google_bigquery_dataset.analyst_sandbox.dataset_id}.${google_bigquery_table.temp_dump.table_id}`
      (col1, val)
      VALUES
        ('2024-01 data maybe?', 1500000),
        ('2024-01 data maybe?', 1500000),
        ('test_row', 99999999);
    EOF
    create_disposition = ""
    write_disposition = ""
    use_legacy_sql = false
  }
  depends_on = [google_bigquery_table.temp_dump]
}