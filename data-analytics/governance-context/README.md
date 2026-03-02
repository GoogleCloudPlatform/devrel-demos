# Data Governance with GenAI Context (Codelab Resources)

This repository provides the foundational infrastructure, governance scripts, and application code required for the **How to Build a Governance-Aware GenAI Agent** codelab series.

## Purpose

This repository serves as a starting point for exploring how Generative AI agents can utilize **Dataplex metadata** as a strict context boundary. By following this sample, you will learn how to build a system where an AI agent strictly answers using only trusted, certified data, preventing hallucinations and ensuring compliance.

## Codelab Series

This repository supports a two-part codelab:
*   **[Part 1: Build the Data Foundation with Dataplex Metadata](https://codelabs.developers.google.com/governance-context-part1)** - Setting up the BigQuery data lake, applying Dataplex Aspects, and local prototyping with the Gemini CLI.
*   **[Part 2: Deploy an Enterprise Governance-Aware Agent with MCP and Cloud Run](https://codelabs.developers.google.com/governance-context-part2)** - Scaling the prototype to production using the Model Context Protocol (MCP) server and Google's Agent Development Kit (ADK).

---

## Repository Structure & File Details

The repository is divided into infrastructure setup, governance automation, and the AI agent application.

### 1. Infrastructure (Terraform)
Located in the `terraform/` directory, these files provision the initial "messy" data lake.
*   **`terraform/main.tf`**: The core Terraform configuration. It deploys:
    *   A custom Dataplex Aspect Type (`official-data-product-spec`) which acts as our governance template.
    *   Three BigQuery Datasets (`finance_mart`, `marketing_prod`, `analyst_sandbox`) and their respective tables to simulate a realistic data environment.
    *   BigQuery Jobs that automatically insert sample data into the tables upon creation.
*   **`terraform/variables.tf`**: Defines the required variables (`project_id` and `region`) for the Terraform deployment.

### 2. Data Governance Automation
Scripts in the root directory used to simulate an automated CI/CD governance pipeline.
*   **`generate_payloads.sh`**: Dynamically generates YAML files (`aspect_payloads/*.yaml`). These payloads represent different governance rules (e.g., Gold/Internal, Silver/Realtime, Bronze/Sandbox) based on the Dataplex Aspect Type schema.
*   **`apply_governance.sh`**: A shell script that iterates through the BigQuery tables and uses the `gcloud dataplex entries update` command to attach the generated YAML metadata (Aspects) to the actual tables.

### 3. AI Agent Local Prototyping
*   **`GEMINI.md`**: The system prompt/instruction file used in Part 1. It acts as the local "brain" for the Gemini CLI extension, teaching the LLM the strict 3-phase algorithm (Metadata Discovery -> Search Execution -> Verification) to query Dataplex.

### 4. Production AI Agent Application (MCP & ADK)
Located in the `mcp_server/` directory, these files are used in Part 2 to deploy the enterprise-grade web application.
*   **`mcp_server/tools.yaml`**: The declarative configuration file for the GenAI Toolbox. It defines the Model Context Protocol (MCP) server settings and explicitly exposes only three specific Dataplex tools (`search_aspect_types`, `search_entries`, `lookup_entry`) to enforce a read-only, governance-first reasoning loop.
*   **`mcp_server/agent.py`**: The core application logic built using **Google's Agent Development Kit (ADK)**. 
    *   It securely connects to the deployed MCP server to fetch available Dataplex tools.
    *   It orchestrates a `SequentialAgent` workflow, utilizing a *Governance Researcher Agent* (to query Dataplex) and a *Compliance Formatter Agent* (to format the output for the user).
*   **`mcp_server/env.temp`**: A template file for runtime environment variables needed by the ADK (e.g., `MCP_SERVER_URL`, `GOOGLE_CLOUD_PROJECT`).
*   **`mcp_server/requirements.txt`**: Python dependencies required to run the ADK application (`google-adk`, `toolbox-core`, etc.).
*   **`mcp_server/__init__.py`**: Python package initialization file.

---

## Getting Started

To begin, please refer to the codelab documentation for step-by-step instructions. You will clone this repository directly into your Google Cloud Shell environment during the setup phase.

1. Start with **Part 1** to provision the Terraform infrastructure and apply the Dataplex governance metadata.
2. Proceed to **Part 2** to deploy the `mcp_server` configurations to Cloud Run and interact with the AI Agent via a web UI.