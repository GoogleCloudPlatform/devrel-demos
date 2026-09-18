# 🌉 Bridge Deck: Multi-Vendor Autonomous Agent Platform

> **Last Updated:** September 18, 2026

**Bridge Deck** is a unified multi-agent cognitive collaboration platform
built on **Google Cloud Vertex AI** and the **Google GenAI SDK**.
It connects human operators and heterogeneous AI models
into collaborative project workspaces with 3-tier persistent memory,
in-process agent-to-agent delegation, and fail-closed security governance.

- 📖 [**Human User & Operator Guide**](docs/human_user_guide.md):
  Practical step-by-step instructions for pairing with Astra,
  navigating the web dashboard, adding models, and managing workspaces.
- 🤖 [**Agent Operational & Architecture Guide**](docs/agent_user_guide.md):
  Comprehensive system architecture reference, JSON schema manifests,
  3-tier memory engine, and background daemon execution rules.
- ☁️ [**Google Cloud Migration Plan**](docs/CLOUD_MIGRATION_PLAN.md):
  Full specification for Google Cloud Run deployment, GCS FUSE storage CAS,
  Cloud Tasks durable queue, Gate G1/G2 governance, and disaster recovery.

---

## 🌟 Key features

- **Google Cloud Run Production Deployment**:
  Fully containerized production deployment on Google Cloud Run with GCS FUSE persistence,
  strict Gate G1 (`--no-allow-unauthenticated`) IAM ingress, and Gate G2 single-instance lock.
- **Durable Distributed A2A Queue (Google Cloud Tasks)**:
  Replaces in-process memory queues in cloud mode with distributed Cloud Tasks (`a2a-tasks`),
  enabling multi-turn agent delegations to survive restarts and crashes with automatic retry.
- **Optimistic Concurrency & GCS CAS Preconditions**:
  `GCSStorageAdapter` provides atomic file writes using `if-generation-match` preconditions
  on versioned Cloud Storage buckets with 7-day soft-delete retention and zero data loss.
- **Multi-vendor frontier model orchestration**:
  Supports Google Gemini 3.7 Flash and Pro, Anthropic Claude
  (through Vertex AI Model Garden), Google ADK runtime,
  and local open-weights backends.
- **Autonomous Agent-to-Agent (A2A) cascades**:
  Autonomous dispatching and long-polling event streaming (`/api/a2a/events`)
  enables agents to delegate tasks, tag collaborators (`@agent`),
  and coordinate autonomously with loop-detection guardrails.
- **3-tier persistent memory engine**:
  - **Episodic stream**: Full multi-turn conversation logs per project room.
  - **Private semantic tier**: Per-agent isolated working memory (`facts.jsonl`).
  - **Shared common ground**: Cross-agent team decisions and project milestones.
- **Multi-tenant workspace partitioning & Identity Governance**:
  Filesystem isolation (`data/tenants/<tenant_id>/` or `/mnt/bridge-data/tenants/<tenant_id>/`)
  with deterministic principal-to-tenant mapping in `core/identity.py`.
- **Modular zero-build web UI**:
  Real-time collaborative dashboard featuring collapsible reasoning traces,
  reaction counters, dynamic model discovery, and high-contrast verdict styling.
- **Cold Disaster Recovery Mirror (Invariants M1–M3)**:
  Automated one-way push-only mirror script (`scripts/sync_backup_depot.sh`)
  with pre-push PII verification and transport-layer fetch prohibition.

## 👥 Default team roster and engines

| Avatar | Role | Model or engine | Default access scope |
| :--- | :--- | :--- | :--- |
| **🧭 Team Lead** | Project Lead and Coordinator | Human Leader | Full Workspace Access |
| **🏗️ Systems Architect** | Systems Architect | Vertex Gemini 3.7 Flash (`global`) | Full Workspace Access |
| **⚙️ Implementation Engineer** | Implementation Engineer | Vertex Gemini 3.7 Flash (`global`) | Full Workspace Access |
| **💡 Technical Advisor** | Technical Advisor | Vertex Anthropic Claude Opus 5 (`global`) | Read-Only Advisory Access |

---

## 🏛️ Architecture overview

```
                               ┌────────────────────────┐
                               │     Bridge Runner      │
                               │  (ThreadingHTTPServer) │
                               └───────────┬────────────┘
                                           │
                        ┌──────────────────┴──────────────────┐
                        │                                     │
             ┌──────────▼──────────┐               ┌──────────▼──────────┐
             │    Agent Router     │               │    Memory Store     │
             │   (core/router.py)  │               │   (memory/store.py) │
             └──────────┬──────────┘               └──────────┬──────────┘
                        │                                     │
        ┌───────────────┼───────────────┐          ┌──────────┴──────────┐
        │               │               │          │                     │
┌───────▼───────┐┌──────▼───────┐┌──────▼───────┐┌─▼─────────────┐┌──────▼────────────┐
│VertexAnthropic││ VertexGemini ││  Google ADK  ││Private Semantic││Shared Common Ground│
│ (Claude Opus) ││ (Gemini 3.7) ││(Agent Runtime││(facts.jsonl)  ││ (Decisions JSON)   │
└───────────────┘└───────────────┘└───────────────┘└───────────────┘└─────────────────────┘
```

---

## 📋 Prerequisites

- [Google Antigravity](https://antigravity.google/)
  (your AI pair programmer who can install dependencies, configure environments, authenticate cloud services, and launch the platform for you).

> [!NOTE]
> For manual setup without an Antigravity agent, you need Python 3.10+, `git`,
> and Google Cloud authentication (`gcloud auth application-default login`) on macOS, Linux, or Windows.

---

## 🚀 Quick start

### Automated setup with your Antigravity agent

You can ask your Antigravity agent:
> *"Please set up Bridge Deck for me: clone the repository, create a Python virtual environment, install dependencies, verify Google Cloud authentication, and launch the server in the background."*

### Manual setup

#### 1. Clone and set up your environment

```bash
# Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` to set your Google Cloud project ID and location:

```bash
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

### 3. Start the server

```bash
python bridge_runner.py --port 8080
```

> [!TIP]
> **Detached Execution (for Agent Environments)**:
> If running inside autonomous agent sessions,
> run detached to avoid blocking active task loops:
> ```bash
> nohup python bridge_runner.py --port 8080 > server.log 2>&1 &
> ```

### 4. Access the platform

- **Bridge Dashboard UI**: [http://localhost:8080](http://localhost:8080)
- **Skill Usage Analytics**: [http://localhost:8080/#skills](http://localhost:8080/#skills)
- **Arize Phoenix Tracing**: [http://localhost:6006](http://localhost:6006) _(if enabled)_

---

## 💬 Command-line interface (`bridge_cli.py`)

Send messages or queries to any agent on the roster directly from the command line:

```bash
# 1. Query Technical Advisor (Claude Opus)
python bridge_cli.py post "Please review our system architecture." --sender "Team Lead" --mode advisor_direct

# 2. Query Systems Architect (Gemini 3.7 Flash)
python bridge_cli.py post "Verify multi-tenant storage partitioning." --sender "Team Lead" --mode architect_direct

# 3. Read Recent History
python bridge_cli.py read --limit 5
```

---

---

## 🧪 Testing and verification

Run the automated test suite covering tenant isolation, provider routing,
A2A cascading, Cloud Tasks durable queuing, storage CAS, and identity governance:

```bash
./venv/bin/python -m unittest discover -s tests
```
*Current test suite status:* **109 / 109 tests passing (100% green)**.

---

## ☁️ Google Cloud Production Deployment

The Bridge Deck is containerized and deployed to Google Cloud Run with GCS FUSE persistence.

```bash
# 1. 1-Click Launch into Cloud Production Web Deck
./scripts/open_cloud_deck.sh

# 2. Deploy updates to Cloud Run
./deploy_cloud_run.sh

# 3. Synchronize cold disaster recovery depot (Invariants M1–M3)
./scripts/sync_backup_depot.sh --dry-run
```

---

## 📂 Project structure

```
bridge_deck/
├── bridge_runner.py       # ThreadingHTTPServer, REST API, & static file server
├── model_client.py        # Low-level Google GenAI and Vertex SDK client
├── bridge_cli.py          # Unified CLI for agent messaging and inspections
├── deploy_cloud_run.sh    # 6-stage automated Cloud Run deployment pipeline
├── cloudbuild.yaml        # Push-on-main Cloud Build CI/CD pipeline
├── Dockerfile             # Multi-stage container definition with gcsfuse
├── index.html             # Modular semantic HTML dashboard shell
├── scripts/
│   ├── open_cloud_deck.sh # 1-click launcher via authenticated IAM proxy tunnel
│   └── sync_backup_depot.sh # M1–M3 disaster recovery cold mirror sync
├── static/                # Zero-build modular frontend assets
│   ├── css/styles.css     # CSS stylesheet (variables, grid, cards, modals)
│   └── js/                # Modular frontend JavaScript (tenant, state, chat, renderer)
├── core/
│   ├── router.py          # Dynamic registry loader & model provider router
│   ├── tenant.py          # Multi-tenant partitioning & GCSStorageAdapter CAS
│   ├── identity.py        # Principal extraction, tenant binding, & authorization
│   ├── a2a_dispatcher.py  # A2A cascade orchestrator (Cloud Tasks & InMemory)
│   └── history.py         # Prompt-layer history synthesizer & self-marking
├── providers/             # VertexGemini, VertexAnthropic, GoogleADK adapters
├── memory/
│   └── store.py           # 3-tier persistent memory engine
├── seed/                  # Clean template fixtures for initial tenant provisioning
├── docs/
│   ├── CLOUD_MIGRATION_PLAN.md # Full architecture & migration specification
│   ├── PHASE1_CAS_REPORT.md    # Optimistic concurrency CAS verification report
│   ├── human_user_guide.md     # Practical operator & human user how-to guide
│   └── agent_user_guide.md     # Comprehensive platform architecture & agent guide
└── tests/                 # Comprehensive unit & integration suite (109 tests)
```
