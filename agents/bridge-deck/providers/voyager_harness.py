#!/usr/bin/env python3
"""
VoyagerHarnessProvider implementing AgentProvider.
Equips Google Model Garden models (Gemini, Claude, Gemma) with the Voyager Harness:
  - Epistemic Grounding via Workspace Tools (read_file, grep_search, list_dir)
  - Allowlisted Inspection Commands (run_command) within ACL boundaries
  - Iterative Action-Reflection ReAct Loop with audit thinking blocks
"""

import os
import re
import sys
import json
import time
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from providers.base import AgentProvider

try:
    from model_client import GCPModelClient
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from model_client import GCPModelClient

try:
    from core.history import format_history_block
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.history import format_history_block

ROOT_DIR = Path(__file__).resolve().parent.parent


class VoyagerHarnessProvider(AgentProvider):
    def __init__(self, provider_id: str = "voyager-harness", config: Optional[Dict[str, Any]] = None):
        super().__init__(provider_id, config)
        self.model_name = self.config.get("model", "gemini-2.5-flash")
        self.project_id = self.config.get("project_id") or self.config.get("project") or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        self.location = self.config.get("location", "us-central1")
        self.max_tool_iterations = self.config.get("max_iterations", 5)
        self.tools_enabled = list(self.config.get("tools_enabled") or [])

        self.client = GCPModelClient(
            project_id=self.project_id,
            location=self.location,
            model_name=self.model_name
        )

    def _execute_tool(self, tool_name: str, args: Dict[str, Any], allowed_dirs: List[str]) -> Tuple[bool, str]:
        """Executes a workspace tool within ACL safety boundaries."""
        try:
            if tool_name not in self.tools_enabled:
                return False, f"ACL Permission Denied: Tool '{tool_name}' is not in authorized tools_enabled list: {self.tools_enabled}"

            allowed_roots = [Path(d).resolve() for d in allowed_dirs if d]
            if not allowed_roots:
                return False, "ACL Permission Denied: no authorized directories configured for this agent."

            def is_path_allowed(p: Path) -> bool:
                return any(p.is_relative_to(r) for r in allowed_roots)

            def resolve_tool_path(rel_or_abs: str) -> Path:
                if not rel_or_abs or rel_or_abs.strip() in [".", "./"]:
                    return allowed_roots[0]
                raw_p = Path(rel_or_abs.strip())
                if raw_p.is_absolute():
                    return raw_p.resolve()
                for root in allowed_roots:
                    cand = (root / raw_p).resolve()
                    if cand.exists():
                        return cand
                return (allowed_roots[0] / raw_p).resolve()

            if tool_name == "read_file":
                rel_or_abs = args.get("path", "")
                p = resolve_tool_path(rel_or_abs)
                if not is_path_allowed(p):
                    return False, f"ACL Permission Denied: '{p}' is outside authorized directories ({[str(r) for r in allowed_roots]})"
                if not p.exists() or not p.is_file():
                    return False, f"File not found: '{p}'"
                content = p.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                if len(lines) > 200:
                    content = "\n".join(lines[:200]) + f"\n... [Truncated {len(lines)-200} lines]"
                return True, content

            elif tool_name == "list_dir":
                rel_or_abs = args.get("path", "")
                p = resolve_tool_path(rel_or_abs)
                if not is_path_allowed(p):
                    return False, f"ACL Permission Denied: '{p}' is outside authorized directories"
                if not p.exists() or not p.is_dir():
                    return False, f"Directory not found: '{p}'"
                items = sorted([f.name + ("/" if f.is_dir() else "") for f in p.iterdir() if not f.name.startswith(".")])
                return True, "\n".join(items[:50])

            elif tool_name == "grep_search":
                query = args.get("query", "")
                target_dir = args.get("path", "")
                p = resolve_tool_path(target_dir)
                if not is_path_allowed(p):
                    return False, f"ACL Permission Denied: '{p}' is outside authorized directories"
                cmd = ["grep", "-rnI", "--exclude-dir=.git", "--exclude-dir=venv", "--exclude-dir=node_modules", query, str(p)]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                out = res.stdout.strip()
                if not out:
                    return True, "No matches found."
                lines = out.splitlines()
                return True, "\n".join(lines[:30])

            elif tool_name == "run_command":
                cmd_str = args.get("command", "")
                cwd_arg = args.get("cwd", "")
                p = resolve_tool_path(cwd_arg)
                if not is_path_allowed(p):
                    return False, f"ACL Permission Denied: cwd '{p}' is outside authorized directories"
                
                # Check command executable allowlist
                parts = shlex.split(cmd_str) if cmd_str else []
                if not parts:
                    return False, "Empty command string."
                exe = parts[0].lower()
                safe_executables = {"git", "ls", "grep", "cat", "head", "tail", "echo"}
                if exe not in safe_executables:
                    return False, f"Command '{exe}' not in allowed inspection set: {sorted(list(safe_executables))}"

                # Reject dangerous flags that escape cwd or execute arbitrary code (including equals form)
                disallowed_flags = {"-C", "--git-dir", "--work-tree", "-exec", "--exec"}
                if any(t == f or t.startswith(f + "=") for t in parts for f in disallowed_flags):
                    return False, "Command rejected: argument contains directory escape or code execution flag."

                # If git, enforce read-only inspection subcommands
                if exe == "git":
                    subcmd = ""
                    for token in parts[1:]:
                        if not token.startswith("-"):
                            subcmd = token.lower()
                            break
                    safe_git_subcommands = {"status", "log", "diff", "show", "blame", "branch", "remote", "ls-files", "rev-parse"}
                    if not subcmd or subcmd not in safe_git_subcommands:
                        return False, f"Git subcommand '{subcmd}' not in allowed inspection set: {sorted(list(safe_git_subcommands))}"

                # Validate any non-flag argument that resolves to an existing filesystem path
                for token in parts[1:]:
                    if token.startswith("-"):
                        continue
                    candidate_path = Path(token) if Path(token).is_absolute() else (p / token)
                    candidate_path = candidate_path.resolve()
                    if candidate_path.exists() and not is_path_allowed(candidate_path):
                        return False, f"ACL Permission Denied: path argument '{token}' resolves outside authorized directories."

                res = subprocess.run(parts, shell=False, cwd=str(p), capture_output=True, text=True, timeout=15)
                out = (res.stdout + "\n" + res.stderr).strip()
                return True, f"Exit code {res.returncode}:\n{out[:2000]}"

            else:
                return False, f"Unknown tool: '{tool_name}'"
        except Exception as e:
            return False, f"Tool execution error: {e}"

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        project_dirs = (context.get("directories") if context else None) or []
        manifest_dirs = self.config.get("access_read") or []
        if manifest_dirs and project_dirs:
            proj_norm = {str(Path(d).resolve()) for d in project_dirs if d}
            allowed_dirs = [d for d in manifest_dirs if d and str(Path(d).resolve()) in proj_norm]
        elif manifest_dirs:
            allowed_dirs = list(manifest_dirs)
        else:
            allowed_dirs = []
        self_name = (context.get("self_name") if context else None) or "Agent"

        # Build Full System Prompt with Voyager Harness Tool Specifications
        TOOL_DOCS = {
            "read_file": "- read_file(path: str): Reads the contents of a file in the workspace.",
            "list_dir": "- list_dir(path: str): Lists files in a directory.",
            "grep_search": "- grep_search(query: str, path: str): Searches for pattern matches in code/text.",
            "run_command": "- run_command(command: str, cwd: str): Runs allowlisted read-only inspection commands (git log/status/diff, ls, grep, cat, head, tail, echo)."
        }
        active_tools = [TOOL_DOCS[t] for t in self.tools_enabled if t in TOOL_DOCS]
        tools_doc_str = "\n".join(active_tools)

        full_system = system_prompt or ""
        if context and context.get("self_context") and context["self_context"] not in full_system:
            full_system = context["self_context"] + "\n\n" + full_system

        if active_tools:
            valid = [t for t in self.tools_enabled if t in TOOL_DOCS]
            example_tool = "read_file" if "read_file" in valid else valid[0]
            example_args = '{"path": "README.md"}' if example_tool in ["read_file", "list_dir"] else ('{"query": "def main", "path": "."}' if example_tool == "grep_search" else '{"command": "git status", "cwd": "."}')
            harness_instruction = (
                "=== VOYAGER AGENT HARNESS ACTIVE ===\n"
                "You are equipped with the Voyager Agent Harness, providing real-time workspace tools and epistemic grounding.\n"
                "If a user asks about files, code, tests, stats, or project state, YOU DO NOT GUESS. You call the tool to inspect reality.\n\n"
                f"Available Workspace Tools:\n{tools_doc_str}\n\n"
                "To invoke a tool, output a single JSON code block in this EXACT format:\n"
                "```tool_call\n"
                "{\n"
                f'  "tool": "{example_tool}",\n'
                f'  "args": {example_args}\n'
                "}\n"
                "```\n"
                "You will immediately receive the tool output and can then formulate your grounded response or call another tool.\n"
                "Once you have all facts, provide your final helpful, warm, and articulate response to the team.\n"
                "===================================="
            )
            full_system = harness_instruction + "\n\n" + full_system

        bridge_dir = context.get("bridge_dir") if context else None
        history_block = format_history_block(messages, self_name=self_name, bridge_dir=bridge_dir)
        if history_block:
            full_system = f"{full_system}\n\n{history_block}"

        thinking_blocks = ["Evaluated residual stream deliberation and architectural parameters."]
        current_prompt = prompt

        try:
            for iteration in range(self.max_tool_iterations):
                # Call underlying model
                resp_text = self.client.generate(
                    prompt=current_prompt,
                    system_prompt=full_system,
                    messages_list=messages,
                    allowed_roots=allowed_dirs
                )

                # Check if model emitted a tool call
                tool_match = re.search(r"```tool_call\s*(\{.*?\})\s*```", resp_text, re.DOTALL)
                if not tool_match:
                    # No tool call, model has finalized response
                    elapsed = round(time.time() - start_time, 2)
                    thinking_blocks.append(f"Deliberation complete in {iteration + 1} turns ({elapsed}s).")
                    return {
                        "success": True,
                        "response": resp_text.strip(),
                        "model": f"{self.model_name} (Voyager Harness)",
                        "elapsed_seconds": elapsed,
                        "thinking_blocks": thinking_blocks,
                        "error": None
                    }

                # Parse tool call
                raw_json = tool_match.group(1)
                try:
                    call_data = json.loads(raw_json)
                    tool_name = call_data.get("tool")
                    args = call_data.get("args", {})
                except Exception as parse_err:
                    thinking_blocks.append(f"⚠️ Tool parse error: {parse_err}")
                    current_prompt = f"{current_prompt}\n\n[System Error: Invalid JSON in tool_call. Please re-format.]"
                    continue

                thinking_blocks.append(f"🛠️ Executed tool via Voyager Harness: `{tool_name}({json.dumps(args)})`")
                success, tool_output = self._execute_tool(tool_name, args, allowed_dirs)

                # Feed tool output back into the next iteration
                observation = (
                    f"--- TOOL OBSERVATION ({tool_name}) ---\n"
                    f"Status: {'Success' if success else 'Failed'}\n"
                    f"Output:\n{tool_output}\n"
                    f"--------------------------------------\n"
                    f"Now provide your grounded response, or call another tool if needed."
                )

                current_prompt = f"{current_prompt}\n\n{resp_text}\n\n{observation}"

            # Fallback if iterations exhausted
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": True,
                "response": resp_text.strip(),
                "model": f"{self.model_name} (Voyager Harness)",
                "elapsed_seconds": elapsed,
                "thinking_blocks": thinking_blocks,
                "error": None
            }

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": False,
                "response": None,
                "model": self.model_name,
                "elapsed_seconds": elapsed,
                "thinking_blocks": thinking_blocks,
                "error": str(e)
            }
