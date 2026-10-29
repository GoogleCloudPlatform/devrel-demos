#!/usr/bin/env python3
"""
CLI commands (`install`, `uninstall`, `setup-key`, `doctor`, `status`, `backend`, `check`),
file locking (`CacheLock`), decision logging, cache persistence, user approval rules, and
6-module runtime state syncing (`_sync_runtime_modules_to_state_dir`) for `safety-gate`.
"""

import datetime
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore[assignment]

try:
    import msvcrt
except ImportError:
    msvcrt = None  # type: ignore[assignment]

class CacheLock:
    def __init__(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.fd = open(CACHE_LOCK_FILE, "w")

    def __enter__(self) -> "CacheLock":
        if fcntl is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX)
            except Exception:
                pass
        elif msvcrt is not None:
            try:
                msvcrt.locking(self.fd.fileno(), msvcrt.LK_LOCK, 1)
            except Exception:
                pass
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if fcntl is not None:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            except Exception:
                pass
        elif msvcrt is not None:
            try:
                msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
        self.fd.close()


def log_decision(
    tool_name: str,
    decision: str,
    stage: str,
    reason: str,
    target_summary: str,
    elapsed_ms: float,
    conversation_id: str = "",
) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        short_conv = (conversation_id or "-")[:8]
        preview = re.sub(r"\s+", " ", target_summary).strip()
        if len(preview) > 180:
            preview = preview[:177] + "..."
        entry = {
            "ts": ts,
            "conv": short_conv,
            "tool": tool_name,
            "decision": decision,
            "stage": stage,
            "ms": round(elapsed_ms, 1),
            "reason": reason,
            "target": preview,
        }
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def load_cache() -> Dict[str, Any]:
    if not CACHE_FILE.exists():
        return {"entries": {}}
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("entries"), dict):
            return data
    except Exception:
        pass
    return {"entries": {}}


def save_cache_entry(cmd_hash: str, decision: str, reason: str, model: str) -> None:
    try:
        with CacheLock():
            data = load_cache()
            entries = data.setdefault("entries", {})
            entries[cmd_hash] = {
                "decision": decision,
                "reason": reason,
                "model": model,
                "updatedAt": datetime.datetime.now().isoformat(),
            }
            if len(entries) > 1000:
                keys = list(entries.keys())
                for k in keys[:-1000]:
                    entries.pop(k, None)
            tmp = CACHE_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(CACHE_FILE)
    except Exception:
        pass




def load_user_rules() -> Dict[str, Any]:
    default_rules: Dict[str, Any] = {
        "global": {"exact": [], "prefixes": []},
        "conversations": {},
    }
    if not RULES_FILE.exists():
        return default_rules
    try:
        data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("global", {"exact": [], "prefixes": []})
            data["global"].setdefault("exact", [])
            data["global"].setdefault("prefixes", [])
            data.setdefault("conversations", {})
            return data
    except Exception:
        pass
    return default_rules


def add_user_approval_rule(
    target: str,
    scope: str = "global",
    is_prefix: bool = False,
    conversation_id: str = "",
) -> bool:
    """
    Save a user-approved rule (Option 2: Always allow, or Option 3: Allow in this conversation)
    into `~/.config/safety-gate/safety-gate-rules.json`.
    """
    cleaned = target.strip()
    if not cleaned:
        return False
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with CacheLock():
            data = load_user_rules()
            if scope == "conversation" and conversation_id:
                bucket = data["conversations"].setdefault(
                    conversation_id, {"exact": [], "prefixes": []}
                )
                bucket.setdefault("exact", [])
                bucket.setdefault("prefixes", [])
            else:
                bucket = data["global"]

            key = "prefixes" if is_prefix else "exact"
            if cleaned not in bucket[key]:
                bucket[key].append(cleaned)

            tmp = RULES_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(RULES_FILE)
        return True
    except Exception:
        return False


def _matches_rule_bucket(target: str, bucket: Dict[str, Any]) -> Optional[str]:
    cleaned = target.strip()
    if not cleaned or not isinstance(bucket, dict):
        return None
    for exact in bucket.get("exact") or []:
        if isinstance(exact, str) and exact.strip() == cleaned:
            return f"exact match `{exact.strip()}`"
    for prefix in bucket.get("prefixes") or []:
        if not isinstance(prefix, str):
            continue
        p = prefix.strip()
        if not p:
            continue
        if cleaned == p or cleaned.startswith(p + " ") or cleaned.startswith(p + "/"):
            return f"prefix `{p}`"
    return None


def check_user_approval_rules(
    target: str, conversation_id: str = ""
) -> Optional[Tuple[str, str]]:
    """
    Check if `target` matches a user-approved rule in `~/.config/safety-gate/safety-gate-rules.json`.
    Returns `(stage, reason)` if matched, or `None`.
    """
    cleaned = target.strip()
    if not cleaned:
        return None
    rules = load_user_rules()
    global_match = _matches_rule_bucket(cleaned, rules.get("global", {}))
    if global_match:
        return (
            "user-rule-global",
            f"Allowed by saved Always-Allow rule ({global_match}).",
        )
    if conversation_id:
        conv_bucket = (rules.get("conversations") or {}).get(conversation_id, {})
        conv_match = _matches_rule_bucket(cleaned, conv_bucket)
        if conv_match:
            return (
                "user-rule-conv",
                f"Allowed in this conversation by user rule ({conv_match}).",
            )
    return None


VALID_THREAD_GATE_MODES = ("default", "off", "ask", "force_ask", "bypass")


def get_conversation_gate_mode(conversation_id: str) -> str:
    """
    Return the per-conversation safety-gate mode from `RULES_FILE`:
    - `"default"`: standard 3-stage binary allow/deny gate.
    - `"off"` / `"ask"` / `"force_ask"` / `"bypass"`: bypass LLM auto-approval for this
      conversation and return `"force_ask"` to trigger the agent's native interactive approval
      (while still enforcing Stage 1 static hard-deny rules).
    """
    cid = str(conversation_id or "").strip().lstrip("#").lower()
    if not cid:
        return "default"
    try:
        rules = load_user_rules()
        convs = rules.get("conversations")
        if not isinstance(convs, dict):
            return "default"
        for k, bucket in convs.items():
            k_low = str(k or "").strip().lstrip("#").lower()
            if not k_low or not isinstance(bucket, dict):
                continue
            if k_low == cid or (len(k_low) >= 8 and (cid.startswith(k_low) or k_low.startswith(cid[:8]))):
                mode = str(bucket.get("mode") or "default").strip().lower()
                if mode in VALID_THREAD_GATE_MODES:
                    return mode
    except Exception:
        pass
    return "default"


def set_conversation_gate_mode(conversation_id: str, mode: str = "default") -> bool:
    """Set or clear the per-conversation safety-gate mode (`default`, `off`, `ask`, `force_ask`) in `RULES_FILE`."""
    cid = str(conversation_id or "").strip().lstrip("#")
    norm_mode = str(mode or "default").strip().lower()
    if norm_mode in ("on", "auto", "clear", "--clear", "reset", ""):
        norm_mode = "default"
    if not cid or norm_mode not in VALID_THREAD_GATE_MODES:
        return False
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with CacheLock():
            data = load_user_rules()
            convs = data.setdefault("conversations", {})
            matched_key = cid
            for k in list(convs.keys()):
                k_low = str(k or "").strip().lstrip("#").lower()
                if k_low == cid.lower() or (len(cid) >= 8 and len(k_low) >= 8 and k_low[:8] == cid.lower()[:8]):
                    matched_key = k
                    break
            if norm_mode == "default":
                bucket = convs.get(matched_key)
                if isinstance(bucket, dict):
                    bucket.pop("mode", None)
                    if not bucket.get("exact") and not bucket.get("prefixes"):
                        convs.pop(matched_key, None)
            else:
                bucket = convs.setdefault(matched_key, {"exact": [], "prefixes": []})
                bucket.setdefault("exact", [])
                bucket.setdefault("prefixes", [])
                bucket["mode"] = norm_mode
            tmp = RULES_FILE.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp.replace(RULES_FILE)
        return True
    except Exception:
        return False



RUNTIME_SIBLING_EXCLUDE = {
    "safety_gate.py",
    "test_safety_gate.py",
    "test_corpus.py",
    "benchmark_historical_corpus.py",
    "test_private_rules.py",
}


def _sync_runtime_modules_to_state_dir(src_dir: Path, dest_dir: Path) -> List[str]:
    """Copy `safety_gate.py` and any sibling runtime `.py` modules from `src_dir` into `dest_dir`."""
    copied: List[str] = []
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        for py_file in sorted(src_dir.glob("*.py")):
            if py_file.name.startswith("test_") or py_file.name in (
                "benchmark_historical_corpus.py",
                "test_corpus.py",
            ):
                continue
            target_path = dest_dir / py_file.name
            try:
                if target_path.resolve() == py_file.resolve():
                    copied.append(py_file.name)
                    continue
            except Exception:
                pass
            raw = py_file.read_bytes()
            if not target_path.exists() or target_path.read_bytes() != raw:
                tmp_p = target_path.with_suffix(".py.tmp")
                tmp_p.write_bytes(raw)
                if py_file.name == "safety_gate.py":
                    try:
                        tmp_p.chmod(0o755)
                    except Exception:
                        pass
                tmp_p.replace(target_path)
            copied.append(py_file.name)
    except Exception:
        pass
    return copied


def _refresh_self_backup_if_changed() -> None:
    """
    Maintain a last-known-good `safety_gate.py.bak` copy (plus any sibling runtime `.py`
    modules in `STATE_DIR`) whenever `safety_gate.py` has been modified and just executed
    cleanly (zero syntax/runtime errors).
    """
    try:
        self_path = Path(__file__).resolve()
        if self_path.name.endswith(".bak"):
            return
        extra_targets = (
            PRIVATE_RULES.extra_self_backup_targets(WORKSPACE_ROOT)
            if globals().get("PRIVATE_RULES") is not None and hasattr(PRIVATE_RULES, "extra_self_backup_targets")
            else ()
        )
        for exec_target in (
            self_path,
            self_path.parent / "test_safety_gate.py",
            *extra_targets,
        ):
            if exec_target.exists() and not os.access(exec_target, os.X_OK):
                try:
                    exec_target.chmod(exec_target.stat().st_mode | 0o755)
                except Exception:
                    pass
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        _sync_runtime_modules_to_state_dir(self_path.parent, STATE_DIR)
        bak_path = SELF_BACKUP_FILE if SELF_BACKUP_FILE.parent == STATE_DIR else (STATE_DIR / "safety_gate.py.bak")
        if bak_path.exists() and self_path.stat().st_mtime <= bak_path.stat().st_mtime:
            return
        tmp_path = bak_path.with_suffix(".bak.tmp")
        tmp_path.write_bytes(self_path.read_bytes())
        tmp_path.replace(bak_path)
    except Exception:
        pass



def handle_check_cli(cmd: str, cwd: str, conv_id: str = "") -> int:
    t0 = time.time()
    payload = {
        "conversationId": conv_id,
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": cmd, "Cwd": cwd},
        },
    }
    out, stage, _ = evaluate_tool_call(payload)
    elapsed_ms = (time.time() - t0) * 1000.0
    result = {
        "command": cmd,
        "cwd": cwd,
        "backend": resolve_safety_gate_backend(),
        "decision": out.get("decision"),
        "stage": stage,
        "reason": out.get("reason", "Allowed by safety gate."),
        "elapsedMs": round(elapsed_ms, 1),
    }
    print(json.dumps(result, indent=2))
    return 0


def handle_backend_cli(mode_arg: str = "") -> int:
    if mode_arg:
        norm = mode_arg.strip().lower()
        if norm not in VALID_BACKEND_MODES:
            print(
                f"Invalid backend {mode_arg!r}. Choose from: {', '.join(VALID_BACKEND_MODES)}",
                file=sys.stderr,
            )
            return 1
        ok = set_configured_backend(norm)
        if not ok:
            print("Failed to save backend setting.", file=sys.stderr)
            return 1
    mode = resolve_safety_gate_backend()
    ls_ep = resolve_internal_ls_endpoint()
    has_key = bool(resolve_gemini_api_key())
    if mode == "internal":
        effective = "internal"
    elif mode == "gcp":
        effective = "gcp"
    else:
        effective = "internal" if ls_ep else "gcp"
    print(
        json.dumps(
            {
                "backend": mode,
                "effectiveBackend": effective,
                "internalLsAddress": ls_ep[0] if ls_ep else None,
                "hasGcpApiKey": has_key,
                "stage2Models": list(STAGE2_GEMINI_MODELS),
                "stage3Models": list(STAGE3_HEAVY_GEMINI_MODELS),
            },
            indent=2,
        )
    )
    return 0


def handle_stats_cli(tail_count: int = 15) -> int:
    if not LOG_FILE.exists():
        print(json.dumps({"totalLogged": 0, "byDecision": {}, "byStage": {}, "recent": []}, indent=2))
        return 0

    by_decision: Dict[str, int] = {}
    by_stage: Dict[str, int] = {}
    entries: List[Dict[str, Any]] = []

    for line in LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            entries.append(obj)
            dec = obj.get("decision", "unknown")
            stg = obj.get("stage", "unknown")
            by_decision[dec] = by_decision.get(dec, 0) + 1
            by_stage[stg] = by_stage.get(stg, 0) + 1
        except Exception:
            continue

    print(
        json.dumps(
            {
                "totalLogged": len(entries),
                "byDecision": by_decision,
                "byStage": by_stage,
                "recent": entries[-tail_count:],
            },
            indent=2,
        )
    )
    return 0


HOOK_TOOL_MATCHER = (
    "run_command|write_to_file|write_file|replace_file_content|multi_replace_file_content|"
    "edit_file|notebook_edit|view_file|read_file|view_file_outline|view_code_item|grep_search|"
    "list_dir|find_by_name|read_url_content|open_browser_url|read_browser_page|manage_task|"
    "call_mcp_tool|mcp_.*"
)


def _verify_modules_smoke_test(src_dir: Path) -> bool:
    """
    Verify that `safety_gate.py` and its sibling `.py` modules in `src_dir` pass both
    `--help` and a synthetic `PreToolUse` `git status` hook smoke test in an isolated temp dir
    before promoting them to `STATE_DIR` or `.bak`.
    """
    import tempfile

    try:
        with tempfile.TemporaryDirectory(prefix="sg_smoke_") as td:
            td_path = Path(td)
            for py_f in sorted(src_dir.glob("*.py")):
                if py_f.name.startswith("test_") or py_f.name in (
                    "benchmark_historical_corpus.py",
                    "test_corpus.py",
                ):
                    continue
                shutil.copy2(py_f, td_path / py_f.name)
            entry = td_path / "safety_gate.py"
            if not entry.is_file():
                return False
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": td,
                "USERPROFILE": td,
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
                "PYTHONPATH": "",
                "SAFETY_GATE_PRIVATE_RULES": "0",
                "SAFETY_GATE_WORKSPACE_ROOT": td,
            }
            r_help = subprocess.run(
                [sys.executable, str(entry), "--help"],
                cwd=td,
                env=env,
                capture_output=True,
                text=True,
                timeout=8.0,
            )
            if r_help.returncode != 0:
                return False
            smoke_payload = json.dumps(
                {
                    "toolCall": {
                        "name": "run_command",
                        "args": {"CommandLine": "git status", "Cwd": td},
                    }
                }
            )
            r_hook = subprocess.run(
                [sys.executable, str(entry), "hook"],
                input=smoke_payload,
                cwd=td,
                env=env,
                capture_output=True,
                text=True,
                timeout=8.0,
            )
            if r_hook.returncode != 0:
                return False
            out_obj = json.loads(r_hook.stdout.strip())
            return out_obj.get("decision") == "allow"
    except Exception:
        return False


def handle_install_cli(target: str = "antigravity", custom_path: str = "") -> int:
    """Install the PreToolUse hook into ~/.gemini/hooks.json and ~/.gemini/config/hooks.json (or a custom hooks.json path)."""
    self_file = Path(__file__).resolve()
    if not _verify_modules_smoke_test(self_file.parent):
        print("Aborted install: smoke test failed on candidate safety_gate modules.", file=sys.stderr)
        return 1
    synced_modules = _sync_runtime_modules_to_state_dir(self_file.parent, STATE_DIR)
    _refresh_self_backup_if_changed()
    installed_entry = (STATE_DIR / "safety_gate.py") if (STATE_DIR / "safety_gate.py").is_file() else self_file
    if os.name == "nt" or sys.platform == "win32":
        try:
            has_py3 = bool(shutil.which("python3"))
        except Exception:
            has_py3 = False
        py_cmd = "python3" if has_py3 else (sys.executable or "python")
        hook_cmd = subprocess.list2cmdline([py_cmd, str(installed_entry), "hook"])
    else:
        hook_cmd = f"python3 {shlex.quote(str(installed_entry))} hook"
    norm_target = (target or "antigravity").strip().lower()
    installed_paths: List[str] = []

    if norm_target in ("antigravity", "default", "both", "all") or custom_path:
        target_paths: Tuple[Path, ...] = (
            (Path(os.path.expanduser(custom_path)),)
            if custom_path
            else (
                Path.home() / ".gemini" / "hooks.json",
                Path.home() / ".gemini" / "config" / "hooks.json",
            )
        )
        for hooks_path in target_paths:
            hooks_path.parent.mkdir(parents=True, exist_ok=True)
            existing: Dict[str, Any] = {}
            if hooks_path.is_file():
                raw_existing = hooks_path.read_text(encoding="utf-8", errors="replace").strip()
                if raw_existing:
                    try:
                        loaded = json.loads(raw_existing)
                    except Exception as exc:
                        print(
                            f"Aborted install: existing {hooks_path} contains invalid JSON ({exc}).",
                            file=sys.stderr,
                        )
                        return 1
                    if not isinstance(loaded, dict):
                        print(
                            f"Aborted install: existing {hooks_path} must be a JSON object.",
                            file=sys.stderr,
                        )
                        return 1
                    existing = loaded
            existing["safety-gate"] = {
                "enabled": True,
                "PreToolUse": [
                    {
                        "matcher": HOOK_TOOL_MATCHER,
                        "hooks": [
                            {
                                "type": "command",
                                "command": hook_cmd,
                                "timeout": 30,
                            }
                        ],
                    }
                ],
            }
            hooks_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
            installed_paths.append(str(hooks_path))

    print(
        json.dumps(
            {
                "ok": bool(installed_paths),
                "target": norm_target,
                "installed": installed_paths,
                "syncedModules": synced_modules,
                "command": hook_cmd,
            },
            indent=2,
        )
    )
    return 0 if installed_paths else 1


def handle_setup_key_cli(key_arg: str = "", use_keychain: bool = False) -> int:
    """Save a Gemini API key to ~/.config/safety-gate/gemini_api_key (0600) or OS credential store."""
    key_val = (key_arg or "").strip()
    if not key_val and not sys.stdin.isatty():
        key_val = sys.stdin.read().strip()
    if not key_val:
        try:
            import getpass
            key_val = getpass.getpass("Enter Gemini API key: ").strip()
        except Exception:
            key_val = ""
    if not key_val:
        print("No API key provided.", file=sys.stderr)
        return 1

    if use_keychain:
        if sys.platform == "darwin":
            res = subprocess.run(
                ["security", "add-generic-password", "-U", "-a", os.environ.get("USER", "user"), "-s", "gemini-api-key", "-w", key_val],
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                print(json.dumps({"ok": True, "store": "macos-keychain", "service": "gemini-api-key"}))
                return 0
        elif sys.platform.startswith("linux") and shutil.which("secret-tool"):
            res = subprocess.run(
                ["secret-tool", "store", "--label=safety-gate", "safety-gate", "gemini_api_key"],
                input=key_val,
                capture_output=True,
                text=True,
            )
            if res.returncode == 0:
                print(json.dumps({"ok": True, "store": "secret-tool", "service": "safety-gate"}))
                return 0

    cfg_dir = Path.home() / ".config" / "safety-gate"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    key_file = cfg_dir / "gemini_api_key"
    key_file.write_text(key_val + "\n", encoding="utf-8")
    try:
        key_file.chmod(0o600)
    except Exception:
        pass
    print(json.dumps({"ok": True, "path": str(key_file)}))
    return 0


def _is_safety_gate_installed_in_hooks_file(path: Path) -> bool:
    """Return True if `path` is a valid JSON file containing an enabled `safety_gate.py` hook entry."""
    if not path.is_file():
        return False
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(loaded, dict):
        return False
    sg_entry = loaded.get("safety-gate")
    if isinstance(sg_entry, dict):
        if sg_entry.get("enabled", True) is False:
            return False
        if "safety_gate.py" in json.dumps(sg_entry):
            return True
    for key in ("PreToolUse", "BeforeTool", "hooks"):
        sub = loaded.get(key)
        if sub and "safety_gate.py" in json.dumps(sub):
            return True
    return False


def _remove_safety_gate_from_hooks_dict(loaded: Dict[str, Any]) -> bool:
    """Remove only `safety-gate` / `safety_gate.py` entries from `loaded`, preserving all other hooks."""
    changed = False
    if "safety-gate" in loaded:
        loaded.pop("safety-gate", None)
        changed = True
    for list_key in ("PreToolUse", "BeforeTool"):
        for container in (loaded, loaded.get("hooks") if isinstance(loaded.get("hooks"), dict) else None):
            if not isinstance(container, dict):
                continue
            arr = container.get(list_key)
            if isinstance(arr, list):
                filtered = [item for item in arr if "safety_gate.py" not in json.dumps(item)]
                if len(filtered) != len(arr):
                    changed = True
                    if filtered:
                        container[list_key] = filtered
                    else:
                        container.pop(list_key, None)
    return changed


def handle_doctor_cli(custom_path: str = "") -> int:
    """Check Python version, hook registration, backend configuration, and API key availability."""
    mode = resolve_safety_gate_backend()
    api_key = resolve_gemini_api_key()
    ls_ep = resolve_internal_ls_endpoint()
    hooks_candidates: Tuple[Path, ...] = (
        (Path(os.path.expanduser(custom_path)),)
        if custom_path
        else (
            Path.home() / ".gemini" / "hooks.json",
            Path.home() / ".gemini" / "config" / "hooks.json",
            Path.home() / ".gemini" / "antigravity" / "hooks.json",
        )
    )
    installed_hooks = [str(p) for p in hooks_candidates if _is_safety_gate_installed_in_hooks_file(p)]
    has_backend_auth = bool(api_key) or (mode in ("internal", "auto") and bool(ls_ep))
    ready = bool(installed_hooks) and has_backend_auth
    report = {
        "ok": ready,
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "backend": mode,
        "hasGeminiApiKey": bool(api_key),
        "internalLsEndpoint": ls_ep[0] if ls_ep else None,
        "privateRulesLoaded": PRIVATE_RULES is not None,
        "hooksInstalled": bool(installed_hooks),
        "hookPaths": installed_hooks,
        "stateDir": str(STATE_DIR),
    }
    print(json.dumps(report, indent=2))
    return 0 if ready else 1


def handle_uninstall_cli(target: str = "antigravity", custom_path: str = "") -> int:
    """Remove the safety-gate PreToolUse hook from ~/.gemini/hooks.json (or a custom hooks.json path)."""
    norm_target = (target or "antigravity").strip().lower()
    removed_from: List[str] = []
    if norm_target in ("antigravity", "default", "both", "all") or custom_path:
        candidates: Tuple[Path, ...] = (
            (Path(os.path.expanduser(custom_path)),)
            if custom_path
            else (
                Path.home() / ".gemini" / "hooks.json",
                Path.home() / ".gemini" / "config" / "hooks.json",
                Path.home() / ".gemini" / "antigravity" / "hooks.json",
            )
        )
        for hooks_path in candidates:
            if hooks_path.is_file():
                try:
                    loaded = json.loads(hooks_path.read_text(encoding="utf-8"))
                    if isinstance(loaded, dict) and _remove_safety_gate_from_hooks_dict(loaded):
                        hooks_path.write_text(json.dumps(loaded, indent=2) + "\n", encoding="utf-8")
                        removed_from.append(str(hooks_path))
                except Exception:
                    pass
    print(json.dumps({"ok": True, "target": norm_target, "uninstalled": removed_from}, indent=2))
    return 0


