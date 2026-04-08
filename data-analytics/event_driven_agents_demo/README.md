# Event-Driven Data Agent with BigQuery and ADK

This demo showcases an **Event-Driven Data Agent** architecture on Google Cloud. It demonstrates how to use BigQuery Continuous Queries, Pub/Sub Single Message Transforms (SMTs), and the Vertex AI Agent Development Kit (ADK) to detect and autonomously respond to real-time anomalies (such as "Impossible Travel" fraud scenarios).

---

## Architecture Overview

1. **BigQuery Continuous Query**: Continuously monitors a stream of retail transactions and joins them with customer profiles in real-time to detect anomalies (e.g., Impossible Travel).
2. **Pub/Sub Topic**: Receives the results of the continuous query directly via BigQuery's `EXPORT DATA` statement.
3. **Pub/Sub Subscription with SMT**: Uses a Single Message Transform (SMT) with Javascript to unwrap and normalize the incoming event payload into the precise envelope expected by the Agent Engine.
4. **ADK Agent (Vertex AI Agent Engine)**: Receives the normalized event and autonomously investigates the escalation using tools like BigQuery and Google Search.
5. **Analytics & Observability**: The agent's actions, traces, and final decisions are automatically logged back into BigQuery for audit and analytics.

---

## Repository Structure

- **`setup/`**: Contains environment preparation scripts (`setup_env.sh`), continuous query definitions, and historical data loading logic.
- **`agent/`**: Contains the ADK agent app, requirements, runner/deployment scripts, and the Pub/Sub `transform.yaml` configuration.
- **`simulator/`**: Contains the `generate_events.py` script used to stream synthetic transactions into BigQuery and trigger the end-to-end flow.

---

## Prerequisites

Enable the following Google Cloud APIs in your project:
- BigQuery API (`bigquery.googleapis.com`)
- Cloud Pub/Sub API (`pubsub.googleapis.com`)
- Vertex AI API (`aiplatform.googleapis.com`)

---

## Usage Instructions

### 1. Environment Setup

Navigate to the setup directory to initialize your environment, base tables, continuous query, and Pub/Sub resources:

```bash
cd setup
./setup_env.sh
```

### 2. Deploying the Agent

Navigate to the agent directory to configure and deploy the ADK agent:

```bash
cd ../agent
pip install -r requirements.txt

# Make sure to populate your .env file with your PROJECT_ID and DATASET_ID
python deploy_agent_script.py
```

### 3. Running the Simulator

With the continuous query running and the agent deployed, run the simulator to stream a synthetic "Impossible Travel" anomaly into BigQuery, triggering the entire pipeline:

```bash
cd ../simulator
python generate_events.py
```

### 4. Clean Up

To prevent ongoing charges for BigQuery Continuous Queries, Pub/Sub, and Vertex AI Agent Engine, run the cleanup script when finished:

```bash
cd ../setup
./cleanup_env.sh
```

---

> [NOTE]
> You can walk through this demo in Google Cloud by following this interactive codelab: [Event-Driven Data Agent with BigQuery and ADK](https://codelabs.developers.google.com/bigquery-adk-event-driven-agents).