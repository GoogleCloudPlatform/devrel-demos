
# Manufacturing Assistant Agent

This repository contains an end-to-end solution for building and querying a **Manufacturing Knowledge Graph** using Google Cloud.

## Overview

The solution consists of two main components:

### 1. Data Pipeline Notebook (`kg_demo_template.ipynb`)
This notebook builds the foundation of the Knowledge Graph:
*   **Ingestion**: Parses unstructured PDF manuals using **Document AI**.
*   **Extraction**: Structured data (Products, Parts, Materials) is extracted and loaded into **BigQuery**.
*   **Graph Construction**: Defines a **BigQuery Property Graph** (`kg_demo.manufacturing_kg`) to model relationships like `(Product)-[contains]->(Part)`.

### 2. Manufacturing Agent (`manufacturing_assistant_agent/`)
A GenAI Agent designed to answer complex questions about the graph:
*   **Graph RAG**: Translates natural language into **GQL (Graph Query Language)** to traverse the knowledge graph.
*   **Multi-Modal**: Combines structured graph data with **Google Maps** to find suppliers and facilities.
*   **Deployment**: Can be run locally or deployed to **Vertex AI Agent Engine**.

---

## Prerequisites

Ensure you have the necessary dependencies installed. The `google-genai-adk` package includes the `adk` CLI tool:
```bash
pip install -r manufacturing_assistant_agent/requirements.txt
```

Verify the installation by checking the ADK version:
```bash
adk --version
```

## Configuration

Before running the agent, you **must** configure the environment variables in `manufacturing_assistant_agent/.env`:

1.  **Project ID**: Update `GOOGLE_CLOUD_PROJECT` with your Google Cloud Project ID.
2.  **Maps API Key**: Update `MAPS_API_KEY` with your Google Maps API Key. This is required for Google Maps MCP toolset (you can disable this toolset in `manufacturing_assistant_agent/agent.py` if you don't need it).

---

## 1. Running with ADK Web UI

To run the agent with the Agent Development Kit (ADK) Web UI, which provides a visual interface for chatting with your agent, tracing execution steps, and debugging:

```bash
# Point to the create_agent_app factory in deploy_agent.py
adk web
```
(This will start a local server at http://localhost:8000. Open this URL in your browser to interact with the agent.)

---

## 2. Running Locally with `main.py`

To run the agent in a simple interactive CLI loop:

```bash
python manufacturing_assistant_agent/main.py
```
This runs the agent using `Runner` with `InMemorySessionService`. It uses your local Application Default Credentials (ADC).

---

## 3. Deploying to Vertex AI Agent Engine

To deploy the agent to Vertex AI Agent Engine:

```bash
python deploy_agent.py
```
This script:
- Initializes Vertex AI for your project and location.
- Builds the agent app using `create_agent_app`.
- Deploys the agent to Vertex AI Agent Engine with the necessary environment variables (e.g., `MAPS_API_KEY`).
- Prints the resource name of the deployed agent once complete.

**Note:** You may want to update the `agent_name` and `agent_desc` in the `__main__` block of `deploy_agent.py` before running.

---

## Example Questions

Here are some example questions you can ask the agent to explore the Knowledge Graph:

*   "Which customers purchased products containing Fiberglass?"
*   "Find the address of our Royal Soft Serve customer in BigQuery and then use the maps tools to find the closest recycling centre"
*   "What parts are in the FroZone Zenith 5000?"
*   "Find all materials used in the Arctic Swirl 5000."


## License
This project is licensed under the Apache License, Version 2.0. See the LICENSE file for details.