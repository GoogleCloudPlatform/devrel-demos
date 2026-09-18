# 🌉 Bridge Deck: Complete Operational and Architecture Guide

> **Last Updated:** September 18, 2026

This document is the operational guide and system reference
for the **Bridge Deck Multi-Vendor Agent Platform**.

---

## 🧭 1. Astra quickstart & bootstrap protocol

When an Antigravity agent is initialized to embody Astra, follow this checklist to achieve operational readiness:

### Step 1: Internalize identity and role directives
- Read and internalize `agents/bridge_deck_lead.json`.
- Embody Astra: Bridge Deck Lead and Communications Officer. Maintain architectural integrity, orchestrate multi-vendor model cognition, pair warmly with the human operator, and enforce safety and governance gates (**Gate G1**, **Gate G2**, **Gate C2**, and **Zero-PII**).

### Step 2: Establish working directory and Python environment
- Always execute commands from the repository root directory (`bridge_deck`).
- Ensure Python 3.10+ virtual environment exists with dependencies installed:
  ```bash
  python3 -m venv venv
  ./venv/bin/pip install -r requirements.txt
  ```

### Step 3: Verify Google Cloud context and credentials
- Verify Google Cloud Application Default Credentials (ADC) and project context:
  ```bash
  gcloud auth list
  gcloud config get-value project
  ```
- If `deploy.env` is missing, initialize it from template:
  ```bash
  cp deploy.env.example deploy.env
  ```

### Step 4: Run pre-flight test gate
- Ensure all 109 automated unit and integration tests pass before launching services or committing code:
  ```bash
  ./venv/bin/python -m unittest discover -s tests
  ```

### Step 5: Launch local background server
- Launch the server detached in the background with `nohup` (never run in foreground to avoid blocking conversation turns):
  ```bash
  nohup ./venv/bin/python bridge_runner.py --port 8080 > server.log 2>&1 &
  ```
- Verify health: `curl -s http://127.0.0.1:8080/api/identity`
- Provide operator with the link: `http://localhost:8080`.

### Step 6: Connect to live Cloud Run production (When requested)
- If the operator asks to connect to the live Cloud Run deployment:
  ```bash
  # 1. Start authenticated IAM proxy tunnel on port 8081
  gcloud run services proxy bridge-deck --region us-central1 --port 8081 &
  
  # 2. Retrieve application auth token from Secret Manager
  TOKEN=$(gcloud secrets versions access latest --secret=BRIDGE_AUTH_TOKEN)
  
  # 3. Launch UI with authenticated token
  ./scripts/open_cloud_deck.sh
  # Or provide direct URL: http://127.0.0.1:8081/?token=${TOKEN}
  ```

---

## 👥 2. Team roster

Bridge Deck includes the following team members out of the box:

| Collaborator | Role | Engine or provider |
| :--- | :--- | :--- |
| **🧭 Team Lead** | **Project Lead and Coordinator** | Human Leader |
| **🏗️ Architect** | **Systems Architect** | `vertex-ai` (`gemini-3.7-flash`) |
| **⚙️ Engineer** | **Implementation Engineer** | `google-adk` (`gemini-3.7-flash`) |
| **💡 Advisor** | **Technical and Scientific Advisor** | `vertex-ai` (`claude-opus-5`) |

For details, consult `agents/*.agent.json` and `profiles.json`.

---

## 🏛️ 3. Key subsystems and design principles

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

### Tenant isolation & optimistic concurrency storage (`core/tenant.py`)

- Stores each tenant partition under `data/tenants/<tenant_id>/` (or `/mnt/bridge-data/tenants/<tenant_id>/` in cloud mode).
- Avoids tracking operator personal information in repository files;
  initial setups self-scaffold from neutral archetypes in `seed/`.
- Provides an in-memory cache (SWR) for instantaneous UI switching
  between project workspaces.
- **Optimistic Concurrency & GCS FUSE (`core/tenant.py:GCSStorageAdapter`)**:
  Enforces atomic writes using Google Cloud Storage `if-generation-match` preconditions. Concurrent update conflicts raise `StorageConflictError` (HTTP 409) with automated retry handling.

### Distributed durable queue (`core/a2a_dispatcher.py`)

- **Pluggable queue backends**: Uses `InMemoryQueueBackend` for local workstations and `CloudTasksQueueBackend` in Google Cloud.
- **Cloud Tasks integration**: Delivers A2A tasks durably via Google Cloud Tasks API v2 with automatic retry, surviving instance restarts and scaling.
- **Defense-in-depth security**: Strictly enforces `hmac.compare_digest` on `BRIDGE_AUTH_TOKEN` and Google IAM OIDC token verification on `/api/a2a/task`.

### Multi-user identity governance (`core/identity.py`)

- **Deterministic principal extraction**: Resolves callers via Google Cloud IAP headers, IAM bearer tokens, and application headers.
- **Tenancy boundary enforcement**: Validates tenant access against authorized principal bindings; read-only roles are prohibited from write actions.

### Multi-threaded HTTP server (`bridge_runner.py`)

- Uses `ThreadingHTTPServer` to prevent long model generations
  from blocking web traffic and background polling requests.
- Uses atomic file replacement (`os.replace`) and CAS generation matching for task queue and storage safety.

---

## 🚀 4. How to run and manage Bridge Deck

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

## ☁️ 5. Google Cloud Run Deployment Protocol (Astra SOP)

When an operator requests a production deployment to Google Cloud Run, any Astra agent can execute the complete end-to-end rollout following this Standard Operating Procedure.

> **Working Directory**: All pre-flight checks, deployment scripts, proxy tunnels, and verification commands MUST be executed from the repository root directory (`bridge_deck`).

#### 1. Pre-Flight Configuration
1. Verify Google Cloud authentication and project context:
   ```bash
   gcloud auth list
   gcloud config get-value project
   ```
2. Ensure `deploy.env` exists (copy from template if missing):
   ```bash
   cp deploy.env.example deploy.env
   ```
   Verify `deploy.env` contains:
   - `GOOGLE_CLOUD_PROJECT=<target-gcp-project>`
   - `GCP_REGION=us-central1`
   - `BRIDGE_DEFAULT_TENANT=<tenant-id>` (must correspond to an existing tenant directory)

#### 2. Run Local Pre-Flight Gates
Before deploying, Astra must ensure all automated unit tests and disaster recovery checks pass:
```bash
# Verify all 109 unit and integration tests are green
./venv/bin/python -m unittest discover -s tests

# Verify cold backup depot invariants M1–M3 in dry-run mode
./scripts/sync_backup_depot.sh --dry-run
```

#### 3. Execute Deployment Pipeline
Run the automated deployment script:
```bash
./deploy_cloud_run.sh
```

The script automatically executes all 6 stages:
1. **Test Gate**: Executes unittest discovery.
2. **APIs & Artifact Registry**: Enables Cloud Run, Cloud Tasks, Secret Manager, Cloud Build, and AI Platform APIs.
3. **Storage Bucket**: Provisions versioned GCS bucket (`gs://${GOOGLE_CLOUD_PROJECT}-bridge-deck-data`) with 7-day soft-delete retention.
4. **Service Account & Queue**: Creates runtime SA (`bridge-deck-sa`), `BRIDGE_AUTH_TOKEN` secret, and `a2a-tasks` Cloud Tasks queue.
5. **Cloud Run Rollout**: Builds container and deploys with Gate G1 (`--no-allow-unauthenticated`), Gate G2 (`--max-instances=1`), `--concurrency=20`, `--timeout=3600`, and GCS FUSE volume mounted at `/mnt/bridge-data`.
6. **URL Injection & IAM**: Resolves live `SERVICE_URL`, updates `CLOUD_TASKS_SERVICE_URL`, and binds `roles/run.invoker` to the runtime SA.

#### 4. Post-Deployment Verification
Once deployment reports complete, Astra verifies the live service:
```bash
# 1. Start authenticated proxy tunnel in background on port 8081
gcloud run services proxy bridge-deck --region "${GCP_REGION}" --project "${GOOGLE_CLOUD_PROJECT}" --port 8081 &

# 2. Retrieve application secret token
TOKEN=$(gcloud secrets versions access latest --secret=BRIDGE_AUTH_TOKEN --project="${GOOGLE_CLOUD_PROJECT}")

# 3. Validate endpoints return HTTP 200
curl -s -H "X-Bridge-Auth: ${TOKEN}" http://127.0.0.1:8081/api/identity
curl -s -H "X-Bridge-Auth: ${TOKEN}" http://127.0.0.1:8081/api/projects

# 4. Open UI in operator's browser
./scripts/open_cloud_deck.sh
```

#### 5. Architectural Invariants Astra Must Enforce
* **Gate G1**: Never pass `--allow-unauthenticated` directly to Cloud Run. Keep ingress protected via Google IAM.
* **Gate G2**: Never increase `--max-instances` above 1. Single-instance concurrency is load-bearing for GCS storage safety and authoritative cascade bounds.
* **Gate C2**: Never deploy regressions to production without passing the Lumen compliance audit.
* **Zero-PII**: Never check personal operator literals into git-tracked files. All configuration must resolve via environment variables or `deploy.env`.

---

## 💬 6. Command-line interface (`bridge_cli.py`)

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

## 📜 7. Register a new agent (Zero-code-edit onboarding)

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

## ⚠️ 8. Troubleshooting and operational gotchas

### Empty projects list in browser dashboard (HTTP 401)
- **Cause**: The browser's `localStorage` has an outdated or missing `bridge_auth_token`, causing `/api/projects` to reject requests with 401 Unauthorized.
- **Remediation**:
  1. Retrieve the active token from Secret Manager:
     ```bash
     TOKEN=$(gcloud secrets versions access latest --secret=BRIDGE_AUTH_TOKEN)
     ```
  2. Launch via the automated launcher `./scripts/open_cloud_deck.sh`, or open the URL with the token query parameter: `http://127.0.0.1:8081/?token=${TOKEN}`.
  3. The web frontend automatically stores the token in `localStorage` upon initial load.

### Antigravity sandbox permission errors (`Operation not permitted`)
- **Cause**: Antigravity's standard sandbox isolates network operations and restricts `.git` file locking by default.
- **Remediation**: When running tests that invoke network services, git pushes, or multi-process socket bindings, run the tool call with `BypassSandbox: true`.

### Port conflict troubleshooting (`Address already in use`)
- **Cause**: An earlier instance of `bridge_runner.py` (port 8080) or `gcloud run proxy` (port 8081) is lingering.
- **Remediation**: Terminate existing listeners before restarting:
  ```bash
  # Clear port 8080 (local server)
  lsof -ti :8080 | xargs kill -9 2>/dev/null || true
  
  # Clear port 8081 (Cloud Run proxy tunnel)
  lsof -ti :8081 | xargs kill -9 2>/dev/null || true
  ```

### Zero-PII scanner failure (`tests/test_tenant_isolation.py`)
- **Cause**: A hardcoded developer username or non-neutral path literal was committed into repository files.
- **Remediation**: Run `./venv/bin/python -m unittest tests/test_tenant_isolation.py`. Replace any identified operator literals with `${GOOGLE_CLOUD_PROJECT}` or dynamic `gcloud` lookups.

### `HTTP 429 RESOURCE_EXHAUSTED` (Vertex AI quota limits)
- **Cause**: Token-per-minute or request-per-minute quota on a specific base model (`claude-opus-5` or `gemini-2.5-pro`) has reached its cap.
- **Remediation**:
  1. The Bridge Deck dispatcher automatically applies exponential backoff retry.
  2. Request quota expansion in Google Cloud Console under **IAM and Admin** -> **Quotas and System Limits** -> `Vertex AI API`.

### `HTTP 400 FAILED_PRECONDITION` (Region resolution)
- **Cause**: Attempting to invoke a global endpoint against a regional deployment, or vice-versa.
- **Remediation**: `core/router.py:resolve_model_location()` automatically defaults Gemini 3.7 and Claude to `global` and standard models to `us-central1`.
