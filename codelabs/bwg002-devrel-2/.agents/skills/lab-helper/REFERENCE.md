# Lab Helper Skill Reference & Verification Rubric

## Table of Contents
1. [Overview & Architectural Rationale](#overview--architectural-rationale)
2. [CLI Usage & Interface Contracts](#cli-usage--interface-contracts)
3. [Exit Codes & Error Semantics](#exit-codes--error-semantics)
4. [JSON Schema Specification](#json-schema-specification)
5. [Canonical 9-Step Verification Rubrics](#canonical-9-step-verification-rubrics)
   - [Module 1: Expand the Agent Team (Steps 1a–1c)](#module-1-expand-the-agent-team-steps-1a1c)
   - [Module 2: Observe and Audit (Steps 2a–2b)](#module-2-observe-and-audit-steps-2a2b)
   - [Module 3: Harden and Secure (Steps 3a–3c)](#module-3-harden-and-secure-steps-3a3c)
   - [Module 4: Optimize for Scale (Step 4a)](#module-4-optimize-for-scale-step-4a)
6. [Drift Detection Strategy & AST Parsing](#drift-detection-strategy--ast-parsing)
7. [Remediation Semantics & Safety Invariants](#remediation-semantics--safety-invariants)

---

## Overview & Architectural Rationale

The Lab Helper skill provides automated, non-invasive workspace analysis for learners completing the Pitch Generator lab. Instead of giving away answers immediately or modifying learner files prematurely, Lab Helper uses static analysis (Python AST inspection, symbol table resolution, and SQL grammar checking) to compare the learner's workspace with the gold-standard reference implementations in `.agents/solutions/`.

Why: Hands-on learning requires scaffolding. Beginners frequently face syntax errors, missing method signatures, or misnamed output keys. Lab Helper bridges the gap between learner confusion and mastery by offering structured, progressive feedback.

---

## CLI Usage & Interface Contracts

The script `verify_workspace.py` can be invoked via CLI or imported as a Python library:

### Command-Line Arguments
- `--module <1|2|3|4>`: Optional filter for the lab module. When combined with `--step`, it validates that the step belongs to this module.
- `--step <1a..4a|all>`: Specific step identifier or `"all"` to inspect all steps across the syllabus. Default is `"all"`.
- `--tier <1|2|3|remediate>`: Progressive hint level or remediation command. Default is `"1"`.
- `--remediate`, `--apply`: Boolean flags that alias `--tier remediate`.
- `--workspace-dir <PATH>`: Absolute or relative path to learner workspace directory. Default is `pitch-generator` project root.
- `--solutions-dir <PATH>`: Path to gold-standard reference solutions directory. Default is `pitch-generator/.agents/solutions`.
- `--json`: Outputs structured JSON to stdout instead of human-readable text.

---

## Exit Codes & Error Semantics

- **Code 0 (Success / Clean Execution)**:
  - Invocation succeeded. Returned JSON contains drift inspection status and requested hint or remediation payload.
- **Code 1 (Drift Detected / Failure Condition)**:
  - Reserved for automated verification pipelines when strict assertions are enabled.
- **Code 2 (CLI / Argument Error)**:
  - Returned when invalid flags or values are supplied (e.g., `--module 99`, `--step 3z`, `--module 1 --step 3a`, or `--tier unknown`).

---

## JSON Schema Specification

When `--json` is supplied, `verify_workspace.py` emits a single JSON object on standard output.

### 1. Drift Inspection & Hint Payload (`--tier 1|2|3`)
```json
{
  "step": "1a",
  "module": 1,
  "title": "Authoring Agent Skills",
  "tier": "1",
  "has_drift": true,
  "drifted": true,
  "status": "drifted",
  "missing_files": [],
  "syntax_errors": [],
  "missing_symbols": ["SkillToolset"],
  "diagnostics": ["Missing required symbol: SkillToolset"],
  "checked_files": ["module_1/step_1a_authoring_skills.py", "module_1/skills/brand-guidelines/SKILL.md"],
  "hint": "Tier 1 Conceptual Nudge (Step 1a): Equip the visual director agent...",
  "message": "Tier 1 Conceptual Nudge (Step 1a): Equip the visual director agent..."
}
```

### 2. Auto-Remediation Payload (`--tier remediate`)
```json
{
  "step": "1a",
  "module": 1,
  "tier": "remediate",
  "remediated": true,
  "restored_files": [".agents/solutions/module_1/step_1a_authoring_skills.py", ".agents/solutions/module_1/skills/brand-guidelines/SKILL.md"],
  "has_drift": false,
  "drifted": false,
  "status": "clean",
  "hint": "Remediated step 1a: restored .agents/solutions/module_1/step_1a_authoring_skills.py, .agents/solutions/module_1/skills/brand-guidelines/SKILL.md.",
  "message": "Remediated step 1a: restored .agents/solutions/module_1/step_1a_authoring_skills.py, .agents/solutions/module_1/skills/brand-guidelines/SKILL.md."
}
```

---

## Canonical 9-Step Verification Rubrics

### Module 1: Expand the Agent Team (Steps 1a–1c)

#### Step 1a: Authoring Agent Skills
- **Target Files**: `pitch_generator/skills/brand-guidelines/SKILL.md`, `pitch_generator/agent.py` (reference: `module_1/step_1a_authoring_skills.py`)
- **Required AST Symbols**: `Skill`, `SkillToolset`, `load_skill_from_dir`, `load_brand_skill`
- **Required Substrings**: `brand-guidelines`, `load_skill`
- **Rationale**: Dynamically equips agents with domain skill playbooks at runtime.

#### Step 1b: Skill Evaluation Harnesses
- **Target File**: `pitch_generator/agent.py` (reference: `module_1/step_1b_skill_evals.py`)
- **Required AST Symbols**: `SkillEvalResult`, `evaluate_brand_skill`, `run_eval_suite`
- **Required Substrings**: `brand-guidelines`, `FORBIDDEN_BRAND_PATTERNS`
- **Rationale**: Automated offline rubric evaluating compliance against style guidelines.

#### Step 1c: Remote A2A Visual Director Service
- **Target Files**: `pitch_generator/fast_api_app.py`, `pitch_generator/agent.py` (reference: `module_1/step_1c_remote_a2a_visual_director.py`)
- **Required AST Symbols**: `generate_key_visual`, `build_visual_director_card`, `build_a2a_visual_director_app`, `remote_visual_director`, `_cloud_run_client`, `_pitch_parts_only`
- **Required Substrings**: `include_artifacts_in_a2a_event_interceptor`, `AgentCardBuilder`
- **Rationale**: Implements Agent2Agent (A2A) protocol over JSON-RPC with Cloud Run authentication.

---

### Module 2: Observe and Audit (Steps 2a–2b)

#### Step 2a: BigQuery Agent Analytics & Key Visuals Object Table
- **Target Files**: `pitch_generator/app_utils/services.py` (reference: `module_2/step_2a_bigquery_analytics.py`, `module_2/sql/create_key_visuals.sql`)
- **Required AST Symbols**: `BigQueryAnalyticsService`, `build_key_visuals_sql`, `register_key_visuals`
- **Required Substrings**: `OBJ.MAKE_REF`, `OBJ.FETCH_METADATA`, `pitch-connection`
- **Rationale**: Tracks agent invocations in BigQuery and indexes multimodal visuals with object tables.

#### Step 2b: Brand Drift Detection & Closed-Loop Prompt Tuning
- **Target Files**: `pitch_generator/app_utils/services.py` (reference: `module_2/step_2b_drift_detection_and_tuning.py`, `module_2/sql/score_brand_fit.sql`)
- **Required AST Symbols**: `build_brand_score_sql`, `score_brand_compliance`, `detect_brand_drift`, `tune_prompt_and_skill`
- **Required Substrings**: `AI.SCORE`, `brand_fit`, `needs another pass`
- **Rationale**: Leverages BigQuery AI analytics to detect brand drift and tune agent prompts.

---

### Module 3: Harden and Secure (Steps 3a–3c)

#### Step 3a: PreToolUse Lifecycle Policy Hooks
- **Target File**: `pitch_generator/agent.py` (reference: `module_3/step_3a_pre_tool_use_hooks.py`)
- **Required AST Symbols**: `HookDecision`, `PreToolUseHook`, `ToolAuthorizationError`, `validate_tool_call`
- **Required Substrings**: `load_skill`, `generate_key_visual`, `Why:`
- **Rationale**: Intercepts tool execution to enforce least privilege and input parameter validation.

#### Step 3b: PII Data Scrubbing & Redaction
- **Target File**: `pitch_generator/app_utils/services.py` (reference: `module_3/step_3b_pii_scrubbing.py`)
- **Required AST Symbols**: `ScrubResult`, `PIIScrubber`, `scrub_pii`, `scrub_text`, `scrub_payload`
- **Required Substrings**: `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`, `Why:`
- **Rationale**: Scrubs sensitive PII (emails, phone numbers, SSNs, credit cards, API keys) from payloads.

#### Step 3c: Human-in-the-Loop (HITL) Authorizations
- **Target File**: `pitch_generator/agent.py` (reference: `module_3/step_3c_hitl_authorizations.py`)
- **Required AST Symbols**: `approve_concept`, `user_approval`, `evaluate_user_approval`, `run_hitl_workflow`
- **Required Substrings**: `RequestInput`, `Approved Concept`, `Why:`
- **Rationale**: Pauses graph execution with RequestInput and resumes upon human review.

---

### Module 4: Optimize for Scale (Step 4a)

#### Step 4a: Tokenomics & History Optimization
- **Target File**: `pitch_generator/agent.py` (reference: `module_4/step_4a_tokenomics.py`)
- **Required AST Symbols**: `CompressedHistoryList`, `PromptCacheManager`, `TokenomicsManager`, `compress_memory`, `prune_history`, `select_model_strategy`
- **Required Substrings**: `sha256`, `Why:`
- **Rationale**: Implements sliding window history pruning, conversation memory compression, and prompt caching.

---

## Drift Detection Strategy & AST Parsing

1. **Existence Check**: Confirms target files exist under `.agents/solutions/` in the target workspace.
2. **AST Parsing**: For `.py` files, parses code with `ast.parse()`. Traps `SyntaxError` and reports detailed line numbers and compiler errors.
3. **Symbol Extraction**: Inspects top-level and class-level `FunctionDef`, `AsyncFunctionDef`, `ClassDef`, `Assign`, `AnnAssign`, `Import`, and `ImportFrom` nodes. Flags missing symbols.
4. **Token & Grammar Validation**: Inspects non-Python files (`.sql`, `.js`, `.md`) for mandatory tokens.

---

## Remediation Semantics & Safety Invariants

- **Read-Only Invariant**: Calling `inspect_step_drift()` or `get_progressive_hint()` across Tiers 1–3 NEVER creates, overwrites, or modifies any files in the learner's workspace directory.
- **Atomic Restoration**: Calling `remediate_step()` or `--tier remediate` copies the authoritative reference implementation from `.agents/solutions/` into the learner's workspace, creating necessary subdirectories automatically.
- **Verification Guarantee**: Every remediation operation immediately re-inspects the workspace to ensure drift is completely resolved before returning.
