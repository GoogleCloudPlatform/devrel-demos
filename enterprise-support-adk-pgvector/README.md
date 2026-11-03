# Low-Latency Enterprise Support Agent Blueprint
### *From 24-Hour Batch Enterprise Wiki Scraping to 6-Second Agentic Knowledge Serving*

This repository provides an enterprise-ready reference implementation demonstrating how to re-architect conversational IT/support agents using the **Google Agent Development Kit (ADK)**, **Cloud SQL / AlloyDB for PostgreSQL (`pgvector`)**, and **Model Context Protocol (MCP)** tools.

---

## 🏗️ Architectural Overview: The 5 Subtasks

Traditional enterprise RAG architectures depend on scheduled batch scrapers over complex Enterprise Wiki pages, resulting in a **1-to-24 hour delay** before emergency incident documentation becomes searchable. This architecture breaks the pipeline into **5 decoupled, event-driven subtasks**, reducing total update latency to **under 6 seconds**.

| Subtask | Engine / Service | Responsibilities | Target Latency |
| :--- | :--- | :--- | :--- |
| **1. Ingestion & Validation** | Cloud Run + Eventarc | Validates mandatory YAML frontmatter (`Target_Audience`, `Last_Verified_Date`, `Content_Owner`) and rejects unindexed macros. | ~50–150 ms |
| **2. AST Chunking & Embedding** | Cloud Run + Vertex AI | Splits Markdown strictly along header hierarchies (`#`, `##`, `###`) and prepends breadcrumbs before vectorization. | ~200–500 ms |
| **3. Real-Time Vector Commit** | Cloud SQL / AlloyDB (`pgvector`) | Writes vectors transactionally into HNSW-indexed tables with deterministic Role-Level Access Control (RLAC). | ~100–300 ms |
| **4. Multi-Surface ADK Runtime** | GCP Agent Runtime + MCP Tools | Enforces prompt sanitization (Model Armor), On-Behalf-Of (OBO) user identity, and deterministic tool actions. | ~1.5–3.0 s |
| **5. Closed-Loop Telemetry** | Pub/Sub + BigQuery + Vertex AI | Clusters unresolved queries (`no_coverage`), auto-drafts structured Markdown SOPs, and alerts SMEs via Enterprise Chat. | Asynchronous / Batch |

---

## 🔒 Enterprise Security & Governance

1. **On-Behalf-Of (OBO) Execution:** Rather than running under a single, over-privileged Service Account, runtime actions propagate authenticated end-user identity (via OAuth tokens) to downstream MCP tools.
2. **Deterministic Routing:** LLMs are restricted to natural language synthesis. Operational actions (ITSM ticket creation, ITSM platform routing, password resets) execute via deterministic code.
3. **Model Armor Prompt Defense:** Inbound user prompts are pre-screened for jailbreaks, prompt injection, and PII leakage before touching reasoning models.

---

## 🚀 Deployment Instructions

### Prerequisites
* Google Cloud Project with Billing enabled.
* Google Cloud CLI (`gcloud`) initialized.
* Terraform >= 1.5.0.

### Step 1: Environment Setup
```bash
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    aiplatform.googleapis.com \
    pubsub.googleapis.com \
    bigquery.googleapis.com \
    eventarc.googleapis.com
