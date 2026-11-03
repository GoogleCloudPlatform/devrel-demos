# Enterprise Support Agent Blueprint (Low-Latency RAG)

This repository provides a reference architecture for an event-driven, low-latency Enterprise Support Agent. It demonstrates how to decouple monolithic RAG pipelines into five highly efficient microservices using the Google Agent Development Kit (ADK), Cloud SQL `pgvector`, and Model Armor.

📖 **For the full, step-by-step walkthrough, refer to the [DevSite Tutorial](https://cloud.google.com/gemini/enterprise/docs/agent-runtime/deploy-low-latency-support-agent).**

## 🏗️ Architecture & Subtasks

1. **Ingestion & Governance (`subtask1_ingestion`):** Replaces batch scraping with instant webhooks, enforcing Role-Level Access Control (RLAC) metadata.
2. **AST Chunking (`subtask2_chunking_embedding`):** Uses heading-aware chunking and Vertex AI `text-embedding-005` to preserve procedural context.
3. **Vector Store (`subtask3_vector_store`):** Transactional HNSW vector storage in Cloud SQL PostgreSQL for fast similarity search.
4. **Agent Runtime (`subtask4_agent_runtime`):** ADK-based orchestrator featuring Model Armor prompt defense and deterministic Model Context Protocol (MCP) tools, running on Agent Runtime on Gemini Enterprise Agent Platform.
5. **Closed-Loop Eval (`subtask5_closed_loop_eval`):** Pub/Sub event streaming and automated runbook generation for unhandled queries.

## 🔒 Enterprise Security & Governance

1. **On-Behalf-Of (OBO) Execution:** Runtime actions propagate authenticated end-user identity (via OAuth tokens) to downstream MCP tools using the ADK `ToolContext`.
2. **Deterministic Routing:** LLMs are restricted to natural language synthesis. Operational actions (ITSM ticketing, helpdesk routing) execute via deterministic code.
3. **Model Armor Prompt Defense:** Inbound user prompts are pre-screened for jailbreaks and prompt injection. *(Note: You must create a template named `default-safety-template` using `gcloud model-armor templates create` before deploying).*

### ⚠️ Networking Note for Development
By default, the Terraform configuration in this blueprint provisions the Cloud SQL database with a private IP only (`ipv4_enabled = false`). In a production environment, you must configure **Private Service Connect (PSC)** or a **Serverless VPC Access Connector** for the Agent Runtime and Cloud Run services to reach the database.

**For local development or testing:** You can temporarily change `ipv4_enabled = true` in `infra/main.tf` and use the Cloud SQL Auth Proxy or authorized networks to allow your test agent to connect.

## 🚀 Quickstart

Clone the repository and provision the infrastructure:

```bash
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
cd devrel-demos/ai-ml/enterprise-support-adk-pgvector

# Initialize and apply Terraform
cd infra
terraform init
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

Once infrastructure is provisioned, you can deploy the chunker and the ADK Agent (see the [DevSite Tutorial](https://docs.cloud.google.com/gemini/enterprise/docs/agent-runtime/deploy-low-latency-support-agent) for full `gcloud run deploy` deployment steps).