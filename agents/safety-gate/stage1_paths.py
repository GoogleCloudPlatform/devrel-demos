#!/usr/bin/env python3
"""
Stage 1 path, boundary, URL, MCP, `rm`, and remote-shell static rules for `safety-gate`.

Contains:
- Allowlists and sets (`READ_ONLY_TOOLS`, `PURE_READ_BINARIES`, `SAFE_GIT_SUBCOMMANDS`,
  `FORCE_ASK_GIT_SUBCOMMANDS`, `SAFE_HG_SUBCOMMANDS`, `SSH_OPTS_WITH_ARG`).
- Workspace and symlink boundary checks (`_norm_user_path_str`, `_is_within_allowed_roots`,
  `_is_allowed_cwd`, `_is_protected_self_path`, `_is_git_hook_or_agent_config_path`,
  `_is_env_secret_file`, `_is_within_allowed_read_roots`, `_is_sensitive_credential_path`).
- Non-shell tool evaluators (`evaluate_read_tool`, `evaluate_file_tool`, `evaluate_url_tool`, `evaluate_mcp_tool`).
- Remote SSH and `rm` target boundary analyzers (`_is_readonly_remote_shell`, `_check_ssh_command`, `_check_rm_safety`).
"""

import json
import os
import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PRIVATE_RULES: Optional[Any] = None

# Pure UI/coordination tools that never access local files or external endpoints
READ_ONLY_TOOLS = {
    "search_web",
    "ask_question",
    "ask_permission",
    "manage_subagents",
    "list_resources",
    "read_resource",
}

# Pure read-only shell commands that are safe when not writing to sensitive paths
PURE_READ_BINARIES = {
    "ls",
    "pwd",
    "which",
    "whereis",
    "type",
    "echo",
    "printf",
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "tr",
    "cut",
    "paste",
    "column",
    "grep",
    "egrep",
    "fgrep",
    "rg",
    "fd",
    "stat",
    "file",
    "du",
    "df",
    "ps",
    "pgrep",
    "lsof",
    "uname",
    "whoami",
    "id",
    "hostname",
    "sw_vers",
    "scutil",
    "system_profiler",
    "dscl",
    "date",
    "cal",
    "jq",
    "shasum",
    "sha256sum",
    "sha1sum",
    "md5",
    "md5sum",
    "cksum",
    "diff",
    "cmp",
    "comm",
    "strings",
    "otool",
    "nm",
    "xxd",
    "hexdump",
    "base64",
    "basename",
    "dirname",
    "realpath",
    "readlink",
    "true",
    "false",
    "test",
    "[",
    "[[",
    "sleep",
    *tuple(getattr(PRIVATE_RULES, "EXTRA_PURE_READ_BINARIES", ()) or ()),
    "printenv",
    "arch",
    "nproc",
    "uptime",
    "free",
    "vm_stat",
    "w",
    "who",
    "groups",
    "locale",
    "getconf",
    "tree",
    "less",
    "more",
    "nl",
    "fold",
    "fmt",
    "expand",
    "unexpand",
    "rev",
    "tac",
    "lsblk",
    "lspci",
    "lsusb",
    "lscpu",
    "lshw",
    "dig",
    "nslookup",
    "host",
    "ifconfig",
    "netstat",
    "ss",
}

SAFE_GIT_SUBCOMMANDS = {
    "status",
    "log",
    "diff",
    "show",
    "branch",
    "rev-parse",
    "ls-files",
    "ls-tree",
    "remote",
    "tag",
    "describe",
    "shortlog",
    "blame",
    "reflog",
    "add",
    "commit",
    "checkout",
    "switch",
    "stash",
    "fetch",
    "merge",
    "rebase",
    "cherry-pick",
    "mv",
    "rm",
    "init",
}

READONLY_GIT_SUBCOMMANDS = {
    "status",
    "log",
    "diff",
    "show",
    "rev-parse",
    "ls-files",
    "ls-tree",
    "describe",
    "shortlog",
    "blame",
    "reflog",
}

FORCE_ASK_GIT_SUBCOMMANDS = {
    "push",
    "clean",
    "restore",
}

SAFE_HG_SUBCOMMANDS = {
    "status",
    "st",
    "diff",
    "log",
    "show",
    "files",
    "manifest",
    "id",
    "identify",
    "branch",
    "branches",
    "bookmarks",
    "bookmark",
    "root",
    "annotate",
    "blame",
    "grep",
    "cat",
    "parents",
    "heads",
    "summary",
    "sum",
    "resolve",
    "add",
    "commit",
    "ci",
    "amend",
    "evolve",
    "rebase",
    "checkout",
    "co",
    "update",
    "up",
    "shelve",
    "unshelve",
    "absorb",
    "split",
    "fold",
    "prune",
    "patch",
    "import",
    "export",
    "help",
    "version",
}

READONLY_HG_SUBCOMMANDS = {
    "status",
    "st",
    "diff",
    "log",
    "show",
    "files",
    "manifest",
    "id",
    "identify",
    "branch",
    "branches",
    "bookmarks",
    "root",
    "annotate",
    "blame",
    "grep",
    "cat",
    "parents",
    "heads",
    "summary",
    "sum",
    "help",
    "version",
}

SSH_OPTS_WITH_ARG = {
    "-B",
    "-b",
    "-c",
    "-D",
    "-E",
    "-e",
    "-F",
    "-I",
    "-i",
    "-J",
    "-L",
    "-l",
    "-m",
    "-O",
    "-o",
    "-P",
    "-p",
    "-Q",
    "-R",
    "-S",
    "-W",
    "-w",
}

SSH_TUNNEL_OR_MUX_OPTS = {"-D", "-L", "-R", "-W", "-w"}



def _norm_user_path_str(path_str: str) -> str:
    raw = path_str.strip()
    if os.sep == "/" and "\\" in raw and not raw.startswith("\\"):
        raw = raw.replace("\\", "/")
    return os.path.expanduser(raw)


def _is_in_temp_root(resolved: Path) -> bool:
    for tr in TMP_ROOTS:
        if resolved == tr or tr in resolved.parents:
            if not any(
                (tr == hr or tr in hr.parents) and (resolved == hr or hr in resolved.parents)
                for hr in HOME_ROOTS
            ):
                return True
    return False


def _is_within_allowed_roots(path_str: str) -> bool:
    if not path_str:
        return True
    expanded = _norm_user_path_str(path_str)
    try:
        resolved = Path(expanded).resolve()
    except Exception:
        resolved = Path(expanded)

    allowed_exact_files = tuple(
        (base / ".ssh" / name)
        for base in HOME_ROOTS
        for name in ("config", "known_hosts")
    )
    for exact_file in allowed_exact_files:
        try:
            if resolved == exact_file or resolved == exact_file.resolve():
                return True
        except Exception:
            pass

    home_config_roots = tuple(
        r
        for base in HOME_ROOTS
        for sub in (Path(".gemini") / "config", Path(".local") / "bin")
        for r in (base / sub, (base / sub).resolve())
    )
    allowed_roots = WORKSPACE_ROOTS + (BRAIN_ROOT,) + home_config_roots + BRAIN_ROOTS
    for root in allowed_roots:
        if resolved == root or root in resolved.parents:
            return True
    if _is_in_temp_root(resolved):
        return True

    if PRIVATE_RULES is not None and hasattr(PRIVATE_RULES, "extra_is_within_allowed_roots"):
        if PRIVATE_RULES.extra_is_within_allowed_roots(expanded, resolved):
            return True
    return False


def _is_allowed_cwd(path_str: str) -> bool:
    """Allow home directory (`~`) and dotfile/config dirs as working directories for shell commands."""
    if not path_str:
        return True
    if _is_within_allowed_roots(path_str):
        return True
    expanded = os.path.expanduser(path_str.strip())
    try:
        resolved = Path(expanded).resolve()
    except Exception:
        resolved = Path(expanded)
    for home_root in HOME_ROOTS:
        if resolved == home_root:
            return True
        for sub in (".gemini", ".config", ".local", ".ssh"):
            sub_dir = home_root / sub
            if resolved == sub_dir or sub_dir in resolved.parents:
                return True
    return False


def _is_protected_self_path(path_str: str) -> bool:
    if not path_str:
        return False
    expanded = os.path.expanduser(path_str.strip())
    try:
        resolved = Path(expanded).resolve()
    except Exception:
        resolved = Path(expanded)

    for prot in PROTECTED_SELF_PATHS:
        if resolved == prot:
            return True
    for base in (*HOME_ROOTS, Path.home(), Path.home().resolve()):
        sg_cfg = base / ".config" / "safety-gate"
        if resolved == sg_cfg or sg_cfg in resolved.parents:
            return True
    return False


def _is_git_hook_or_agent_config_path(path_str: str) -> bool:
    """
    Return True if `path_str` targets `.git/hooks/*`, `.git/config`, or project-level agent hook/settings JSON files
    (protects against autonomous Git hook / project config RCE: CVE-2026-26268 & CVE-2025-59536).
    """
    if not path_str:
        return False
    norm = path_str.strip().replace("\\", "/")
    if re.search(
        r"(?:^|/)\.git/(?:hooks(?:/|$)|config$)|(?:^|/)\.[a-z0-9_-]+/(?:hooks|settings)(?:\.local)?\.json$",
        norm,
    ):
        return True
    try:
        resolved_str = str(Path(os.path.expanduser(norm)).resolve()).replace("\\", "/")
        if re.search(
            r"(?:^|/)\.git/(?:hooks(?:/|$)|config$)|(?:^|/)\.[a-z0-9_-]+/(?:hooks|settings)(?:\.local)?\.json$",
            resolved_str,
        ):
            return True
    except Exception:
        pass
    return False


def _is_env_secret_file(path_str: str) -> bool:
    """Return True if `path_str` is a `.env` or `.env.*` secret file (excluding `.example`/`.sample`/`.template`)."""
    if not path_str:
        return False
    for candidate in (path_str, os.path.expanduser(path_str)):
        base = os.path.basename(candidate.strip().replace("\\", "/").rstrip("/"))
        if re.match(
            r"^\.env(?:\.[A-Za-z0-9_-]+)?(?<!\.example)(?<!\.sample)(?<!\.template)$",
            base,
            re.I,
        ):
            return True
    return False


def _is_within_allowed_read_roots(path_str: str, is_dir_listing: bool = False) -> bool:
    """
    Return True if `path_str` is within allowed workspace, `.gemini`, `.config/safety-gate`,
    `.local`, `/tmp`, `/opt/homebrew`, or standard non-secret developer dotfiles in `~`.
    (Sensitive credential files and `.env` files are checked BEFORE calling this function.)
    """
    if not path_str:
        return True
    if _is_within_allowed_roots(path_str):
        return True

    expanded = _norm_user_path_str(path_str)
    try:
        resolved = Path(expanded).resolve()
    except Exception:
        resolved = Path(expanded)

    allowed_read_dotfiles = {
        ".zshrc",
        ".zshenv",
        ".bashrc",
        ".bash_profile",
        ".zprofile",
        ".profile",
        ".gitconfig",
        ".gitignore",
        ".gitignore_global",
        ".tmux.conf",
        ".vimrc",
    }

    extra_read_subs = tuple(getattr(PRIVATE_RULES, "EXTRA_ALLOWED_READCWD_SUBDIRS", ()) or ())
    for home_root in HOME_ROOTS:
        if is_dir_listing and resolved in (
            home_root,
            home_root / ".ssh",
            home_root / ".config",
        ):
            return True
        if resolved.parent == home_root and resolved.name in allowed_read_dotfiles:
            return True
        ssh_dir = home_root / ".ssh"
        if resolved.parent == ssh_dir and (
            resolved.name in ("config", "known_hosts", "known_hosts.old", "authorized_keys")
            or resolved.name.endswith(".pub")
        ):
            return True
        for sub in (".gemini", ".config/safety-gate", ".local", *extra_read_subs):
            sub_dir = (home_root / sub).resolve()
            if resolved == sub_dir or sub_dir in resolved.parents:
                return True

    for sys_root in (Path("/opt/homebrew"), Path("/usr/local/share"), *EXTRA_READONLY_ROOTS):
        try:
            sr = sys_root.resolve()
            if resolved == sr or sr in resolved.parents:
                return True
        except Exception:
            pass

    if PRIVATE_RULES is not None and hasattr(PRIVATE_RULES, "extra_is_within_allowed_read_roots"):
        if PRIVATE_RULES.extra_is_within_allowed_read_roots(expanded, resolved):
            return True

    return False


def evaluate_read_tool(tool_name: str, args: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Evaluate file/directory read & search tools (`view_file`, `read_file`, `view_file_outline`,
    `view_code_item`, `grep_search`, `list_dir`, `find_by_name`).
    - Hard-denies reading sensitive credential/private-key files (`~/.ssh/id_ed25519`,
      `~/.config/safety-gate/credentials.enc`, `.encryption_key`, `client_secret.json`, etc.).
    - Escalates `.env` file reads and out-of-workspace personal file reads (`~/Desktop`,
      `~/Documents`, `~/Downloads`, `~/Library`, `/etc`) to Stage 3 full-context verification.
    - Fast-allows (<0.5ms) workspace, `.gemini`, `/tmp`, and standard non-secret dotfile reads.
    """
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
    if not target:
        return "allow", "static-allow", "No target path specified."

    is_dir_listing = tool_name in ("list_dir", "find_by_name")
    expanded = os.path.expanduser(target)
    try:
        resolved_str = str(Path(expanded).resolve())
    except Exception:
        resolved_str = expanded

    if not is_dir_listing:
        for candidate in dict.fromkeys((target, target.replace("\\", "/"), resolved_str, resolved_str.replace("\\", "/"))):
            for pat in SENSITIVE_CREDENTIAL_PATTERNS:
                if re.search(pat, candidate):
                    return (
                        "deny",
                        "static-deny",
                        f"Direct read of sensitive credential or private key file ({target}) is blocked.",
                    )
            if _is_env_secret_file(candidate):
                return (
                    "force_ask",
                    "static-env-read",
                    f"Reading `.env` secret file ({target}) requires full-context verification.",
                )

    if not _is_within_allowed_read_roots(target, is_dir_listing=is_dir_listing):
        return (
            "force_ask",
            "static-read-boundary",
            f"Reading outside ~/projects/ ({target}) requires explicit user authorization.",
        )

    return "allow", "static-allow", "File read within allowed workspace boundary."


def evaluate_file_tool(tool_name: str, args: Dict[str, Any]) -> Tuple[str, str, str]:
    """Evaluate write_to_file, write_file, replace_file_content, multi_replace_file_content, edit_file, notebook_edit."""
    target = str(args.get("TargetFile") or args.get("Path") or args.get("NotebookPath") or "").strip()
    if not target:
        return "allow", "static-allow", "No target file specified."

    expanded = os.path.expanduser(target)
    try:
        resolved_str = str(Path(expanded).resolve())
    except Exception:
        resolved_str = expanded

    for candidate in dict.fromkeys((target, target.replace("\\", "/"), resolved_str, resolved_str.replace("\\", "/"))):
        for pat in SENSITIVE_CREDENTIAL_PATTERNS:
            if re.search(pat, candidate):
                return (
                    "deny",
                    "static-deny",
                    f"Direct modification of sensitive credential file ({target}) is blocked.",
                )

    if _is_protected_self_path(target):
        return (
            "force_ask",
            "static-self-protect",
            f"Modifying safety configuration or hook file ({Path(target).name}) requires explicit user confirmation.",
        )

    if _is_git_hook_or_agent_config_path(target):
        return (
            "force_ask",
            "static-self-protect",
            f"Modifying Git hook or repository/agent config ({target}) requires full-context verification (CVE-2026-26268 / CVE-2025-59536).",
        )

    for candidate in dict.fromkeys((target, target.replace("\\", "/"), resolved_str, resolved_str.replace("\\", "/"))):
        if _is_env_secret_file(candidate):
            return (
                "force_ask",
                "static-env-write",
                f"Modifying `.env` secret file ({target}) requires full-context verification.",
            )

    if not _is_within_allowed_roots(target):
        return (
            "force_ask",
            "static-boundary",
            f"Writing outside ~/projects/ ({target}) requires explicit user confirmation.",
        )

    # Inspect proposed file content for embedded exfiltration sinks when editing non-test files
    base_name = os.path.basename(resolved_str)
    if base_name not in TRUSTED_CREDENTIAL_SCRIPT_NAMES and not base_name.startswith("test_") and not base_name.endswith(".md"):
        written_blobs: List[str] = []
        for k in ("CodeContent", "Content", "ReplacementContent", "Replacement", "NewSource"):
            val = args.get(k)
            if isinstance(val, str) and val:
                written_blobs.append(val)
        chunks = args.get("ReplacementChunks")
        if isinstance(chunks, list):
            for ch in chunks:
                if isinstance(ch, dict) and isinstance(ch.get("ReplacementContent"), str):
                    written_blobs.append(ch["ReplacementContent"])
        combined_content = "\n".join(written_blobs)
        if combined_content and re.search(
            r"\b(webhook\.site|requestbin\.|pipedream\.net|oastify\.com|burpcollaborator\.net|interact\.sh|canarytokens\.com)\b",
            combined_content.lower(),
        ):
            return (
                "force_ask",
                "static-content-exfil",
                f"File edit to `{base_name}` embeds a request-capture exfiltration domain and requires full-context verification.",
            )

    return "allow", "static-allow", "File write within allowed workspace boundary."


def _evaluate_external_url(raw_url: str, source_label: str = "URL request") -> Tuple[str, str, str]:
    """Inspect a URL for exfiltration sink domains, embedded raw API keys, or sensitive query parameters."""
    cleaned = (raw_url or "").strip()
    if not cleaned:
        return "allow", "static-allow", f"Empty {source_label}."

    lower_url = cleaned.lower()
    if re.search(
        r"\b(webhook\.site|requestbin\.|pipedream\.net|oastify\.com|burpcollaborator\.net|interact\.sh|canarytokens\.com)\b",
        lower_url,
    ):
        return (
            "deny",
            "static-deny",
            f"Blocked {source_label} to request-capture exfiltration sink ({cleaned[:80]}).",
        )
    if re.search(
        r"(AIza[0-9A-Za-z_-]{20,}|ya29\.[0-9A-Za-z_-]{20,}|ghp_[0-9A-Za-z]{20,}|sk-[0-9A-Za-z_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN\s+[A-Z ]*PRIVATE\s+KEY)",
        cleaned,
    ):
        return (
            "deny",
            "static-deny",
            f"Blocked {source_label} containing a raw API key or private key in the URL.",
        )
    if "?" in cleaned:
        query_part = cleaned.split("?", 1)[1]
        if re.search(
            r"(?:^|[&;])(secret|password|passwd|api_key|apikey|private_key|credentials|cred|env|exfil|leaked)=",
            query_part,
            re.I,
        ):
            return (
                "force_ask",
                "static-mcp-exfil",
                f"{source_label.capitalize()} URL contains sensitive-looking query parameters ({cleaned[:80]}); verifying against conversation context.",
            )
    return "allow", "static-allow", f"Safe {source_label}."


def evaluate_url_tool(tool_name: str, args: Dict[str, Any]) -> Tuple[str, str, str]:
    """Evaluate `read_url_content`, `open_browser_url`, or `read_browser_page`."""
    raw_url = str(args.get("Url") or args.get("url") or args.get("uri") or "").strip()
    return _evaluate_external_url(raw_url, source_label=f"`{tool_name}`")


def evaluate_mcp_tool(args: Dict[str, Any]) -> Tuple[str, str, str]:
    """Evaluate call_mcp_tool (e.g. playwright / browser-bridge)."""
    server = str(args.get("ServerName") or "").strip().lower()
    tool = str(args.get("ToolName") or "").strip().lower()
    mcp_args = args.get("Arguments") or {}
    if not isinstance(mcp_args, dict):
        mcp_args = {}

    read_only_mcp_tools = {
        "tabs_context",
        "read_page",
        "get_page_text",
        "find",
        "read_console_messages",
        "read_network_requests",
        "browser_snapshot",
        "browser_take_screenshot",
        "browser_console_messages",
        "browser_network_requests",
        "browser_tab_list",
        "browser_wait_for",
    }
    if tool in read_only_mcp_tools:
        return "allow", "static-allow", f"Read-only browser MCP tool ({server}/{tool})."

    # Inspect browser navigation URLs for indirect prompt-injection data exfiltration (PromptArmor advisory)
    if tool in ("navigate", "browser_navigate", "tabs_create"):
        raw_url = str(
            mcp_args.get("url") or mcp_args.get("Url") or mcp_args.get("uri") or ""
        ).strip()
        if raw_url:
            dec_u, stg_u, rsn_u = _evaluate_external_url(raw_url, source_label="browser navigation")
            if dec_u != "allow":
                return dec_u, stg_u, rsn_u

    # Check if clicking/submitting a final action button (e.g. form submit, delete, purchase)
    if tool in ("browser_click", "computer", "form_input", "javascript_tool"):
        serialized = json.dumps(mcp_args).lower()
        if re.search(
            r"\b(submit\s+(proposal|talk|application|form|order|payment)|delete\s+(account|repository|project)|confirm\s+purchase)\b",
            serialized,
        ):
            return (
                "force_ask",
                "static-mcp-submit",
                f"Browser action ({server}/{tool}) appears to submit or delete external state; confirming with user.",
            )

    return "allow", "static-allow", f"Standard MCP tool call ({server}/{tool})."



def _is_readonly_remote_shell(remote_cmd: str, depth: int = 0) -> bool:
    """
    Return True if `remote_cmd` executed over `ssh` consists exclusively of safe
    read-only inspection commands with no file output redirection or secret exfiltration.
    """
    if depth > 3:
        return False
    stripped = remote_cmd.strip()
    if not stripped:
        return True

    if any(re.search(pat, stripped) for pat in SENSITIVE_EXFIL_PATTERNS):
        return False
    if re.search(r"security\s+find-(generic|internet)-password", stripped):
        return False
    if _has_executable_sudo(stripped):
        return False

    segments = _split_shell_segments(stripped)
    if not segments:
        return True

    for seg in segments:
        seg_clean = re.sub(r"(?:(?<=\s)|^|\b[12])>>?\s*/dev/null\b|\b2>&1\b|&>>?\s*/dev/null\b", "", seg).strip()
        if not seg_clean:
            continue

        if _find_unquoted_redirection(seg_clean) is not None:
            return False

        if "`" in seg_clean or "$IFS" in seg_clean or "${IFS" in seg_clean:
            return False

        if "$(" in seg_clean:
            subs = re.findall(r"\$\(([^()]+)\)", seg_clean)
            if not subs:
                return False
            for sub_cmd in subs:
                if not _is_readonly_remote_shell(sub_cmd, depth + 1):
                    return False
            seg_clean = re.sub(r"\$\([^()]+\)", "CMD_SUB", seg_clean)
            if "$(" in seg_clean:
                return False

        try:
            tokens = shlex.split(seg_clean, posix=True)
        except ValueError:
            return False

        tokens = _strip_leading_env_and_wrappers(tokens)
        if not tokens:
            continue

        head = tokens[0]
        prog = os.path.basename(head)

        if prog in ("fi", "done", "esac"):
            continue

        if (
            prog == "for"
            and len(tokens) >= 3
            and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", tokens[1])
            and tokens[2] == "in"
        ):
            continue

        if prog in PURE_READ_BINARIES:
            if _has_pure_read_binary_exec_flag(prog, tokens):
                return False
            continue

        if prog in ("cd", "pushd", "popd", "export", "unset", "local", "ulimit", "umask"):
            continue

        if prog in ("sh", "bash", "zsh") and len(tokens) == 3 and tokens[1] in ("-c", "-lc"):
            if _is_readonly_remote_shell(tokens[2], depth + 1):
                continue
            return False

        if prog == "find":
            if any(
                t in ("-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls")
                for t in tokens[1:]
            ):
                return False
            continue

        if prog == "sed":
            if _has_sed_exec_or_inplace(tokens):
                return False
            continue

        if prog == "git":
            if _is_readonly_git_tokens(tokens):
                continue
            return False

        if prog == "hg":
            hg_idx = 1
            while hg_idx < len(tokens) and tokens[hg_idx].startswith("-"):
                if tokens[hg_idx] in ("-R", "--repository", "--cwd", "--config"):
                    if tokens[hg_idx] == "--config":
                        return False
                    hg_idx += 2
                elif tokens[hg_idx].startswith("--config="):
                    return False
                else:
                    hg_idx += 1
            hg_sub = tokens[hg_idx] if hg_idx < len(tokens) else "status"
            if hg_sub in READONLY_HG_SUBCOMMANDS:
                continue
            return False

        if prog == "gh":
            if _is_readonly_gh_tokens(tokens):
                continue
            return False

        if prog == "ssh-add":
            if tokens[1:] in (["-l"], ["-L"]):
                continue
            return False

        if prog == "tmux":
            if len(tokens) >= 2 and tokens[1] in (
                "ls",
                "list-sessions",
                "list-windows",
                "list-panes",
                "capture-pane",
                "show-options",
                "-V",
            ):
                continue
            return False

        if prog == "systemctl":
            if any(
                t in ("status", "is-active", "is-enabled", "list-units", "list-timers", "show")
                for t in tokens[1:]
            ):
                continue
            return False

        if prog == "journalctl":
            if not any(
                t.startswith(("--vacuum", "--rotate", "--flush", "--relinquish"))
                for t in tokens[1:]
            ):
                continue
            return False

        if prog == "tar":
            if _has_tar_exec_flag(tokens):
                return False
            # Streaming an archive to stdout (`tar -C <dir> -cf - .` or `tar czf - ...`) is read-only on remote host
            if "-" in tokens[1:] and any(
                t in ("-c", "--create") or (t.startswith("-") and not t.startswith("--") and "c" in t) or (idx == 1 and "c" in t)
                for idx, t in enumerate(tokens)
                if idx >= 1
            ):
                continue
            return False

        return False

    return True


def _check_ssh_command(tokens: List[str]) -> Optional[Tuple[str, str, str]]:
    """
    Inspect `ssh` invocations.
    - Pure local config/version queries (`ssh -V`, `ssh -G host`, `ssh -Q ...`) -> allow.
    - SSH ControlMaster multiplexing setup/checks (`ssh -M -S ... -fN host`, `ssh -S ... -O check host`) -> allow.
    - Remote commands that are strictly read-only (`_is_readonly_remote_shell`) -> allow.
    - Remote commands with `sudo` or disk formatting -> deny.
    - Anything else -> None (falls through to Stage 2 Gemini classifier).
    """
    idx = 1
    n = len(tokens)
    is_local_query = False
    destination = ""
    remote_tokens: List[str] = []

    while idx < n:
        tok = tokens[idx]
        if tok == "--":
            idx += 1
            if idx < n:
                destination = tokens[idx]
                remote_tokens = tokens[idx + 1 :]
            break
        if tok in ("-V", "-G"):
            is_local_query = True
            idx += 1
            continue
        if tok == "-Q" and idx + 1 < n:
            is_local_query = True
            idx += 2
            continue
        if tok in SSH_OPTS_WITH_ARG:
            if tok in SSH_TUNNEL_OR_MUX_OPTS:
                return None
            idx += 2
            continue
        if tok.startswith("-"):
            if any(tok.startswith(opt) and len(tok) > 2 for opt in SSH_TUNNEL_OR_MUX_OPTS):
                return None
            idx += 1
            continue
        destination = tok
        remote_tokens = tokens[idx + 1 :]
        break

    # Do not fast-allow if outer SSH options or destination contain command substitution
    outer_tokens = tokens[: len(tokens) - len(remote_tokens)]
    if any("$(" in t or "`" in t for t in outer_tokens):
        return None

    if is_local_query and not remote_tokens:
        return "allow", "static-allow", "Read-only local SSH configuration/version query."

    if destination and not remote_tokens:
        return "allow", "static-allow", f"SSH session / ControlMaster connection to `{destination}`."

    if not destination or not remote_tokens:
        return None

    remote_cmd = " ".join(remote_tokens).strip()
    if not remote_cmd:
        return None

    if _has_executable_sudo(remote_cmd):
        return "deny", "static-deny", "Remote `sudo` privilege escalation over SSH is blocked."

    if re.search(
        r"\b(mkfs|diskutil\s+erase(Disk|Volume)|dd\s+[^>]*of=/dev/(?!(?:null|zero|stdout|stderr|fd/)\b)[A-Za-z0-9_/-]+)",
        remote_cmd,
    ):
        return "deny", "static-deny", "Remote disk formatting / raw block device write over SSH is blocked."

    if _is_readonly_remote_shell(remote_cmd):
        return "allow", "static-allow", f"Read-only SSH command to `{destination}`."

    return None


def _check_rm_safety(tokens: List[str], cwd: str) -> Optional[Tuple[str, str, str]]:
    """Inspect `rm` arguments for catastrophic or broad deletions."""
    flags = [t for t in tokens[1:] if t.startswith("-")]
    targets = [t for t in tokens[1:] if not t.startswith("-")]
    is_recursive = any(
        "r" in f.lower() or f == "--recursive" for f in flags if not f.startswith("--") or f == "--recursive"
    )

    catastrophic_raw = {
        "/",
        "/*",
        "~",
        "~/",
        "~/*",
        "$HOME",
        "$HOME/",
        "$HOME/*",
        "${HOME}",
        "${HOME}/",
        "${HOME}/*",
        "/Users",
        "/Users/",
        "/home",
        "/home/",
        "/tmp",
        "/tmp/",
        "/tmp/*",
        "/var/tmp",
        "/var/tmp/",
        ".",
        "..",
        "../*",
        "*",
    }
    for hr in HOME_ROOTS:
        hs = str(hr)
        catastrophic_raw.update((hs, f"{hs}/", f"{hs}/*"))
    for wr in WORKSPACE_ROOTS:
        ws = str(wr)
        catastrophic_raw.update((ws, f"{ws}/", f"{ws}/*"))

    for tgt in targets:
        cleaned = tgt.strip("'\"")
        if cleaned in catastrophic_raw:
            return (
                "deny",
                "static-deny",
                f"Blocked destructive deletion target `{tgt}` in `rm` command.",
            )
        expanded = _norm_user_path_str(cleaned)
        if not os.path.isabs(expanded) and cwd:
            expanded = os.path.join(cwd, expanded)
        try:
            resolved = Path(expanded).resolve()
            norm_p = Path(os.path.normpath(expanded))
            critical_roots = {
                Path("/"),
                Path("/Users"),
                Path("/home"),
                Path("/tmp"),
                Path("/var/tmp"),
                *TMP_ROOTS,
                *HOME_ROOTS,
            }
            for wr in WORKSPACE_ROOTS:
                critical_roots.add(wr)
                for sub_crit in getattr(PRIVATE_RULES, "EXTRA_CRITICAL_SUBDIRS", ("dotfiles",)):
                    critical_roots.add(wr / sub_crit)
            if resolved in critical_roots or norm_p in critical_roots:
                return (
                    "deny",
                    "static-deny",
                    f"Blocked deletion of critical root directory ({resolved}).",
                )
        except Exception:
            pass

    if is_recursive:
        # Allow `rm -rf` only on narrow subdirectories inside ~/projects (e.g. build/dist/.cache/tmp) or /tmp
        for tgt in targets:
            cleaned = tgt.strip("'\"")
            if any(ch in cleaned for ch in ("$", "`", "*")):
                return (
                    "force_ask",
                    "static-ask",
                    f"Recursive deletion (`rm -rf`) with wildcard/variable `{tgt}` requires confirmation.",
                )
            expanded = os.path.expanduser(cleaned)
            if not os.path.isabs(expanded) and cwd:
                expanded = os.path.join(cwd, expanded)
            try:
                resolved = Path(expanded).resolve()
            except Exception:
                return (
                    "force_ask",
                    "static-ask",
                    f"Recursive deletion (`rm -rf {tgt}`) requires confirmation.",
                )
            if _is_protected_self_path(str(resolved)):
                return (
                    "force_ask",
                    "static-self-protect",
                    f"Deleting safety configuration ({resolved}) requires confirmation.",
                )
            # Allow known disposable build/temp paths without prompting
            safe_temp_names = {
                ".cache", *tuple(getattr(PRIVATE_RULES, "EXTRA_SAFE_TEMP_DIR_NAMES", ()) or ()),
                "node_modules",
                "dist",
                "build",
                "__pycache__",
                ".pytest_cache",
                "scratch",
            }
            is_temp_root = any(r in resolved.parents for r in TMP_ROOTS)
            is_safe_sub = any(
                wr in resolved.parents
                and len(resolved.relative_to(wr).parts) >= 2
                and (resolved.name in safe_temp_names or resolved.name.startswith(".tmp"))
                for wr in WORKSPACE_ROOTS
            ) or (
                any(br in resolved.parents for br in BRAIN_ROOTS)
                and (
                    "scratch" in resolved.parts
                    or resolved.name in safe_temp_names
                    or resolved.name.startswith(".tmp")
                )
            )
            if not (is_temp_root or is_safe_sub):
                return (
                    "force_ask",
                    "static-ask",
                    f"Recursive deletion (`rm -rf {tgt}`) requires user confirmation.",
                )
        return "allow", "static-allow", "Recursive deletion of temporary/build directory inside allowed workspace."

    return None



def _is_sensitive_credential_path(path_str: str) -> bool:
    """Return True if `path_str` matches any sensitive credential pattern that must never be sent to an LLM."""
    if not path_str:
        return False
    norm_path = path_str.replace("\\", "/")
    if any(re.search(pat, norm_path) for pat in SENSITIVE_CREDENTIAL_PATTERNS):
        return True
    base = os.path.basename(norm_path).lower()
    if (
        base.startswith(("client_secret", ".env", ".encryption_key", ".gemini_api_key"))
        or base in (".netrc", "credentials.enc", "credentials.json")
        or base.endswith((".pem", ".key", ".p12", ".pfx", ".enc"))
    ):
        return True
    return False


