# Vegas Concert Navigator — Real-Time Agent Playground

> [!IMPORTANT]
> **Google Cloud Authentication**: Before running any setup script or starting the playground, you must authenticate to Google Cloud and enable Application Default Credentials (ADC). If you encounter connection or token errors, run these commands:
> ```bash
> # 1. Authenticate your gcloud CLI
> gcloud auth login
> 
> # 2. Generate Application Default Credentials (ADC) for client libraries
> gcloud auth application-default login
> ```

This subdirectory contains the real-time agent setup built with the Google Agent Development Kit (ADK) and orchestrated using `agents-cli`. It features:
* **Hotel Agent**: Answers Mandalay Bay mapping and amenities questions using `venue_knowledge` tables via BigQuery.
* **Stadium Agent**: Handles security policies and admission criteria using `stadium_logistics` tables via BigQuery.
* **Supervisor Agent / App**: Acts as the central gateway coordinating sub-agents and enabling real-time human interaction.

> [!NOTE]
> This application uses the BigQuery Agent Analytics Plugin with default flags enabled. On the very first execution of agent logging/tracing, initialization may take some time. This is because the plugin automatically creates multiple database tables and analytics views to land, structure, and facilitate the visualization of trace data. You can read more about this [automatically created views and tables behavior](https://adk.dev/integrations/bigquery-agent-analytics/#automatically-created-views), as well as instructions on how it can be customized or disabled.

---

## Quick Start & Teardown

If you want to run everything and subsequently clean up, use these two main scripts:

```bash
# 1. Start / Setup everything (provisions BigQuery, registers AI models, seeds embeddings from root)
../.venv/bin/python3 ../scripts/setup_bigquery.py
 
# 2. Teardown everything (stops running local agents and deletes all GCP resources from root)
../.venv/bin/python3 ../scripts/teardown_bigquery.py
```

---

## Step-by-Step Setup Guide

### 1. Google Cloud Authentication & Setup
Before running any script, you must authenticate to Google Cloud and enable Application Default Credentials (ADC):

```bash
# Authenticate your gcloud CLI
gcloud auth login

# Generate Application Default Credentials for client libraries (e.g. bigquery, genai SDK)
gcloud auth application-default login
```

Make sure your `.env` file at the repository root contains the correct project identifier:
```env
GOOGLE_CLOUD_PROJECT=<YOUR_PROJECT_ID>
BIG_QUERY_DATASET_ID=next_navigator
REGION=us-central1
AGENT_MODEL=gemini-3.5-flash
```

---

### 2. Environment Initialization
Set up a clean virtual environment and install dependencies:

```bash
# Navigate to the real-time directory
cd real-time

# Since our consolidated virtual environment is at the root, simply activate it
source ../.venv/bin/activate
```

---

### 3. Bootstrap Cloud Resources & Seed Data
Initialize the necessary GCP and BigQuery backend components:

```bash
# Run the Python setup script
../.venv/bin/python3 ../scripts/setup_bigquery.py
```

> [!NOTE]
> **IAM Propagation Delay:** When registering the remote models, BigQuery needs to authenticate Vertex AI. Because GCP IAM policy bindings take time to propagate, the bootstrap script might retry model registration up to 20 times (200s total). This is normal behavior.

**What this script automates:**
1. Creates the BigQuery dataset `next_navigator` inside your configured Google Cloud project in region `us-central1`.
2. Sets up a BigQuery External Cloud Resource Connection named `vertex_ai_conn`.
3. Binds both `roles/aiplatform.user` and `roles/cloudaicompanion.user` roles to the connection's dedicated service account automatically.
4. Registers the Remote Embedding Model `embedding_model` mapped to Vertex AI `text-embedding-005`.
5. Creates tables `venue_knowledge` and `stadium_logistics` and seeds them by converting the local `data/enriched_payload.json` file into vector embeddings using the Google GenAI SDK.

---

### 4. Running the ADK Agent Playground (a2ui)
We use the Agent-to-User developer interface (a2ui) playground to interact with our agents.
The playground provides a visual canvas to chat with the supervisor and sub-agents, inspect trace timelines, and view live tool executions. To launch it:

```bash
# Start the background agents-cli playground and web UI
agents-cli playground
```

Once started, open your web browser to the visual playground:
👉 **[http://127.0.0.1:8080/dev-ui/?app=agents](http://127.0.0.1:8080/dev-ui/?app=agents)**

Alternatively, if you want to host the FastAPI endpoints directly without the playground UI wrapper:
```bash
# Start the underlying backend agent services individually
../scripts/start_agents.sh
```

---

### 5. Real-Time Sentiment & Entity Continuous Query (Event Stream Pipeline)
We have implemented a BigQuery Continuous Query pipeline that monitors incoming streaming event records from the `agent_events_v2` table, applies Natural Language analysis (`ML.UNDERSTAND_TEXT`) for sentiment and entities, and streams parsed results in real-time to `sentiment_analysis_results`.

Because continuous queries run endlessly and require dedicated serverless capacity, you must configure a BigQuery Slot Reservation and register a remote NLU model.

#### Step A: Configure Reservation in `.env`
Continuous queries do not support standard on-demand billing and require an Enterprise capacity slot allocation. Set your slot reservation identifier in your `.env` file:
```env
BQ_RESERVATION_ID=projects/<RESERVATION_PROJECT>/locations/<LOCATION>/reservations/<RESERVATION_NAME>
```

#### Step B: Validate Capacity and Assignment
Use our pre-flight checking script to verify that your slot reservation exists and is properly assigned to execute `CONTINUOUS` jobs in your runner project. This script supports cross-project administration:
```bash
../.venv/bin/python3 ../scripts/create_bq_reservation.py
```
*Note: If no reservation exists, the script will safely prompt you to confirm the reservation name to automatically provision an Enterprise reservation (starting at 50 slots) with autoscale capacity.*

#### Step C: Start the Continuous Query
The start command provisions the schema (with `entities` stored as flexible `JSON`), registers the NLU remote model, maps the reservation, and submits the continuous stream runner:
```bash
../.venv/bin/python3 queries/run_continuous_query.py start
```

#### Step D: Monitor Status and Cancel
```bash
# Check status of the continuous query background job
../.venv/bin/python3 queries/run_continuous_query.py status

# Cancel the continuous query job
../.venv/bin/python3 queries/run_continuous_query.py cancel
```

---

### 6. Teardown
Once you are done playing with the agents or running the continuous query pipeline, use the teardown script to cleanly shut down the entire environment and delete all provisioned cloud resources:

```bash
# Run the teardown script
../.venv/bin/python3 ../scripts/teardown_bigquery.py
```

**Teardown flow:**
1. **Continuous Query Cancellation**: Detects if an active continuous query is running using `queries/running_job.id` and submits a cancel request to BigQuery.
2. **Process Termination**: Scans for any active Python agent processes running on local ports `8080`, `8081`, and `8082` and terminates them cleanly.
3. **BigQuery Clean-up**: Drops the models (`embedding_model`, `nlu_model`), drops tables (`venue_knowledge`, `stadium_logistics`, `sentiment_analysis_results`, `agent_events_v2`), and drops the dataset (`next_navigator`).
4. **IAM Retraction & Connection Removal**: Removes delegated project IAM policy bindings (`roles/aiplatform.user`, `roles/cloudaicompanion.user`, `roles/serviceusage.serviceUsageConsumer`) from the connection's service account, and deletes the BigQuery connection (`vertex_ai_conn`).
5. **Interactive Preview**: Prompts the user with a confirmation preview containing the exact PIDs and table/connection resource identifiers before taking any actions.
