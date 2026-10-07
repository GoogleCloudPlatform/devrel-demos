---
name: lab-helper
description: Diagnoses workspace drift across Modules 1 to 4 of the Pitch Generator lab, delivers progressive 3-tier hints, and restores reference step implementations when hints are exhausted. Use when a learner asks for a hint, gets stuck on a lab step, wants to verify their workspace against a module solution, or requests workspace remediation.
---

# Pitch Generator Lab Helper Skill

The **Lab Helper** skill provides an interactive, pedagogical diagnosis and recovery engine for learners working through the Pitch Generator lab (`bwg001-devlab-1b`). It actively inspects the learner's workspace directory against the 13 reference solution steps across Modules 1–4, assesses syntactic and structural drift, delivers calibrated educational guidance, and safely restores files if a learner gets stuck.

---

## Conversational & Prompt-Driven Interaction

The learner interacts with this skill **entirely through natural conversation** in the Antigravity chat panel. The learner does not need to run terminal verification commands or remember CLI flags.

### 1. Handling Learner Inquiries

When the learner sends prompts such as:
- *"I can't get step 2a working properly, can you give me a hint?"*
- *"Please verify I completed step 1a correctly"*
- *"Can I have another hint?"*
- *"I am completely stuck on step 3c, please help me fix it"*

The assistant follows this multi-step protocol:

1. **Step Identification**: Identify the module and step referenced in the user's prompt (for example, `step 2a` maps to Module 2, Step 2a). If the user asks generally ("verify step 2"), inspect the workspace to identify the active step.
2. **Contextual Tier Tracking**: Inspect the recent conversation history to determine which hint tier to provide:
   - **First inquiry on a step** (e.g., *"give me a hint"* or *"verify step 1a"*): Use **Tier 1** (Conceptual Nudge).
   - **Follow-up request** (e.g., *"can I have another hint?"* or *"need more detail"*): Advance to **Tier 2** (Targeted File & Symbol Hint).
   - **Second follow-up** (e.g., *"still stuck, another hint?"*): Advance to **Tier 3** (Implementation Blueprint & Code Snippet).
   - **Exhausted hints or explicit remediation request** (e.g., *"please bring my workspace into a working state"*): Use **Tier `remediate`** to restore reference files.
3. **Execute the Diagnostic Tool**: Run the verification script behind the scenes using `run_command`:
   ```bash
   python3 .agents/skills/lab-helper/scripts/verify_workspace.py --module <M> --step <S> --tier <T> --json
   ```
4. **Interpret Output & Formulate Response**:
   - **If `drift_detected: false`**: Congratulate the learner, confirm that their implementation meets the step specifications, and briefly summarize what they accomplished before suggesting the next step.
   - **If `drift_detected: true`**: Present the progressive hint corresponding to the current tier (see [TEMPLATES.md](TEMPLATES.md)). Explain the architectural rationale ("why") and encourage the learner to iterate. Remind them that they can ask for another hint anytime.
   - **If Tier `remediate`**: Inform the learner which files were restored, explain why the canonical implementation solves the issue, and confirm that tests now pass.

---

## Progressive 3-Tier Hint & Remediation Protocol

To ensure learners build genuine understanding without having solutions spoiled prematurely, Lab Helper enforces a deterministic 3-tier progressive hint protocol:

1. **Tier 1 — Conceptual Nudge**:
   - Offers an architectural "why" explanation and high-level conceptual nudge.
   - Highlights the core design pattern (for example, ADK single-responsibility agents, JoinNode fan-in, PreToolUse policy hooks).
   - Strictly read-only: does not disclose specific file paths, code snippets, or modify workspace files.

2. **Tier 2 — Targeted File & Symbol Hint**:
   - Identifies the exact target file path relative to the workspace root.
   - Details required classes, functions, AST symbols, interface signatures, or schema keys.
   - Highlights missing tokens without writing code or modifying learner files.

3. **Tier 3 — Concrete Implementation Blueprint**:
   - Delivers a concrete implementation blueprint and minimal idiomatic code snippet illustrating how to resolve the drift.
   - Explains parameter bindings, edge cases, and verification commands.
   - Strictly read-only: does not overwrite any learner files.

4. **Workspace Auto-Remediation (`--tier remediate` or `--remediate`)**:
   - Used when hints are exhausted or the learner explicitly asks to reset/restore a step.
   - Atomically restores the reference files (including Python modules, SQL scripts, Markdown skills, and browser JavaScript) from `.agents/solutions/` into the workspace.
   - Verifies that post-remediation drift is zero.

---

## Supported Modules and Steps (`1a`–`4b`)

Lab Helper supports all 13 progressive steps across the 4 syllabus modules:

| Module | Step ID | Step Title & Description | Target Deliverable(s) (Application & Reference) |
|---|---|---|---|
| **Module 1** | `1a` | Specialist Agents & State Isolation | `pitch_generator/agent.py` (ref: `module_1/step_1a_specialist_agents.py`) |
| | `1b` | Authoring Agent Skills (`brand-guidelines`) | `pitch_generator/skills/brand-guidelines/SKILL.md`, `pitch_generator/agent.py` (ref: `module_1/step_1b_authoring_skills.py`) |
| | `1c` | Skill Evaluation Harnesses | `tests/test_module_1.py` / `pitch_generator/` (ref: `module_1/step_1c_skill_evals.py`) |
| | `1d` | Graph Orchestration & Loop Prevention | `pitch_generator/agent.py` (ref: `module_1/step_1d_graph_orchestration.py`) |
| | `1e` | Remote A2A Visual Director Service | `pitch_generator/agent.py`, `pitch_generator/fast_api_app.py` (ref: `module_1/step_1e_remote_a2a_visual_director.py`) |
| **Module 2** | `2a` | BigQuery Telemetry & Object Tables | `pitch_generator/app_utils/services.py` (ref: `module_2/step_2a_bigquery_analytics.py`, `sql/create_key_visuals.sql`) |
| | `2b` | Cloud Storage Artifact Service | `pitch_generator/app_utils/services.py` (ref: `module_2/step_2b_cloud_storage_artifacts.py`) |
| | `2c` | Brand Drift Detection & Prompt Tuning | `pitch_generator/app_utils/services.py` (ref: `module_2/step_2c_drift_detection_and_tuning.py`, `sql/score_brand_fit.sql`) |
| **Module 3** | `3a` | PreToolUse Lifecycle Policy Hooks | `pitch_generator/agent.py` (ref: `module_3/step_3a_pre_tool_use_hooks.py`) |
| | `3b` | PII Data Scrubbing & Redaction | `pitch_generator/app_utils/services.py` (ref: `module_3/step_3b_pii_scrubbing.py`) |
| | `3c` | Human-in-the-Loop (HITL) Authorizations | `pitch_generator/agent.py` (ref: `module_3/step_3c_hitl_authorizations.py`) |
| **Module 4** | `4a` | Tokenomics & History Optimization | `pitch_generator/agent.py` (ref: `module_4/step_4a_tokenomics.py`) |
| | `4b` | Hybrid Routing (WebLLM / Local / Cloud) | `pitch_generator/agent.py`, `frontend/app.js` (ref: `module_4/step_4b_hybrid_routing.py`, `module_4/webllm_router.js`) |

---

## Running the Workspace Verification Script

The underlying diagnostic engine is implemented in `scripts/verify_workspace.py` and executed by the assistant via CLI commands:

### 1. Requesting Progressive Hints (Read-Only)
```bash
# Tier 1 Conceptual Nudge
python3 .agents/skills/lab-helper/scripts/verify_workspace.py --module 1 --step 1a --tier 1 --json

# Tier 2 Targeted File & Symbol Hint
python3 .agents/skills/lab-helper/scripts/verify_workspace.py --module 1 --step 1a --tier 2 --json

# Tier 3 Implementation Blueprint
python3 .agents/skills/lab-helper/scripts/verify_workspace.py --module 1 --step 1a --tier 3 --json
```

### 2. Auto-Remediating a Stuck Step
```bash
# Restore step files to bring workspace to 0 drift
python3 .agents/skills/lab-helper/scripts/verify_workspace.py --module 1 --step 1a --tier remediate --json
```

### 3. Inspecting the Entire Workspace
```bash
# Verify all steps across all 4 modules
python3 .agents/skills/lab-helper/scripts/verify_workspace.py --step all --json
```

---

## Reference Documentation

- See [REFERENCE.md](REFERENCE.md) for the detailed step rubrics, AST symbols, CLI flags, exit codes, and JSON response schema.
- See [TEMPLATES.md](TEMPLATES.md) for the standardized educator response formatting templates for Tiers 1–3 and auto-remediation.
- Structured hint data and drift rules are maintained in `references/hints_catalog.json` and consumed by `scripts/verify_workspace.py`.
