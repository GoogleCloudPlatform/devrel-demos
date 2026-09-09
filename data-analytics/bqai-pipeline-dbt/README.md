# SQL-First AI: Building Intelligent Data Pipelines with BigQuery & dbt

Companion demo repository for the **dbt Summit 2026** breakout session:
> **"SQL-first AI: Building Intelligent Data Pipelines with BigQuery and dbt"**  
> **Speaker:** Alicia Williams, Developer Relations Engineer, Google Cloud

---

## 📌 Overview

This project demonstrates how data engineers can operationalize **generative AI natively in SQL** using **BigQuery AI functions** inside a standard **dbt** project. Using realistic e-commerce customer review data from **Cymbal Pets**, this pipeline extracts aspect-based sentiment scores, builds concise review summaries, and aggregates product feedback into automated executive briefings.

---

## 🏗️ Architecture & DAG

The pipeline follows a modular 3-stage data transformation pattern:

```
  ┌────────────────────────────────────────────────────────┐
  │                 Raw Source Data                        │
  │     cymbal_pets.reviews    +    cymbal_pets.orders     │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 1. STAGING LAYER (View)                                │
  │    stg_customer_reviews                                │
  │    - Casts and maps raw schema                         │
  │    - Filters empty strings to avoid wasted token spend │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 2. INTERMEDIATE LAYER (Incremental Table)              │
  │    int_reviews_enriched                                │
  │    - Multi-aspect sentiment via AI.SCORE() (1 to 5)    │
  │    - One-sentence summaries via AI.GENERATE()          │
  │    - Poison-pill handling & max 3 retries              │
  └───────────────────────────┬────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │ 3. MART LAYER (Table)                                  │
  │    fct_customer_insights                               │
  │    - Statistical sentiment averages per product        │
  │    - Semantic rollups & PM briefings via AI.AGG()      │
  └────────────────────────────────────────────────────────┘
```

### Model Pipeline Summary

| Stage | Model Name | Materialization | Responsibilities & Functions |
|---|---|---|---|
| **Staging** | `stg_customer_reviews` | `view` | Cleans up raw review logs, joins customer order dates, and pre-filters blank records. |
| **Intermediate** | `int_reviews_enriched` | `incremental` | Runs `AI.SCORE` across three distinct pillars (product, shipping, support) and `AI.GENERATE` for summaries; records status codes and retry counts. |
| **Mart** | `fct_customer_insights` | `table` | Aggregates numerical scores by product and runs `AI.AGG` to compile semantic executive summaries. |

---

## ⚙️ Key Patterns & Production Best Practices

### 1. Incremental Materialization (Cost & Latency Optimization)
Calling LLMs inside standard views or full-refresh tables resends every historical row to the model on every pipeline run. Materializing the AI layer incrementally ensures only new or failed records are processed:

```sql
{{ config(
    materialized = 'incremental',
    unique_key = 'review_id'
) }}

select
  s.review_id,
  s.product_id,
  s.review_text,
  AI.SCORE((s.review_text, 'Score customer sentiment regarding product quality from 1 to 5.')) as product_sentiment_score,
  AI.SCORE((s.review_text, 'Score customer sentiment regarding shipping speed from 1 to 5.')) as shipping_sentiment_score,
  AI.SCORE((s.review_text, 'Score customer sentiment regarding customer service from 1 to 5.')) as customer_service_sentiment_score,
  AI.GENERATE('Generate a concise one-sentence summary: ' || s.review_text) as gen_struct
from {{ ref('stg_customer_reviews') }} s
{% if is_incremental() %}
where s.review_date > (select max(review_date) from {{ this }})
   or s.review_id in (
       select review_id from {{ this }}
       where ai_generation_status != 'SUCCESS' and coalesce(ai_retry_count, 0) < 3
   )
{% endif %}
```

### 2. Multi-Aspect Sentiment with `AI.SCORE`
A single blended sentiment score frequently conceals critical feedback (e.g., loving the item but hating late delivery). Calling `AI.SCORE` with targeted prompts extracts multi-aspect numerical scores (1–5) independently for:
* **Product Quality & Features**
* **Delivery & Shipping Experience**
* **Customer Support & Returns**

### 3. Graceful Error Handling & 3-Strike Retry Caps
Unstructured text can hit content safety triggers, rate limits, or quota drops.
* **Struct Inspection:** `AI.GENERATE` returns a `STRUCT` with `.result`, `.status`, and `.full_response` fields so failures can be inspected in SQL.
* **Retry Caps:** The pipeline tracks retry counts and sets permanent failures to `MAX_RETRIES_EXCEEDED` after 3 attempts, preventing toxic or blocked rows from causing infinite retries.

### 4. Semantic Rollups with `AI.AGG`
`AI.AGG` enables native group-by aggregation over unstructured text, creating executive briefings per product directly within SQL:

```sql
select
  product_id,
  count(review_id) as total_reviews,
  round(avg(product_sentiment_score), 2) as avg_product_sentiment_score,
  round(avg(shipping_sentiment_score), 2) as avg_shipping_sentiment_score,
  coalesce(
    AI.AGG(
      review_text,
      'Synthesize customer feedback into a concise product manager briefing. Highlight explicit feature requests and usability complaints.'
    ),
    'No summary generated.'
  ) as product_improvement_recommendations
from {{ ref('int_reviews_enriched') }}
group by product_id;
```

### 5. Automated Testing with dbt
LLM outputs are validated using schema tests in `models/schema.yml` to prevent model hallucinations or null drops from polluting downstream tables:

```yaml
version: 2
models:
  - name: int_reviews_enriched
    columns:
      - name: review_id
        tests:
          - unique
          - not_null
      - name: product_sentiment_score
        tests:
          - not_null
      - name: ai_generation_status
        tests:
          - not_null
```

---

## 📁 Repository Structure

```text
bqai-pipeline-dbt/
├── README.md                          # Project documentation and demo guide
├── dbt_project.yml                    # dbt project definition and configs
├── profiles.yml                       # Target environment BigQuery credentials
├── models/
│   ├── staging/
│   │   ├── stg_customer_reviews.sql   # Source cleaning and pre-filtering view
│   │   └── src_cymbal_pets.yml        # Staging source definitions (reviews & orders)
│   ├── intermediate/
│   │   └── int_reviews_enriched.sql   # Incremental AI scoring & summary model
│   ├── marts/
│   │   └── fct_customer_insights.sql  # Final analytics table with AI.AGG rollups
│   └── schema.yml                     # Test assertions (not_null, unique)
```

---

## 🚀 Setup & Execution

### Prerequisites

| Tool / Requirement | Minimum Version / Role | Purpose |
|---|---|---|
| **Google Cloud Project** | Active billing & BigQuery API enabled | Hosting raw data and executing BigQuery AI SQL queries |
| **IAM Permissions** | `roles/bigquery.user` & `roles/bigquery.dataEditor` | Running queries, creating datasets, and writing tables |
| **Google Cloud CLI (`gcloud`)** | Latest | Authenticating via Application Default Credentials (ADC) |
| **Python** | `3.10+` | Running dbt in a local environment |
| **dbt-core & dbt-bigquery** | `1.8+` | dbt CLI core engine and BigQuery adapter |

Install dbt and the BigQuery adapter:
```bash
pip install dbt-core dbt-bigquery
```

---

### 1. Authenticate with Google Cloud

Ensure you have the [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) installed. Then log in to generate Application Default Credentials (ADC) for dbt:

```bash
# 1. Log in to the Google Cloud CLI
gcloud auth login

# 2. Set your active Google Cloud project
gcloud config set project YOUR_PROJECT_ID

# 3. Generate Application Default Credentials (ADC) for dbt to connect
gcloud auth application-default login
```

---

### 2. Clone the Repository & Navigate to the Project

Clone the repository from GitHub using `git sparse-checkout` to pull down only the `bqai-pipeline-dbt` demo folder from the `devrel-demos` repository:

```bash
# 1. Clone the devrel-demos repository with sparse checkout enabled
git clone --depth 1 --filter=blob:none --sparse https://github.com/GoogleCloudPlatform/devrel-demos.git
cd devrel-demos

# 2. Checkout only the bqai-pipeline-dbt project directory
git sparse-checkout set data-analytics/bqai-pipeline-dbt
cd data-analytics/bqai-pipeline-dbt
```

> **Note:** All subsequent `dbt` commands must be executed from within this `data-analytics/bqai-pipeline-dbt/` root directory where `dbt_project.yml` is located.

---

### 3. Configure dbt Profile

Create or update your `~/.dbt/profiles.yml` (or local `profiles.yml`) to connect to your BigQuery project using OAuth (ADC):

```yaml
bigquery:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: YOUR_PROJECT_ID
      dataset: cymbal_pets_dbt
      threads: 4
      timeout_seconds: 1200
      location: US
```

---

### 4. Update Source Configuration & Dataset Setup

In `models/staging/src_cymbal_pets.yml`, ensure the `database` property points to the Google Cloud project where your raw reviews and orders tables are hosted:

```yaml
version: 2

sources:
  - name: cymbal_pets
    database: YOUR_PROJECT_ID
    schema: cymbal_pets
    tables:
      - name: reviews
      - name: orders
```

> [!IMPORTANT]
> **Source Dataset Setup (`cymbal_pets`):**  
> Before running the dbt pipeline, you must set up a `cymbal_pets` dataset in your Google Cloud project with both source tables:
> * **`orders` Table**: You can copy or query the public dataset table **`bigquery-public-data.cymbal_pets.orders`**.
> * **`reviews` Table**: You will need to generate or upload your own `reviews` table in your `cymbal_pets` dataset (containing `order_item_id`, `order_id`, `product_id`, and `review` text columns).

---

### 5. Run the Pipeline

From the `bqai-pipeline-dbt/` directory, execute:

```bash
# 1. Verify your credentials and BigQuery connectivity
dbt debug

# 2. Build the pipeline (staging views, incremental AI models, and mart summaries)
dbt run

# 3. Validate AI outputs against test assertions
dbt test

# Or run materialization and assertions together in one command:
dbt build
```
---

## 📖 Additional Resources

* [BigQuery Generative AI Overview](https://docs.cloud.google.com/bigquery/docs/generative-ai-overview)
* [dbt BigQuery Guide](https://docs.getdbt.com/reference/warehouse-setups/bigquery-setup)
