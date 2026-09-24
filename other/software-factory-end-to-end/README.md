# Software Factory Reference Implementation

> **Notice:** This demo is unmaintained and provided as-is.

Reference code for the Google Cloud Hands-on Lab:
**"HOL: Architecting an Autonomous Software Factory: End-to-End Agentic Delivery"**.

## Architecture & Concepts

- **Tech Lead (`tech_lead`):** Orchestrator running locally via ADK using `gemini-3.8-flash`. Parses user requests into formal specifications and manages the verification loop.
- **Antigravity Managed Agent (`antigravity_agent`):** Hosted on Google Cloud Agent Platform (`antigravity-preview-05-2026`). You leave it running in the cloud, accessible anywhere over API, with code execution handled in cloud sandboxes.

```
                      [ Feature Request ]
                               │
                               ▼
               ┌───────────────────────────────┐
               │       Tech Lead (ADK)         │ gemini-3.8-flash (Orchestrator)
               └───────┬───────────────┬───────┘
                       │               │
        Phase 1: Build │               │ Phase 2: Test (Hands off code)
        session_id:    │               │ session_id:
        "dev-build"    │               │ "qa-eval-v1" (Fresh)
                       ▼               ▼
      ┌─────────────────────────────────────────────────┐
      │         Antigravity Managed Agent               │
      │        (antigravity-preview-05-2026)            │
      │                                                 │
      │  [dev-build Session]       [qa-eval-v1 Session] │
      │  Retains patch context     Fresh, clean context │
      └────────────────────────┬────────────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │          Quality Gate         │ ──[ Tests Fail (max 2 retries) ]──┐
               └───────────────┬───────────────┘                                   ▼
                               │                                       Fixes in "dev-build";
                        [ Tests Pass ]                                 re-tests in "qa-eval-v2".
                               ▼
                     [ Delivery Package ]
```

### Sessions
- **dev-build session:** Stays open so the developer agent retains context when fixing bugs.
- **qa-eval-v{n} sessions:** Fresh session each test run so tests are written objectively against the spec without assertion softening.

## Prerequisites & Environment Setup

Run these commands in your shell to authenticate and configure Vertex AI:

```bash
export PATH=$PATH:~/.local/bin
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI=true
gcloud auth application-default login --no-browser

# Install dependencies (ADK, GenAI SDK, pytest)
pip install --user --upgrade -r requirements.txt
```

## Project Structure

```text
software_factory/
├── lead_agent_only/         # Standalone Tech Lead architect agent (ADK)
│   ├── agent.py
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── agents-cli-manifest.yaml
├── environment/             # Sandbox provisioner script & configs
│   ├── create_environment.py
│   └── requirements.txt
└── integrated_factory/      # Full end-to-end multi-agent software factory
    ├── agent.py             # Orchestrator (Tech Lead + persistent Antigravity agent)
    ├── barista.py           # Domain implementation module
    ├── test_barista.py      # Independent unit test suite
    ├── pyproject.toml
    ├── requirements.txt
    └── agents-cli-manifest.yaml
```

---

## How to Run

### Option 1: Run the Standalone Tech Lead (`lead_agent_only/`)

To inspect and test the Tech Lead architect agent standalone without sub-agents or managed sandboxes:

```bash
cd lead_agent_only

# Ensure port 8080 is clear, then start playground in the background
fuser -k 8080/tcp 2>/dev/null || true
agents-cli playground --port 8080 > playground.log 2>&1 &
```

1. Open **Web Preview on port 8080** in Cloud Shell.
2. In the chat box, send a prompt:
   ```text
   Design an automated coffee barista order and pricing engine for a cafe.
   ```
3. Observe how the Tech Lead breaks the problem down into structured technical specifications, dataclasses, formulas, and edge cases.
4. When finished, return to the root folder:
   ```bash
   cd ..
   ```

---

### Option 2: Provision the Remote Sandbox (`environment/`)

Before running the full multi-agent factory, stop the standalone playground and provision a persistent cloud sandbox container:

```bash
# Free port 8080 from previous playground
fuser -k 8080/tcp 2>/dev/null || true

cd environment
python3 create_environment.py
```

This captures the canonical server-assigned `environment_id` (`env_CAEQ...`) and writes it to `.env`. Export it to your shell session:

```bash
export ANTIGRAVITY_ENV_ID=$(grep ANTIGRAVITY_ENV_ID .env | cut -d '=' -f2)
echo "Active Sandbox: $ANTIGRAVITY_ENV_ID"
cd ..
```

---

### Option 3: Run the Full Software Factory (`integrated_factory/`)

With `ANTIGRAVITY_ENV_ID` exported, navigate to `integrated_factory/` to launch the complete multi-agent delivery engine:

```bash
cd integrated_factory
```

#### Interactive Web UI (Playground)
```bash
# Ensure port 8080 is clear, then start integrated playground in the background
fuser -k 8080/tcp 2>/dev/null || true
agents-cli playground --port 8080 > playground.log 2>&1 &
```
Open **Web Preview on port 8080** and submit your user story or feature ticket:
```text
Build a Python module for Byte & Brew Coffee Shop's smart barista system in barista.py with drink pricing, decaf caffeine tracking, and safety caps. Test with pytest in the sandbox and report results.
```

#### Headless / Non-Interactive (CLI)
You can also run a direct prompt without opening the browser:
```bash
adk run . "Design and implement the Byte & Brew coffee ordering engine in barista.py, test it with pytest, and report verified results."
```

---

### Option 4: Run the Local Unit Tests (`test_barista.py`)

To verify the barista implementation logic locally outside of the agent sandbox:

```bash
cd integrated_factory
pytest test_barista.py -v
```
All 6 tests should pass:
```text
test_barista.py::test_standard_medium_latte PASSED
test_barista.py::test_plant_milk_and_syrup_surcharge PASSED
test_barista.py::test_extra_shots_pricing_and_caffeine PASSED
test_barista.py::test_decaf_caffeine_calculation PASSED
test_barista.py::test_invalid_drink_size_raises_value_error PASSED
test_barista.py::test_excessive_shots_safety_cap PASSED
```

## Clean Up & Teardown

> **Preview Notice:** At the time of this codelab development, the Antigravity managed agent was in preview (`antigravity-preview-05-2026`), and as such pricing, storage persistence, and billing details will have changed. Check the official Google Cloud Agent Platform documentation for current rates.

1. **Stop Playground:** Run `fuser -k 8080/tcp 2>/dev/null || true` to stop any running background servers.
2. **Local Files:** Remove project workspace with `rm -rf ~/software_factory`.
3. **Cloud Sandbox Environment:** The remote sandbox has an automatic 7-day TTL expiration, or can be torn down immediately via the Google Cloud Console under **Agent Platform** > **Deployments**.
 
## License

All solutions within this repository are provided under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license. Please see the [LICENSE](../LICENSE) file for more information.
