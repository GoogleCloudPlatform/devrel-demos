# Sentiment Agent and Real-Time Analytics Codelab

Welcome to the Sentiment Agent and Real-Time Analytics Codelab. This workspace houses a multi-agent conversational application integrated with a continuous real-time streaming analytics pipeline.

---

## Repository Architecture

The repository is modularized into folders to allow development, testing, and reuse without needing to rebuild or tear down independent sub-systems.

```
[ sentiment-agent (root) ]
   ├── setup.sh         <── Environment bootstrap script (Requires 'uv')
   ├── agents/          <── Conversational Multi-Agent application & Playground
   ├── scripts/         <── Database orchestration and seeding bootstrap scripts
   ├── real-time/       <── Continuous streaming analytics pipeline & schema
   ├── grafana/         <── Pipeline observability metrics and monitoring control center
   └── rag-augment/     <── RAG augmentation and policy editing lab workspace
```

---

## Developer Setup

> [!IMPORTANT]
> **Google Cloud Authentication**: Before running the setup script or launching any agent, you must authenticate your local shell with Google Cloud. Otherwise, the database seed and agent logging integrations will fail:
> ```bash
> # 1. Authenticate your gcloud CLI
> gcloud auth login
> 
> # 2. Generate Application Default Credentials (ADC) for backend API calls
> gcloud auth application-default login
> ```

To set up your local development environment and bootstrap the BigQuery database schema and remote models, execute the root-level setup script:

```bash
./setup.sh
```

Once the setup is completed, refer to `agents/README.md` for launch instructions, local execution, and playground testing.

> [!IMPORTANT]
> **Prerequisites**: The setup script requires the `uv` package manager and Python 3. Standard fallback to pip is disabled to enforce reliable dependency resolution.

---

## End-to-End User Journey

Follow this sequential progression to explore the core capabilities of the lab:

### 1. Launch Conversational Agents (`agents/`)
Start the background microservices (`./scripts/start_agents.sh`) and open the developer UI (`agents-cli playground` -> `http://localhost:8080`). Test single-agent navigation and cross-domain routing with the supervisor:
*   💬 *"Where is the closest quiet zone at Mandalay Bay?"*
*   💬 *"Find me a restaurant at Mandalay Bay and also tell me what time the stadium doors open."*

### 2. Test Live RAG Augmentation (`rag-augment/`)
Query the agent about laptop bag policies in the UI, apply a live policy update to recompute vector embeddings in BigQuery without restarting code, and observe the answer change:
*   💬 *"I have a laptop with me, I can't walk all the way back to my hotel, the concert will be over!"* (Before: Refuses laptops / no lockers. After running `./scripts/update_policy.py allow`: Directs to Gate 4 bag check).

### 3. Run CDC Analytics & AI Aggregation (`real-time/` & `batch-analytics/`)
Your chat history automatically streams into BigQuery via CDC. Run `python3 batch-analytics/run_analytics_demo.py` to analyze quantitative entity frequencies and generate qualitative executive summaries using Gemini `AI.AGG`.

### 4. Monitor in Grafana (`grafana/`)
Launch `./grafana/start_grafana.sh` to visualize real-time sentiment polarity trends and throughput metrics on `http://localhost:3000`.

---

## Component Directory Map

Detailed instructions for running and modifying each subsystem are located inside their respective folders:

### 1. Conversational Multi-Agent App
Contains the supervisor, hotel, and stadium agents built using the Gemini Agent Development Kit (ADK) and `agents-cli`.
*   **Location**: `agents/`
*   **Guide**: Read `agents/README.md` for launch instructions, local execution, and playground testing.

### 2. Continuous Analytics Pipeline & Grafana Observability
Houses the SQL streaming pipeline structures, continuous query engines, and database configurations, alongside system monitoring.
1.  **Pipeline Location**: `real-time/` (Read `real-time/README.md` for managing continuous streams, BigQuery subscriptions, and execution procedures)
2.  **Grafana Dashboard Location**: `grafana/` (Read `grafana/README.md` for dashboard layout, telemetry tracking, and visualizing pipeline throughput metrics)

### 3. RAG Augmentation Lab
Workspace for editing stadium logistics/hotel policies and verifying RAG augmentation answers.
*   **Location**: `rag-augment/`
*   **IMPORTANT DEPENDENCY**: Completing RAG augmentation testing requires the BigQuery database to not be torn down. The agents query the active BigQuery vector store to retrieve updated policies; do not execute cloud teardown scripts beforehand.

---

## Verification & Operations

### Managing or Tearing Down Resources
To prevent needing a full environment rebuild when you only want to reset specific components, teardowns are separated into modular scripts:

*   **Initialize / Seed Database**: Run `./setup.sh` (orchestrates `scripts/setup_bigquery.py`).
*   **BigQuery Reservation Setup**: `python3 scripts/create_bq_reservation.py`.
*   **Local Process Kill**: `python3 scripts/agents_teardown.py` (Terminates local microservices on ports 8080/8081/8082, leaving cloud data intact).
*   **Cloud Resource Drop**: `python3 scripts/cloud_resources_teardown.py` (Drops BigQuery tables, remote models, and connections, leaving local agent processes running).
*   **Full Teardown**: Run `python3 scripts/teardown_all.py` to clean up both local processes and GCP cloud databases.
