# Lab 2: Data Analysis & Multimodal Insights
This repository contains the deployment scripts and data for Lab 2 of the **Informed AI Roadshow**. In this lab, you'll act as a developer-investigator to track down a missing high-value cargo container using Google Cloud's data and database AI capabilities.
## What You'll Build & Learn
*   **Multimodal Image Analysis**: Scan port security footage to extract container IDs and colors using Gemini directly inside BigQuery (`AI.GENERATE`).
*   **Time-Series Anomaly Detection**: Analyze temperature readings using TimesFM inside BigQuery (`AI.DETECT_ANOMALIES`) to prove the container was tampered with.
*   **Low-Latency Vector Search**: Export enriched embeddings to AlloyDB and run similarity matching (`pgvector` + `google_ml_integration`) to trace the container's GPS beacon signal.
*   **Conversational Data Exploration**: Connect the **Data Agent Kit** to chat with your investigation database using natural language.
## Repository Contents
*   `scripts/setup_lab.sh`: Initializes BigQuery datasets, Cloud Resource connections, and GCS buckets.
*   `scripts/setup_alloydb.sh`: Automates the background creation of a Postgres-compatible AlloyDB cluster.
