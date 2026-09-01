# 🌉 Bridge Deck: Multi-Vendor Autonomous Agent Platform

> **Last Updated:** September 1, 2026

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

---

## 🌟 Key features

- **Multi-vendor frontier model orchestration**:
  Supports Google Gemini 3.7 Flash and Pro, Anthropic Claude
  (through Vertex AI Model Garden), Google ADK runtime,
  and local open-weights backends.
- **Autonomous Agent-to-Agent (A2A) cascades**:
  In-process dispatching and long-polling event streaming (`/api/a2a/events`)
  enables agents to delegate tasks, tag collaborators (`@agent`),
  and coordinate autonomously with loop-detection guardrails.
- **3-tier persistent memory engine**:
  - **Episodic stream**: Full multi-turn conversation logs per project room.
  - **Private semantic tier**: Per-agent isolated working memory (`facts.jsonl`).
  - **Shared common ground**: Cross-agent team decisions and project milestones.
- **Multi-tenant workspace partitioning**:
  Complete filesystem isolation (`data/tenants/<tenant_id>/`)
  with automatic template provisioning from `seed/`.
- **Modular zero-build web UI**:
  Real-time collaborative dashboard featuring collapsible reasoning traces,
  reaction counters, dynamic model discovery, and modular JavaScript architecture.
- **Arize Phoenix OpenTelemetry tracing**:
  Optional observability integration for latency, token consumption,
  and trace evaluations.

---

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

## 🧪 Testing and verification

Run the automated test suite covering tenant isolation, provider routing,
A2A cascading, and governance:

```bash
python -m unittest discover tests
```

---

## 📂 Project structure

```
bridge_deck/
├── bridge_runner.py       # ThreadingHTTPServer, REST API, & static file server
├── model_client.py        # Low-level Google GenAI and Vertex SDK client
├── bridge_cli.py          # Unified CLI for agent messaging and inspections
├── index.html             # Modular semantic HTML dashboard shell
├── static/                # Zero-build modular frontend assets
│   ├── css/
│   │   └── styles.css     # CSS stylesheet (variables, grid, cards, modals)
│   └── js/
│       ├── tenant-fetch.js# Tenant interceptor for API requests
│       ├── state.js       # Central client state store
│       ├── renderer.js    # Markdown & cognitive style formatters
│       ├── navigation.js  # Project, channel, & member navigation
│       ├── modals.js      # Project settings, persona, & engine modals
│       ├── chat.js        # Chat feed, composer, & attachments
│       ├── a2a-monitor.js # A2A live cascade telemetry
│       └── bootstrap.js   # Application lifecycle initialization
├── core/
│   ├── router.py          # Dynamic registry loader & model provider router
│   ├── tenant.py          # Multi-tenant partitioning & filesystem scoping
│   ├── a2a_dispatcher.py  # Agent-to-Agent cascade orchestrator & guardrails
│   └── history.py         # Prompt-layer history synthesizer & self-marking
├── providers/
│   ├── base.py            # Abstract AgentProvider base class
│   ├── vertex_gemini.py   # Google Gemini 3.7 Flash provider
│   ├── vertex_anthropic.py# Anthropic Claude on Vertex AI Model Garden
│   └── google_adk.py      # Google ADK agent provider
├── memory/
│   └── store.py           # 3-tier persistent memory engine
├── seed/                  # Clean template fixtures for initial tenant auto-provisioning
│   ├── profiles.json      # Starter agent roster & metadata
│   ├── projects.json      # Starter collaborative workspace rooms
│   ├── engines.json       # Supported model providers & backends
│   ├── models.json        # Configured model list
│   ├── skill_usage.json   # Seed skill usage telemetry
│   └── agents/            # Declarative JSON agent manifests
├── docs/
│   ├── agent_user_guide.md    # Comprehensive platform architecture & agent guide
│   └── human_user_guide.md    # Practical operator & human user how-to guide
└── tests/                 # Unit & integration test suites (48 tests)
```
