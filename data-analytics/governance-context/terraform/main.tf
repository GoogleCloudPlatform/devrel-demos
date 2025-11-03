# main.tf

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
