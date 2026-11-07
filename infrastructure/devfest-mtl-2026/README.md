# DevFest Montréal 2026: From Data to Action with Google ADK, Skills & AlloyDB MCP

This demo showcases a customer support and order triage agent built with **Google Agent Development Kit (ADK)**, **ADK Skills** (`SkillToolset`), and **AlloyDB for PostgreSQL** using two switchable **Model Context Protocol (MCP)** architectures:

1. **Option 1 — Local / Custom MCP Toolbox (`MCP_MODE=toolbox`)**: Connects to [MCP Toolbox for Databases](https://github.com/googleapis/mcp-toolbox) (`mcp_toolbox/tools.yaml`) exposing curated, parameterized SQL tools over IAM + ADC.
2. **Option 2 — Managed AlloyDB Remote MCP (`MCP_MODE=remote`)**: Connects directly to Google Cloud's serverless [AlloyDB Remote MCP endpoint](https://docs.cloud.google.com/alloydb/docs/ai/use-alloydb-mcp) (`https://alloydb.googleapis.com/mcp`) over Streamable HTTP with dynamic OAuth token refresh, using the `ticket-triage` skill and `references/schema_guide.md` to ground SQL execution.

---

## Project Structure

```text
infrastructure/devfest-mtl-2026/
├── .env.example                                        # Sample environment configuration
├── Dockerfile                                          # Container image for FastAPI + ADK app
├── requirements.txt                                    # Python dependencies (google-adk, fastapi, etc.)
├── app/
│   ├── main.py                                         # FastAPI server & streaming trace API
│   └── static/index.html                               # Interactive Triage Console & Live MCP Trace UI
├── mcp_toolbox/
│   └── tools.yaml                                      # MCP Toolbox source & SQL tool definitions
├── sql/
│   └── 01_schema_and_seed.sql                          # AlloyDB tables, extensions & sample seed data
└── support_agent/
    ├── agent.py                                        # ADK LlmAgent + SkillToolset + dual MCP toolset
    └── skills/ticket-triage/
        ├── SKILL.md                                    # SLA & escalation policy instructions
        └── references/schema_guide.md                  # On-demand schema reference for Remote MCP SQL
```

---

## Prerequisites

- A Google Cloud project with billing enabled
- [Google Cloud SDK (`gcloud`)](https://cloud.google.com/sdk/docs/install)
- **Google Antigravity** with the **AlloyDB MCP server** enabled
- **Python 3.12+**
- **Node.js 20+** (`npx`, used to launch `@toolbox-sdk/server`)
- `curl` and `jq`

---

## 1. Enable APIs, Grant IAM Roles & Initialize ADC

Set your project, region, and account variables in a terminal:

```bash
export PROJECT_ID="devfest-project"   # Replace with your Google Cloud project ID
export REGION="us-west1"
export USER_EMAIL="$(gcloud config get-value account)"

gcloud config set project "${PROJECT_ID}"
```

### Enable required Google Cloud APIs

```bash
gcloud services enable \
  alloydb.googleapis.com \
  aiplatform.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com \
  iam.googleapis.com
```

### Grant required IAM roles to your user

Grant the roles needed to provision AlloyDB Express, authenticate via IAM database login, connect via MCP Toolbox, invoke the managed AlloyDB Remote MCP server, and call Gemini on Vertex AI:

```bash
for ROLE in \
  roles/alloydb.admin \
  roles/alloydb.databaseUser \
  roles/alloydb.client \
  roles/mcp.toolUser \
  roles/aiplatform.user \
  roles/serviceusage.serviceUsageConsumer; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="user:${USER_EMAIL}" \
    --role="${ROLE}"
done
```

### Initialize Application Default Credentials (ADC)

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project "${PROJECT_ID}"
```

---

## 2. Provision AlloyDB Express & Seed Data in Antigravity

Open this folder (`infrastructure/devfest-mtl-2026`) in **Antigravity** and run the following prompts in chat:

1. **Create the AlloyDB Express cluster and primary instance** (in `us-west1`):
   ```text
   Create an AlloyDB Express cluster named devfest-cluster in my project with Private Service Connect enabled. Then create a 1 vCPU PRIMARY instance named devfest-cluster-pr inside that cluster with Public DNS and IAM authentication enabled.
   ```

2. **Check provisioning duration**:
   ```text
   How much time did it take to create the cluster and the instance?
   ```

3. **Create `support_db` and apply the schema and seed script**:
   ```text
   Create support_db database and in that database run the sql script from sql folder
   ```

---

## 3. Run with Local MCP Toolbox (`MCP_MODE=toolbox`)

### Start MCP Toolbox (Terminal 1)

From `infrastructure/devfest-mtl-2026`, export the `ALLOYDB_*` variables and launch the MCP Toolbox server:

```bash
cd infrastructure/devfest-mtl-2026

export ALLOYDB_PROJECT_ID="devfest-project"   # Replace with your Google Cloud project ID
export ALLOYDB_REGION="us-west1"
export ALLOYDB_CLUSTER="devfest-cluster"
export ALLOYDB_INSTANCE="devfest-cluster-pr"
export ALLOYDB_DATABASE="support_db"
export ALLOYDB_IP_TYPE="public"

npx -y @toolbox-sdk/server --config mcp_toolbox/tools.yaml
```

### Verify MCP Toolbox tools (Terminal 2)

In a second terminal, verify that MCP Toolbox is serving the `support_triage_toolset` tools over HTTP:

```bash
curl -s -X POST http://127.0.0.1:5000/mcp/support_triage_toolset \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | jq '.result.tools[].name'
```

Expected tool names:
- `"find_customer_tickets"`
- `"list_open_high_priority_tickets"`
- `"get_order_details"`
- `"search_past_resolutions"`
- `"update_ticket_status"`

### Initialize Python & configure environment (Terminal 2)

Create a virtual environment, install dependencies, load `.env`, and set `MCP_MODE=toolbox`:

```bash
cd infrastructure/devfest-mtl-2026

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env to set GOOGLE_CLOUD_PROJECT and ALLOYDB_PROJECT_ID to your project ID, then load it:
set -a
source .env
set +a

export MCP_MODE=toolbox
```

### Test in `adk web`

Launch the ADK Developer UI:

```bash
adk web
```

Open the URL printed in the terminal (typically `http://127.0.0.1:8000`) in your browser, select **`support_agent`**, and ask:

```text
Triage all open high-priority tickets and tell me which ones breach our SLA.
```

### Run the FastAPI Triage Console

Stop `adk web` (`Ctrl+C`) and start the web application:

```bash
uvicorn app.main:app --reload --port 8080
```

Open `http://127.0.0.1:8080` in your browser to interact with the **Montréal TechGear Support & Order Triage Agent** and inspect the live **Skill + Local MCP Toolbox** execution trace.

When finished testing Option 1, stop `uvicorn` (`Ctrl+C`) in Terminal 2 (and you can also stop MCP Toolbox in Terminal 1).

---

## 4. Switch to AlloyDB Remote MCP (`MCP_MODE=remote`)

Switch the agent to Google Cloud's managed AlloyDB Remote MCP endpoint (`https://alloydb.googleapis.com/mcp`)—no local MCP Toolbox server is required:

```bash
export MCP_MODE=remote
```

> [!TIP]
> Ensure your IAM database user has privileges on `support_db` (or set `export ALLOYDB_IAM_USER="${USER_EMAIL}"` if authenticating queries as your IAM principal).

### Repeat `adk web` test

```bash
adk web
```

Open `http://127.0.0.1:8000`, select **`support_agent`**, and ask the same prompt:

```text
Triage all open high-priority tickets and tell me which ones breach our SLA.
```

Watch the trace: in `remote` mode, the agent loads `ticket-triage` (`SKILL.md`), dynamically loads `references/schema_guide.md` via `load_skill_resource`, and calls `execute_sql_read_only` directly against `https://alloydb.googleapis.com/mcp`.

### Repeat FastAPI Triage Console test

Stop `adk web` (`Ctrl+C`) and launch the FastAPI app again:

```bash
uvicorn app.main:app --reload --port 8080
```

Open `http://127.0.0.1:8080`—confirm the top-bar badge now shows **`MCP: Cloud AlloyDB Remote (read/write)`** and test the preset triage and escalation flows.

---

## 5. Clean Up

To avoid incurring ongoing charges after the demo, delete the AlloyDB instance and cluster (either by asking Antigravity to delete `devfest-cluster-pr` and `devfest-cluster`, or via `gcloud`):

```bash
gcloud alloydb instances delete devfest-cluster-pr \
  --cluster=devfest-cluster \
  --region=us-west1 \
  --project="${PROJECT_ID}" \
  --quiet

gcloud alloydb clusters delete devfest-cluster \
  --region=us-west1 \
  --project="${PROJECT_ID}" \
  --quiet
```
