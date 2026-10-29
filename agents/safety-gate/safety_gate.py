#!/usr/bin/env python3
"""
Antigravity Hybrid Safety Gate (`safety-gate`)

A three-stage binary (`allow` / `deny`) `PreToolUse` security gate for Antigravity (`~/.gemini/hooks.json`)
that never prompts with `force_ask`, escalating borderline or
high-impact actions to a heavy reasoning model with full conversation transcript and reference file context:
1. Stage 1 (Deterministic Static Policy Engine, <5ms):
   - Fast-allows (`allow`) known-safe read-only commands, local git operations, and local test runs.
   - Enforces hard `deny` rules on `run_command` and file tools for catastrophic deletions (`rm -rf /`, `~`,
     `~/projects`), credential/secret exfiltration (`security find-generic-password`, `~/.ssh/id_*`,
     cloud and CLI token files), disk formatting, `git push --force`, and privilege escalation (`sudo`).
   - Flags gray-area commands (`needs_review`) for Stage 2 and high-impact/boundary actions (`force_ask` / `escalate`,
     such as `git push`, `git reset --hard`, `gh pr/issue create/merge`, `rm -rf` on project directories,
     out-of-workspace file edits, `curl | sh`, and browser form submissions) for Stage 3.
2. Stage 2 (Fast Context-Aware Classifier - `gemini-3.1-flash-lite-preview`, ~0.8s p50 uncached, <1ms cached):
   - Evaluates gray-area shell commands (`python3 -c "..."`, `node -e "..."`, local scripts, `tmux`)
     with conversation transcript context, referenced local files, and recent tool history.
   - Returns `allow`, `deny`, or `escalate` (which delegates to Stage 3).
3. Stage 3 (Heavy Full-Context Judge - `gemini-3.1-pro-preview`, ~3.5s p50 uncached):
   - Invoked for high-impact actions (`git push`, `rm -rf`, out-of-workspace writes, `gh` mutations,
     browser form submissions) or when Stage 2 escalates.
   - Reads the full conversation transcript (`transcript.jsonl`, distinguishing authoritative `USER_INPUT`
     requests from untrusted tool outputs to block prompt injection), plus referenced local files and
     proposed file edits, to make an informed binary `allow` or `deny` decision.
"""

import ast
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile as _tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]

for _stdio_stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stdio_stream, "reconfigure"):
        try:
            _stdio_stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _load_private_rules() -> Any:
    """Load optional workstation-local rules overlay if present and not disabled."""
    env_val = os.environ.get("SAFETY_GATE_PRIVATE_RULES", "").strip()
    if env_val.lower() in ("0", "false", "off", "none"):
        return None
    candidates: List[Path] = []
    if env_val:
        env_p = Path(os.path.expanduser(env_val))
        if env_p.is_dir():
            candidates.extend(sorted(env_p.glob("private*rules.py")))
        else:
            candidates.append(env_p)
    cfg_dir = Path.home() / ".config" / "safety-gate"
    candidates.append(cfg_dir / "private_rules.py")
    if cfg_dir.is_dir():
        candidates.extend(sorted(cfg_dir.glob("private*rules.py")))
    for cand in candidates:
        if cand.is_file():
            try:
                spec = importlib.util.spec_from_file_location(cand.stem, str(cand))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    return mod
            except Exception:
                continue
    return None


PRIVATE_RULES = _load_private_rules()

_default_state_fallback = getattr(PRIVATE_RULES, "DEFAULT_STATE_DIR", None) or (Path.home() / ".config" / "safety-gate")
DEFAULT_STATE_DIR = Path(os.environ.get("SAFETY_GATE_STATE_DIR", str(_default_state_fallback)))
STATE_DIR = DEFAULT_STATE_DIR
LOG_FILE = STATE_DIR / "safety-gate.log"
CACHE_FILE = STATE_DIR / "safety-gate-cache.json"
CACHE_LOCK_FILE = STATE_DIR / "safety-gate-cache.lock"
RULES_FILE = STATE_DIR / "safety-gate-rules.json"
SELF_BACKUP_FILE = STATE_DIR / "safety_gate.py.bak"

_env_home_aliases = tuple(
    p.strip()
    for p in re.split(r";|(?<!^[A-Za-z])(?<![;:][A-Za-z]):", os.environ.get("SAFETY_GATE_HOME_ALIASES", ""))
    if p.strip()
)
_priv_home_aliases = tuple(getattr(PRIVATE_RULES, "EXTRA_HOME_ALIASES", ()) or ())
HOMES: Tuple[Path, ...] = tuple(
    dict.fromkeys(
        Path(p)
        for p in (str(Path.home()), *_env_home_aliases, *_priv_home_aliases)
    )
)
HOME_ROOTS: Tuple[Path, ...] = tuple(
    dict.fromkeys(
        r
        for h in HOMES
        for r in (h, h.resolve())
    )
)

_env_ws_roots = tuple(
    Path(os.path.expanduser(p.strip()))
    for p in re.split(r";|(?<!^[A-Za-z])(?<![;:][A-Za-z]):", os.environ.get("SAFETY_GATE_WORKSPACE_ROOT", ""))
    if p.strip()
)
WORKSPACE_ROOT = (_env_ws_roots[0] if _env_ws_roots else (Path.home() / "projects")).resolve()
_extra_ws_roots = tuple(getattr(PRIVATE_RULES, "EXTRA_WORKSPACE_ROOTS", ()) or ())
WORKSPACE_ROOTS: Tuple[Path, ...] = tuple(
    dict.fromkeys(
        r
        for base_ws in (*_env_ws_roots, *(h / "projects" for h in HOMES), *_extra_ws_roots)
        for r in (base_ws, base_ws.resolve())
    )
)

_extra_ro_roots = tuple(getattr(PRIVATE_RULES, "EXTRA_READONLY_ROOTS", ()) or ())
EXTRA_READONLY_ROOTS: Tuple[Path, ...] = tuple(
    dict.fromkeys(
        r
        for ro in _extra_ro_roots
        for r in (ro, ro.resolve())
    )
)

GEMINI_APP_DIRS: Tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            "antigravity-cli",
            "antigravity",
            "antigravity-ide",
            *tuple(getattr(PRIVATE_RULES, "EXTRA_GEMINI_APP_DIRS", ()) or ()),
        )
    )
)
GEMINI_SAFE_SUBDIRS = ("brain", "artifacts", "html_artifacts", "scratch")
BRAIN_ROOT = (Path.home() / ".gemini" / GEMINI_APP_DIRS[-1] / "brain").resolve()
BRAIN_ROOTS: Tuple[Path, ...] = tuple(
    dict.fromkeys(
        r
        for base in HOMES
        for app_dir in GEMINI_APP_DIRS
        for sub_dir in GEMINI_SAFE_SUBDIRS
        for r in ((base / ".gemini" / app_dir / sub_dir), (base / ".gemini" / app_dir / sub_dir).resolve())
    )
)
TMP_ROOTS = tuple(
    dict.fromkeys(
        r
        for p in (
            Path("/tmp"),
            Path("/private/tmp"),
            Path("/var/folders"),
            Path("/private/var/folders"),
            Path(_tempfile.gettempdir()),
        )
        for r in (p, p.resolve())
    )
)

PROTECTED_SELF_PATHS: Tuple[Path, ...] = tuple(
    dict.fromkeys(
        r
        for base in HOMES
        for p in (
            base / ".config" / "safety-gate" / "safety_gate.py",
            base / ".config" / "safety-gate" / "safety_gate.py.bak",
            base / ".config" / "safety-gate" / "cli_install.py",
            base / ".config" / "safety-gate" / "stage1_paths.py",
            base / ".config" / "safety-gate" / "stage1_shell.py",
            base / ".config" / "safety-gate" / "stage1_ast.py",
            base / ".config" / "safety-gate" / "llm_classifiers.py",
            base / ".config" / "safety-gate" / "safety-gate-rules.json",
            base / ".config" / "safety-gate" / "private_rules.py",
            base / ".gemini" / "hooks.json",
            base / ".gemini" / "antigravity" / "hooks.json",
        )
        for r in (p, p.resolve())
    )
)

SENSITIVE_CREDENTIAL_PATTERNS = (
    r"\.config/safety-gate/gemini_api_key",
    r"\.config/safety-gate/api_key",
    r"\.config/safety-gate/\.gemini_api_key",
    r"\.ssh/(?:id_[a-z0-9_*?\[\]]*(?!\.pub\b)(?:\b|$|[*?])|\*(?!\.pub\b))",
    r"\.config/gcloud/application_default_credentials\.json",
    r"\.config/gcloud/credentials\.db",
    r"\.config/gcloud/access_tokens\.db",
    r"\.config/gcloud/legacy_credentials/",
    r"\.aws/credentials",
    r"\.npmrc",
    r"\.pypirc",
    r"\.git-credentials\b",
    r"\.config/gh/hosts\.yml\b",
    r"\.kube/config\b",
    *tuple(getattr(PRIVATE_RULES, "EXTRA_SECRET_PATTERNS", ()) or ()),
)

ENV_FILE_PATTERN = (
    r"(?:^|[/\s'\"=])\.env(?:\.[A-Za-z0-9_-]+)?(?![A-Za-z0-9_.-])(?!\.example\b|\.sample\b|\.template\b)"
)

SENSITIVE_EXFIL_PATTERNS = SENSITIVE_CREDENTIAL_PATTERNS + (
    ENV_FILE_PATTERN,
)

DANGEROUS_GIT_CONFIG_PREFIXES = (
    "core.hookspath",
    "core.fsmonitor",
    "core.sshcommand",
    "core.pager",
    "core.editor",
    "core.askpass",
    "core.gitproxy",
    "diff.external",
    "credential.helper",
    "filter.",
    "alias.",
    "protocol.",
    "uploadpack.",
    "receivepack.",
)

PRIMARY_GEMINI_MODEL = (
    os.environ.get("SAFETY_GATE_STAGE2_MODEL")
    or os.environ.get("SAFETY_GATE_GEMINI_MODEL")
    or str(getattr(PRIVATE_RULES, "DEFAULT_STAGE2_GEMINI_MODEL", "") or "gemini-3.1-flash-lite-preview")
)
FALLBACK_GEMINI_MODEL = PRIMARY_GEMINI_MODEL
STAGE2_GEMINI_MODELS = (PRIMARY_GEMINI_MODEL,)
PRIMARY_HEAVY_GEMINI_MODEL = (
    os.environ.get("SAFETY_GATE_STAGE3_MODEL")
    or os.environ.get("SAFETY_GATE_HEAVY_MODEL")
    or "gemini-3.1-pro-preview"
)
STAGE3_HEAVY_GEMINI_MODELS = (PRIMARY_HEAVY_GEMINI_MODEL,)
LLM_MAX_RETRIES = int(os.environ.get("SAFETY_GATE_MAX_RETRIES") or "3")
LLM_RETRY_BASE_DELAY_SECONDS = float(os.environ.get("SAFETY_GATE_RETRY_BASE_DELAY") or "0.25")
VALID_BACKEND_MODES = ("internal", "gcp", "gemini", "auto")
DEFAULT_BACKEND_MODE = str(getattr(PRIVATE_RULES, "DEFAULT_BACKEND", "gcp") or "gcp")
_CLI_BACKEND_OVERRIDE: str = ""
GEMINI_TIMEOUT_SECONDS = float(
    os.environ.get("SAFETY_GATE_STAGE2_TIMEOUT")
    or os.environ.get("SAFETY_GATE_LLM_TIMEOUT")
    or "5.0"
)
HEAVY_GEMINI_TIMEOUT_SECONDS = float(
    os.environ.get("SAFETY_GATE_STAGE3_TIMEOUT")
    or os.environ.get("SAFETY_GATE_HEAVY_TIMEOUT")
    or os.environ.get("SAFETY_GATE_HEAVY_TIMEOUT_SECONDS")
    or "10.0"
)



# --- Submodule Wiring (6 Focused Modules) ---
_SELF_DIR = str(Path(__file__).resolve().parent)
if _SELF_DIR not in sys.path:
    sys.path.insert(0, _SELF_DIR)

import types
import cli_install as _cli_install_mod  # noqa: E402
import stage1_paths as _stage1_paths_mod  # noqa: E402
import stage1_ast as _stage1_ast_mod  # noqa: E402
import stage1_shell as _stage1_shell_mod  # noqa: E402
import llm_classifiers as _llm_classifiers_mod  # noqa: E402


def _bind_submodule_into_namespace(submod: types.ModuleType) -> None:
    """
    Re-export all constants, classes, and functions from `submod` onto `safety_gate` and bind
    function `__globals__` to `safety_gate.__dict__` so any `unittest.mock.patch('safety_gate.<attr>')`
    or runtime attribute override propagates immediately across all 6 modules.
    """
    g = globals()
    for k, v in list(submod.__dict__.items()):
        if k.startswith("__") and k.endswith("__"):
            continue
        if not isinstance(v, types.FunctionType):
            g.setdefault(k, v)
    for k, v in list(submod.__dict__.items()):
        if k.startswith("__") and k.endswith("__"):
            continue
        if isinstance(v, types.FunctionType):
            bound = types.FunctionType(
                v.__code__,
                g,
                name=v.__name__,
                argdefs=v.__defaults__,
                closure=v.__closure__,
            )
            bound.__doc__ = v.__doc__
            bound.__annotations__ = dict(getattr(v, "__annotations__", {}))
            bound.__qualname__ = v.__qualname__
            bound.__kwdefaults__ = getattr(v, "__kwdefaults__", None)
            g[k] = bound
            setattr(submod, k, bound)
        elif isinstance(v, type) and getattr(v, "__module__", "") == submod.__name__:
            for attr_k, attr_v in list(v.__dict__.items()):
                if isinstance(attr_v, types.FunctionType):
                    bound_m = types.FunctionType(
                        attr_v.__code__,
                        g,
                        name=attr_v.__name__,
                        argdefs=attr_v.__defaults__,
                        closure=attr_v.__closure__,
                    )
                    setattr(v, attr_k, bound_m)
            g[k] = v


for _mod in (
    _cli_install_mod,
    _stage1_paths_mod,
    _stage1_ast_mod,
    _stage1_shell_mod,
    _llm_classifiers_mod,
):
    _bind_submodule_into_namespace(_mod)

PURE_READ_BINARIES.update(getattr(PRIVATE_RULES, "EXTRA_PURE_READ_BINARIES", ()) or ())
TRUSTED_CREDENTIAL_SCRIPT_NAMES.update(getattr(PRIVATE_RULES, "EXTRA_TRUSTED_SCRIPT_NAMES", ()) or ())
_PASSIVE_PROSE_CLI_BINARIES = frozenset(
    set(_PASSIVE_PROSE_CLI_BINARIES) | set(getattr(PRIVATE_RULES, "EXTRA_PASSIVE_PROSE_BINARIES", ()) or ())
)
_PASSIVE_PATH_FLAGS = tuple(
    dict.fromkeys((*_PASSIVE_PATH_FLAGS, *tuple(getattr(PRIVATE_RULES, "EXTRA_PASSIVE_PATH_FLAGS", ()) or ())))
)
_PASSIVE_PATH_EQ_PREFIXES = tuple(
    f"{fl}=" for fl in _PASSIVE_PATH_FLAGS if fl.startswith("--")
)

def _resolve_payload_cwd(payload: Dict[str, Any], args: Dict[str, Any]) -> str:
    """
    Resolve the effective working directory for a tool call:
    1. Explicit `args["Cwd"]` / `args["cwd"]` / `args["WorkingDirectory"]`.
    2. Top-level `payload["cwd"]` / `payload["workingDirectory"]`.
    3. First entry in `payload["workspacePaths"]`.
    4. Fallback to `WORKSPACE_ROOT` (`~/projects`).
    """
    for key in ("Cwd", "cwd", "WorkingDirectory", "workingDirectory"):
        val = args.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for key in ("cwd", "workingDirectory", "Cwd"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    ws_paths = payload.get("workspacePaths")
    if isinstance(ws_paths, list):
        for p in ws_paths:
            if isinstance(p, str) and p.strip():
                return p.strip()
    return str(WORKSPACE_ROOT)


def evaluate_tool_call(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], str, str]:
    """
    Evaluate a `PreToolUse` hook payload.
    Returns (hook_output_dict, stage, target_summary) where `decision` is strictly `"allow"` or `"deny"`.
    """
    tool_call = payload.get("toolCall") or {}
    if not isinstance(tool_call, dict):
        return {"decision": "allow", "permissionOverrides": ["command(ls)"]}, "noop", ""

    tool_name = str(tool_call.get("name") or "").strip()
    conv_id = str(payload.get("conversationId") or "").strip()
    transcript_hint = str(payload.get("transcriptPath") or payload.get("transcript") or "").strip()
    args = tool_call.get("args") or {}
    if not isinstance(args, dict):
        args = {}

    if not tool_name or tool_name in READ_ONLY_TOOLS:
        return {"decision": "allow", "permissionOverrides": ["command(ls)"]}, "readonly-tool", tool_name

    if tool_name in (
        "view_file",
        "read_file",
        "view_file_outline",
        "view_code_item",
        "grep_search",
        "list_dir",
        "find_by_name",
    ):
        target = str(
            args.get("AbsolutePath")
            or args.get("Path")
            or args.get("File")
            or args.get("TargetFile")
            or args.get("SearchPath")
            or args.get("DirectoryPath")
            or args.get("SearchDirectory")
            or ""
        ).strip()
        decision, stage, reason = evaluate_read_tool(tool_name, args)
        if decision in ("force_ask", "ask", "escalate"):
            rule_hit = check_user_approval_rules(target, conv_id)
            if rule_hit:
                decision, stage, reason = "allow", rule_hit[0], rule_hit[1]
            else:
                # Never attach file contents on disk when deciding whether reading the file is permitted
                serialized_args = json.dumps(args, ensure_ascii=False)[:2000]
                extra_fp = hashlib.sha256(serialized_args.encode("utf-8")).hexdigest()[:16]
                extra_ctx = f"\n\nTool Arguments (`{tool_name}`):\n{serialized_args}"
                decision, stage, reason = classify_with_heavy_gemini(
                    target_summary=target,
                    cwd=str(WORKSPACE_ROOT),
                    hint=reason,
                    conv_id=conv_id,
                    tool_name=tool_name,
                    extra_context=extra_ctx,
                    extra_fp=extra_fp,
                    transcript_hint=transcript_hint,
                )
        out_r: Dict[str, Any] = {"decision": decision}
        if decision == "allow":
            out_r["permissionOverrides"] = ["command(ls)"]
        if reason:
            out_r["reason"] = reason
        return out_r, stage, target

    if tool_name in ("read_url_content", "open_browser_url", "read_browser_page"):
        target = str(args.get("Url") or args.get("url") or args.get("uri") or "").strip()
        decision, stage, reason = evaluate_url_tool(tool_name, args)
        if decision in ("force_ask", "ask", "escalate"):
            rule_hit = check_user_approval_rules(target, conv_id)
            if rule_hit:
                decision, stage, reason = "allow", rule_hit[0], rule_hit[1]
            else:
                extra_fp, extra_ctx = _build_non_shell_tool_context(tool_name, args, conv_id)
                decision, stage, reason = classify_with_heavy_gemini(
                    target_summary=target,
                    cwd=str(WORKSPACE_ROOT),
                    hint=reason,
                    conv_id=conv_id,
                    tool_name=tool_name,
                    extra_context=extra_ctx,
                    extra_fp=extra_fp,
                    transcript_hint=transcript_hint,
                )
        out_u: Dict[str, Any] = {"decision": decision}
        if decision == "allow":
            out_u["permissionOverrides"] = ["command(ls)"]
        if reason:
            out_u["reason"] = reason
        return out_u, stage, target

    if tool_name == "manage_task":
        action = str(args.get("Action") or "").strip().lower()
        if action != "send_input":
            return {"decision": "allow", "permissionOverrides": ["command(ls)"]}, "readonly-tool", f"manage_task:{action or 'status'}"
        cmd = str(args.get("Input") or "").strip()
        cwd = _resolve_payload_cwd(payload, args)
        decision, stage, reason = evaluate_shell_static(cmd, cwd, conv_id)
        if decision in ("force_ask", "ask", "escalate", "needs_review"):
            rule_hit = check_user_approval_rules(cmd, conv_id)
            if rule_hit:
                decision, stage, reason = "allow", rule_hit[0], rule_hit[1]
        if decision == "needs_review":
            decision, stage, reason = classify_command_with_gemini(
                cmd, cwd, reason, conv_id, transcript_hint=transcript_hint
            )
        elif decision in ("force_ask", "ask", "escalate"):
            decision, stage, reason = classify_with_heavy_gemini(
                target_summary=cmd,
                cwd=cwd,
                hint=reason,
                conv_id=conv_id,
                tool_name="manage_task(send_input)",
                transcript_hint=transcript_hint,
            )
        out_m: Dict[str, Any] = {"decision": decision}
        if decision == "allow":
            out_m["permissionOverrides"] = ["command(ls)"]
        if reason:
            out_m["reason"] = reason
        return out_m, stage, cmd

    if tool_name in (
        "write_to_file",
        "write_file",
        "replace_file_content",
        "multi_replace_file_content",
        "edit_file",
        "notebook_edit",
    ):
        target = str(args.get("TargetFile") or args.get("Path") or args.get("NotebookPath") or "")
        if PRIVATE_RULES is not None and hasattr(PRIVATE_RULES, "extra_hook_precheck"):
            pre = PRIVATE_RULES.extra_hook_precheck(
                tool_name, args, conv_id, transcript_hint,
                WORKSPACE_ROOTS, STATE_DIR, WORKSPACE_ROOT, HOME_ROOTS, GEMINI_APP_DIRS,
            )
            if pre is not None:
                return pre
        decision, stage, reason = evaluate_file_tool(tool_name, args)
        if decision != "deny" and get_conversation_gate_mode(conv_id) in ("off", "ask", "force_ask", "bypass"):
            return (
                {
                    "decision": "force_ask",
                    "reason": "Safety gate turned off for this conversation thread (interactive user approval required).",
                },
                "thread-force-ask",
                target,
            )
        if decision in ("force_ask", "ask", "escalate"):
            rule_hit = check_user_approval_rules(target, conv_id)
            if rule_hit:
                decision, stage, reason = "allow", rule_hit[0], rule_hit[1]
            else:
                extra_fp, extra_ctx = _build_non_shell_tool_context(tool_name, args, conv_id)
                decision, stage, reason = classify_with_heavy_gemini(
                    target_summary=target,
                    cwd=str(WORKSPACE_ROOT),
                    hint=reason,
                    conv_id=conv_id,
                    tool_name=tool_name,
                    extra_context=extra_ctx,
                    extra_fp=extra_fp,
                    transcript_hint=transcript_hint,
                )
        out: Dict[str, Any] = {"decision": decision}
        if decision == "allow":
            out["permissionOverrides"] = ["command(ls)"]
        if reason:
            out["reason"] = reason
        return out, stage, target

    if tool_name == "call_mcp_tool" or tool_name.startswith("mcp_"):
        if tool_name.startswith("mcp_") and tool_name != "call_mcp_tool":
            parts = tool_name.split("_", 2)
            mcp_eval_args = {
                "ServerName": parts[1] if len(parts) > 1 else "mcp",
                "ToolName": parts[2] if len(parts) > 2 else tool_name,
                "Arguments": args,
            }
        else:
            mcp_eval_args = args
        target = f"{mcp_eval_args.get('ServerName', '')}/{mcp_eval_args.get('ToolName', '')}"
        decision, stage, reason = evaluate_mcp_tool(mcp_eval_args)
        if decision in ("force_ask", "ask", "escalate"):
            rule_hit = check_user_approval_rules(target, conv_id)
            if rule_hit:
                decision, stage, reason = "allow", rule_hit[0], rule_hit[1]
            else:
                extra_fp, extra_ctx = _build_non_shell_tool_context(tool_name, mcp_eval_args, conv_id)
                decision, stage, reason = classify_with_heavy_gemini(
                    target_summary=target,
                    cwd=str(WORKSPACE_ROOT),
                    hint=reason,
                    conv_id=conv_id,
                    tool_name=tool_name,
                    extra_context=extra_ctx,
                    extra_fp=extra_fp,
                    transcript_hint=transcript_hint,
                )
        out = {"decision": decision}
        if decision == "allow":
            out["permissionOverrides"] = ["command(ls)"]
        if reason:
            out["reason"] = reason
        return out, stage, target

    if tool_name == "run_command":
        cmd = str(args.get("CommandLine") or "").strip()
        cwd = _resolve_payload_cwd(payload, args)
        if PRIVATE_RULES is not None and hasattr(PRIVATE_RULES, "extra_hook_precheck"):
            pre = PRIVATE_RULES.extra_hook_precheck(
                tool_name, args, conv_id, transcript_hint,
                WORKSPACE_ROOTS, STATE_DIR, WORKSPACE_ROOT, HOME_ROOTS, GEMINI_APP_DIRS,
            )
            if pre is not None:
                return pre
        decision, stage, reason = evaluate_shell_static(cmd, cwd, conv_id)
        if decision != "deny" and (
            get_conversation_gate_mode(conv_id) in ("off", "ask", "force_ask", "bypass")
            or bool(re.search(r"(?:^|\s)SAFETY_GATE_FORCE_ASK=1(?:\s|$)", cmd))
        ):
            return (
                {
                    "decision": "force_ask",
                    "reason": "Safety gate turned off for this conversation thread (interactive user approval required).",
                },
                "thread-force-ask",
                cmd,
            )
        # Never allow user rules to override hard `deny`, but allow overriding `force_ask`, `escalate`, or `needs_review`
        if decision in ("force_ask", "ask", "escalate", "needs_review"):
            rule_hit = check_user_approval_rules(cmd, conv_id)
            if rule_hit:
                decision, stage, reason = "allow", rule_hit[0], rule_hit[1]
        if decision == "needs_review":
            decision, stage, reason = classify_command_with_gemini(
                cmd, cwd, reason, conv_id, transcript_hint=transcript_hint
            )
        elif decision in ("force_ask", "ask", "escalate"):
            decision, stage, reason = classify_with_heavy_gemini(
                target_summary=cmd,
                cwd=cwd,
                hint=reason,
                conv_id=conv_id,
                tool_name="run_command",
                transcript_hint=transcript_hint,
            )
        out = {"decision": decision}
        if decision == "allow":
            out["permissionOverrides"] = ["command(ls)"]
        if reason:
            out["reason"] = reason
        return out, stage, cmd

    return {"decision": "allow", "permissionOverrides": ["command(ls)"]}, "other-tool", tool_name



def handle_hook() -> int:
    t0 = time.time()
    raw_stdin = sys.stdin.read()
    if not raw_stdin.strip():
        sys.stdout.write(json.dumps({"decision": "allow"}) + "\n")
        sys.stdout.flush()
        return 0

    try:
        payload = json.loads(raw_stdin)
    except Exception:
        sys.stdout.write(json.dumps({"decision": "allow"}) + "\n")
        sys.stdout.flush()
        return 0

    tool_name = str((payload.get("toolCall") or {}).get("name") or "")
    conv_id = str(payload.get("conversationId") or "")
    step_idx = payload.get("stepIdx")
    if not isinstance(step_idx, int):
        step_idx = None

    out, stage, target_summary = evaluate_tool_call(payload)
    elapsed_ms = (time.time() - t0) * 1000.0
    decision = str(out.get("decision", "allow"))
    reason = str(out.get("reason", "Allowed."))

    if (
        tool_name
        in (
            "run_command",
            "write_to_file",
            "write_file",
            "replace_file_content",
            "multi_replace_file_content",
            "edit_file",
            "notebook_edit",
        )
        or stage not in ("static-allow", "readonly-tool", "other-tool", "noop")
        or decision != "allow"
    ):
        log_decision(
            tool_name=tool_name,
            decision=decision,
            stage=stage,
            reason=reason,
            target_summary=target_summary,
            elapsed_ms=elapsed_ms,
            conversation_id=conv_id,
        )

    if decision in ("force_ask", "ask", "deny") and stage != "thread-force-ask":
        notify_fn = getattr(sys.modules[__name__], "_notify_denial_hook", None)
        if callable(notify_fn):
            notify_fn(
                conversation_id=conv_id,
                step_idx=step_idx,
                tool_name=tool_name,
                decision=decision,
                stage=stage,
                reason=reason,
                target_summary=target_summary,
            )

    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
    return 0


if PRIVATE_RULES is not None and hasattr(PRIVATE_RULES, "register_on_module"):
    PRIVATE_RULES.register_on_module(sys.modules[__name__])

for _submod in (
    _cli_install_mod,
    _stage1_paths_mod,
    _stage1_ast_mod,
    _stage1_shell_mod,
    _llm_classifiers_mod,
):
    for _k, _v in list(globals().items()):
        if not (_k.startswith("__") and _k.endswith("__")):
            setattr(_submod, _k, _v)


def main() -> int:
    global _CLI_BACKEND_OVERRIDE
    if "--backend" in sys.argv:
        b_idx = sys.argv.index("--backend")
        if b_idx + 1 < len(sys.argv):
            _CLI_BACKEND_OVERRIDE = sys.argv[b_idx + 1].strip().lower()

    if len(sys.argv) < 2 or sys.argv[1] == "hook":
        return handle_hook()

    sub = sys.argv[1]
    if sub in ("-h", "--help", "help"):
        print(
            "Usage:\n"
            "  safety-gate install [--path <hooks.json>]               # Register PreToolUse hook in ~/.gemini/hooks.json\n"
            "  safety-gate uninstall [--path <hooks.json>]             # Remove PreToolUse hook from ~/.gemini/hooks.json\n"
            "  safety-gate setup-key [<key>] [--keychain]              # Save Gemini API key\n"
            "  safety-gate doctor                                      # Check setup and API key\n"
            "  safety-gate hook [--backend gcp|internal|auto]          # PreToolUse stdin->stdout JSON hook\n"
            "  safety-gate check \"<command>\" [--backend ...]           # Test classification of a shell command\n"
            "  safety-gate backend [gcp|internal|auto]                 # Show or switch active LLM gateway mode\n"
            "  safety-gate stats [N]                                   # Show decision stats and last N audit log entries\n"
            "  safety-gate rules                                       # Show saved Always-Allow / conversation rules\n"
            "  safety-gate allow-rule \"<target>\"                       # Add an Always-Allow or conversation rule\n"
            "  safety-gate thread-mode <cid> [off|ask|default]         # Configure per-thread approval mode"
        )
        return 0
    if sub == "install":
        target = "antigravity"
        custom_path = ""
        if "--target" in sys.argv:
            idx = sys.argv.index("--target")
            if idx + 1 < len(sys.argv):
                target = sys.argv[idx + 1]
        elif len(sys.argv) >= 3 and not sys.argv[2].startswith("-"):
            target = sys.argv[2]
        if "--path" in sys.argv:
            idx = sys.argv.index("--path")
            if idx + 1 < len(sys.argv):
                custom_path = sys.argv[idx + 1]
        return handle_install_cli(target=target, custom_path=custom_path)
    elif sub == "uninstall":
        target = "antigravity"
        custom_path = ""
        if "--target" in sys.argv:
            idx = sys.argv.index("--target")
            if idx + 1 < len(sys.argv):
                target = sys.argv[idx + 1]
        elif len(sys.argv) >= 3 and not sys.argv[2].startswith("-"):
            target = sys.argv[2]
        if "--path" in sys.argv:
            idx = sys.argv.index("--path")
            if idx + 1 < len(sys.argv):
                custom_path = sys.argv[idx + 1]
        return handle_uninstall_cli(target=target, custom_path=custom_path)
    elif sub == "setup-key":
        use_kc = "--keychain" in sys.argv
        positional = [a for a in sys.argv[2:] if not a.startswith("-")]
        key_arg = positional[0] if positional else ""
        return handle_setup_key_cli(key_arg=key_arg, use_keychain=use_kc)
    elif sub == "doctor":
        custom_path = ""
        if "--path" in sys.argv:
            idx = sys.argv.index("--path")
            if idx + 1 < len(sys.argv):
                custom_path = sys.argv[idx + 1]
        return handle_doctor_cli(custom_path=custom_path)
    elif sub == "check":
        if len(sys.argv) < 3:
            print(
                "Usage: safety-gate check \"<command>\" [--cwd <dir>] [--conv <id>] [--backend gcp|internal|auto]",
                file=sys.stderr,
            )
            return 1
        cmd = sys.argv[2]
        cwd = str(WORKSPACE_ROOT)
        conv_id = ""
        if "--cwd" in sys.argv:
            idx = sys.argv.index("--cwd")
            if idx + 1 < len(sys.argv):
                cwd = sys.argv[idx + 1]
        if "--conv" in sys.argv:
            idx = sys.argv.index("--conv")
            if idx + 1 < len(sys.argv):
                conv_id = sys.argv[idx + 1]
        return handle_check_cli(cmd, cwd, conv_id)
    elif sub == "backend":
        mode_arg = ""
        if len(sys.argv) >= 3 and not sys.argv[2].startswith("-"):
            if sys.argv[2].strip().lower() == "set" and len(sys.argv) >= 4:
                mode_arg = sys.argv[3]
            else:
                mode_arg = sys.argv[2]
        return handle_backend_cli(mode_arg)
    elif sub in ("stats", "status", "tail"):
        n = int(sys.argv[2]) if len(sys.argv) >= 3 and sys.argv[2].isdigit() else 15
        return handle_stats_cli(n)
    elif sub == "rules":
        print(json.dumps(load_user_rules(), indent=2))
        return 0
    elif sub in ("thread-mode", "conv-mode"):
        if len(sys.argv) < 3:
            print("Usage: safety-gate thread-mode <conversation_id> [default|off|ask|force_ask|--clear]", file=sys.stderr)
            return 1
        cid_arg = sys.argv[2].strip()
        if len(sys.argv) >= 4:
            mode_arg = sys.argv[3].strip().lower()
            ok = set_conversation_gate_mode(cid_arg, mode_arg)
            cur_mode = get_conversation_gate_mode(cid_arg)
            print(json.dumps({"ok": ok, "conversationId": cid_arg, "mode": cur_mode}))
            return 0 if ok else 1
        cur_mode = get_conversation_gate_mode(cid_arg)
        print(json.dumps({"ok": True, "conversationId": cid_arg, "mode": cur_mode}))
        return 0
    elif sub == "allow-rule":
        if len(sys.argv) < 3:
            print("Usage: safety-gate allow-rule \"<target>\" [--prefix] [--conv <id>]", file=sys.stderr)
            return 1
        target = sys.argv[2]
        is_prefix = "--prefix" in sys.argv
        conv_id = ""
        scope = "global"
        if "--conv" in sys.argv:
            idx = sys.argv.index("--conv")
            if idx + 1 < len(sys.argv):
                conv_id = sys.argv[idx + 1]
                scope = "conversation"
        ok = add_user_approval_rule(
            target=target,
            scope=scope,
            is_prefix=is_prefix,
            conversation_id=conv_id,
        )
        print(json.dumps({"ok": ok, "target": target, "scope": scope, "isPrefix": is_prefix, "conversationId": conv_id}))
        return 0 if ok else 1
    else:
        print(
            "Usage:\n"
            "  safety-gate install [--path <hooks.json>]               # Register PreToolUse hook in ~/.gemini/hooks.json\n"
            "  safety-gate uninstall [--path <hooks.json>]             # Remove PreToolUse hook from ~/.gemini/hooks.json\n"
            "  safety-gate setup-key [<key>] [--keychain]              # Save Gemini API key\n"
            "  safety-gate doctor                                      # Check setup and API key\n"
            "  safety-gate hook [--backend gcp|internal|auto]          # PreToolUse stdin->stdout JSON hook\n"
            "  safety-gate check \"<command>\" [--backend ...]           # Test classification of a shell command\n"
            "  safety-gate backend [gcp|internal|auto]                 # Show or switch active LLM gateway mode\n"
            "  safety-gate stats [N]                                   # Show decision stats and last N audit log entries\n"
            "  safety-gate rules                                       # Show saved Always-Allow / conversation rules\n"
            "  safety-gate allow-rule \"<target>\"                       # Add an Always-Allow or conversation rule\n"
            "  safety-gate thread-mode <cid> [off|ask|default]         # Configure per-thread approval mode",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
