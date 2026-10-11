# Lab Helper Response Templates

This document provides standardized educator response templates for each hint tier and workspace auto-remediation.

---

## Template 1: Tier 1 — Conceptual Nudge

Use when a learner first gets stuck or requests general guidance on how to begin. Focus strictly on architectural rationale, design patterns, and mental models without exposing concrete code or exact file paths.

```markdown
### 💡 Tier 1 Hint: Conceptual Direction for Step {step_id} ({step_title})

**Architectural Focus**: {pattern_concept}

**Conceptual Nudge**:
{tier_1_nudge}

**Guiding Questions to Consider**:
- What is the primary single responsibility of this component?
- Which inputs does it require, and what isolated outputs should it produce?
- How does this step fit into the upstream and downstream graph flow?

*Tip: Try designing the high-level interface first. If you need targeted details on class names or method signatures, request a Tier 2 hint.*
```

---

## Template 2: Tier 2 — Targeted File & Symbol Hint

Use when a learner understands the concept but needs specific orientation on where to write the code, which classes/functions to implement, or which interface contract to fulfill.

```markdown
### 🔍 Tier 2 Hint: Targeted File & Interface Specification for Step {step_id}

**Target File**: `{target_file_path}`

**Required Symbols & Structures**:
{required_symbols_list}

**Implementation Guidance**:
{tier_2_guidance}

**Drift Diagnostics**:
- Missing Files: {missing_files}
- Missing Symbols: {missing_symbols}
- Syntax Warnings: {syntax_warnings}

*Next Steps: Open `{target_file_path}`, declare the missing definitions with thorough Javadoc-style "why" docstrings, and run the verification command below.*

**Verification Command**:
```bash
python3 .agents/skills/lab-helper/scripts/verify_workspace.py --module {module_num} --step {step_id} --tier 2
```
```

---

## Template 3: Tier 3 — Concrete Implementation Blueprint

Use when a learner has attempted the step but remains blocked by syntax errors, complex wiring, or edge cases. Delivers a minimal, working code blueprint and parameter specification.

```markdown
### 🛠️ Tier 3 Hint: Implementation Blueprint for Step {step_id}

**Target File**: `{target_file_path}`

**Implementation Pattern**:
```python
{code_blueprint}
```

**Key Implementation Notes**:
1. **Design Rationale**: {why_explanation}
2. **State Management**: {state_explanation}
3. **Safety & Bounds**: {bounds_explanation}

**Self-Check Verification**:
```bash
python3 .agents/skills/lab-helper/scripts/verify_workspace.py --module {module_num} --step {step_id} --tier 3
```

*If you are unable to resolve the drift, you can request auto-remediation using `--tier remediate`.*
```

---

## Template 4: Workspace Auto-Remediation Confirmation

Use when a learner explicitly requests workspace remediation or passes `--tier remediate`.

```markdown
### ✅ Workspace Remediated: Step {step_id} ({step_title})

The Lab Helper has restored the reference implementation for Step `{step_id}` to bring your workspace to zero drift.

**Restored Files**:
{restored_files_list}

**Post-Remediation Status**:
- Status: **Clean (0 Drift)**
- Missing Files: 0
- Missing Symbols: 0
- Syntax Errors: 0

**What Changed**:
{remediation_summary}

**Next Step in Syllabus**:
You are now ready to proceed to Step `{next_step_id}`! Run:
```bash
python3 .agents/skills/lab-helper/scripts/verify_workspace.py --step {next_step_id} --tier 1
```
```
