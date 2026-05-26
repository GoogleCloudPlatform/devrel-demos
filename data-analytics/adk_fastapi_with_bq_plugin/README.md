# Google ADK + FastAPI + BigQuery Telemetry Example

This example demonstrates how to run a conversational agent using the Google Agent Development Kit (ADK) and FastAPI, with telemetry data (spans, tool executions, model queries) automatically streamed to Google BigQuery.

It demonstrates how to use the `extra_plugins` parameter in `get_fast_api_app` to dynamically register the `BigQueryAgentAnalyticsPlugin`.

## Prerequisites

1. **Google Cloud Credentials**: Authenticate your local environment:
   ```bash
   gcloud auth application-default login
   ```
2. **APIs Enabled**: Make sure Vertex AI API is enabled in your GCP project.
3. **BigQuery Table**: Create a BigQuery dataset and table to store telemetry data.
4. **Python & uv**: Install [uv](https://astral.sh/uv) for fast package management.

## Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and fill in your GCP project, dataset, and table details.
3. Install dependencies:
   ```bash
   uv sync
   ```

## Running the Application

1. Start the FastAPI server:
   ```bash
   uv run python main.py
   ```
2. Open the chat interface in your browser:
   ```
   http://localhost:8080/
   ```
3. Converse with the agent. The runtime logs and execution traces will automatically sync to your BigQuery table.
