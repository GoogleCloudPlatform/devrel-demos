#!/usr/bin/env python3
"""
Stage 1 shell tokenizer, segment splitter, and static command evaluator (`evaluate_shell_static`) for `safety-gate`.

Contains:
- Shell segment splitter, environment/wrapper stripper, and unquoted redirection detector
  (`_split_shell_segments`, `_strip_leading_env_and_wrappers`, `_find_unquoted_redirection`).
- Git, GitHub CLI, `sed`, `tar`, and pure-read binary flag analyzers (`_has_dangerous_git_flags`,
  `_has_sed_exec_or_inplace`, `_has_pure_read_binary_exec_flag`, `_has_tar_exec_flag`,
  `_is_readonly_git_tokens`, `_is_readonly_gh_tokens`).
- Main Stage 1 shell static evaluator (`evaluate_shell_static`).
"""

import os
import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PRIVATE_RULES: Optional[Any] = None

def _split_shell_segments(cmd: str) -> List[str]:
    """
    Split a shell command string on top-level operators (;, &&, ||, |, newline)
    while respecting single and double quotes.
    """
    segments: List[str] = []
    buf: List[str] = []
    in_single = False
    in_double = False
    escape = False
    i = 0
    n = len(cmd)

    while i < n:
        ch = cmd[i]
        if escape:
            buf.append(ch)
            escape = False
            i += 1
            continue
        if ch == "\\" and not in_single:
            buf.append(ch)
            escape = True
            i += 1
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            buf.append(ch)
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            i += 1
            continue

        if not in_single and not in_double:
            if ch in (";", "\n"):
                seg = "".join(buf).strip()
                if seg:
                    segments.append(seg)
                buf = []
                i += 1
                continue
            if ch in ("&", "|"):
                if i + 1 < n and cmd[i + 1] == ch:
                    seg = "".join(buf).strip()
                    if seg:
                        segments.append(seg)
                    buf = []
                    i += 2
                    continue
                elif ch == "|" or (
                    ch == "&"
                    and (i == 0 or cmd[i - 1] not in (">", "<"))
                    and (i + 1 >= n or cmd[i + 1] != ">")
                ):
                    seg = "".join(buf).strip()
                    if seg:
                        segments.append(seg)
                    buf = []
                    i += 1
                    continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        segments.append(tail)
    return segments


def _strip_leading_env_and_wrappers(tokens: List[str]) -> List[str]:
    """Strip leading shell control keywords, KEY=VAL env assignments, and `env` / `command` / `time` wrappers."""
    idx = 0
    n = len(tokens)
    while idx < n:
        tok = tokens[idx]
        if tok in ("if", "then", "else", "elif", "do", "while", "until", "!"):
            idx += 1
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", tok):
            idx += 1
            continue
        if tok == "timeout":
            idx += 1
            while idx < n and tokens[idx].startswith("-"):
                if tokens[idx] in ("-k", "--kill-after", "-s", "--signal") and idx + 1 < n:
                    idx += 2
                else:
                    idx += 1
            if idx < n:
                idx += 1
            continue
        if tok == "nice":
            idx += 1
            while idx < n and tokens[idx].startswith("-"):
                if tokens[idx] == "-n" and idx + 1 < n:
                    idx += 2
                else:
                    idx += 1
            continue
        if tok in ("env", "command", "time", "nohup", "stdbuf", "builtin"):
            idx += 1
            while idx < n and tokens[idx].startswith("-"):
                idx += 1
            continue
        break
    return tokens[idx:]


def _find_all_unquoted_redirections(seg: str) -> List[str]:
    """
    Find all target paths of unquoted output redirections (`>` or `>>`) in `seg`.
    Ignores `>` inside single or double quotes, `<>`, and fd duplications like `>&2` or `2>&1`.
    """
    targets: List[str] = []
    in_single = False
    in_double = False
    escape = False
    i = 0
    n = len(seg)

    while i < n:
        ch = seg[i]
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

        if not in_single and not in_double and ch == ">":
            if i > 0 and seg[i - 1] == "<":
                i += 1
                continue
            j = i + 1
            if j < n and seg[j] == ">":
                j += 1
            if j < n and seg[j] == "&":
                i = j + 1
                continue
            while j < n and seg[j].isspace():
                j += 1
            if j >= n or seg[j] == "&":
                i = j + 1
                continue
            end = j
            while end < n and not seg[end].isspace() and seg[end] not in (";", "&", "|", ">"):
                end += 1
            t = seg[j:end].strip("'\"")
            if t:
                targets.append(t)
            i = end
            continue
        i += 1
    return targets


def _find_unquoted_redirection(seg: str) -> Optional[str]:
    """Return the first unquoted output redirection target in `seg`, or `None`."""
    targets = _find_all_unquoted_redirections(seg)
    return targets[0] if targets else None


def _has_dangerous_git_flags(tokens: List[str]) -> Optional[str]:
    """
    Check a `git` token list for command-execution flags or dangerous `-c key=val` overrides
    (CVE-2025-66032 `--upload-pa*` flag abbreviation & CVE-2026-26268 `git -c core.fsmonitor=...`).
    Returns a human-readable reason if a dangerous flag is present, or None if clean.
    """
    idx = 1
    n = len(tokens)
    while idx < n:
        tok = tokens[idx]
        low = tok.lower()
        if low in ("-c", "--config-env") and idx + 1 < n:
            kv = tokens[idx + 1].lower().strip()
            key = kv.split("=", 1)[0].strip()
            if key.startswith(DANGEROUS_GIT_CONFIG_PREFIXES):
                return f"Executable `git {tok} {tokens[idx + 1]}` configuration override requires full-context verification (CVE-2026-26268)."
            idx += 2
            continue
        if low.startswith("--config-env="):
            kv = low.split("=", 1)[1].strip()
            key = kv.split("=", 1)[0].strip()
            if key.startswith(DANGEROUS_GIT_CONFIG_PREFIXES):
                return f"Executable `git {tok}` configuration override requires full-context verification (CVE-2026-26268)."
        if low.startswith("-c") and len(low) > 2:
            kv = low[2:].lstrip("=").strip()
            key = kv.split("=", 1)[0].strip()
            if key.startswith(DANGEROUS_GIT_CONFIG_PREFIXES):
                return f"Executable `git {tok}` configuration override requires full-context verification (CVE-2026-26268)."
        if low.startswith(("--upload-pa", "--receive-pa", "--exec")):
            return f"Git flag `{tok}` can execute arbitrary external commands (CVE-2025-66032) and requires confirmation."
        idx += 1
    return None


def _has_sed_exec_or_inplace(tokens: List[str]) -> bool:
    """Return True if `sed` tokens use `-i`, `-f`/`--file`, or the GNU sed `e` command-execution modifier (CVE-2025-66032)."""
    for tok in tokens[1:]:
        if (
            tok in ("-i", "-f")
            or tok.startswith(("-i", "-f", "--in-place", "--file"))
            or (tok.startswith("-") and not tok.startswith("--") and any(c in tok[1:] for c in ("i", "f")))
        ):
            return True
        if re.search(
            r"(?:^|;|/)s(?P<d>[^A-Za-z0-9\s]).*?(?P=d).*?(?P=d)[gGpPiImM0-9]*e(?:\b|;|$)|(?:^|;)\s*e\s+\S",
            tok,
        ):
            return True
    return False


def _has_pure_read_binary_exec_flag(prog: str, tokens: List[str]) -> bool:
    """
    Return True if a command in `PURE_READ_BINARIES` passes a flag that executes an external binary
    (CVE-2025-66032: `sort --compress-program=...`, `rg --pre=...` / `--pre-glob`).
    """
    if prog == "sort":
        return any(t == "--compress-program" or t.startswith("--compress-program=") for t in tokens[1:])
    if prog == "rg":
        return any(
            t in ("--pre", "--pre-glob") or t.startswith(("--pre=", "--pre-glob="))
            for t in tokens[1:]
        )
    return False


def _has_tar_exec_flag(tokens: List[str]) -> bool:
    """Return True if `tar` tokens include flags that execute external commands (`--checkpoint-action`, `--to-command`, `--use-compress-program`, `-I`)."""
    for tok in tokens[1:]:
        if tok == "-I" or tok.startswith(
            (
                "--checkpoint-action",
                "--to-command",
                "--use-compress-program",
            )
        ):
            return True
    return False


def _is_readonly_git_tokens(tokens: List[str]) -> bool:
    """Return True if a `git` command token list is strictly read-only."""
    if _has_dangerous_git_flags(tokens) is not None:
        return False
    git_idx = 1
    while git_idx < len(tokens) and tokens[git_idx].startswith("-"):
        if tokens[git_idx] in ("-C", "-c", "--git-dir", "--work-tree"):
            git_idx += 2
        else:
            git_idx += 1
    subcmd = tokens[git_idx] if git_idx < len(tokens) else "status"
    rest_args = tokens[git_idx + 1 :]

    if subcmd in READONLY_GIT_SUBCOMMANDS:
        return True
    if subcmd == "remote":
        return not rest_args or rest_args[0] in ("-v", "--verbose", "show", "get-url")
    if subcmd == "branch":
        return not any(
            (a.startswith("-") and not a.startswith("--") and any(ch in a[1:] for ch in "dDmMcC"))
            or a in ("--delete", "--move", "--copy")
            for a in rest_args
        )
    if subcmd == "tag":
        return not rest_args or rest_args[0] in ("-l", "--list", "-v", "--verify")
    if subcmd == "config":
        return any(
            a in ("--get", "--get-all", "--get-regexp", "-l", "--list") for a in rest_args
        )
    if subcmd == "worktree":
        return bool(rest_args) and rest_args[0] == "list"
    return False


def _is_readonly_gh_tokens(tokens: List[str]) -> bool:
    """Return True if a `gh` command token list is strictly read-only."""
    sub1 = tokens[1] if len(tokens) >= 2 else ""
    sub2 = tokens[2] if len(tokens) >= 3 else ""
    if (sub1, sub2) in {
        ("auth", "status"),
        ("pr", "view"),
        ("pr", "list"),
        ("pr", "status"),
        ("pr", "checks"),
        ("pr", "diff"),
        ("issue", "view"),
        ("issue", "list"),
        ("issue", "status"),
        ("repo", "view"),
        ("repo", "list"),
        ("run", "view"),
        ("run", "list"),
        ("release", "view"),
        ("release", "list"),
    } or sub1 == "search":
        return True
    return False



def evaluate_shell_static(cmd: str, cwd: str, conv_id: str = "") -> Tuple[str, str, str]:
    """
    Stage 1 static evaluation for `run_command`.
    Returns (decision, stage, reason) where decision is one of:
    - "allow"
    - "force_ask"
    - "deny"
    - "needs_review" (triggers Stage 2 Gemini Flash-Lite classifier)
    """
    stripped = cmd.strip()
    if not stripped:
        return "allow", "static-allow", "Empty command."

    py_only_src = _extract_pure_python_inline_or_heredoc(stripped)
    py_ast_flags = _python_ast_has_exec_or_network(py_only_src) if py_only_src is not None else None
    py_is_pure_local_no_exec_no_net = bool(
        py_ast_flags is not None and not py_ast_flags[0] and not py_ast_flags[1]
    )
    is_static_cat_write = _is_pure_static_cat_heredoc_write(stripped)

    # 1. Hard-Deny: Fork bombs, disk formatting, privilege escalation (always checked first regardless of cwd)
    if (
        not is_static_cat_write
        and not (py_ast_flags is not None and not py_ast_flags[0])
        and re.search(r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", stripped)
    ):
        return "deny", "static-deny", "Blocked shell fork bomb pattern."

    if _has_executable_sudo(stripped):
        return "deny", "static-deny", "`sudo` privilege escalation is blocked."

    if not is_static_cat_write and re.search(
        r"\b(mkfs|diskutil\s+erase(Disk|Volume)|dd\s+[^>]*of=/dev/(?!(?:null|zero|stdout|stderr|fd/)\b)[A-Za-z0-9_/-]+)",
        stripped,
    ):
        return "deny", "static-deny", "Blocked disk formatting / raw block device write command."

    # 2. Hard-Deny: Credential & secret exfiltration
    raw_for_cred = _strip_passive_builtin_cli_segments(stripped)
    if is_static_cat_write:
        raw_for_cred, _ = _strip_heredoc_bodies(raw_for_cred)
    accesses_keychain = (
        not py_is_pure_local_no_exec_no_net
        and bool(re.search(r"\bfind-(generic|internet)-password\b", raw_for_cred))
    )
    # Ignore benign file-existence checks (`[ -f ~/.ssh/id_... ]`, `test -f ...`) and `ssh-keygen ... -f ~/.ssh/id_...`
    cred_check_str = re.sub(
        r"(?:\btest|\[|\[\[)\s+!?-[efrsw]\s+[^\s;\]]+|\bssh-keygen\b[^;&|\n]*-f\s+[^\s;&|]+",
        "",
        raw_for_cred,
    )
    accesses_cred_files = any(re.search(pat, cred_check_str) for pat in SENSITIVE_CREDENTIAL_PATTERNS)
    accesses_exfil_files = accesses_cred_files or any(
        re.search(pat, cred_check_str) for pat in SENSITIVE_EXFIL_PATTERNS
    )

    if accesses_cred_files:
        # Never allow deleting or truncating credential files (checked per segment so `rm /tmp/a.wav` + a separate segment does not cross-match)
        if re.search(r">\s*[^\s]*credentials\.enc", cred_check_str) or any(
            any(re.search(pat, seg_d) for pat in SENSITIVE_CREDENTIAL_PATTERNS)
            and re.search(r"\b(rm|unlink|shred|truncate)\b", seg_d)
            for seg_d in _split_shell_segments(cred_check_str)
        ):
            return "deny", "static-deny", "Blocked deletion or overwriting of credential files."
        # Moving credential files (e.g. installing ~/Downloads/client_secret_*.json) escalates to Stage 3 full-context judge
        if any(
            any(re.search(pat, seg_m) for pat in SENSITIVE_CREDENTIAL_PATTERNS)
            and re.search(r"\bmv\b", seg_m)
            for seg_m in _split_shell_segments(cred_check_str)
        ):
            return (
                "force_ask",
                "static-ask",
                "Moving a credential or secret file requires full-context verification.",
            )
        # Never allow dumping raw credential or private key contents via read/text utilities in the same segment
        for seg_c in _split_shell_segments(cred_check_str):
            if any(re.search(pat, seg_c) for pat in SENSITIVE_CREDENTIAL_PATTERNS) and re.search(
                r"(?<![-\w./])(cat|head|tail|less|more|nl|od|xxd|hexdump|strings|base64|sed|awk|grep|egrep|fgrep|rg|jq|cut|paste|tr|sort|uniq|pr|fold|fmt)(?![-\w.])",
                seg_c,
            ):
                return (
                    "deny",
                    "static-deny",
                    "Blocked reading or printing raw credential or private key file.",
                )

    if accesses_exfil_files and not py_is_pure_local_no_exec_no_net:
        # Never allow reading credential or .env files alongside network or DNS exfiltration commands
        py_has_ext_net = bool(
            py_ast_flags is not None
            and py_ast_flags[1]
            and (
                accesses_cred_files
                or any(
                    h.lower().split(":", 1)[0] not in ("127.0.0.1", "localhost")
                    for h in re.findall(r"https?://([^\s/'\"`]+)", cred_check_str)
                )
            )
        )
        if py_has_ext_net or re.search(
            r"(?<![-\w.])(curl|wget|nc|netcat|scp|rsync|ssh|ftp|dig|nslookup|host|gh\s+gist)(?![-\w/])",
            cred_check_str,
        ):
            return "deny", "static-deny", "Blocked potential exfiltration of local credential or `.env` files."
        # Reading `.env` secret files via shell text utilities in the same segment requires Stage 2/3 context verification
        if not accesses_cred_files:
            for seg_e in _split_shell_segments(cred_check_str):
                if re.search(ENV_FILE_PATTERN, seg_e) and re.search(
                    r"(?<![-\w./])(cat|head|tail|less|more|nl|od|xxd|hexdump|strings|base64|sed|awk|grep|egrep|fgrep|rg|jq|cut|paste|tr|sort|uniq)(?![-\w.])",
                    seg_e,
                ):
                    return (
                        "needs_review",
                        "needs-llm",
                        "Reading `.env` secret file via shell requires context verification.",
                    )

    if accesses_keychain:
        # Check if command talks to any network host other than generativelanguage.googleapis.com
        urls = re.findall(r"https?://([^\s/'\"`]+)", stripped)
        lower_urls = [h.lower() for h in urls]
        disallowed_hosts = [
            h for h in urls if h.lower() != "generativelanguage.googleapis.com"
        ]
        if disallowed_hosts and "generativelanguage.googleapis.com" not in lower_urls:
            return (
                "deny",
                "static-deny",
                f"Blocked command accessing macOS Keychain while connecting to external host ({disallowed_hosts[0]}).",
            )
        if re.search(r"(?<![-\w.])(wget|nc|netcat|scp|rsync|ssh|gh\s+gist)(?![-\w/])", stripped) and "generativelanguage.googleapis.com" not in lower_urls:
            return (
                "deny",
                "static-deny",
                "Blocked command accessing macOS Keychain alongside network transfer tool.",
            )
        # Block bare `security find-generic-password ... -w` or inline Python `print(...check_output(...find-generic-password...-w)...)` that directly prints secret to terminal stdout
        # (Allow piped commands like `security find-generic-password ... -w | wc -c` or `generativelanguage.googleapis.com` calls to proceed to Stage 2 review)
        if re.match(
            r"^\s*security\s+find-(generic|internet)-password\b[^|;&`\n]*\s-w\s*($|[;&\n])",
            stripped,
        ) or (
            re.search(r"\b(print|sys\.stdout\.write)\s*\(", stripped)
            and re.search(r"['\"\s]-w['\"\s,\)]", stripped)
            and "len(" not in stripped
            and "generativelanguage.googleapis.com" not in lower_urls
        ):
            return (
                "deny",
                "static-deny",
                "Blocked printing raw Keychain secret directly to terminal output.",
            )

    # 3. Check working directory boundary (if outside allowed roots and not in allowed cwd like ~)
    if cwd and not _is_allowed_cwd(cwd):
        return (
            "force_ask",
            "static-boundary",
            f"Command working directory ({cwd}) is outside ~/projects/.",
        )

    # 4. Escalate: Piping curl/wget directly into an interpreter that executes stdin as code
    # Strip quoted string literals first so `python3 -c '... "curl ... | sh" ...'` is not falsely matched.
    unquoted_cmd = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", '""', stripped)
    if re.search(
        r"\b(curl|wget)\b[^|;\n]*\|\s*(env\s+)?(ba|z|da|k)?sh\b|\b(curl|wget)\b[^|;\n]*\|\s*(env\s+)?(python3?|node|perl|ruby)(\s+-[uIBb]|\s+-)?\s*($|[;&|\n])",
        unquoted_cmd,
    ):
        return (
            "force_ask",
            "static-ask",
            "Piping remote content from `curl`/`wget` directly into an interpreter requires confirmation.",
        )

    # 5. Check self-protection: modifying hooks.json via shell redirection or editors
    if re.search(r"hooks\.json\b", unquoted_cmd):
        if re.search(
            r"(>\s*[^\s]*hooks\.json|\b(rm|mv|cp|ln|sed\s+-i|perl\s+-i|tee|chmod|chown|nano|vim|vi)\b[^\n;]*hooks\.json)",
            unquoted_cmd,
        ):
            return (
                "force_ask",
                "static-self-protect",
                "Modifying `hooks.json` via shell requires user confirmation.",
            )

    # 5b. Escalate inline Python `shutil.rmtree(...)` on non-/tmp paths to Stage 3 heavy judge
    if re.search(r"\bshutil\.rmtree\s*\(", stripped):
        rmtree_args = re.findall(r"\bshutil\.rmtree\s*\(\s*['\"]([^'\"]+)['\"]", stripped)
        if not rmtree_args or not all(p.startswith(("/tmp/", "/private/tmp/", "/var/folders/")) for p in rmtree_args):
            return (
                "force_ask",
                "static-ask",
                "Recursive directory deletion via `shutil.rmtree` outside `/tmp` requires Stage 3 verification.",
            )

    # 6. Segment-by-segment analysis (strip heredoc body lines first so `> 60` inside heredocs isn't parsed as shell redirection)
    cmd_for_segments, has_heredoc = _strip_heredoc_bodies(stripped)
    segments = _split_shell_segments(cmd_for_segments)
    if not segments:
        return "allow", "static-allow", "No executable segments."

    needs_llm_review = has_heredoc
    llm_reason_hint = "Contains heredoc payload." if has_heredoc else ""
    mutates_or_writes = False

    for seg in segments:
        # Strip benign stderr/stdout redirects like 2>/dev/null, 2>&1, >/dev/null, > /dev/null
        seg_clean = re.sub(r"(?:(?<=\s)|^|\b[12])>>?\s*/dev/null\b|\b2>&1\b|&>>?\s*/dev/null\b", "", seg).strip()
        if not seg_clean:
            continue

        # Check all unquoted file output redirections `>` or `>>` in the segment
        redir_targets = _find_all_unquoted_redirections(seg_clean)
        redir_target = redir_targets[0] if redir_targets else None
        for r_target in redir_targets:
            expanded_r_target = os.path.expanduser(r_target)
            resolved_redir = (
                expanded_r_target
                if os.path.isabs(expanded_r_target)
                else os.path.join(cwd or str(WORKSPACE_ROOT), expanded_r_target)
            )
            if _is_env_secret_file(resolved_redir) or _is_env_secret_file(r_target):
                return (
                    "force_ask",
                    "static-env-write",
                    f"Redirecting output to `.env` secret file ({r_target}) requires full-context verification.",
                )
            if _is_sensitive_credential_path(resolved_redir) or _is_sensitive_credential_path(r_target):
                return (
                    "deny",
                    "static-deny",
                    f"Redirecting output to sensitive credential file ({r_target}) is blocked.",
                )
            if (
                _is_protected_self_path(r_target)
                or _is_protected_self_path(resolved_redir)
                or _is_git_hook_or_agent_config_path(r_target)
                or _is_git_hook_or_agent_config_path(resolved_redir)
            ):
                return (
                    "force_ask",
                    "static-self-protect",
                    f"Redirecting output to protected hook or config path ({r_target}) requires confirmation.",
                )
            if not _is_within_allowed_roots(resolved_redir):
                return (
                    "force_ask",
                    "static-boundary",
                    f"Redirecting output outside ~/projects/ ({r_target}) requires confirmation.",
                )

        try:
            tokens = shlex.split(_win_preserve_backslashes(seg_clean), posix=True)
        except ValueError:
            needs_llm_review = True
            llm_reason_hint = "Complex shell quoting."
            continue

        # Escalate dangerous execution/linker environment variable overrides before stripping env prefixes
        for tok_env in tokens:
            if tok_env in ("if", "then", "else", "elif", "do", "while", "until", "!", "env", "command", "time", "nohup"):
                continue
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*$", tok_env):
                env_k = tok_env.split("=", 1)[0].upper()
                if env_k in (
                    "GIT_SSH_COMMAND",
                    "GIT_SSH",
                    "GIT_ASKPASS",
                    "GIT_EXEC_PATH",
                    "GIT_TEMPLATE_DIR",
                    "GIT_EXTERNAL_DIFF",
                    "SSH_ASKPASS",
                    "LD_PRELOAD",
                    "LD_LIBRARY_PATH",
                    "DYLD_INSERT_LIBRARIES",
                    "DYLD_LIBRARY_PATH",
                    "BASH_ENV",
                    "ENV",
                    "PROMPT_COMMAND",
                ):
                    return (
                        "force_ask",
                        "static-ask",
                        f"Environment variable `{env_k}=...` overrides command execution or dynamic linking and requires confirmation.",
                    )
                continue
            break

        tokens = _strip_leading_env_and_wrappers(tokens)
        if not tokens:
            continue

        head = tokens[0]
        prog = os.path.basename(head)

        # Built-in safety gate CLI and optional private overlay tools
        if prog == "safety-gate" or prog in getattr(PRIVATE_RULES, "EXTRA_BUILTIN_SAFE_PROGS", ()):
            continue
        if PRIVATE_RULES is not None and hasattr(PRIVATE_RULES, "check_segment_tokens"):
            priv_seg_early = PRIVATE_RULES.check_segment_tokens(
                prog, tokens, stripped, cwd, redir_target, _is_allowed_cwd
            )
            if priv_seg_early is not None:
                pe_dec, pe_stg, pe_rsn = priv_seg_early
                if pe_dec in ("deny", "force_ask"):
                    return pe_dec, pe_stg, pe_rsn
                if pe_dec == "allow":
                    continue
                needs_llm_review = True
                llm_reason_hint = pe_rsn
                continue

        # Check `ssh` before generic command-substitution check so read-only remote commands
        # (including simple read-only `$(...)` on the remote host) are evaluated cleanly
        if prog == "ssh":
            ssh_res = _check_ssh_command(tokens)
            if ssh_res is not None:
                dec, stg, rsn = ssh_res
                if dec in ("deny", "force_ask"):
                    return dec, stg, rsn
                continue
            needs_llm_review = True
            llm_reason_hint = "Non-trivial or state-modifying `ssh` command."
            continue

        # If segment contains command substitution `$(...)`, backticks, or `$IFS` token splitting (CVE-2025-66032), mark for review
        if "$(" in seg_clean or "`" in seg_clean or "$IFS" in seg_clean or "${IFS" in seg_clean:
            needs_llm_review = True
            llm_reason_hint = "Contains command substitution or $IFS token expansion."

        # Shell control-flow closing keywords and `for <var> in ...` headers
        if prog in ("fi", "done", "esac"):
            continue

        if (
            prog == "for"
            and len(tokens) >= 3
            and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tokens[1])
            and tokens[2] == "in"
        ):
            continue

        # Shell builtins for variable export / directory navigation within workspace
        if prog in ("export", "unset", "local", "popd"):
            if prog in ("export", "local"):
                for tok_exp in tokens[1:]:
                    if "=" in tok_exp:
                        exp_k = tok_exp.split("=", 1)[0].lstrip("-").upper()
                        if exp_k in (
                            "PATH",
                            "LD_PRELOAD",
                            "LD_LIBRARY_PATH",
                            "DYLD_INSERT_LIBRARIES",
                            "DYLD_LIBRARY_PATH",
                            "GIT_SSH_COMMAND",
                            "GIT_SSH",
                            "GIT_ASKPASS",
                            "GIT_EXEC_PATH",
                            "GIT_EXTERNAL_DIFF",
                            "SSH_ASKPASS",
                            "BASH_ENV",
                            "ENV",
                            "PROMPT_COMMAND",
                            "PYTHONSTARTUP",
                            "NODE_OPTIONS",
                        ):
                            needs_llm_review = True
                            llm_reason_hint = f"`{prog} {exp_k}=...` modifies execution environment."
            continue

        if prog in ("cd", "pushd"):
            cd_targets = [t for t in tokens[1:] if not t.startswith("-")]
            if not cd_targets or cd_targets[0] == "-":
                continue
            cd_dest = cd_targets[-1]
            resolved_cd = (
                cd_dest
                if os.path.isabs(os.path.expanduser(cd_dest))
                else os.path.join(cwd or str(WORKSPACE_ROOT), cd_dest)
            )
            if _is_allowed_cwd(resolved_cd):
                cwd = str(Path(os.path.expanduser(resolved_cd)).resolve())
                continue
            return (
                "force_ask",
                "static-boundary",
                f"Changing directory outside ~/projects/ ({cd_dest}) requires confirmation.",
            )

        # Check `ssh-add` read-only agent key listing (`-l` / `-L`)
        if prog == "ssh-add" and tokens[1:] in (["-l"], ["-L"]):
            continue

        # Check `open` for URLs or static local files without app/args execution flags
        if (
            prog == "open"
            and not redir_target
            and not any(t in ("-a", "-b", "-e", "-t", "-f", "--args") or t.startswith("-a") for t in tokens[1:])
            and not any(t.endswith((".sh", ".command", ".py", ".rb", ".pl", ".app")) for t in tokens[1:])
        ):
            continue

        # Check `defaults` read-only queries (`defaults read ...`)
        if prog == "defaults" and not redir_target and len(tokens) >= 2 and tokens[1] in ("read", "read-type", "domains", "find"):
            continue

        # Check `xattr` (read-only extended attribute inspection)
        if prog == "xattr" and not redir_target:
            if not any(t in ("-w", "-d", "-c", "-wx") for t in tokens[1:]):
                continue

        # Check `ipconfig` read-only LAN IP lookup (`ipconfig getifaddr en0`)
        if prog == "ipconfig" and len(tokens) >= 2 and tokens[1] in ("getifaddr", "getoption", "getpacket", "ifcount"):
            continue

        # Check `sed` without `-i` / `--in-place`, `-f`, or GNU sed `e` execution modifier (CVE-2025-66032)
        if prog == "sed" and not redir_target:
            if not _has_sed_exec_or_inplace(tokens):
                continue

        # Check `cp` inside workspace roots (and not writing to `.git/hooks` or `.git/config`)
        if prog == "cp":
            cp_targets = [t for t in tokens[1:] if not t.startswith("-")]
            if cp_targets and _is_git_hook_or_agent_config_path(cp_targets[-1]):
                return (
                    "force_ask",
                    "static-self-protect",
                    f"Copying into Git hook or config path ({cp_targets[-1]}) requires full-context verification (CVE-2026-26268).",
                )
            if cp_targets and all(
                not _is_protected_self_path(t)
                and _is_within_allowed_roots(
                    t
                    if os.path.isabs(os.path.expanduser(t))
                    else os.path.join(cwd or str(WORKSPACE_ROOT), t)
                )
                for t in cp_targets
            ):
                continue

        # Check `chmod` / `mv` / `ln` targeting `.git/hooks/*` or `.git/config`
        if prog in ("chmod", "mv", "ln"):
            non_flags = [t for t in tokens[1:] if not t.startswith("-")]
            if any(_is_git_hook_or_agent_config_path(t) for t in non_flags):
                return (
                    "force_ask",
                    "static-self-protect",
                    f"Modifying Git hook or config via `{prog}` requires full-context verification (CVE-2026-26268).",
                )

        # Check `rm`
        if prog == "rm":
            rm_res = _check_rm_safety(tokens, cwd)
            if rm_res is not None:
                dec, stg, rsn = rm_res
                if dec in ("deny", "force_ask"):
                    return dec, stg, rsn
                continue
            needs_llm_review = True
            llm_reason_hint = "File deletion via `rm`."
            continue

        # Check `git`
        if prog == "git":
            git_danger_rsn = _has_dangerous_git_flags(tokens)
            if git_danger_rsn is not None:
                return "force_ask", "static-ask", git_danger_rsn

            # Skip git global flags like -C <dir> or --no-pager
            git_idx = 1
            while git_idx < len(tokens) and tokens[git_idx].startswith("-"):
                if tokens[git_idx] in ("-C", "-c", "--git-dir", "--work-tree"):
                    git_idx += 2
                else:
                    git_idx += 1
            subcmd = tokens[git_idx] if git_idx < len(tokens) else "status"
            rest_args = tokens[git_idx + 1 :]

            if subcmd == "push":
                if any(f in rest_args for f in ("--force", "-f", "--force-with-lease")):
                    return "deny", "static-deny", "`git push --force` is blocked."
                return (
                    "force_ask",
                    "static-ask",
                    "`git push` to a remote repository requires explicit user confirmation.",
                )
            if subcmd == "reset" and "--hard" in rest_args:
                return (
                    "force_ask",
                    "static-ask",
                    "`git reset --hard` discards uncommitted changes and requires confirmation.",
                )
            if subcmd == "config":
                if any(
                    a in ("--get", "--get-all", "--get-regexp", "-l", "--list")
                    for a in rest_args
                ):
                    continue
                cfg_non_flags = [a.lower() for a in rest_args if not a.startswith("-")]
                if cfg_non_flags and cfg_non_flags[0].startswith(DANGEROUS_GIT_CONFIG_PREFIXES):
                    return (
                        "force_ask",
                        "static-ask",
                        f"Setting executable `git config {cfg_non_flags[0]}` hook/command option requires full-context verification (CVE-2026-26268).",
                    )
                if cfg_non_flags and cfg_non_flags[0] in (
                    "user.name",
                    "user.email",
                    "init.defaultbranch",
                    "pull.rebase",
                ):
                    continue
                needs_llm_review = True
                llm_reason_hint = f"`git config` mutation (`{' '.join(rest_args[:2])}`)."
                continue
            if subcmd in FORCE_ASK_GIT_SUBCOMMANDS:
                return (
                    "force_ask",
                    "static-ask",
                    f"`git {subcmd}` requires explicit user confirmation.",
                )
            if subcmd == "stash":
                stash_non_flags = [a for a in rest_args if not a.startswith("-")]
                if stash_non_flags and stash_non_flags[0] in ("drop", "clear"):
                    return (
                        "force_ask",
                        "static-ask",
                        f"`git stash {stash_non_flags[0]}` permanently discards stashed changes and requires explicit user confirmation.",
                    )
            if subcmd == "checkout":
                co_non_flags = [a for a in rest_args if not a.startswith("-")]
                has_branch_create = any(a in ("-b", "-B", "--orphan") for a in rest_args)
                if (
                    "--" in rest_args
                    or "." in rest_args
                    or any(a in ("-f", "--force") for a in rest_args)
                    or (not has_branch_create and len(co_non_flags) >= 2)
                ):
                    return (
                        "force_ask",
                        "static-ask",
                        "`git checkout` discarding or overwriting worktree changes requires explicit user confirmation.",
                    )
            if subcmd == "remote":
                rem_non_flags = [a for a in rest_args if not a.startswith("-")]
                if rem_non_flags and rem_non_flags[0] not in ("show", "get-url"):
                    return (
                        "force_ask",
                        "static-ask",
                        f"`git remote {rem_non_flags[0]}` mutates remote repository configuration and requires explicit user confirmation.",
                    )
            if subcmd == "branch":
                short_bundles = [
                    a[1:] for a in rest_args if a.startswith("-") and not a.startswith("--") and len(a) > 1
                ]
                has_cap_d = any("D" in b for b in short_bundles)
                has_del = has_cap_d or "--delete" in rest_args or any("d" in b for b in short_bundles)
                has_force = "--force" in rest_args or any("f" in b for b in short_bundles)
                if has_cap_d or (has_del and has_force):
                    return (
                        "force_ask",
                        "static-ask",
                        "`git branch -D` force-deletes a branch and requires explicit user confirmation.",
                    )
            if subcmd in SAFE_GIT_SUBCOMMANDS:
                continue
            needs_llm_review = True
            llm_reason_hint = f"Uncommon git subcommand `git {subcmd}`."
            continue

        # Check `hg` (Mercurial)
        if prog == "hg":
            hg_idx = 1
            while hg_idx < len(tokens) and tokens[hg_idx].startswith("-"):
                tok_h = tokens[hg_idx]
                if tok_h == "--config" and hg_idx + 1 < len(tokens):
                    cfg_kv = tokens[hg_idx + 1].lower().strip()
                    if cfg_kv.startswith(("alias.", "hooks.", "extensions.")):
                        return (
                            "force_ask",
                            "static-ask",
                            f"Executable `hg --config {tokens[hg_idx + 1]}` override requires confirmation.",
                        )
                    hg_idx += 2
                    continue
                if tok_h.startswith("--config="):
                    cfg_kv = tok_h.split("=", 1)[1].lower().strip()
                    if cfg_kv.startswith(("alias.", "hooks.", "extensions.")):
                        return (
                            "force_ask",
                            "static-ask",
                            f"Executable `hg {tok_h}` override requires confirmation.",
                        )
                    hg_idx += 1
                    continue
                if tok_h in ("-R", "--repository", "--cwd"):
                    hg_idx += 2
                else:
                    hg_idx += 1
            hg_sub = tokens[hg_idx] if hg_idx < len(tokens) else "status"
            hg_rest = tokens[hg_idx + 1 :]
            is_hg_help = any(t in ("-h", "--help") for t in hg_rest)
            if not is_hg_help and hg_sub == "revert":
                return (
                    "force_ask",
                    "static-ask",
                    "`hg revert` discards uncommitted working-tree changes and requires explicit user confirmation.",
                )
            if not is_hg_help and hg_sub == "push":
                return (
                    "force_ask",
                    "static-ask",
                    "`hg push` mutates external repository state and requires explicit user confirmation.",
                )
            if hg_sub in SAFE_HG_SUBCOMMANDS or is_hg_help:
                continue
            needs_llm_review = True
            llm_reason_hint = f"Uncommon Mercurial subcommand `hg {hg_sub}`."
            continue

        # Check `jj` (Jujutsu)
        if prog == "jj":
            jj_idx = 1
            while jj_idx < len(tokens) and tokens[jj_idx].startswith("-"):
                tok_j = tokens[jj_idx]
                if tok_j in ("-R", "--repository", "--at-op", "--at-operation", "--color", "--config", "--config-toml") and jj_idx + 1 < len(tokens):
                    jj_idx += 2
                else:
                    jj_idx += 1
            jj_sub = tokens[jj_idx] if jj_idx < len(tokens) else "status"
            jj_rest = tokens[jj_idx + 1 :]
            is_jj_help = any(t in ("-h", "--help") for t in jj_rest) or jj_sub in ("help", "version")
            if is_jj_help and not redir_target:
                continue
            if not is_jj_help and jj_sub == "restore":
                return (
                    "force_ask",
                    "static-ask",
                    "`jj restore` discards working-copy changes and requires explicit user confirmation.",
                )

        # Escalate scheduled task persistence (`at`, `batch`, `crontab`) to Stage 3 full-context review
        if prog in ("at", "batch", "crontab"):
            return (
                "force_ask",
                "static-ask",
                f"Scheduled task command (`{prog}`) requires full-context verification.",
            )

        # Escalate `docker.sock` volume mounts or direct socket access to Stage 3 full-context review
        if "docker.sock" in seg_clean and (
            prog in ("docker", "podman", "docker-compose", "nerdctl", "curl", "nc", "socat")
            or bool(re.search(r"(-v|--volume|--mount|--unix-socket)", seg_clean))
        ):
            return (
                "force_ask",
                "static-ask",
                f"Mounting or accessing `docker.sock` via `{prog}` grants host-equivalent privileges and requires full-context verification.",
            )

        # Check `systemctl` read-only queries (`status`, `is-active`, `is-enabled`, `list-units`, `list-timers`, `show`)
        if prog == "systemctl" and not redir_target:
            if any(
                t in ("status", "is-active", "is-enabled", "list-units", "list-timers", "show")
                for t in tokens[1:]
            ) and not any(
                t in ("start", "stop", "restart", "reload", "enable", "disable", "mask", "unmask", "daemon-reload")
                for t in tokens[1:]
            ):
                continue

        # Delegate optional workstation-internal CLIs to PRIVATE_RULES when loaded
        if PRIVATE_RULES is not None and hasattr(PRIVATE_RULES, "check_segment_tokens"):
            priv_seg = PRIVATE_RULES.check_segment_tokens(
                prog, tokens, stripped, cwd, redir_target, _is_allowed_cwd
            )
            if priv_seg is not None:
                p_dec, p_stg, p_rsn = priv_seg
                if p_dec in ("deny", "force_ask"):
                    return p_dec, p_stg, p_rsn
                if p_dec == "allow":
                    continue
                needs_llm_review = True
                llm_reason_hint = p_rsn
                continue

        # Check `gcloud`, `gsutil`, `aws`, and `rclone` cloud queries vs external cloud mutations
        if prog == "gcloud":
            gc_non_flags = [t for t in tokens[1:] if not t.startswith("-")]
            is_gc_help = any(t in ("-h", "--help", "--version", "-v") for t in tokens[1:])
            if not redir_target and (
                is_gc_help
                or gc_non_flags[:2] in (["auth", "list"], ["config", "list"], ["config", "get-value"], ["config", "get"])
                or gc_non_flags[:1] in (["version"], ["info"], ["topic"])
            ):
                continue
            if not is_gc_help and (
                (len(gc_non_flags) >= 2 and gc_non_flags[0] == "storage" and gc_non_flags[1] in ("cp", "mv", "rm", "rsync", "restore", "buckets"))
                or any(
                    v in gc_non_flags
                    for v in (
                        "deploy", "delete", "create", "update", "import", "export", "restore",
                        "add-iam-policy-binding", "remove-iam-policy-binding", "set-iam-policy", "ssh", "scp",
                    )
                )
            ):
                return (
                    "force_ask",
                    "static-ask",
                    f"`gcloud {' '.join(gc_non_flags[:3])}` mutates or accesses external cloud resources and requires explicit user confirmation.",
                )

        if prog == "gsutil":
            gs_idx = 1
            while gs_idx < len(tokens) and tokens[gs_idx].startswith("-"):
                if tokens[gs_idx] in ("-h", "-o", "-i", "-u", "-p") and gs_idx + 1 < len(tokens):
                    gs_idx += 2
                else:
                    gs_idx += 1
            gs_sub = tokens[gs_idx] if gs_idx < len(tokens) else ""
            gs_rest = tokens[gs_idx + 1 :] if gs_idx < len(tokens) else []
            is_gs_help = (
                gs_sub in ("help", "version")
                or "--help" in tokens[1:]
                or "-h" in gs_rest
                or (not gs_sub and any(t in ("-h", "--help", "-v") for t in tokens[1:]))
            )
            if not redir_target and (is_gs_help or gs_sub in ("ls", "stat", "du", "hash", "version", "help")):
                continue
            if not is_gs_help and gs_sub in (
                "cp", "mv", "rm", "rsync", "mb", "rb", "acl", "iam", "defacl", "setmeta", "rewrite", "compose", "notification", "lifecycle", "cors", "retention"
            ):
                return (
                    "force_ask",
                    "static-ask",
                    f"`gsutil {gs_sub}` mutates external cloud storage and requires explicit user confirmation.",
                )

        if prog == "aws":
            aws_non_flags = [t for t in tokens[1:] if not t.startswith("-")]
            is_aws_help = any(t in ("-h", "--help", "--version", "help") for t in tokens[1:])
            if not is_aws_help and len(aws_non_flags) >= 2 and aws_non_flags[0] in ("s3", "s3api") and aws_non_flags[1] in (
                "cp", "mv", "rm", "sync", "mb", "rb", "put-object", "delete-object", "delete-objects", "delete-bucket", "create-bucket", "put-bucket-acl", "put-bucket-policy"
            ):
                return (
                    "force_ask",
                    "static-ask",
                    f"`aws {aws_non_flags[0]} {aws_non_flags[1]}` mutates external cloud storage and requires explicit user confirmation.",
                )

        if prog == "rclone":
            rc_non_flags = [t for t in tokens[1:] if not t.startswith("-")]
            rc_sub = rc_non_flags[0] if rc_non_flags else ""
            is_rc_help = any(t in ("-h", "--help", "--version", "version", "help") for t in tokens[1:])
            if not is_rc_help and rc_sub in (
                "copy", "sync", "move", "delete", "deletefile", "purge", "mkdir", "rmdir", "copyto", "moveto", "bisync"
            ):
                return (
                    "force_ask",
                    "static-ask",
                    f"`rclone {rc_sub}` mutates external cloud storage and requires explicit user confirmation.",
                )

        # Check `gh` (GitHub CLI)
        if prog == "gh":
            sub1 = tokens[1] if len(tokens) >= 2 else ""
            sub2 = tokens[2] if len(tokens) >= 3 else ""
            if (sub1, sub2) in {
                ("auth", "status"),
                ("pr", "view"),
                ("pr", "list"),
                ("pr", "status"),
                ("pr", "checks"),
                ("pr", "diff"),
                ("issue", "view"),
                ("issue", "list"),
                ("issue", "status"),
                ("repo", "view"),
                ("repo", "list"),
                ("run", "view"),
                ("run", "list"),
                ("release", "view"),
                ("release", "list"),
            } or sub1 == "search":
                continue
            if (sub1, sub2) in {
                ("pr", "create"),
                ("pr", "merge"),
                ("pr", "close"),
                ("pr", "comment"),
                ("pr", "edit"),
                ("issue", "create"),
                ("issue", "close"),
                ("issue", "comment"),
                ("issue", "delete"),
                ("repo", "create"),
                ("repo", "delete"),
                ("repo", "archive"),
                ("release", "create"),
                ("release", "delete"),
                ("gist", "create"),
            }:
                return (
                    "force_ask",
                    "static-ask",
                    f"`gh {sub1} {sub2}` mutates remote GitHub state and requires confirmation.",
                )
            if sub1 == "api":
                if any(a in ("-X", "--method") or a.startswith(("-X", "--method=")) for a in tokens[2:]):
                    # Check if method is GET
                    joined_api = " ".join(tokens[2:])
                    if not re.search(r"(-X|--method=?)\s*GET\b", joined_api, re.I):
                        return (
                            "force_ask",
                            "static-ask",
                            "Non-GET `gh api` request requires confirmation.",
                        )
                if any(a in ("-f", "-F", "--field", "--raw-field", "--input") for a in tokens[2:]):
                    return (
                        "force_ask",
                        "static-ask",
                        "`gh api` request with payload fields defaults to POST and requires confirmation.",
                    )
                continue
            needs_llm_review = True
            llm_reason_hint = f"GitHub CLI command `gh {sub1} {sub2}`."
            continue

        # Check `find`
        if prog == "find":
            if any(
                t in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls")
                for t in tokens[1:]
            ):
                needs_llm_review = True
                llm_reason_hint = "`find` with `-delete`, `-exec`, or file output action."
            continue

        # Check pure read binaries (with CVE-2025-66032 flag checks for `sort --compress-program` and `rg --pre`)
        if prog in PURE_READ_BINARIES and not redir_target:
            if _has_pure_read_binary_exec_flag(prog, tokens):
                return (
                    "force_ask",
                    "static-ask",
                    f"`{prog}` flag executes an external binary (CVE-2025-66032) and requires confirmation.",
                )
            continue

        # Check `mkdir`, `touch` inside workspace
        if prog in ("mkdir", "touch"):
            targets = [t for t in tokens[1:] if not t.startswith("-")]
            if all(
                _is_within_allowed_roots(
                    t if os.path.isabs(os.path.expanduser(t)) else os.path.join(cwd or str(WORKSPACE_ROOT), t)
                )
                for t in targets
            ):
                continue

        # Check `python3` / `python` / `pytest`
        if prog in ("python3", "python", "pytest", "py.test"):
            if prog in ("pytest", "py.test"):
                needs_llm_review = True
                llm_reason_hint = f"`{prog}` executes arbitrary test code and requires Stage 2 semantic review."
                continue
            # Inline `python3 -c "..."` or `python3 -` -> check for external/mutating network AST first (Stage 3), else Stage 2
            if "-c" in tokens[1:] or "-" in tokens[1:]:
                inline_src = ""
                if "-c" in tokens[1:]:
                    c_idx = tokens.index("-c", 1)
                    if c_idx + 1 < len(tokens):
                        inline_src = tokens[c_idx + 1]
                if not inline_src and has_heredoc:
                    hd_res = _extract_heredoc_body(stripped)
                    if hd_res is not None:
                        inline_src = hd_res[1]
                if not inline_src and py_only_src:
                    inline_src = py_only_src
                ext_net_rsn = _python_has_external_or_mutating_network(inline_src)
                if ext_net_rsn is not None:
                    return "force_ask", "static-ask", ext_net_rsn
                needs_llm_review = True
                llm_reason_hint = "Inline `python3 -c` code execution."
                continue
            # Scan leading Python interpreter flags before the first positional script argument
            m_idx = -1
            py_opt_i = 1
            while py_opt_i < len(tokens):
                t_opt = tokens[py_opt_i]
                if t_opt == "-m":
                    m_idx = py_opt_i
                    break
                if t_opt in ("-W", "-X") and py_opt_i + 1 < len(tokens):
                    py_opt_i += 2
                    continue
                if t_opt.startswith("-") and t_opt not in ("-", "--"):
                    py_opt_i += 1
                    continue
                break
            if m_idx != -1 and m_idx + 1 < len(tokens):
                mod_name = tokens[m_idx + 1]
                if mod_name in ("unittest", "pytest") or mod_name.startswith(("unittest.", "pytest.")):
                    needs_llm_review = True
                    llm_reason_hint = f"Python test runner (`{prog} -m {mod_name}`) executes arbitrary test code and requires Stage 2 semantic review."
                    continue
                if mod_name in ("py_compile", "json.tool", "http.server"):
                    continue
                needs_llm_review = True
                llm_reason_hint = f"Python module execution (`{prog} -m {mod_name}`)."
                continue
            # Local `.py` script -> inspect file contents and conversation edit history
            script_tok = next((t for t in tokens[1:] if not t.startswith("-")), "")
            if script_tok:
                script_dec, script_stg, script_rsn = _inspect_local_script_static(
                    script_tok, cwd, conv_id
                )
                if script_dec in ("deny", "force_ask"):
                    return script_dec, script_stg, script_rsn
                if script_dec == "allow":
                    continue
                needs_llm_review = True
                llm_reason_hint = script_rsn
                continue
            needs_llm_review = True
            llm_reason_hint = f"Python script execution (`{' '.join(tokens[:3])}`)."
            continue

        # Check `agy` / `antigravity` / `antigravity-cli` inside allowed working directories
        if (
            prog in ("agy", "antigravity", "antigravity-cli")
            or prog in getattr(PRIVATE_RULES, "EXTRA_AGENT_CLI_PROGS", ())
        ) and _is_allowed_cwd(cwd or str(WORKSPACE_ROOT)):
            continue

        # Check `node`
        if prog == "node":
            if any(t in ("-e", "--eval", "-p", "--print") for t in tokens[1:]):
                needs_llm_review = True
                llm_reason_hint = "Inline `node -e` code execution."
                continue
            if "--test" in tokens[1:]:
                needs_llm_review = True
                llm_reason_hint = "`node --test` executes arbitrary test code and requires Stage 2 semantic review."
                continue
            if any(t in ("--check", "--version", "-v") for t in tokens[1:]):
                continue
            script_tok = next((t for t in tokens[1:] if not t.startswith("-")), "")
            if script_tok:
                script_dec, script_stg, script_rsn = _inspect_local_script_static(
                    script_tok, cwd, conv_id
                )
                if script_dec in ("deny", "force_ask"):
                    return script_dec, script_stg, script_rsn
                if script_dec == "allow":
                    continue
                needs_llm_review = True
                llm_reason_hint = script_rsn
                continue

        # Check `sh` / `bash` / `zsh` running a script file
        if prog in ("sh", "bash", "zsh") and len(tokens) >= 2 and not tokens[1].startswith("-"):
            script_dec, script_stg, script_rsn = _inspect_local_script_static(
                tokens[1], cwd, conv_id
            )
            if script_dec in ("deny", "force_ask"):
                return script_dec, script_stg, script_rsn
            if script_dec == "allow":
                continue
            needs_llm_review = True
            llm_reason_hint = script_rsn
            continue

        # Check `curl`
        if prog == "curl":
            # Read-only GET curl (no -X POST/PUT/DELETE/PATCH, no -d/--data/--form/--upload-file)
            mutating_curl_flags = {
                "-d",
                "--data",
                "--data-raw",
                "--data-binary",
                "--data-urlencode",
                "-F",
                "--form",
                "-T",
                "--upload-file",
            }
            has_mutate = any(
                t in mutating_curl_flags or t.startswith(("--data=", "--form=", "--upload-file="))
                for t in tokens[1:]
            )
            has_non_get = bool(
                re.search(r"(-X|--request)\s*(POST|PUT|DELETE|PATCH)\b", " ".join(tokens[1:]), re.I)
            )
            if not has_mutate and not has_non_get:
                continue
            needs_llm_review = True
            llm_reason_hint = "Mutating `curl` request (POST/PUT/DELETE or data payload)."
            continue

        # Check `tmux` session inspection and management
        if prog == "tmux":
            tmux_sub = next((t for t in tokens[1:] if not t.startswith("-")), "")
            if tmux_sub in (
                "ls",
                "list-sessions",
                "list-windows",
                "list-panes",
                "capture-pane",
                "capturep",
                "show-options",
                "has-session",
                "has",
                "kill-session",
                "wait-for",
            ) or any(t in ("-V",) for t in tokens[1:]):
                continue
            if tmux_sub in ("new-session", "new"):
                # Extract any command argument passed to `tmux new-session`
                sub_idx = tokens.index(tmux_sub)
                rem_args: List[str] = []
                skip_arg = False
                for tok_m in tokens[sub_idx + 1 :]:
                    if skip_arg:
                        skip_arg = False
                        continue
                    if tok_m in ("-s", "-t", "-n", "-c", "-F", "-x", "-y", "-e"):
                        skip_arg = True
                        continue
                    if tok_m.startswith("-"):
                        continue
                    rem_args.append(tok_m)
                if not rem_args:
                    continue
                inner_cmd = " ".join(rem_args)
                inner_dec, inner_stg, inner_rsn = evaluate_shell_static(inner_cmd, cwd, conv_id)
                if inner_dec in ("deny", "force_ask"):
                    return inner_dec, inner_stg, inner_rsn
                if inner_dec == "allow":
                    continue
                needs_llm_review = True
                llm_reason_hint = f"`tmux {tmux_sub}` command `{inner_cmd}` requires semantic review."
                continue
            if tmux_sub in ("send-keys", "send"):
                sub_idx = tokens.index(tmux_sub)
                key_tokens: List[str] = []
                skip_arg = False
                for tok_k in tokens[sub_idx + 1 :]:
                    if skip_arg:
                        skip_arg = False
                        continue
                    if tok_k in ("-t", "-N"):
                        skip_arg = True
                        continue
                    if tok_k.startswith("-"):
                        continue
                    if tok_k in ("Enter", "C-m", "C-c", "Escape", "Space", "Tab", "BSpace"):
                        continue
                    key_tokens.append(tok_k)
                sent_cmd = " ".join(key_tokens).strip()
                if sent_cmd:
                    sent_dec, sent_stg, sent_rsn = evaluate_shell_static(sent_cmd, cwd, conv_id)
                    if sent_dec in ("deny", "force_ask"):
                        return sent_dec, sent_stg, sent_rsn
                needs_llm_review = True
                llm_reason_hint = "Sending keys to a `tmux` session requires semantic review with conversation command history."
                continue

        # Check `tar` inside allowed workspace roots or stdin/stdout (`-`)
        if prog == "tar":
            if _has_tar_exec_flag(tokens):
                return (
                    "force_ask",
                    "static-ask",
                    "`tar` command-execution flag (`--checkpoint-action` / `--to-command` / `--use-compress-program`) requires confirmation.",
                )
            tar_C_ok = True
            has_explicit_C = False
            for idx_t, tok_t in enumerate(tokens[1:], start=1):
                if tok_t in ("-C", "--directory") and idx_t + 1 < len(tokens):
                    has_explicit_C = True
                    c_dir = tokens[idx_t + 1]
                    resolved_c = (
                        c_dir
                        if os.path.isabs(os.path.expanduser(c_dir))
                        else os.path.join(cwd or str(WORKSPACE_ROOT), c_dir)
                    )
                    if not _is_within_allowed_roots(resolved_c):
                        tar_C_ok = False
                        break
            if tar_C_ok and (has_explicit_C or _is_within_allowed_roots(cwd or str(WORKSPACE_ROOT))):
                continue

        # Check `rsync` / `scp` pulling FROM remote host (`host:path`) into allowed local workspace root
        if prog in ("rsync", "scp"):
            non_flag_args: List[str] = []
            skip_next = False
            for tok_r in tokens[1:]:
                if skip_next:
                    skip_next = False
                    continue
                if tok_r in ("-e", "--rsh", "-i", "-F", "-o", "-P", "-p", "-S"):
                    skip_next = True
                    continue
                if tok_r.startswith("-"):
                    continue
                non_flag_args.append(tok_r)
            if len(non_flag_args) >= 2:
                sources = non_flag_args[:-1]
                dest = non_flag_args[-1]
                resolved_dest = (
                    dest
                    if os.path.isabs(os.path.expanduser(dest))
                    else os.path.join(cwd or str(WORKSPACE_ROOT), dest)
                )
                if (
                    all(":" in s and not s.startswith("/") for s in sources)
                    and ":" not in dest
                    and not _is_protected_self_path(resolved_dest)
                    and _is_within_allowed_roots(resolved_dest)
                ):
                    continue
                if ":" in dest and not dest.startswith("/"):
                    return (
                        "force_ask",
                        "static-ask",
                        f"`{prog}` pushing files to a remote host ({dest}) requires explicit user confirmation.",
                    )

        # Anything else (osascript, kill, pkill, chmod, sed -i, open, swift, etc.) -> Stage 2 LLM review
        needs_llm_review = True
        llm_reason_hint = f"Command `{prog}` requires semantic safety classification."

    if needs_llm_review:
        return "needs_review", "needs-llm", llm_reason_hint

    return "allow", "static-allow", "All command segments matched safe local allowlist."


