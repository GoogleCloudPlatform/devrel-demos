# CHARM Workspace Rules (`AGENTS.md`)

## 1. Strict Prohibition on Tier 2 / Heuristic Fallbacks (CRITICAL)

- **NEVER use Tier 2 (`evaluateBrowserSystemOne`, `evaluateBrowserDecisions`, `evaluate_browser_decisions_via_jsc`, or any keyword/lexical heuristic) as a runtime fallback** when calling the decision model (`gemini-decision-1` on `POST https://generativelanguage.googleapis.com/v1beta/decisions`).
- **Never fail silently.** If the live `gemini-decision-1` model is unavailable for any reason—including a missing `GEMINI_API_KEY`, network error, timeout, CORS block, or non-200 HTTP status—both the browser runtime (`app.js`) and the Python client (`charm_gemini/client.py`) **MUST throw an explicit error** and surface it visibly to the user (e.g., via `#form-error-banner` and `#transport-status-pill` in the UI, or `RuntimeError` in Python).
- **No `try / catch` fallback routing:** Never catch a live API error or missing API key and substitute synthetic or heuristic scores in production runtime paths (`runSystemOneEvaluation`, `callGeminiDecisionsApi`, `handleEvaluateSubmit`, `call_gemini_decisions_api`).
- **Testing isolation only:** `evaluateBrowserSystemOne` (in `ocean-core.js`) and `evaluate_browser_decisions_via_jsc` (in `charm_gemini/client.py`) may only be invoked explicitly inside automated test suites (`tests/`) to test schema normalization and UI rendering—never as a fallback in user-facing evaluation flows.
