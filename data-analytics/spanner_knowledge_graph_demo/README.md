# Spanner & BigQuery Hybrid Knowledge Graph & Reverse ETL Demo

This repository expands the Manufacturing Knowledge Graph architecture to demonstrate **Hybrid Data Architecture across Cloud Spanner and BigQuery**, including **Operational & Analytical Property Graphs**, **Document AI PDF Parsing**, **Gemini Knowledge Extraction**, and **Reverse ETL**.

---

## Architecture Overview

```
 ┌─────────────────────────────────────────────────────────────┐
 │                    Cloud Spanner                            │
 │ (Transactional Storage & Operational Graph)                │
 │                                                             │
 │  Customers  ──(Purchased)──>  Products                      │
 │      │                          ▲                           │
 │ (Filed Complaint)     (Regarding Product)                   │
 │      ▼                          │                           │
 │  CustomerComplaints ────────────┘                           │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Live BigQuery Federated Queries
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                      BigQuery                               │
 │ (Analytical Graph & Gemini Unstructured Extraction)        │
 │                                                             │
 │  Unstructured Manual PDFs  ──[Document AI]──> JSON Chunks   │
 │                                                     │       │
 │  BigQuery Property Graph  <──[Gemini AI.GENERATE]───┘       │
 │  (Products ──> Parts ──> Materials)                         │
 └──────────────────────────────┬──────────────────────────────┘
                                │ Reverse ETL Sync
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                Reverse ETL Operational Push                 │
 │ BigQuery Analytics  ──>  Spanner.ReverseEtlEnrichedInsights │
 └─────────────────────────────────────────────────────────────┘
```

---

## Key Features & Modular SQL Files

All extraction, database definitions, graph builds, visualizations, and Reverse ETL flows are fully modularized in standalone `.sql` files within the `sql/` directory:

### 1. Cloud Spanner Definition & Operational Graph SQLs
* **`sql/01_spanner_schema.sql`**: Spanner DDL defining transactional tables (`Customers`, `Products`, `PurchaseOrders`, `CustomerComplaints`, and `ReverseEtlEnrichedInsights`).
* **`sql/02_spanner_sample_data.sql`**: Sample DML data for customers, products, purchase orders, and customer complaints.
* **`sql/03_spanner_graph.sql`**: Spanner Property Graph DDL (`spanner_manufacturing_graph`) linking operational nodes and edges.
* **`sql/04_spanner_graph_queries.sql`**: Operational GQL graph queries executing directly in Spanner.

### 2. BigQuery AI & Extraction SQLs
* **`sql/05_bq_spanner_federated_views.sql`**: BigQuery external views over live Spanner data using `EXTERNAL_QUERY`.
* **`sql/06_bq_extract_knowledge.sql`**: Extracts structured parts and material relationships from document chunks using Gemini 3.1 Pro (`AI.GENERATE`).
* **`sql/07_bq_build_graph.sql`**: Builds BigQuery Node & Edge tables and defines the BigQuery Property Graph (`manufacturing_kg`).

### 3. Visualizations Split into Separate SQL Files
* **`sql/08_bq_viz_full_graph.sql`**: Full graph traversal query (`MATCH (source)-[r]->(target)`).
* **`sql/09_bq_viz_product_materials.sql`**: Product -> Part -> Material engineering graph visualization.
* **`sql/10_bq_viz_customer_fiberglass.sql`**: Customer purchases matching extracted fiberglass component path.
* **`sql/11_bq_viz_customer_complaints.sql`**: Spanner customer complaints cross-referenced with Document AI component graph.

### 4. Reverse ETL Demonstration
* **`sql/12_bq_reverse_etl_to_spanner.sql`**: Joins Spanner complaints with BigQuery extracted component materials to compute risk scores, and pushes enriched insights back into Spanner's `ReverseEtlEnrichedInsights` operational table.

---

## Running the Demo

### Option A: Interactive Notebook (`spanner_kg_demo_template.ipynb`)
Open `spanner_kg_demo_template.ipynb` in Google Cloud Vertex AI Workbench or Google Colab. The notebook:
1. Keeps the Document AI layout parser pipeline running directly in Python.
2. Imports and executes each independent SQL file sequentially.
3. Renders interactive graph visualisations for each query.

### Option B: Executing SQL Files Independently
You can execute any `.sql` file independently via `gcloud`, `bq`, or the Google Cloud Console BigQuery / Spanner Studio interfaces.

---

## Manufacturing Assistant Agent (`manufacturing_assistant_agent/`)

The GenAI Agent translates natural language questions into GQL graph queries spanning both Spanner and BigQuery:

```bash
# Install dependencies
pip install -r manufacturing_assistant_agent/requirements.txt

# Run CLI interaction
python manufacturing_assistant_agent/main.py
```

Deploy to Vertex AI Agent Engine:
```bash
python deploy_agent.py
```

## License
Apache License, Version 2.0.
