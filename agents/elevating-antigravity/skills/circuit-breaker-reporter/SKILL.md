---
name: circuit-breaker-reporter
description: Orchestrates parallel worker subagents with real-time telemetry reporting and automated hard circuit-breaking via manage_subagents upon fatal worker errors.
---

# Circuit Breaker Reporter

Orchestrates multi-agent parallel workflows with real-time milestone reporting via `send_message` and automated hard circuit-breaking via `manage_subagents` upon unrecoverable worker failures.

---

## Workflow Steps

### 1. Register Custom Worker Persona (`define_subagent`)

Invoke `define_subagent` to register a specialized worker subagent persona:

- **name**: `pipeline_step_runner`
- **description**: "Executes a 4-step workflow and reports completion of each milestone back to the orchestrator via send_message. Sends an urgent FATAL_ERROR callback if a step fails."
- **system_prompt**: "You are a pipeline step runner subagent. You execute a 4-step workflow (Step 1: Init, Step 2: Process, Step 3: Validate, Step 4: Finalize), pausing 5 seconds between steps. After successfully completing EACH step, call send_message to transmit a progress report to the Parent Orchestrator ID provided in your task prompt: {\"worker\": \"<Role>\", \"step\": <step_number>, \"name\": \"<Step Name>\", \"status\": \"COMPLETE\"}. If your prompt specifies a failure condition or an unrecoverable step error occurs, immediately call send_message with payload: {\"worker\": \"<Role>\", \"step\": <step_number>, \"name\": \"<Step Name>\", \"status\": \"FATAL_ERROR\", \"error\": \"<Details>\"} and stop execution."
- **enable_write_tools**: `true`
- **enable_mcp_tools**: `false`
- **enable_subagent_tools**: `false`

---

### 2. Dispatch Parallel Workers (`invoke_subagent`)

Retrieve the parent orchestrator's conversation ID (e.g. `parent-123`).

Dispatch 6 worker subagents concurrently in a single `invoke_subagent` call using `TypeName: "pipeline_step_runner"`.

The worker pool consists of:
1. `Dataset Ingestion Worker`
2. `Image Processing Worker`
3. `Model Inference Worker`
4. `Database Sync Worker` (Designated Circuit Breaker Trigger)
5. `Cache Prewarming Worker`
6. `Telemetry Export Worker`

For standard workers (1, 2, 3, 5, 6), set `Role` to the worker name and `Prompt` to:

> *"Execute your assigned pipeline for '<Role>'. Transmit step completion and error payloads via send_message to Recipient '<parent_id>'."*

For the designated failing worker (`Database Sync Worker`), set `Role` to `Database Sync Worker` and `Prompt` to:

> *"Execute your assigned pipeline for 'Database Sync Worker'. Complete Step 1 (Init) successfully and transmit status COMPLETE via send_message to Recipient '<parent_id>'. Upon reaching Step 2 (Process), simulate an unrecoverable database deadlock failure and immediately transmit a FATAL_ERROR payload via send_message to Recipient '<parent_id>': {\"worker\": \"Database Sync Worker\", \"step\": 2, \"name\": \"Process\", \"status\": \"FATAL_ERROR\", \"error\": \"Fatal DB deadlock in cluster node db-master-01\"}."*

*(Note: Spawning 6 workers with a 50% random failure chance yields a 98.44% probability of at least one failure ($1 - (0.5)^6$). Explicitly designating `Database Sync Worker` guarantees 100% deterministic triggering of the circuit breaker during execution while testing 6 concurrent streams).*

---

### 3. Handle Telemetry & Execute Hard Circuit Breaker (`manage_subagents`)

As `send_message` events arrive reactively from active subagents:

1. **Progress Telemetry:** Parse incoming `COMPLETE` payloads and update the live status dashboard:

```markdown
⏳ **Live Pipeline Execution Dashboard**

* **Dataset Ingestion Worker**: [██████████░░░░░░░░░░] Step 2/4 Complete (Process)
* **Image Processing Worker**:  [█████░░░░░░░░░░░░░░░] Step 1/4 Complete (Init)
* **Model Inference Worker**:   [█████░░░░░░░░░░░░░░░] Step 1/4 Complete (Init)
* **Database Sync Worker**:     [█████░░░░░░░░░░░░░░░] Step 1/4 Complete (Init) 🚨 FATAL ERROR (Step 2 Process)
* **Cache Prewarming Worker**:  [█████░░░░░░░░░░░░░░░] Step 1/4 Complete (Init)
* **Telemetry Export Worker**:  [█████░░░░░░░░░░░░░░░] Step 1/4 Complete (Init)
```

2. **Automated Hard Circuit Breaker:** If any subagent transmits `"status": "FATAL_ERROR"` (e.g., database lock or fatal API failure):
   - Immediately call `manage_subagents` with `Action: "kill_all"` to instantly terminate all running worker subagents across the process tree.
   - Automatically clean up temporary workspace branches to avoid resource leakages.

---

### 4. Aggregate Results or Report Incident

- **On Success:** Upon receiving Step 4 completion callbacks from all subagents, synthesize final metrics and present a completion summary.
- **On Circuit Breaker Trigger:** Present an incident post-mortem detailing the failing subagent role, step number, and error details, confirming all background processes were cleanly terminated via `manage_subagents`.
