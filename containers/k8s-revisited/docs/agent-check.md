# The agent check

Each episode asks one question: can a coding agent write this episode's Kubernetes config for GKE correctly, and what does the agent harness fix?

## Hypothesis

Models trained mostly on older documentation reach for older APIs. We measure this; we don't assume it.

## Tasks

Three tasks per episode, in `shared/agent-check/tasks/epNN.yaml`. Each task is a short natural-language spec plus deterministic checks.

## Conditions

1. `bare`: the model on its own.
2. `context_skill`: the model plus the Kubernetes 1.37 context file in `shared/skills/k8s-1.37/`, added to the system instruction.
3. `repair_loop`: the model on its own, plus a loop that feeds checker errors back in the same session, for up to 5 turns.

## The harness

An ADK (`google-adk`) `LlmAgent` on Gemini, run through an `InMemoryRunner` with one session per run (`shared/agent-check/agent_check/models.py`). The system instruction asks for YAML only, in one fenced block. Temperature is pinned (0.0 by default).

## Checks

- `stale_apis`: flags removed or older API versions and deprecated annotations (`shared/agent-check/agent_check/stale_apis.py`).
- `kubeconform`: schema validation against Kubernetes 1.37 in strict mode. Schemas come from kubeconform's default location (cached in a temp directory), or from `AGENT_CHECK_KUBECONFORM_SCHEMAS`. A missing schema fails the check, because a removed apiVersion has none; tasks with CRDs set `ignore_missing_schemas: true`.
- `server_dry_run`: `kubectl apply --dry-run=server` against the episode's GKE cluster, so a pass also means GKE accepted the config.
- `assert`: task-specific assertions, such as "the Pod is Guaranteed" or "the sidecar uses `restartPolicy: Always`".

A check that can't run is recorded as `skipped`. Published runs use `--require-all-checks`, which fails a run with any skipped check.

## Output

- `results/agent-check.csv`: one row per run with passed, first-try pass, turns, stale-API hits, failed and skipped checks, tokens in and out, wall time, model and temperature.
- `results/agent-check-details.jsonl`: every reply and every check result, turn by turn.

Both stay on your machine (`results/` is gitignored).

## Model

One pinned model for the whole series, Gemini 3.8 Flash (`gemini-3.8-flash`), set in `PINNED_FLASH_MODEL` and recorded in every CSV row with the temperature. Calls go through the Google Gen AI SDK's enterprise backend in your project: `GOOGLE_GENAI_USE_ENTERPRISE=true`, `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` (see `shared/infra/env.example`), with Application Default Credentials.

## Running it

```bash
make agent-check EP=01 FAKE_MODEL=1        # offline: canned model replies, checks the pipeline
make agent-venv                            # once: shared/agent-check/.venv with google-adk
gcloud auth application-default login      # once: credentials for the model calls
make agent-check EP=01 AGENT_CHECK_ARGS=--require-all-checks   # real run: needs the episode's cluster up
```
