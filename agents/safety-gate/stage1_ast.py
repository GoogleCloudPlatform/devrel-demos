#!/usr/bin/env python3
"""
Stage 1 Python `ast` static scanner, heredoc/substitution parser, and local script inspector for `safety-gate`.

Contains:
- Local script resolver and conversation-edit detector (`_resolve_script_file`,
  `_was_file_modified_in_conversation`, `_inspect_local_script_static`).
- Heredoc and command-substitution parsers (`_strip_heredoc_bodies`, `_extract_heredoc_body`,
  `_extract_non_single_quoted_substitutions`, `_extract_pure_python_inline_or_heredoc`,
  `_is_pure_static_cat_heredoc_write`).
- Inline Python `ast` and hardened network scanners (`_is_py_exec_call`,
  `_python_ast_has_exec_or_network`, `_python_has_external_or_mutating_network`,
  `_python_ast_reaches_exec_sink`).
- Passive prose stripping and executable `sudo` detection (`_strip_passive_builtin_cli_segments`,
  `_has_executable_sudo`).
- Referenced script and non-shell argument context builders (`_extract_referenced_script_files`,
  `_build_referenced_scripts_context`, `_build_non_shell_tool_context`).
"""

import ast
import hashlib
import json
import os
import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PRIVATE_RULES: Optional[Any] = None

TRUSTED_CREDENTIAL_SCRIPT_NAMES = {
    "safety_gate.py",
    "cli_install.py",
    "stage1_paths.py",
    "stage1_ast.py",
    "stage1_shell.py",
    "llm_classifiers.py",
    "test_safety_gate.py",
    "test_corpus.py",
    *set(getattr(PRIVATE_RULES, "EXTRA_TRUSTED_SCRIPT_NAMES", ()) or ()),
}


def _win_preserve_backslashes(s: str) -> str:
    if os.name != "nt" or "\\" not in s:
        return s
    return re.sub(
        r"'[^']*'|\\(?=[A-Za-z0-9_.~/-])",
        lambda m: m.group(0) if m.group(0).startswith("'") else r"\\",
        s,
    )


def _resolve_script_file(raw_path: str, cwd: str) -> Optional[Path]:
    """Resolve a script path token relative to `cwd` (or `WORKSPACE_ROOT`)."""
    cleaned = raw_path.strip("'\"")
    if not cleaned or cleaned.startswith("-"):
        return None
    expanded = os.path.expanduser(cleaned)
    if not os.path.isabs(expanded) and not expanded.startswith(("/", "\\")):
        cand_cwd = Path(os.path.join(cwd or str(WORKSPACE_ROOT), expanded))
        if cand_cwd.exists():
            try:
                return cand_cwd.resolve()
            except Exception:
                pass
        cand_ws = Path(os.path.join(str(WORKSPACE_ROOT), expanded))
        if cand_ws.exists():
            try:
                return cand_ws.resolve()
            except Exception:
                pass
        expanded = str(cand_cwd)
    try:
        return Path(expanded).resolve()
    except Exception:
        return None


def _was_file_modified_in_conversation(file_path: Path, conv_id: str) -> bool:
    """
    Return True if `file_path` was created or modified via `write_to_file`,
    `replace_file_content`, `multi_replace_file_content`, or `notebook_edit`
    in the current conversation (recorded in `safety-gate.log`).
    """
    if not conv_id or not LOG_FILE.exists():
        return False
    short_conv = conv_id[:8]
    target_str = str(file_path)
    target_name = file_path.name
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
        for line in reversed(lines):
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("conv") != short_conv:
                continue
            if obj.get("tool") in (
                "write_to_file",
                "write_file",
                "replace_file_content",
                "multi_replace_file_content",
                "edit_file",
                "notebook_edit",
            ):
                logged_target = str(obj.get("target") or "")
                if logged_target == target_str or os.path.basename(logged_target) == target_name:
                    return True
    except Exception:
        pass
    return False


def _inspect_local_script_static(
    raw_path: str, cwd: str, conv_id: str = ""
) -> Tuple[str, str, str]:
    """
    Inspect a local script file (`python3 <file>`, `node <file>`, `sh/bash <file>`) before allowing execution:
    1. Always allow built-in CLI wrappers (`safety-gate`, plus any private overlay tools).
    2. If the script file exists on disk, read its contents and enforce Stage 1 hard-deny rules:
       - Accessing sensitive credentials (`credentials.enc`, `.encryption_key`, `.ssh/id_`) alongside
         network/transfer APIs (`urllib`, `requests`, `socket`, `curl`, `wget`, `scp`, `rsync`, `fetch`)
         -> immediate `deny`.
       - Executing `sudo`, disk formatting (`mkfs`, `diskutil erase`), or `git push --force` -> immediate `deny`.
    3. Route to Stage 2 (`needs_review` with full script file contents attached) if:
       - The script lives in `/tmp` or `/var/folders` (scratch/temp script), OR
       - The script was newly created or modified in this conversation (and is not a standard `test_*` suite), OR
       - The script contains external side-effect operations (`git push`, `gh pr create/merge`, `osascript`, `rm -rf`).
    """
    script_base = os.path.basename(raw_path.strip("'\""))
    builtin_scripts = {
        "safety-gate",
        *set(getattr(PRIVATE_RULES, "EXTRA_BUILTIN_SAFE_PROGS", ()) or ()),
    }
    if script_base in builtin_scripts:
        return "allow", "static-allow", f"Built-in tool `{script_base}`."

    resolved = _resolve_script_file(raw_path, cwd)
    is_temp_script = resolved is not None and _is_in_temp_root(resolved)
    is_test_file = (
        script_base.startswith("test_")
        or script_base.endswith(("_test.py", ".test.mjs", ".test.js"))
    )
    is_verified_trusted_copy = False
    is_self_signature_verified = False
    if resolved is not None and script_base in TRUSTED_CREDENTIAL_SCRIPT_NAMES:
        if resolved.is_file():
            canonical_mod = Path(__file__).resolve().parent / script_base
            try:
                if resolved == canonical_mod.resolve() or (
                    canonical_mod.is_file()
                    and resolved.read_bytes().replace(b"\r\n", b"\n")
                    == canonical_mod.read_bytes().replace(b"\r\n", b"\n")
                ):
                    is_verified_trusted_copy = True
                    is_self_signature_verified = True
            except Exception:
                pass
            if not is_verified_trusted_copy:
                extra_trusted = set(getattr(PRIVATE_RULES, "EXTRA_TRUSTED_SCRIPT_NAMES", ()) or ())
                if script_base in extra_trusted and not is_temp_script and _is_within_allowed_roots(str(resolved)):
                    is_verified_trusted_copy = True
                    is_self_signature_verified = True
                elif script_base in (
                    "safety_gate.py",
                    "cli_install.py",
                    "stage1_paths.py",
                    "stage1_ast.py",
                    "stage1_shell.py",
                    "llm_classifiers.py",
                    "test_safety_gate.py",
                ):
                    try:
                        head_txt = resolved.read_text(encoding="utf-8", errors="replace")[:65536]
                    except Exception:
                        head_txt = ""
                    sig_map = {
                        "safety_gate.py": ("def evaluate_tool_call(", "SENSITIVE_CREDENTIAL_PATTERNS"),
                        "cli_install.py": ("def handle_install_cli(", "def handle_doctor_cli("),
                        "stage1_paths.py": ("def _is_within_allowed_roots(", "PURE_READ_BINARIES"),
                        "stage1_ast.py": ("def _inspect_local_script_static(", "TRUSTED_CREDENTIAL_SCRIPT_NAMES"),
                        "stage1_shell.py": ("def evaluate_shell_static(", "_split_shell_segments"),
                        "llm_classifiers.py": ("def classify_command_with_gemini(", "def classify_with_heavy_gemini("),
                        "test_safety_gate.py": ("TestRecentCodingAgentCVEsAndAdvisories", "evaluate_shell_static"),
                    }
                    req_sigs = sig_map.get(script_base, ())
                    if req_sigs and all(s in head_txt for s in req_sigs):
                        is_self_signature_verified = True
                        if not is_temp_script and _is_within_allowed_roots(str(resolved)):
                            is_verified_trusted_copy = True
        elif script_base != "test_corpus.py" and not is_temp_script and _is_within_allowed_roots(str(resolved)):
            is_verified_trusted_copy = True
    if resolved is None or (not is_verified_trusted_copy and not _is_within_allowed_roots(str(resolved))):
        return (
            "needs_review",
            "needs-llm",
            f"Script `{raw_path}` is outside workspace roots or cannot be resolved.",
        )

    if resolved.exists() and resolved.is_file():
        try:
            content = resolved.read_text(encoding="utf-8", errors="replace")[:65536]
        except Exception:
            content = ""

        if content and not is_self_signature_verified:
            is_py_script = resolved.suffix == ".py"
            py_flags = _python_ast_has_exec_or_network(content) if is_py_script else None
            accesses_creds = any(re.search(pat, content) for pat in SENSITIVE_EXFIL_PATTERNS)
            if py_flags is not None and not py_flags[0] and not py_flags[1]:
                has_net_or_exfil = False
            else:
                has_net_or_exfil = bool(
                    re.search(
                        r"\b(urllib\.request|requests\.(get|post|put|request)|http\.client|socket\.|curl\b|wget\b|scp\b|rsync\b|nc\b|netcat\b|dig\b|nslookup\b|host\b|fetch\s*\()",
                        content,
                    )
                )
            if accesses_creds and has_net_or_exfil:
                return (
                    "deny",
                    "static-deny",
                    f"Blocked execution of `{script_base}`: script accesses sensitive credential/env files alongside network APIs.",
                )
            if not is_verified_trusted_copy and re.search(
                r"(?:^|['\"\s;&|])sudo\s+[A-Za-z0-9_./-]+", content
            ):
                sudo_exec = (
                    _python_ast_reaches_exec_sink(
                        content, r"(?<![A-Za-z0-9_])(?:/usr/bin/|/bin/)?sudo(?![A-Za-z0-9_])"
                    )
                    if is_py_script
                    else None
                )
                if sudo_exec is not False:
                    return (
                        "deny",
                        "static-deny",
                        f"Blocked execution of `{script_base}`: script invokes `sudo`.",
                    )
            if not is_verified_trusted_copy and re.search(
                r"\b(mkfs|diskutil\s+erase(Disk|Volume)|git\s+push\s+[^\n]*(--force|-f\b))", content
            ):
                destr_exec = (
                    _python_ast_reaches_exec_sink(
                        content, r"\b(mkfs|diskutil\s+erase(Disk|Volume)|git\s+push\s+[^\n]*(--force|-f\b))"
                    )
                    if is_py_script
                    else None
                )
                if destr_exec is not False:
                    return (
                        "deny",
                        "static-deny",
                        f"Blocked execution of `{script_base}`: script contains destructive disk or forced git push command.",
                    )
            if is_py_script and not is_verified_trusted_copy:
                ext_net_rsn = _python_has_external_or_mutating_network(content)
                if ext_net_rsn is not None:
                    return (
                        "force_ask",
                        "static-ask",
                        f"Script `{script_base}`: {ext_net_rsn}",
                    )
            if not is_test_file and re.search(
                r"\b(git\s+push\b|gh\s+(pr|issue|repo|release)\s+(create|merge|delete|close)\b|osascript\b|rm\s+-rf\b)",
                content,
            ):
                return (
                    "needs_review",
                    "needs-llm",
                    f"Script `{script_base}` contains mutating commands (`git push`, `gh`, `osascript`, or `rm -rf`) and requires semantic review of its contents.",
                )

        if is_test_file and not is_verified_trusted_copy:
            return (
                "needs_review",
                "needs-llm",
                f"Test script `{script_base}` executes arbitrary test code and requires Stage 2 semantic review.",
            )

        if is_temp_script and not is_verified_trusted_copy:
            return (
                "needs_review",
                "needs-llm",
                f"Temporary script `{resolved}` in `/tmp` requires semantic inspection of its file contents.",
            )

        if (
            not is_test_file
            and not is_verified_trusted_copy
            and _was_file_modified_in_conversation(resolved, conv_id)
        ):
            return (
                "needs_review",
                "needs-llm",
                f"Script `{script_base}` was created or modified in this conversation and requires semantic inspection of its contents.",
            )

        return "allow", "static-allow", f"Verified workspace script `{script_base}`."

    if is_test_file and not is_verified_trusted_copy:
        return (
            "needs_review",
            "needs-llm",
            f"Test script `{script_base}` executes arbitrary test code and requires Stage 2 semantic review.",
        )

    if is_temp_script:
        return (
            "needs_review",
            "needs-llm",
            f"Temporary script `{raw_path}` requires semantic review.",
        )

    return "allow", "static-allow", f"Workspace script `{script_base}`."


def _strip_heredoc_bodies(cmd: str) -> Tuple[str, bool]:
    """
    Strip heredoc body lines (`<< 'EOF' ... EOF` or `<< EOF ... EOF`) from `cmd`
    while keeping the command header line intact (so header redirections like
    `cat << 'EOF' > ~/.zshrc` are still inspected).
    Returns `(cmd_without_heredoc_bodies, has_heredoc)`.
    """
    lines = cmd.splitlines()
    if len(lines) <= 1 or "<<" not in cmd:
        return cmd, False

    out_lines: List[str] = []
    in_heredoc = False
    delim = ""
    has_heredoc = False

    for line in lines:
        if in_heredoc:
            if line.strip() == delim:
                in_heredoc = False
                delim = ""
            continue

        out_lines.append(line)
        # Look for unquoted `<<` heredoc operator on this line
        unq_line = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", '""', line)
        if "<<" in unq_line and "<<<" not in unq_line:
            m = re.search(
                r"<<[-~]?\s*(?:'([A-Za-z0-9_]+)'|\"([A-Za-z0-9_]+)\"|\\?([A-Za-z0-9_]+))",
                line,
            )
            if m:
                delim = m.group(1) or m.group(2) or m.group(3) or ""
                if delim:
                    in_heredoc = True
                    has_heredoc = True

    return "\n".join(out_lines), has_heredoc


def _extract_non_single_quoted_substitutions(cmd: str) -> List[str]:
    """
    Extract command substitutions `$(...)` and backticks `` `...` `` that appear outside
    single quotes (including unquoted and double-quoted contexts where the shell expands them).
    """
    subs: List[str] = []
    in_single = False
    in_double = False
    escape = False
    i = 0
    n = len(cmd)

    while i < n:
        ch = cmd[i]
        if escape:
            escape = False
            i += 1
            continue
        if ch == "\\" and not in_single:
            escape = True
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue

        if not in_single:
            if ch == "$" and i + 1 < n and cmd[i + 1] == "(":
                depth = 1
                j = i + 2
                sub_single = False
                sub_double = False
                sub_esc = False
                while j < n and depth > 0:
                    c2 = cmd[j]
                    if sub_esc:
                        sub_esc = False
                        j += 1
                        continue
                    if c2 == "\\" and not sub_single:
                        sub_esc = True
                        j += 1
                        continue
                    if c2 == "'" and not sub_double:
                        sub_single = not sub_single
                    elif c2 == '"' and not sub_single:
                        sub_double = not sub_double
                    elif not sub_single and not sub_double:
                        if c2 == "(":
                            depth += 1
                        elif c2 == ")":
                            depth -= 1
                            if depth == 0:
                                break
                    j += 1
                subs.append(cmd[i + 2 : j])
                i = j + 1
                continue
            if ch == "`":
                j = i + 1
                sub_esc = False
                while j < n:
                    c2 = cmd[j]
                    if sub_esc:
                        sub_esc = False
                        j += 1
                        continue
                    if c2 == "\\":
                        sub_esc = True
                        j += 1
                        continue
                    if c2 == "`":
                        break
                    j += 1
                subs.append(cmd[i + 1 : j])
                i = j + 1
                continue

        i += 1
    return subs


_PY_EXEC_MODULES = frozenset({"subprocess", "pty", "commands", "ctypes", "importlib"})
_PY_NET_MODULES = frozenset(
    {"urllib", "requests", "http", "httpx", "aiohttp", "socket", "ssl", "ftplib", "smtplib", "paramiko", "websocket", "websockets"}
)
_PY_EXEC_FUNCS = frozenset(
    {
        "Popen",
        "run",
        "call",
        "check_call",
        "check_output",
        "getoutput",
        "getstatusoutput",
        "system",
        "popen",
        "exec",
        "eval",
        "compile",
        "__import__",
    }
)


def _is_py_exec_call(node: ast.Call) -> bool:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id in _PY_EXEC_FUNCS or fn.id.startswith(("exec", "spawn"))
    if isinstance(fn, ast.Attribute):
        attr = fn.attr
        root_name = fn.value.id if isinstance(fn.value, ast.Name) else ""
        if root_name in ("subprocess", "pty", "commands"):
            return True
        if root_name == "os" and (attr in ("system", "popen") or attr.startswith(("exec", "spawn", "posix_spawn"))):
            return True
        if attr in (_PY_EXEC_FUNCS - {"compile"}) or attr.startswith(("exec", "spawn", "posix_spawn")):
            return True
    return False


def _python_ast_has_exec_or_network(py_src: str) -> Optional[Tuple[bool, bool]]:
    """
    Parse `py_src` via stdlib `ast.parse` without executing anything.
    Returns `(has_exec_sink, has_network_sink)`, or `None` if `py_src` is not valid Python.
    """
    try:
        tree = ast.parse(py_src)
    except Exception:
        return None
    has_exec = False
    has_net = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".", 1)[0]
                if top in _PY_EXEC_MODULES:
                    has_exec = True
                if top in _PY_NET_MODULES:
                    has_net = True
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".", 1)[0]
            if top in _PY_EXEC_MODULES:
                has_exec = True
            if top in _PY_NET_MODULES:
                has_net = True
            for alias in node.names:
                if alias.name in _PY_EXEC_FUNCS or alias.name.startswith(("exec", "spawn")):
                    has_exec = True
        elif isinstance(node, ast.Call):
            if _is_py_exec_call(node):
                has_exec = True
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in ("getattr", "globals", "locals", "vars"):
                has_exec = True
                has_net = True
            if isinstance(fn, ast.Attribute) and fn.attr in ("urlopen", "urlretrieve", "HTTPConnection", "HTTPSConnection", "create_connection"):
                has_net = True
    return has_exec, has_net


def _python_has_external_or_mutating_network(py_src: str) -> Optional[str]:
    """
    Inspect Python source code (inline `-c`, heredoc, or `.py` script file) for network client
    libraries (`urllib.request`, `http.client`, `requests`, `httpx`, `aiohttp`, `socket`).
    Returns a Stage 3 escalation reason (`force_ask`) if the code imports/uses any of these
    libraries AND does NOT exclusively perform read-only GET requests to `localhost` / `127.0.0.1` / `::1`
    (or uses raw `socket` connections or non-GET methods/payloads).
    """
    if not py_src or not py_src.strip():
        return None
    if not re.search(r"\b(urllib\.request|http\.client|requests|httpx|aiohttp|socket)\b", py_src):
        return None
    ast_flags = _python_ast_has_exec_or_network(py_src)
    if ast_flags is not None and not ast_flags[1]:
        return None
    if re.search(r"\bsocket\b", py_src):
        return "Python code imports `socket` and requires Stage 3 full-context verification."
    if re.search(
        r"\.\s*(post|put|delete|patch)\s*\(|\bmethod\s*=\s*['\"](POST|PUT|DELETE|PATCH)['\"]|\b(data|json)\s*=",
        py_src,
        re.I,
    ):
        return "Python network client uses non-GET method or request body payload and requires Stage 3 full-context verification."
    urls = re.findall(r"https?://(\[[^\]]+\](?::\d+)?|[^\s/'\"`)\]]+)", py_src, re.I)
    if not urls:
        return "Python code imports network client libraries without a static localhost target and requires Stage 3 full-context verification."
    local_hosts = {"localhost", "127.0.0.1", "::1", "[::1]"}
    for raw_host in urls:
        h = raw_host.lower()
        if h.startswith("[") and "]" in h:
            h = h[: h.index("]") + 1]
        elif ":" in h and h != "::1":
            h = h.split(":", 1)[0]
        if h not in local_hosts:
            return f"Python network client targets non-localhost host (`{raw_host}`) and requires Stage 3 full-context verification."
    return None


def _python_ast_reaches_exec_sink(py_src: str, pattern_re: str) -> Optional[bool]:
    """
    Return `False` when `py_src` parses cleanly and `pattern_re` does NOT appear inside any
    process/code execution `Call` subtree or any variable/function transitively referenced by one.
    Returns `True` if reachable (or dynamic reflection is present), and `None` on `SyntaxError`.
    """
    try:
        tree = ast.parse(py_src)
    except Exception:
        return None

    defs_by_name: Dict[str, List[ast.AST]] = {}
    exec_calls: List[ast.Call] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in ("getattr", "globals", "locals", "vars"):
                return True
            if _is_py_exec_call(node):
                exec_calls.append(node)
        elif isinstance(node, ast.Assign):
            for tgt in node.targets:
                for sub in ast.walk(tgt):
                    if isinstance(sub, ast.Name):
                        defs_by_name.setdefault(sub.id, []).append(node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    defs_by_name.setdefault(sub.id, []).append(node.value)
        elif isinstance(node, ast.AugAssign):
            for sub in ast.walk(node.target):
                if isinstance(sub, ast.Name):
                    defs_by_name.setdefault(sub.id, []).append(node.value)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs_by_name.setdefault(node.name, []).append(node)

    if not exec_calls:
        return False

    rx = re.compile(pattern_re)
    visited_names: set[str] = set()
    queue: List[ast.AST] = list(exec_calls)

    while queue:
        cur = queue.pop()
        for sub in ast.walk(cur):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if rx.search(sub.value):
                    return True
            elif isinstance(sub, ast.Name) and sub.id not in visited_names:
                visited_names.add(sub.id)
                for def_node in defs_by_name.get(sub.id, ()):
                    queue.append(def_node)
    return False


def _extract_heredoc_body(cmd: str) -> Optional[Tuple[str, str, bool]]:
    """
    For a single-heredoc command, return `(header_without_body, body_text, quoted_delimiter)`
    or `None` if `cmd` does not contain a single heredoc.
    """
    lines = cmd.splitlines()
    if len(lines) <= 1 or "<<" not in cmd:
        return None
    hdr_lines: List[str] = []
    body_lines: List[str] = []
    in_hd = False
    delim = ""
    quoted_delim = False
    found_count = 0
    for line in lines:
        if in_hd:
            if line.strip() == delim:
                in_hd = False
                delim = ""
            else:
                body_lines.append(line)
            continue
        hdr_lines.append(line)
        unq_line = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", '""', line)
        if "<<" in unq_line and "<<<" not in unq_line:
            m = re.search(
                r"<<[-~]?\s*(?:'([A-Za-z0-9_]+)'|\"([A-Za-z0-9_]+)\"|\\([A-Za-z0-9_]+)|([A-Za-z0-9_]+))",
                line,
            )
            if m:
                delim = m.group(1) or m.group(2) or m.group(3) or m.group(4) or ""
                if delim:
                    quoted_delim = bool(m.group(1) or m.group(2) or m.group(3))
                    in_hd = True
                    found_count += 1
    if found_count != 1 or in_hd:
        return None
    return "\n".join(hdr_lines), "\n".join(body_lines), quoted_delim


def _extract_pure_python_inline_or_heredoc(cmd: str) -> Optional[str]:
    """
    If `cmd` is a single `python`/`python3` command (`python3 - << 'EOF'` or `python3 -c '...'`)
    with no shell command substitutions outside single quotes, return the Python source string.
    """
    hd = _extract_heredoc_body(cmd)
    if hd is not None:
        hdr, body, quoted_delim = hd
        if not quoted_delim or _extract_non_single_quoted_substitutions(hdr):
            return None
        segs = _split_shell_segments(hdr)
        if len(segs) != 1:
            return None
        try:
            toks = _strip_leading_env_and_wrappers(shlex.split(segs[0], posix=True))
        except ValueError:
            return None
        if toks and os.path.basename(toks[0]) in ("python", "python3"):
            return body
        return None

    if _extract_non_single_quoted_substitutions(cmd):
        return None
    segs = _split_shell_segments(cmd)
    if len(segs) != 1:
        return None
    try:
        toks = _strip_leading_env_and_wrappers(shlex.split(segs[0], posix=True))
    except ValueError:
        return None
    if len(toks) >= 3 and os.path.basename(toks[0]) in ("python", "python3") and "-c" in toks[1:]:
        c_idx = toks.index("-c", 1)
        if c_idx + 1 < len(toks):
            return toks[c_idx + 1]
    return None


def _is_pure_static_cat_heredoc_write(cmd: str) -> bool:
    """Return True if `cmd` is a single `cat << 'EOF' > <path>` static file write with quoted delimiter."""
    hd = _extract_heredoc_body(cmd)
    if hd is None:
        return False
    hdr, _, quoted_delim = hd
    if not quoted_delim or _extract_non_single_quoted_substitutions(hdr):
        return False
    segs = _split_shell_segments(hdr)
    if len(segs) != 1:
        return False
    try:
        toks = _strip_leading_env_and_wrappers(shlex.split(segs[0], posix=True))
    except ValueError:
        return False
    return bool(toks and os.path.basename(toks[0]) == "cat")


_PASSIVE_PROSE_CLI_BINARIES = frozenset(
    set(getattr(PRIVATE_RULES, "EXTRA_PASSIVE_PROSE_BINARIES", ()) or ())
)
_PASSIVE_PATH_FLAGS: Tuple[str, ...] = (
    "--todo-file",
    "--prompt-file",
    "--attach",
    "-d",
    "--dir",
    *tuple(getattr(PRIVATE_RULES, "EXTRA_PASSIVE_PATH_FLAGS", ()) or ()),
)
_PASSIVE_PATH_EQ_PREFIXES: Tuple[str, ...] = tuple(
    f"{fl}=" for fl in _PASSIVE_PATH_FLAGS if fl.startswith("--")
)


def _strip_passive_builtin_cli_segments(cmd: str) -> str:
    """
    Strip passive quoted prose arguments passed to built-in orchestration/notification CLIs
    when the segment has no shell command substitution or file
    output redirection, preventing prose mentions of `.env` or `credentials.enc` inside task
    descriptions from triggering Stage 1 shell exfiltration regexes.
    """
    if not cmd:
        return cmd
    segs = _split_shell_segments(cmd)
    if not segs:
        return cmd
    changed = False
    kept: List[str] = []
    for seg in segs:
        s_clean = seg.strip()
        if not s_clean:
            continue
        if "$(" in s_clean or "`" in s_clean or "${" in s_clean or _find_unquoted_redirection(s_clean):
            kept.append(seg)
            continue
        try:
            toks = shlex.split(s_clean, posix=True)
        except ValueError:
            kept.append(seg)
            continue
        toks = _strip_leading_env_and_wrappers(toks)
        if not toks:
            continue
        prog = os.path.basename(toks[0])
        if prog in _PASSIVE_PROSE_CLI_BINARIES:
            changed = True
            safe_toks: List[str] = [toks[0]]
            idx_t = 1
            while idx_t < len(toks):
                t = toks[idx_t]
                if t in _PASSIVE_PATH_FLAGS and idx_t + 1 < len(toks):
                    safe_toks.extend([t, toks[idx_t + 1]])
                    idx_t += 2
                    continue
                if t.startswith(_PASSIVE_PATH_EQ_PREFIXES):
                    safe_toks.append(t)
                idx_t += 1
            kept.append(" ".join(shlex.quote(x) for x in safe_toks))
        else:
            kept.append(seg)
    return " ; ".join(kept) if changed else cmd


def _has_executable_sudo(cmd: str, depth: int = 0) -> bool:
    """
    Return True if `cmd` executes `sudo` (as a direct or wrapped command, in a compound chain,
    inside `$(...)` or backticks, or inside a quoted string passed to an execution sink such as
    `bash -c`, `sh -c`, `zsh -c`, `eval`, `ssh`, `tmux`, `xargs`, `find -exec`, or `python -c`
    with `subprocess`/`os.system`/`exec`).
    Ignores passive quoted text (e.g. `echo "..."`, `grep "..."`, or a
    Python string constant not passed to `subprocess`/`os.system`/`exec`).
    """
    if "sudo" not in cmd:
        return False
    if depth > 4:
        return True

    for sub in _extract_non_single_quoted_substitutions(cmd):
        if "sudo" in sub and _has_executable_sudo(sub, depth + 1):
            return True

    cmd_without_heredoc, has_heredoc = _strip_heredoc_bodies(cmd)
    if has_heredoc and "sudo" in cmd:
        for hdr_seg in _split_shell_segments(cmd_without_heredoc):
            try:
                hdr_toks = _strip_leading_env_and_wrappers(shlex.split(hdr_seg, posix=True))
            except ValueError:
                return True
            if not hdr_toks:
                continue
            hdr_prog = os.path.basename(hdr_toks[0])
            if hdr_prog in (
                "sh",
                "bash",
                "zsh",
                "dash",
                "ksh",
                "csh",
                "tcsh",
                "fish",
                "eval",
                "ssh",
                "at",
                "batch",
                "crontab",
            ):
                if re.search(r"(?:^|[;&|\n(`]\s*)(?:/usr/bin/|/bin/)?sudo(?:\s+|$)", cmd):
                    return True
            if hdr_prog in ("python", "python3") and re.search(
                r"\b(subprocess|os\s*\.\s*(system|popen|exec\w*|spawn\w*)|pty\s*\.\s*spawn|commands\s*\.|Popen|check_output|check_call)\b",
                cmd,
            ):
                hd_info = _extract_heredoc_body(cmd)
                if hd_info is not None and hd_info[2]:
                    ast_hit = _python_ast_reaches_exec_sink(
                        hd_info[1], r"(?<![A-Za-z0-9_])(?:/usr/bin/|/bin/)?sudo(?![A-Za-z0-9_])"
                    )
                    if ast_hit is False:
                        continue
                return True

    segments = _split_shell_segments(cmd_without_heredoc)
    for seg in segments:
        if "sudo" not in seg:
            continue
        seg_clean = re.sub(r"(?:(?<=\s)|^|\b[12])>>?\s*/dev/null\b|\b2>&1\b|&>>?\s*/dev/null\b", "", seg).strip()
        if not seg_clean:
            continue
        try:
            tokens = shlex.split(seg_clean, posix=True)
        except ValueError:
            if re.search(r"(?:^|[;&|\n(`]\s*)(?:/usr/bin/|/bin/)?sudo(?:\s+|$)", seg_clean):
                return True
            continue

        tokens = _strip_leading_env_and_wrappers(tokens)
        if not tokens:
            continue

        prog = os.path.basename(tokens[0])
        if prog == "sudo":
            return True

        if prog.startswith(("subprocess.", "os.system", "os.popen", "os.exec", "os.spawn")) and re.search(
            r"(?<![A-Za-z0-9_])(?:/usr/bin/|/bin/)?sudo(?![A-Za-z0-9_])", seg_clean
        ):
            return True

        if prog in ("eval", "exec", "source", "."):
            inner = " ".join(t for t in tokens[1:] if not t.startswith("-"))
            if _has_executable_sudo(inner, depth + 1):
                return True

        if prog in ("sh", "bash", "zsh", "dash", "ksh", "csh", "tcsh", "fish"):
            for tok in tokens[1:]:
                if "sudo" in tok and (
                    _has_executable_sudo(tok, depth + 1)
                    or bool(re.search(r"(?:^|[;&|\n(`]\s*)(?:/usr/bin/|/bin/)?sudo(?:\s+|$)", tok))
                ):
                    return True

        if prog in ("ssh", "xargs", "watch", "parallel", "at", "batch"):
            for tok in tokens[1:]:
                if os.path.basename(tok) == "sudo" or (
                    "sudo" in tok and _has_executable_sudo(tok, depth + 1)
                ):
                    return True

        if prog == "find" and any(t in ("-exec", "-execdir", "-ok", "-okdir") for t in tokens[1:]):
            for tok in tokens[1:]:
                if os.path.basename(tok) == "sudo" or (
                    "sudo" in tok and _has_executable_sudo(tok, depth + 1)
                ):
                    return True

        if prog == "tmux":
            tmux_sub = next((t for t in tokens[1:] if not t.startswith("-")), "")
            if tmux_sub in (
                "new-session",
                "new",
                "send-keys",
                "send",
                "split-window",
                "splitw",
                "new-window",
                "neww",
                "run-shell",
                "run",
            ):
                for tok in tokens[1:]:
                    if "sudo" in tok and _has_executable_sudo(tok, depth + 1):
                        return True

        if prog in ("python", "python3"):
            py_code = " ".join(tokens[1:])
            if re.search(
                r"(?<![A-Za-z0-9_])(?:/usr/bin/|/bin/)?sudo(?![A-Za-z0-9_])", py_code
            ) and re.search(
                r"\b(subprocess|os\s*\.\s*(system|popen|exec\w*|spawn\w*)|pty\s*\.\s*spawn|commands\s*\.|Popen|check_output|check_call)\b",
                py_code,
            ):
                if "-c" in tokens[1:]:
                    c_idx = tokens.index("-c", 1)
                    if c_idx + 1 < len(tokens):
                        ast_hit = _python_ast_reaches_exec_sink(
                            tokens[c_idx + 1], r"(?<![A-Za-z0-9_])(?:/usr/bin/|/bin/)?sudo(?![A-Za-z0-9_])"
                        )
                        if ast_hit is False:
                            continue
                return True

        if prog in ("node", "ruby", "perl", "php", "osascript"):
            script_code = " ".join(tokens[1:])
            if re.search(
                r"(?<![A-Za-z0-9_])(?:/usr/bin/|/bin/)?sudo(?![A-Za-z0-9_])", script_code
            ) and re.search(
                r"\b(child_process|execSync|execFile|spawnSync|spawn|system|popen|do\s+shell\s+script)\b|`",
                script_code,
            ):
                return True

    return False



REFERENCE_FILE_EXTS = (
    ".py",
    ".mjs",
    ".js",
    ".cjs",
    ".sh",
    ".zsh",
    ".bash",
    ".rb",
    ".pl",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".plist",
    ".html",
    ".css",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".swift",
    ".sql",
)

REFERENCE_DOTFILE_NAMES = {
    ".zshrc",
    ".bashrc",
    ".zprofile",
    ".bash_profile",
    ".gitconfig",
    "config",
    "hooks.json",
    "Makefile",
    "Dockerfile",
}


def _extract_referenced_script_files(cmd: str, cwd: str) -> List[Path]:
    """
    Find existing local script, config, or reference files referenced in `cmd`
    so Stage 2 and Stage 3 can inspect their contents and include their SHA-256 in the cache key.
    Never includes sensitive credential files.
    """
    found: List[Path] = []
    seen: set[str] = set()
    try:
        tokens = shlex.split(_win_preserve_backslashes(cmd), posix=True)
    except ValueError:
        tokens = cmd.split()

    candidates: List[str] = []
    for idx, tok in enumerate(tokens):
        prev_tok = tokens[idx - 1] if idx > 0 else ""
        if prev_tok in ("-c", "-e", "-p", "--eval", "--print"):
            continue
        cleaned = tok.strip("'\"`;|&()")
        if (
            not cleaned
            or cleaned.startswith("-")
            or len(cleaned) > 240
            or "\n" in cleaned
            or "\r" in cleaned
            or "\x00" in cleaned
            or any(ch.isspace() for ch in cleaned)
        ):
            continue
        prev_prog = os.path.basename(prev_tok) if idx > 0 else ""
        base_name = os.path.basename(cleaned)
        is_candidate = (
            cleaned.endswith(REFERENCE_FILE_EXTS)
            or base_name in REFERENCE_DOTFILE_NAMES
            or prev_prog
            in (
                "python",
                "python3",
                "node",
                "sh",
                "bash",
                "zsh",
                "ruby",
                "perl",
                "cat",
                "head",
                "tail",
                "sed",
                "awk",
                "jq",
                "cp",
                "mv",
                "rm",
                "chmod",
                "source",
                ".",
            )
            or "/" in cleaned
            or "\\" in cleaned
            or cleaned.startswith("~")
        )
        if is_candidate:
            candidates.append(cleaned)

    # Also extract explicit path literals inside inline scripts (`~/...`, `<home>/...`, `/tmp/...`)
    _home_alt = "|".join(re.escape(str(h)) for h in HOMES)
    for match in re.findall(rf"(?:~|{_home_alt}|/tmp|/private/tmp)/[A-Za-z0-9._/-]{{1,200}}", cmd):
        candidates.append(match)

    for cand in candidates:
        resolved = _resolve_script_file(cand, cwd)
        if not resolved:
            continue
        try:
            if not resolved.exists() or not resolved.is_file():
                continue
        except OSError:
            continue
        key = str(resolved)
        if _is_sensitive_credential_path(key) or _is_sensitive_credential_path(cand):
            continue
        if key not in seen:
            seen.add(key)
            found.append(resolved)
    return found


def _build_referenced_scripts_context(
    cmd: str, cwd: str, conv_id: str = "", max_files: int = 4, max_chars_per_file: int = 3500
) -> Tuple[str, str]:
    """
    Return `(scripts_hash_fingerprint, formatted_prompt_section)` for local script and reference
    files referenced in `cmd`.
    """
    files = _extract_referenced_script_files(cmd, cwd)
    if not files:
        return "", ""

    hash_parts: List[str] = []
    sections: List[str] = []
    for path_obj in files[:max_files]:
        try:
            if _is_sensitive_credential_path(str(path_obj)):
                continue
            raw_bytes = path_obj.read_bytes()[:65536]
            if b"\x00" in raw_bytes[:1024]:
                continue
            file_hash = hashlib.sha256(raw_bytes).hexdigest()[:16]
            modified_in_conv = _was_file_modified_in_conversation(path_obj, conv_id)
            hash_parts.append(f"{path_obj}:{file_hash}:mod={int(modified_in_conv)}")
            text = raw_bytes.decode("utf-8", errors="replace")
            snippet = text[:max_chars_per_file]
            if len(text) > max_chars_per_file:
                snippet += "\n... [truncated]"
            mod_tag = " (MODIFIED IN THIS CONVERSATION)" if modified_in_conv else ""
            sections.append(
                f"--- File: {path_obj} (sha256={file_hash}{mod_tag}) ---\n{snippet}"
            )
        except Exception:
            continue

    if not sections:
        return "", ""
    return "|".join(hash_parts), "\n\nReferenced script file contents:\n" + "\n\n".join(sections)



def _build_non_shell_tool_context(tool_name: str, args: Dict[str, Any], conv_id: str = "") -> Tuple[str, str]:
    """
    Build reference file and argument context when a non-shell tool (`write_to_file`,
    `write_file`, `replace_file_content`, `multi_replace_file_content`, `edit_file`,
    `notebook_edit`, `call_mcp_tool`) is escalated to Stage 3.
    """
    serialized_args = json.dumps(args, ensure_ascii=False)[:4000]
    args_fp = hashlib.sha256(serialized_args.encode("utf-8")).hexdigest()[:16]
    sections: List[str] = [f"Tool Arguments (`{tool_name}`):\n{serialized_args}"]

    target = str(args.get("TargetFile") or args.get("Path") or args.get("NotebookPath") or "").strip()
    if target and not _is_sensitive_credential_path(target):
        try:
            resolved = Path(os.path.expanduser(target)).resolve()
            if resolved.exists() and resolved.is_file():
                raw_bytes = resolved.read_bytes()[:32768]
                if b"\x00" not in raw_bytes[:1024]:
                    file_hash = hashlib.sha256(raw_bytes).hexdigest()[:16]
                    args_fp = f"{args_fp}:{file_hash}"
                    existing_text = raw_bytes.decode("utf-8", errors="replace")[:3000]
                    sections.append(
                        f"--- Existing File on Disk: {resolved} (sha256={file_hash}) ---\n{existing_text}"
                    )
        except Exception:
            pass

    return args_fp, "\n\n" + "\n\n".join(sections)


