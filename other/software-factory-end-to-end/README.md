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

## Quickstart (Google Cloud Shell)

```bash
export PATH=$PATH:~/.local/bin
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI=true
gcloud auth application-default login --no-browser

pip install --user --upgrade -r requirements.txt
agents-cli playground --port 8080
```
Open **Web Preview on port 8080** in Cloud Shell.

## Clean Up & Teardown

> **Preview Notice:** At the time of this codelab development, the Antigravity managed agent was in preview (`antigravity-preview-05-2026`), and as such pricing, storage persistence, and billing details will have changed. Check the official Google Cloud Agent Platform documentation for current rates.

1. **Stop Playground:** Press `Ctrl + C` in Cloud Shell.
2. **Local Files:** Remove project workspace with `rm -rf ~/software_factory`.
3. **Cloud Sandbox Environment:** The remote sandbox has an automatic 7-day TTL expiration, or can be torn down immediately via the Google Cloud Console under **Agent Platform** > **Deployments**.
 
## License

All solutions within this repository are provided under the [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license. Please see the [LICENSE](../LICENSE) file for more information.
