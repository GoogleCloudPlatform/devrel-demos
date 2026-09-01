# 🌉 Bridge Deck: Complete Operational and Architecture Guide

> **Last Updated:** September 1, 2026

This document is the operational guide and system reference
for the **Bridge Deck Multi-Vendor Agent Platform**.

---

## 👥 1. Team roster

Bridge Deck includes the following team members out of the box:

| Collaborator | Role | Engine or provider |
| :--- | :--- | :--- |
| **🧭 Team Lead** | **Project Lead and Coordinator** | Human Leader |
| **🏗️ Architect** | **Systems Architect** | `vertex-ai` (`gemini-3.7-flash`) |
| **⚙️ Engineer** | **Implementation Engineer** | `google-adk` (`gemini-3.7-flash`) |
| **💡 Advisor** | **Technical and Scientific Advisor** | `vertex-ai` (`claude-opus-5`) |

For details, consult `agents/*.agent.json` and `profiles.json`.

---

## 🏛️ 2. Key subsystems and design principles

### Registry-driven agent router (`core/router.py`)

- Dynamically scans `agents/*.agent.json` upon file modification.
- **Formal JSON Schema validation**:
  Validates every manifest against [`agents/_schema.json`](file://./agents/_schema.json)
  using `jsonschema.validate()`.
- **The containment principle**:
  Wires new provider adapters in `_create_provider()`
  without modifying caller code.

### 3-tier hybrid memory architecture (`memory/store.py`)

- **Private semantic tier (`memory/semantic/<agent_id>/facts.jsonl`)**:
  Each agent maintains private distilled working facts.
- **Shared project common ground (`memory/shared/<project_id>.json`)**:
  Universally read by all project members.
  Stores ratified team architecture decisions.
- **Episodic stream (`history_<project_id>.json`)**:
  Complete conversational history across room turns.
- **Cognitive injection**:
  `build_agent_self_context(agent_id, project_id)`
  injects private semantic facts and shared project decisions
  into the agent's system prompt header.

### Canonical history synthesizer (`core/history.py`)

- Shares the `format_history_block()` function across all providers
  (`VertexAnthropicProvider`, `VertexGeminiProvider`, `GoogleADKProvider`).
- **Dynamic self-marking `(you)`**:
  Injects structural self-identification for the reading agent
  (for example, `[Advisor (you)]:` or `[Architect (you)]:`).
- **Zero fabricated speech**:
  Omits internal placeholder turns so models never mimic synthetic utterances.
- **Prefix collision safety**:
  Discovers prefixes dynamically from registered manifests
  and sorts them by length descending.

### Multi-tenant storage and isolation (`core/tenant.py`)

- Stores each tenant partition under `data/tenants/<tenant_id>/`.
- Avoids tracking operator personal information in repository files;
  initial setups self-scaffold from neutral archetypes in `seed/`.
- Provides an in-memory cache (SWR) for instantaneous UI switching
  between project workspaces.

### Multi-threaded HTTP server (`bridge_runner.py`)

- Uses `ThreadingHTTPServer` to prevent long model generations
  from blocking web traffic and background polling requests.
- Uses atomic file replacement (`os.replace`) for task queue safety.

---

## 🚀 3. How to run and manage Bridge Deck

### Detached background execution (Mandatory for AI agents)

To keep the primary conversation stream unblocked,
launch the server as a detached background daemon:

```bash
cd ./bridge_deck
nohup ./venv/bin/python bridge_runner.py --port 8080 > server.log 2>&1 &
```

> [!WARNING]
> **Critical Rule for Antigravity Agents**:
> Never run `bridge_runner.py` in the foreground
> or inside an infinite subagent loop.
> Doing so attaches active task handles to the chat window,
> causing the conversation stream to block.
> Always use `nohup ... > server.log 2>&1 &`,
> which completes immediately with exit code 0
> while the server runs independently in the background.

### Dashboard endpoints

- **Main Bridge Deck UI**: `http://localhost:8080`
- **Skill Analytics**: `http://localhost:8080/#skills`
- **Arize Phoenix Visualizer**: `http://localhost:6006`

### Port conflict troubleshooting and restarts

If port 8080 is occupied by an earlier process,
terminate the process and restart:

```bash
lsof -ti :8080 | xargs kill -9 2>/dev/null || true
nohup ./venv/bin/python bridge_runner.py --port 8080 > server.log 2>&1 &
```

---

## 💬 4. Command-line interface (`bridge_cli.py`)

To send messages or queries to any agent directly,
use `bridge_cli.py`:

```bash
# Query Advisor
./venv/bin/python bridge_cli.py post "Hi Advisor, please evaluate our memory store." --mode advisor_direct

# Query Engineer
./venv/bin/python bridge_cli.py post "Hi Engineer, please confirm system readiness." --mode engineer_direct

# Query Architect
./venv/bin/python bridge_cli.py post "Hi Architect, status check." --mode architect_direct

# Read History
./venv/bin/python bridge_cli.py read --limit 5
```

---

## 📜 5. Register a new agent (Zero-code-edit onboarding)

To add a new agent to Bridge Deck,
create a new JSON manifest in `agents/<agent_id>.agent.json`
conforming to [`agents/_schema.json`](file://./agents/_schema.json):

```json
{
  "id": "specialist",
  "name": "Specialist",
  "role": "Domain Specialist",
  "system_prompt": "You are the Domain Specialist for Bridge Deck...",
  "access_read": ["/path/to/workspace"],
  "access_write": [],
  "memory": {
    "silo": "private",
    "shared_access": ["*"]
  },
  "provider": {
    "type": "vertex-gemini",
    "model": "gemini-3.7-flash",
    "project_id": "your-gcp-project-id",
    "location": "global"
  }
}
```

The router dynamically detects, validates,
and routes messages to the new agent.

---

## ⚠️ 6. Troubleshooting and error modes

### `HTTP 429 RESOURCE_EXHAUSTED` (Vertex AI quota limits)

- **Cause**:
  Token-per-minute or request-per-minute quota on a specific base model
  (such as `claude-opus-5` or `gemini-2.5-pro`) has reached its cap.
- **Remediation**:
  1.  The Bridge Deck dispatcher implements automatic exponential backoff retry.
  2.  Request quota expansion in Google Cloud Console under
      **IAM and Admin** -> **Quotas and System Limits** -> `Vertex AI API`.

### `HTTP 400 FAILED_PRECONDITION` (Region resolution)

- **Cause**:
  Attempting to invoke a global endpoint against a regional deployment,
  or vice-versa.
- **Remediation**:
  `core/router.py:resolve_model_location()`
  automatically defaults Gemini 3.7 and Claude to `global`
  and standard models to `us-central1`.
