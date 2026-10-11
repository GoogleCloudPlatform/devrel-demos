#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
/**
 * @file verify_workspace.py
 * @description Workspace diagnostic, progressive hint delivery, and auto-remediation engine for the Pitch Generator lab.
 *
 * Why: Learners working through the 13 steps of Modules 1–4 frequently encounter syntax errors,
 * missing AST symbols, or incomplete file implementations. This script provides an automated, non-destructive
 * inspection pipeline that diagnoses workspace drift against authoritative reference solutions, emits calibrated
 * 3-tier progressive hints (Level 1 conceptual nudge -> Level 2 targeted file/symbol hint -> Level 3 exact blueprint),
 * and safely restores reference implementations when hints are exhausted.
 */
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import shutil
import sys
from typing import Any

# ==============================================================================
# Path Resolution and Global Constants
# ==============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
APP_ROOT = SKILL_DIR.parents[2]
DEFAULT_SOLUTIONS_DIR = APP_ROOT / ".agents" / "solutions"
HINTS_CATALOG_PATH = SKILL_DIR / "references" / "hints_catalog.json"

VALID_MODULES = (1, 2, 3, 4)
VALID_STEPS = ("1a", "1b", "1c", "2a", "2b", "3a", "3b", "3c", "4a")
VALID_TIERS = ("1", "2", "3", "remediate")

# Step metadata mapping: relative file paths, AST required symbols, and required substrings
STEP_REGISTRY: dict[str, dict[str, Any]] = {
    "1a": {
        "module": 1,
        "title": "Authoring Agent Skills",
        "files": ["module_1/step_1a_authoring_skills.py", "module_1/skills/brand-guidelines/SKILL.md"],
        "required_symbols": ["Skill", "SkillToolset", "load_skill_from_dir", "load_brand_skill"],
        "step_new_symbols": ["Skill", "SkillToolset", "load_skill_from_dir", "load_brand_skill"],
        "required_substrings": ["brand-guidelines"],
    },
    "1b": {
        "module": 1,
        "title": "Skill Evaluation Harnesses",
        "files": ["module_1/step_1b_skill_evals.py"],
        "required_symbols": ["SkillEvalResult", "evaluate_brand_skill", "run_eval_suite"],
        "step_new_symbols": ["SkillEvalResult", "evaluate_brand_skill", "run_eval_suite"],
        "required_substrings": ["brand-guidelines", "FORBIDDEN_BRAND_PATTERNS"],
    },
    "1c": {
        "module": 1,
        "title": "Remote A2A Visual Director Service",
        "files": ["module_1/step_1c_remote_a2a_visual_director.py"],
        "required_symbols": [
            "generate_key_visual",
            "build_visual_director_card",
            "build_a2a_visual_director_app",
            "remote_visual_director",
            "_cloud_run_client",
            "_pitch_parts_only",
        ],
        "step_new_symbols": [
            "build_visual_director_card",
            "build_a2a_visual_director_app",
            "remote_visual_director",
            "_cloud_run_client",
            "_pitch_parts_only",
        ],
        "required_substrings": ["include_artifacts_in_a2a_event_interceptor", "AgentCardBuilder", "Why:"],
    },
    "2a": {
        "module": 2,
        "title": "BigQuery Agent Analytics & Key Visuals Object Table",
        "files": ["module_2/step_2a_bigquery_analytics.py", "module_2/sql/create_key_visuals.sql"],
        "required_symbols": ["BigQueryAnalyticsService", "build_key_visuals_sql", "register_key_visuals"],
        "step_new_symbols": ["register_key_visuals"],
        "required_substrings": ["OBJ.MAKE_REF", "OBJ.FETCH_METADATA", "pitch-connection"],
    },
    "2b": {
        "module": 2,
        "title": "Brand Drift Detection & Closed-Loop Prompt Tuning",
        "files": ["module_2/step_2b_drift_detection_and_tuning.py", "module_2/sql/score_brand_fit.sql"],
        "required_symbols": ["score_brand_compliance", "detect_brand_drift", "tune_prompt_and_skill"],
        "step_new_symbols": ["detect_brand_drift", "tune_prompt_and_skill"],
        "required_substrings": ["AI.SCORE", "brand_fit", "needs another pass"],
    },
    "3a": {
        "module": 3,
        "title": "Agent Lifecycle Hooks (PreToolUse)",
        "files": ["module_3/step_3a_pre_tool_use_hooks.py"],
        "required_symbols": ["HookDecision", "PreToolUseHook", "ToolAuthorizationError", "validate_tool_call"],
        "step_new_symbols": ["HookDecision", "PreToolUseHook", "ToolAuthorizationError", "validate_tool_call"],
        "required_substrings": ["load_skill", "generate_key_visual", "Why:"],
    },
    "3b": {
        "module": 3,
        "title": "Sensitive PII Data Scrubbing & Redaction",
        "files": ["module_3/step_3b_pii_scrubbing.py"],
        "required_symbols": ["ScrubResult", "PIIScrubber", "scrub_pii", "scrub_text", "scrub_payload"],
        "step_new_symbols": ["ScrubResult", "PIIScrubber", "scrub_pii", "scrub_text", "scrub_payload"],
        "required_substrings": ["[REDACTED_EMAIL]", "[REDACTED_PHONE]", "Why:"],
    },
    "3c": {
        "module": 3,
        "title": "Human-in-the-Loop (HITL) Authorizations",
        "files": ["module_3/step_3c_hitl_authorizations.py"],
        "required_symbols": ["approve_concept", "user_approval", "evaluate_user_approval", "run_hitl_workflow"],
        "step_new_symbols": ["approve_concept", "user_approval", "evaluate_user_approval", "run_hitl_workflow"],
        "required_substrings": ["RequestInput", "Approved Concept", "Why:"],
    },
    "4a": {
        "module": 4,
        "title": "Tokenomics (Memory Compression, History Pruning, Prompt Caching)",
        "files": ["module_4/step_4a_tokenomics.py"],
        "required_symbols": [
            "CompressedHistoryList",
            "PromptCacheManager",
            "TokenomicsManager",
            "compress_memory",
            "prune_history",
            "select_model_strategy",
        ],
        "step_new_symbols": [
            "CompressedHistoryList",
            "PromptCacheManager",
            "TokenomicsManager",
            "compress_memory",
            "prune_history",
            "select_model_strategy",
        ],
        "required_substrings": ["sha256", "Why:"],
    },
}


# ==============================================================================
# Helper & Catalog Functions
# ==============================================================================

def _load_catalog() -> dict[str, Any]:
    """
    /**
     * Loads the hints catalog JSON dictionary.
     *
     * Why: Provides a single source of truth for progressive hint templates across
     * all 9 steps in Modules 1–4.
     *
     * @return Dictionary containing step entries keyed by step_id.
     */
    """
    if not HINTS_CATALOG_PATH.is_file():
        raise FileNotFoundError(f"Hints catalog not found at {HINTS_CATALOG_PATH}")
    with open(HINTS_CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("steps", data)


def _validate_step_and_module(step: str, module: int | str | None = None) -> tuple[str, int | None]:
    """
    /**
     * Validates and normalizes step and module identifiers.
     *
     * Why: Enforces strict boundary verification per Interface Contract 4. Rejects
     * invalid module numbers (e.g. 99), unknown step IDs (e.g. 3z), or mismatched pairs
     * (e.g. module 1 with step 3a) with informative ValueError exceptions.
     *
     * @param step Step identifier (e.g. "1a", "3b", "all").
     * @param module Optional module number (1, 2, 3, or 4).
     * @return Tuple of (normalized_step_id, validated_module_int).
     */
    """
    step_id = str(step).strip().lower()
    mod_int: int | None = None

    if module is not None:
        try:
            mod_int = int(module)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Invalid module argument: {module!r}. Expected integer 1-4.") from exc
        if mod_int not in VALID_MODULES:
            raise ValueError(f"Module {mod_int} is out of bounds. Valid modules: {VALID_MODULES}")

    if step_id != "all":
        if step_id not in VALID_STEPS:
            raise ValueError(f"Unknown step identifier: {step!r}. Valid steps: {VALID_STEPS}")
        step_mod = int(step_id[0])
        if mod_int is not None and step_mod != mod_int:
            raise ValueError(f"Step {step_id!r} does not belong to module {mod_int} (expected module {step_mod})")
        if mod_int is None:
            mod_int = step_mod

    return step_id, mod_int


def _extract_ast_symbols(source_code: str, filename: str) -> tuple[set[str], str | None]:
    """
    /**
     * Parses Python source code into an AST and extracts all defined symbol names.
     *
     * Why: Verifies that learners have declared the necessary functions, classes, and
     * assignments without running untrusted code. Detects syntax errors gracefully.
     *
     * @param source_code Raw Python code to inspect.
     * @param filename Target filename for AST error reporting.
     * @return Tuple of (set_of_symbol_names, syntax_error_message_or_None).
     */
    """
    try:
        tree = ast.parse(source_code, filename=filename)
    except SyntaxError as exc:
        return set(), f"{filename}:SyntaxError:line {exc.lineno}: {exc.msg}"

    symbols: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.add(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                symbols.add(node.target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                symbols.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                symbols.add(alias.asname or alias.name)

    return symbols, None


def _strip_comment_lines(source_code: str) -> str:
    """Remove `#` comment lines from Python source so guidepost comments do not trigger substring matches."""
    return "\n".join(
        line for line in source_code.splitlines() if not line.lstrip().startswith("#")
    )


# ==============================================================================
# Core Verification API (Interface Contract 4)
# ==============================================================================

def inspect_step_drift(
    step: str,
    workspace_dir: str | Path | None = None,
    solutions_dir: str | Path | None = None,
    *,
    module: int | str | None = None,
) -> dict[str, Any]:
    """
    /**
     * Inspects a workspace for drift against reference solutions.
     *
     * Why: Interface Contract 4 function. Enables programmatic and CLI inspection of
     * learner code against gold-standard solutions, reporting missing files, syntax errors,
     * missing AST symbols, and missing required substrings. Strictly read-only: never
     * writes or modifies files.
     *
     * @param step Step identifier ("1a"–"4a") or "all".
     * @param workspace_dir Path to learner's workspace directory (defaults to project root).
     * @param solutions_dir Path to gold-standard solutions directory (defaults to project solutions).
     * @param module Optional module filter (1–4).
     * @return Structured drift report dictionary.
     */
    """
    step_id, mod_int = _validate_step_and_module(step, module)
    ws_root = Path(workspace_dir).resolve() if workspace_dir is not None else APP_ROOT
    sol_root = Path(solutions_dir).resolve() if solutions_dir is not None else DEFAULT_SOLUTIONS_DIR

    if step_id == "all":
        steps_to_check = [s for s in VALID_STEPS if mod_int is None or int(s[0]) == mod_int]
        step_reports: dict[str, Any] = {}
        all_missing_files: list[str] = []
        all_missing_symbols: list[str] = []
        all_diagnostics: list[str] = []
        any_drift = False

        for sid in steps_to_check:
            rep = inspect_step_drift(sid, workspace_dir=ws_root, solutions_dir=sol_root)
            step_reports[sid] = rep
            if rep["has_drift"]:
                any_drift = True
            all_missing_files.extend(rep["missing_files"])
            all_missing_symbols.extend(rep["missing_symbols"])
            all_diagnostics.extend(rep["diagnostics"])

        return {
            "step": "all",
            "module": mod_int or 0,
            "title": f"Workspace Audit ({len(steps_to_check)} steps)",
            "has_drift": any_drift,
            "drifted": any_drift,
            "status": "drifted" if any_drift else "clean",
            "missing_files": all_missing_files,
            "missing_symbols": all_missing_symbols,
            "diagnostics": all_diagnostics,
            "steps": step_reports,
        }

    spec = STEP_REGISTRY[step_id]
    missing_files: list[str] = []
    syntax_errors: list[str] = []
    missing_symbols: list[str] = []
    diagnostics: list[str] = []
    checked_files: list[str] = []

    # Proper application paths for real-world project structure
    app_file_map: dict[str, str] = {
        "module_1/skills/brand-guidelines/SKILL.md": "pitch_generator/skills/brand-guidelines/SKILL.md",
        "module_1/step_1a_authoring_skills.py": "pitch_generator/agent.py",
        "module_1/step_1b_skill_evals.py": "pitch_generator/agent.py",
        "module_1/step_1c_remote_a2a_visual_director.py": "pitch_generator/agent.py",
        "module_2/step_2a_bigquery_analytics.py": "pitch_generator/app_utils/services.py",
        "module_2/sql/create_key_visuals.sql": "pitch_generator/sql/create_key_visuals.sql",
        "module_2/step_2b_drift_detection_and_tuning.py": "pitch_generator/app_utils/services.py",
        "module_2/sql/score_brand_fit.sql": "pitch_generator/sql/score_brand_fit.sql",
        "module_3/step_3a_pre_tool_use_hooks.py": "pitch_generator/agent.py",
        "module_3/step_3b_pii_scrubbing.py": "pitch_generator/app_utils/services.py",
        "module_3/step_3c_hitl_authorizations.py": "pitch_generator/agent.py",
        "module_4/step_4a_tokenomics.py": "pitch_generator/agent.py",
    }

    target_files: list[str] = [app_file_map.get(f, f) for f in spec["files"]]
    step_new_syms: list[str] = list(spec.get("step_new_symbols", spec.get("required_symbols", [])))

    # Determine whether the learner has started or completed this step in canonical app files
    canonical_py_exists = False
    canonical_started = False
    canonical_completed = True

    for rel_path in spec["files"]:
        canonical_app_rel = app_file_map.get(rel_path)
        if not canonical_app_rel:
            canonical_completed = False
            continue
        cand_path = ws_root / canonical_app_rel
        if cand_path.suffix == ".py":
            if cand_path.is_file() and cand_path.stat().st_size > 0:
                canonical_py_exists = True
                c_content = cand_path.read_text(encoding="utf-8")
                if step_id == "1c" and (ws_root / "pitch_generator/fast_api_app.py").is_file():
                    c_content = c_content + "\n" + (ws_root / "pitch_generator/fast_api_app.py").read_text(encoding="utf-8")
                c_symbols, c_syn_err = _extract_ast_symbols(c_content, str(cand_path))
                c_code_only = _strip_comment_lines(c_content)
                if c_syn_err:
                    canonical_started = True
                    canonical_completed = False
                else:
                    present_new = [
                        s
                        for s in step_new_syms
                        if (s in c_symbols if s.isidentifier() else s in c_code_only)
                    ]
                    if present_new:
                        canonical_started = True
                    req_syms = set(spec.get("required_symbols", []))
                    all_subs = all(sub in c_code_only for sub in spec.get("required_substrings", []))
                    if not (req_syms.issubset(c_symbols) and all_subs):
                        canonical_completed = False
            else:
                canonical_completed = False
        else:
            if cand_path.is_file() and cand_path.stat().st_size > 0:
                canonical_started = True
                c_content = cand_path.read_text(encoding="utf-8")
                all_subs = all(sub in c_content for sub in spec.get("required_substrings", []))
                if not all_subs:
                    canonical_completed = False
            else:
                canonical_completed = False

    not_started = bool(canonical_py_exists and not canonical_started and not canonical_completed)

    for rel_path in spec["files"]:
        checked_files.append(rel_path)
        canonical_app_rel = app_file_map.get(rel_path)
        ref_path = ws_root / ".agents" / "solutions" / rel_path
        canonical_path = (ws_root / canonical_app_rel) if canonical_app_rel else None

        target_path: Path | None = None
        if canonical_completed and canonical_path is not None and canonical_path.is_file():
            target_path = canonical_path
        elif canonical_started and canonical_path is not None:
            # Learner has started modifying canonical app files for this step:
            # inspect the canonical app file directly so partial work is flagged.
            target_path = canonical_path
        else:
            # Step not started yet in canonical app files (or running in a solution-only test dir)
            candidates: list[Path] = []
            if (ws_root / rel_path).is_file():
                candidates.append(ws_root / rel_path)
            if ref_path.is_file():
                candidates.append(ref_path)
            if canonical_path is not None and canonical_path.is_file():
                candidates.append(canonical_path)
            target_path = candidates[0] if candidates else (canonical_path or (ws_root / rel_path))

        if not target_path.is_file() or target_path.stat().st_size == 0:
            missing_files.append(rel_path)
            diagnostics.append(f"Missing file: {rel_path} (checked {target_path})")
            continue

        try:
            content = target_path.read_text(encoding="utf-8")
            if (
                step_id == "1c"
                and canonical_path is not None
                and target_path == canonical_path
                and (ws_root / "pitch_generator/fast_api_app.py").is_file()
            ):
                content = content + "\n" + (ws_root / "pitch_generator/fast_api_app.py").read_text(encoding="utf-8")
        except Exception as exc:
            syntax_errors.append(f"{rel_path}:ReadError:{exc}")
            diagnostics.append(f"Failed to read file {rel_path}: {exc}")
            continue

        sub_check_content = content
        if rel_path.endswith(".py"):
            sub_check_content = _strip_comment_lines(content)
            ast_symbols, syn_err = _extract_ast_symbols(content, str(target_path))
            if syn_err:
                syntax_errors.append(syn_err)
                diagnostics.append(f"Syntax error in {rel_path}: {syn_err}")
                for sym in spec["required_symbols"]:
                    missing_symbols.append(sym)
            else:
                for sym in spec["required_symbols"]:
                    if sym not in ast_symbols:
                        missing_symbols.append(sym)
                        diagnostics.append(f"Missing required symbol: {sym} in {rel_path}")

        for sub in spec.get("required_substrings", []):
            if sub not in sub_check_content:
                missing_symbols.append(sub)
                diagnostics.append(f"Missing required pattern or keyword '{sub}' in {rel_path}")

    has_drift = bool(missing_files or syntax_errors or missing_symbols or diagnostics)

    return {
        "step": step_id,
        "module": spec["module"],
        "title": spec["title"],
        "has_drift": has_drift,
        "drifted": has_drift,
        "status": "drifted" if has_drift else "clean",
        "not_started": not_started,
        "completed": bool(canonical_completed and not has_drift),
        "readiness": (
            "ready_to_begin"
            if not_started
            else ("drifted" if has_drift else "completed")
        ),
        "target_files": target_files,
        "pending_symbols": step_new_syms if not_started else missing_symbols,
        "missing_files": missing_files,
        "syntax_errors": syntax_errors,
        "missing_symbols": missing_symbols,
        "diagnostics": diagnostics,
        "checked_files": checked_files,
    }


def get_progressive_hint(
    step: str,
    tier: int | str = 1,
    workspace_dir: str | Path | None = None,
    solutions_dir: str | Path | None = None,
) -> str:
    """
    /**
     * Generates a calibrated progressive hint for a specific step.
     *
     * Why: Interface Contract 4 function. Supplies learners with non-invasive, progressive
     * scaffolding. Strictly adheres to length invariant len(tier_3) > len(tier_2) > len(tier_1).
     * Strictly read-only: never alters workspace files.
     *
     * @param step Step identifier ("1a"–"4b").
     * @param tier Hint level (1, 2, or 3).
     * @param workspace_dir Path to learner's workspace directory.
     * @param solutions_dir Path to gold-standard solutions directory.
     * @return Formatted hint string.
     */
    """
    tier_str = str(tier).strip().lower()
    if tier_str not in ("1", "2", "3"):
        raise ValueError(f"Invalid hint tier: {tier!r}. Must be 1, 2, or 3.")

    step_id, _ = _validate_step_and_module(step)
    catalog = _load_catalog()
    if step_id not in catalog:
        raise ValueError(f"Step {step_id!r} not found in hints catalog.")

    entry = catalog[step_id]
    drift = inspect_step_drift(step_id, workspace_dir=workspace_dir, solutions_dir=solutions_dir)

    base_hint = entry[f"tier_{tier_str}_hint"]

    # If workspace has specific drift, personalize the hint with diagnostic context
    # while preserving the strict length inequality: len(tier_3) > len(tier_2) > len(tier_1).
    if tier_str == "1":
        return base_hint
    elif tier_str == "2":
        context_parts = []
        if drift["missing_files"]:
            context_parts.append(f"Missing file(s): {', '.join(drift['missing_files'])}.")
        if drift["missing_symbols"]:
            context_parts.append(f"Missing symbol(s): {', '.join(drift['missing_symbols'][:4])}.")
        diag_str = f" Context: {' '.join(context_parts)}" if context_parts else ""
        return f"{base_hint}{diag_str}"
    else:  # tier_str == "3"
        extra = (
            f"\nRemediation Guidance: Review the reference patterns above or run "
            f"'verify_workspace.py --module {entry['module']} --step {step_id} --tier remediate' "
            f"to restore reference state and achieve 0 drift."
        )
        return f"{base_hint}{extra}"


def remediate_step(
    step: str,
    workspace_dir: str | Path | None = None,
    solutions_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    /**
     * Atomically restores reference solution files for a given step into the learner's workspace.
     *
     * Why: Interface Contract 4 function. When hints are exhausted, Lab Helper brings the
     * workspace back into a working state by copying authoritative files from .agents/solutions/.
     *
     * @param step Step identifier ("1a"–"4b") or "all".
     * @param workspace_dir Path to learner's workspace directory.
     * @param solutions_dir Path to gold-standard solutions directory.
     * @return Remediation summary dictionary.
     */
    """
    step_id, mod_int = _validate_step_and_module(step)
    ws_root = Path(workspace_dir).resolve() if workspace_dir is not None else APP_ROOT
    sol_root = Path(solutions_dir).resolve() if solutions_dir is not None else DEFAULT_SOLUTIONS_DIR

    steps_to_remediate = [s for s in VALID_STEPS if mod_int is None or int(s[0]) == mod_int] if step_id == "all" else [step_id]

    restored_files: list[str] = []

    # Ensure parent solutions package directories exist with __init__.py files
    ws_solutions_dir = ws_root / ".agents" / "solutions"
    ws_solutions_dir.mkdir(parents=True, exist_ok=True)
    init_sol = sol_root / "__init__.py"
    if init_sol.is_file():
        shutil.copy2(init_sol, ws_solutions_dir / "__init__.py")

    for sid in steps_to_remediate:
        spec = STEP_REGISTRY[sid]
        mod_num = spec["module"]
        ws_mod_dir = ws_solutions_dir / f"module_{mod_num}"
        ws_mod_dir.mkdir(parents=True, exist_ok=True)

        mod_init = sol_root / f"module_{mod_num}" / "__init__.py"
        if mod_init.is_file():
            shutil.copy2(mod_init, ws_mod_dir / "__init__.py")

        for rel in spec["files"]:
            src = sol_root / rel
            dst = ws_solutions_dir / rel
            if not src.is_file():
                # If solutions on disk don't exist yet, we cannot restore
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.resolve() != dst.resolve():
                shutil.copy2(src, dst)
            restored_files.append(str(dst.relative_to(ws_root)))

    post_drift = inspect_step_drift(step_id, workspace_dir=ws_root, solutions_dir=sol_root)

    return {
        "step": step_id,
        "module": mod_int or (int(step_id[0]) if step_id != "all" else 0),
        "tier": "remediate",
        "remediated": True,
        "restored_files": restored_files,
        "has_drift": post_drift["has_drift"],
        "drifted": post_drift["drifted"],
        "status": post_drift["status"],
        "hint": f"Remediated step {step_id}: restored {', '.join(restored_files) if restored_files else 'files'}.",
        "message": f"Remediated step {step_id}: restored {', '.join(restored_files) if restored_files else 'files'}.",
    }


# ==============================================================================
# CLI Argument Parser & Execution Flow
# ==============================================================================

def build_parser() -> argparse.ArgumentParser:
    """
    /**
     * Constructs the CLI argument parser for verify_workspace.py.
     *
     * Why: Provides a standardized, robust command-line interface supporting flags
     * --module, --step, --tier, --remediate, --apply, --workspace-dir, --solutions-dir, and --json.
     *
     * @return Configured ArgumentParser instance.
     */
    """
    parser = argparse.ArgumentParser(
        description="Verify workspace drift, provide progressive hints, and auto-remediate Pitch Generator lab steps."
    )
    parser.add_argument("--module", type=int, default=None, help="Lab module number (1-4)")
    parser.add_argument("--step", type=str, default="all", help="Step identifier (e.g. '1a', '3b', 'all')")
    parser.add_argument("--tier", type=str, default="1", help="Progressive hint tier (1, 2, 3, or 'remediate')")
    parser.add_argument("--remediate", action="store_true", help="Restore reference step implementations to zero drift")
    parser.add_argument("--apply", action="store_true", help="Alias for --remediate")
    parser.add_argument("--workspace-dir", type=str, default=str(APP_ROOT), help="Path to workspace directory")
    parser.add_argument("--solutions-dir", type=str, default=str(DEFAULT_SOLUTIONS_DIR), help="Path to reference solutions")
    parser.add_argument("--json", action="store_true", help="Output JSON payload to stdout")
    return parser


def main() -> int:
    """
    /**
     * Main CLI entrypoint for verify_workspace.py.
     *
     * Why: Parses CLI arguments, executes drift checks, hint queries, or auto-remediation,
     * formats output (text or JSON), and enforces appropriate exit codes (0 for success,
     * 2 for invalid arguments).
     *
     * @return Process exit code.
     */
    """
    parser = build_parser()
    args = parser.parse_args()

    effective_tier = "remediate" if (args.remediate or args.apply) else str(args.tier).strip().lower()

    # Validate tier argument strictly
    if effective_tier not in VALID_TIERS:
        err_msg = f"Invalid --tier argument: {args.tier!r}. Valid values: {VALID_TIERS}"
        if args.json:
            print(json.dumps({"error": err_msg, "exit_code": 2}))
        else:
            sys.stderr.write(f"Error: {err_msg}\n")
        return 2

    try:
        step_id, mod_int = _validate_step_and_module(args.step, args.module)
    except ValueError as exc:
        err_msg = str(exc)
        if args.json:
            print(json.dumps({"error": err_msg, "exit_code": 2}))
        else:
            sys.stderr.write(f"Error: {err_msg}\n")
        return 2

    if effective_tier == "remediate":
        res = remediate_step(step_id, workspace_dir=args.workspace_dir, solutions_dir=args.solutions_dir)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(res["message"])
        return 0

    # Progressive hint inspection (Tiers 1, 2, 3)
    drift = inspect_step_drift(
        step_id,
        workspace_dir=args.workspace_dir,
        solutions_dir=args.solutions_dir,
        module=mod_int,
    )

    if step_id == "all":
        hint_text = (
            f"Workspace audit complete: {'Drift detected' if drift['has_drift'] else 'Clean (0 drift)'} "
            f"across {len(drift.get('steps', {}))} steps."
        )
    else:
        hint_text = get_progressive_hint(
            step_id,
            tier=effective_tier,
            workspace_dir=args.workspace_dir,
            solutions_dir=args.solutions_dir,
        )

    output_payload = {
        **drift,
        "tier": effective_tier,
        "hint": hint_text,
        "message": hint_text,
    }

    if args.json:
        print(json.dumps(output_payload, indent=2))
    else:
        if drift.get("not_started"):
            status_banner = "📋 READY TO BEGIN"
            print(
                f"[{status_banner}] Step {step_id.upper()} (Tier {effective_tier}) — "
                f"You haven't started Step {step_id.upper()} ({drift.get('title', '')}) yet."
            )
            if drift.get("target_files"):
                print(f"  Target File(s): {', '.join(drift['target_files'])}")
            if drift.get("pending_symbols"):
                print(f"  Symbols to Add: {', '.join(drift['pending_symbols'])}")
        elif drift["has_drift"]:
            status_banner = "⚠️ INCOMPLETE / DRIFT DETECTED"
            print(f"[{status_banner}] Step {step_id.upper()} (Tier {effective_tier})")
            if drift["missing_files"]:
                print(f"  Missing Files: {', '.join(drift['missing_files'])}")
            if drift["missing_symbols"]:
                print(f"  Missing Symbols: {', '.join(drift['missing_symbols'])}")
        else:
            status_banner = "✅ COMPLETED (0 DRIFT)"
            print(f"[{status_banner}] Step {step_id.upper()} (Tier {effective_tier})")
        print(f"\n{hint_text}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
