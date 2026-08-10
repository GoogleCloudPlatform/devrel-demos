---
name: multi-step-workflow-reporter
description: Orchestrates parallel worker subagents executing a 4-step workflow, streaming mid-flight milestone progress reports back to the parent orchestrator via send_message. Use when running multi-step pipeline tasks with live progress reporting.
---

# Multi-Step Workflow Reporter

Orchestrates multi-agent parallel workflows with real-time mid-flight milestone reporting via `send_message`.

---

## Workflow Steps

### 1. Register Custom Worker Persona (`define_subagent`)

Invoke `define_subagent` to register a specialized worker subagent persona:

- **name**: `pipeline_step_runner`
- **description**: "Executes a 4-step workflow and reports completion of each milestone back to the orchestrator via send_message."
- **system_prompt**: "You are a pipeline step runner subagent. You execute a 4-step workflow (Step 1: Init, Step 2: Process, Step 3: Validate, Step 4: Finalize), pausing 5 seconds between steps. After successfully completing EACH step, call send_message to transmit a progress report to the Parent Orchestrator ID provided in your task prompt. Format your payload as structured JSON: {\"worker\": \"<Role>\", \"step\": <step_number>, \"name\": \"<Step Name>\", \"status\": \"COMPLETE\"}."
- **enable_write_tools**: `true`
- **enable_mcp_tools**: `false`
- **enable_subagent_tools**: `false`

---

### 2. Dispatch Parallel Workers (`invoke_subagent`)

Retrieve the parent orchestrator's conversation ID (e.g. `parent-123`).

Dispatch 3 worker subagents concurrently in a single `invoke_subagent` call using `TypeName: "pipeline_step_runner"`. For each worker (`Dataset Ingestion Worker`, `Image Processing Worker`, `Model Inference Worker`), set `Role` to the worker name and `Prompt` to:

> *"Execute your assigned pipeline for '<Role>'. Transmit step completion payloads via send_message to Recipient '<parent_id>'."*

---

### 3. Handle Incoming Telemetry & Update Live Dashboard

As `send_message` events arrive reactively from active subagents:

1. Parse the incoming JSON telemetry payload.
2. Render or update a consolidated live status dashboard in the chat window:

```markdown
⏳ **Live Pipeline Execution Dashboard**

* **Dataset Ingestion Worker**: [██████████░░░░░░░░░░] Step 2/4 Complete (Process)
* **Image Processing Worker**:  [█████░░░░░░░░░░░░░░░] Step 1/4 Complete (Init)
* **Model Inference Worker**:   [███████████████░░░░░] Step 3/4 Complete (Validate)
```

---

### 4. Aggregate & Report Final Results

Upon receiving Step 4 completion callbacks from all background subagents:

1. Synthesize final metrics and duration totals.
2. Present a final completion summary to the user with actionable next steps.
