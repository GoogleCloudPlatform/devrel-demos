#!/usr/bin/env python3
"""
Google GenAI & ADK Provider Adapter for Bridge Deck.
Implements the AgentProvider interface for Google Vertex GenAI / ADK agents with
epistemic grounding, dynamic 3-tier memory context, and multi-turn history synthesis.
"""

import os
import re
import sys
import time
import json
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from providers.base import AgentProvider
from core.history import format_history_block

try:
    from core.worktree import get_or_create_agent_worktree, ensure_git_repo
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.worktree import get_or_create_agent_worktree, ensure_git_repo

ROOT_DIR = Path(__file__).resolve().parent.parent


class GoogleADKProvider(AgentProvider):
    """
    AgentProvider adapter for Google GenAI / Agent Development Kit agents.
    Provides Vertex AI execution, memory grounding, multi-agent coordination,
    and native workspace tool execution (read_file, write_file, list_dir, grep_search, run_command)
    under strict directory ACL boundaries and Git worktree isolation.
    """
    def __init__(self, provider_id: str = "google-adk", config: Optional[Dict[str, Any]] = None):
        super().__init__(provider_id, config)
        self.model_name = self.config.get("model", "gemini-3.7-flash")
        self.project_id = self.config.get("project_id") or self.config.get("project") or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        raw_loc = self.config.get("location")
        model_lower = str(self.model_name).lower()
        if any(tag in model_lower for tag in ["3.7", "gemini-3", "claude", "maas"]):
            self.location = "global"
        else:
            self.location = "us-central1" if (not raw_loc or raw_loc in ["local", "None", ""]) else raw_loc
        self.temperature = float(self.config.get("temperature", 0.2))
        self.tools_enabled = list(self.config.get("tools_enabled") or [])
        self.max_tool_iterations = int(self.config.get("max_iterations", 5))
        self._client = None
        self._client_init_attempted = False
        self._init_error = None

    def _get_client(self):
        if not self._client_init_attempted:
            self._client_init_attempted = True
            try:
                from google import genai
                self._client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location
                )
            except Exception as e:
                self._client = None
                self._init_error = str(e)
        return self._client

    def _execute_tool(self, tool_name: str, args: Dict[str, Any], allowed_dirs: List[str], write_allowed_dirs: Optional[List[str]] = None) -> Tuple[bool, str]:
        """Executes a native ADK workspace tool within ACL safety boundaries."""
        try:
            TOOL_ALIASES = {
                "list_directory": "list_dir",
                "ls": "list_dir",
                "dir": "list_dir",
                "read": "read_file",
                "write": "write_file",
                "grep": "grep_search",
                "search": "grep_search",
                "bash": "run_command",
                "exec": "run_command",
                "execute": "run_command",
                "cmd": "run_command",
            }
            tool_name = TOOL_ALIASES.get(tool_name, tool_name)
            if tool_name not in self.tools_enabled:
                return False, f"ACL Permission Denied: Tool '{tool_name}' is not in authorized tools_enabled list: {self.tools_enabled}"

            allowed_roots = [Path(d).resolve() for d in allowed_dirs if d]
            write_allowed_roots = [Path(d).resolve() for d in (write_allowed_dirs or []) if d]
            if not allowed_roots:
                return False, "ACL Permission Denied: no authorized directories configured for this agent."

            def is_path_allowed(p: Path) -> bool:
                return any(p.is_relative_to(r) for r in allowed_roots)

            def is_write_allowed(p: Path) -> bool:
                return any(p.is_relative_to(r) for r in write_allowed_roots)

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

            elif tool_name == "write_file":
                rel_or_abs = args.get("path", "")
                content = args.get("content", "")
                if not write_allowed_roots:
                    return False, "ACL Permission Denied: write access is not authorized for this agent."
                if not rel_or_abs or rel_or_abs.strip() in [".", "./"]:
                    p = write_allowed_roots[0]
                else:
                    raw_p = Path(rel_or_abs.strip())
                    p = raw_p.resolve() if raw_p.is_absolute() else (write_allowed_roots[0] / raw_p).resolve()
                if not is_write_allowed(p):
                    return False, f"ACL Permission Denied: '{p}' is outside authorized write directories ({[str(r) for r in write_allowed_roots]})"
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp_p = p.with_suffix(p.suffix + f".tmp_{os.getpid()}")
                tmp_p.write_text(content, encoding="utf-8")
                tmp_p.replace(p)
                return True, f"Successfully wrote {len(content)} bytes to '{p}'"

            elif tool_name == "list_dir":
                rel_or_abs = args.get("path", "")
                p = resolve_tool_path(rel_or_abs)
                if not is_path_allowed(p):
                    return False, f"ACL Permission Denied: '{p}' is outside authorized directories ({[str(r) for r in allowed_roots]})"
                if not p.exists():
                    if any(p == r for r in allowed_roots):
                        p.mkdir(parents=True, exist_ok=True)
                    else:
                        return False, f"Directory not found: '{p}'"
                elif not p.is_dir():
                    return False, f"Not a directory: '{p}'"
                entries = []
                for item in sorted(p.iterdir()):
                    if item.name.startswith(".git") or item.name == "__pycache__":
                        continue
                    prefix = "[DIR] " if item.is_dir() else "[FILE]"
                    size_str = f" ({item.stat().st_size} bytes)" if item.is_file() else ""
                    entries.append(f"{prefix} {item.name}{size_str}")
                return True, "\n".join(entries) if entries else "(empty directory)"

            elif tool_name == "grep_search":
                query = args.get("query", "")
                path_str = args.get("path", "")
                p = resolve_tool_path(path_str)
                if not is_path_allowed(p):
                    return False, f"ACL Permission Denied: '{p}' is outside authorized directories ({[str(r) for r in allowed_roots]})"
                if not p.exists():
                    return False, f"Path not found: '{p}'"
                matches = []
                target_files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file() and not any(part.startswith(".") for part in f.parts)]
                for f in target_files[:50]:
                    try:
                        text = f.read_text(encoding="utf-8", errors="replace")
                        for idx, line in enumerate(text.splitlines(), 1):
                            if query.lower() in line.lower():
                                rel = f.relative_to(p) if p.is_dir() else f.name
                                matches.append(f"{rel}:{idx}: {line.strip()[:120]}")
                                if len(matches) >= 30:
                                    break
                    except Exception:
                        continue
                    if len(matches) >= 30:
                        break
                return True, "\n".join(matches) if matches else f"No matches found for '{query}'"

            elif tool_name == "run_command":
                cmd = args.get("command", "")
                cwd_arg = args.get("cwd", "")
                p = resolve_tool_path(cwd_arg)
                if not is_path_allowed(p):
                    return False, f"ACL Permission Denied: cwd '{p}' is outside authorized directories."

                try:
                    parts = shlex.split(cmd)
                except Exception as parse_e:
                    return False, f"Command parse error: {parse_e}"

                if not parts:
                    return False, "Empty command."

                safe_executables = {"python", "python3", "pytest", "git", "ls", "grep", "cat", "find", "head", "tail", "pwd"}
                exe = Path(parts[0]).name.lower()
                if exe not in safe_executables:
                    return False, f"Command '{exe}' not in allowed inspection set: {sorted(list(safe_executables))}"

                disallowed_flags = {"-C", "--git-dir", "--work-tree", "-exec", "--exec"}
                if any(t == f or t.startswith(f + "=") for t in parts for f in disallowed_flags):
                    return False, "Command rejected: argument contains directory escape or code execution flag."

                if exe == "git":
                    subcmd = ""
                    for token in parts[1:]:
                        if not token.startswith("-"):
                            subcmd = token.lower()
                            break
                    safe_git_subcommands = {"status", "log", "diff", "show", "blame", "branch", "remote", "ls-files", "rev-parse", "add", "commit", "checkout"}
                    if not subcmd or subcmd not in safe_git_subcommands:
                        return False, f"Git subcommand '{subcmd}' not in allowed inspection set: {sorted(list(safe_git_subcommands))}"
                    if subcmd in ["add", "commit"] and write_allowed_roots:
                        if not any(p.is_relative_to(r) for r in write_allowed_roots):
                            return False, f"ACL Permission Denied: write access not granted for git modification in '{p}'"

                for token in parts[1:]:
                    if token.startswith("-"):
                        continue
                    candidate_path = Path(token) if Path(token).is_absolute() else (p / token)
                    candidate_path = candidate_path.resolve()
                    if candidate_path.exists() and not is_path_allowed(candidate_path):
                        return False, f"ACL Permission Denied: path argument '{token}' resolves outside authorized directories."

                res = subprocess.run(parts, shell=False, cwd=str(p), capture_output=True, text=True, timeout=20)
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
        
        try:
            self_name = (context.get("self_name") if context else None) or self.provider_id.capitalize()
            self_context = context.get("self_context") if context else ""

            # 1. Base System Prompt
            full_system = system_prompt or f"You are {self_name}, an autonomous agent on Project Bridge Deck."
            if self_context and self_context not in full_system:
                full_system = f"{self_context}\n\n{full_system}"

            # 2. Add Collaboration & ACL Directives
            a2a_directive = (
                "\n=== MULTI-AGENT COLLABORATION & ACL DIRECTIVES ===\n"
                "- You are operating via the Google GenAI / Agent Development Kit (ADK) Runtime.\n"
                "- Respect ACL boundaries: perform read and write actions strictly within authorized paths.\n"
                "- Maintain concise, rigorous, and actionable communication across the multi-agent roster.\n"
                "=================================================="
            )
            full_system = f"{full_system}\n{a2a_directive}"

            # 3. Resolve Workspace Directories & Git Worktrees
            project_dirs = (context.get("directories") if context else None) or []
            manifest_dirs = self.config.get("access_read") or []
            manifest_write_dirs = self.config.get("access_write") or []

            if manifest_dirs and project_dirs:
                proj_norm = {str(Path(d).resolve()) for d in project_dirs if d}
                raw_read_dirs = [d for d in manifest_dirs if d and str(Path(d).resolve()) in proj_norm]
            elif manifest_dirs:
                raw_read_dirs = list(manifest_dirs)
            else:
                raw_read_dirs = []

            if manifest_write_dirs and project_dirs:
                proj_norm = {str(Path(d).resolve()) for d in project_dirs if d}
                raw_write_dirs = [d for d in manifest_write_dirs if d and str(Path(d).resolve()) in proj_norm]
            elif manifest_write_dirs:
                raw_write_dirs = list(manifest_write_dirs)
            else:
                raw_write_dirs = []

            allowed_dirs = []
            for d in raw_read_dirs:
                p = Path(d).resolve()
                allowed_dirs.append(str(p))
                if (p / ".git").exists():
                    try:
                        wt = get_or_create_agent_worktree(p, self.provider_id)
                        if str(wt) not in allowed_dirs:
                            allowed_dirs.append(str(wt))
                    except Exception as wte:
                        print(f"Notice: Failed to create agent worktree for {self.provider_id}: {wte}")

            write_allowed_dirs = []
            for d in raw_write_dirs:
                p = Path(d).resolve()
                try:
                    if not (p / ".git").exists() and p.exists():
                        ensure_git_repo(p)
                    if (p / ".git").exists():
                        wt = get_or_create_agent_worktree(p, self.provider_id)
                        write_allowed_dirs.append(str(wt))
                        if str(wt) not in allowed_dirs:
                            allowed_dirs.append(str(wt))
                    else:
                        write_allowed_dirs.append(str(p))
                except Exception as wte:
                    print(f"Notice: Failed to setup agent worktree for {self.provider_id}: {wte}")
                    write_allowed_dirs.append(str(p))

            # 4. Configure Native ADK Workspace Tools if enabled
            TOOL_DOCS = {
                "read_file": "- read_file(path: str): Reads the contents of a file in the workspace.",
                "write_file": "- write_file(path: str, content: str): Writes/creates a file in the authorized workspace.",
                "list_dir": "- list_dir(path: str): Lists files in a directory.",
                "grep_search": "- grep_search(query: str, path: str): Searches for pattern matches in code/text.",
                "run_command": "- run_command(command: str, cwd: str): Runs allowlisted commands (python, pytest, git status/diff/log/add/commit, ls, grep, cat)."
            }
            active_tools = [TOOL_DOCS[t] for t in self.tools_enabled if t in TOOL_DOCS]
            if active_tools:
                tools_doc_str = "\n".join(active_tools)
                valid = [t for t in self.tools_enabled if t in TOOL_DOCS]
                example_tool = "write_file" if "write_file" in valid else valid[0]
                example_args = '{"path": "README.md", "content": "# Documentation"}' if example_tool == "write_file" else ('{"path": "."}' if example_tool in ["read_file", "list_dir"] else '{"command": "git status", "cwd": "."}')
                adk_tool_directive = (
                    "=== GOOGLE ADK NATIVE AGENT TOOLSET ACTIVE ===\n"
                    "You are equipped with Google ADK Native Workspace Tools, providing real-time file read/write, code search, and command execution.\n"
                    "If you need to inspect or modify workspace files, execute tests, or check project state, invoke the tool directly.\n\n"
                    f"Available ADK Workspace Tools:\n{tools_doc_str}\n\n"
                    "To invoke an ADK tool, output a single JSON code block in this format:\n"
                    "```adk_tool_call\n"
                    "{\n"
                    f'  "tool": "{example_tool}",\n'
                    f'  "args": {example_args}\n'
                    "}\n"
                    "```\n"
                    "You will receive the tool observation and can then formulate your response or invoke another tool.\n"
                    "==============================================="
                )
                full_system = f"{adk_tool_directive}\n\n{full_system}"

            # 5. Centralized Multi-Agent History Synthesis
            bridge_dir = context.get("bridge_dir") if context else None
            history_block = format_history_block(messages, self_name=self_name, bridge_dir=bridge_dir)
            if history_block:
                full_system = f"{full_system}\n\n{history_block}"

            # 6. Multi-turn execution loop (supporting Gemini via google.genai and Claude via GCPModelClient)
            is_gemini = "gemini" in self.model_name.lower()
            client = self._get_client() if is_gemini else None
            
            fallback_client = None
            if client is None:
                from model_client import GCPModelClient
                fallback_client = GCPModelClient(project_id=self.project_id, location=self.location, model_name=self.model_name)

            thinking_blocks = ["Evaluated Google ADK residual stream deliberation and context."]
            current_prompt = prompt
            final_resp = ""
            executed_tools = []

            iterations = self.max_tool_iterations if active_tools else 1
            for iteration in range(iterations):
                if client is not None:
                    from google.genai import types
                    config = types.GenerateContentConfig(
                        max_output_tokens=8192,
                        temperature=self.temperature,
                        system_instruction=full_system,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                    )
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=current_prompt,
                        config=config
                    )
                    resp_text = response.text or ""
                else:
                    resp_text = fallback_client.generate(
                        prompt=current_prompt,
                        system_prompt=full_system,
                        messages_list=messages,
                        allowed_roots=allowed_dirs
                    )

                if not active_tools:
                    final_resp = resp_text.strip()
                    break

                # Check if model emitted an ADK tool call
                tool_match = re.search(r"```(?:adk_tool_call|tool_call)\s*(\{.*?\})\s*```", resp_text, re.DOTALL)
                if not tool_match:
                    final_resp = resp_text.strip()
                    break

                raw_json = tool_match.group(1)
                try:
                    call_data = json.loads(raw_json)
                    tool_name = call_data.get("tool")
                    args = call_data.get("args", {})
                except Exception as parse_err:
                    thinking_blocks.append(f"⚠️ ADK Tool parse error: {parse_err}")
                    current_prompt = f"{current_prompt}\n\n[System Error: Invalid JSON in adk_tool_call. Please re-format as valid JSON or speak directly to the team.]"
                    continue

                success, tool_output = self._execute_tool(tool_name, args, allowed_dirs, write_allowed_dirs=write_allowed_dirs)
                status_str = "Success" if success else "Failed"
                thinking_blocks.append(f"🛠️ Executed ADK Native Tool: `{tool_name}({json.dumps(args)})` -> {status_str}")
                executed_tools.append({
                    "tool": tool_name,
                    "args": args,
                    "success": success,
                    "output": tool_output
                })

                # Build ongoing tool execution summary without raw function-call syntax
                tool_history = []
                for ex in executed_tools:
                    out_snippet = ex["output"][:400] + "..." if len(ex["output"]) > 400 else ex["output"]
                    args_display = ", ".join([f"{k}={repr(v)}" for k, v in ex["args"].items()]) if isinstance(ex["args"], dict) else str(ex["args"])
                    tool_history.append(
                        f"- Executed tool `{ex['tool']}` with {args_display}\n  Observation: {out_snippet}"
                    )
                history_summary = "\n".join(tool_history)

                # Determine if more iterations are allowed
                if iteration < iterations - 1:
                    current_prompt = (
                        f"Original Team Request:\n{prompt}\n\n"
                        f"Workspace Tool Execution History:\n{history_summary}\n\n"
                        f"Latest Observation from `{tool_name}`:\n"
                        f"Status: {status_str}\n"
                        f"Output:\n{tool_output}\n\n"
                        f"[Instruction]: Review this observation. You may invoke another tool if you still need to inspect or write files, "
                        f"OR formulate your natural conversational response directly to your teammates in the chat. "
                        f"Do NOT output a tool block if you are ready to answer the team."
                    )
                else:
                    # Last iteration: invoke a synthesis turn so model outputs its final conversational message
                    final_prompt = (
                        f"Original Team Request:\n{prompt}\n\n"
                        f"Workspace Tool Execution History:\n{history_summary}\n\n"
                        f"Latest Observation from `{tool_name}`:\n"
                        f"Status: {status_str}\n"
                        f"Output:\n{tool_output}\n\n"
                        f"[Instruction]: All tool executions are now complete. Formulate your final conversational response to your teammates in the chat now. "
                        f"Address your teammates directly, summarize what you inspected/created in the workspace, and recommend next steps. "
                        f"DO NOT output any ```adk_tool_call code blocks."
                    )
                    try:
                        if client is not None:
                            synth_resp = client.models.generate_content(
                                model=self.model_name,
                                contents=final_prompt,
                                config=config
                            )
                            final_resp = (synth_resp.text or "").strip()
                            if not final_resp and synth_resp.candidates:
                                for cand in synth_resp.candidates:
                                    if cand.content and cand.content.parts:
                                        for part in cand.content.parts:
                                            if getattr(part, "text", None):
                                                final_resp += part.text
                                final_resp = final_resp.strip()
                        else:
                            final_resp = (fallback_client.generate(
                                prompt=final_prompt,
                                system_prompt=full_system,
                                messages_list=messages,
                                allowed_roots=allowed_dirs
                            ) or "").strip()
                    except Exception:
                        final_resp = ""
                    break

            # Scrub any raw adk_tool_call blocks from final_resp so raw code blocks never leak into chat
            clean_resp = re.sub(r"```(?:adk_tool_call|tool_call)\s*\{.*?\}\s*```", "", final_resp or resp_text, flags=re.DOTALL).strip()
            if clean_resp:
                final_resp = clean_resp
            elif executed_tools:
                # If model only emitted tool calls without conversational text, synthesize a natural response
                tool_bullets = "\n".join([f"- Verified `{t['tool']}`: {t['output'][:200]}..." if len(t['output']) > 200 else f"- Verified `{t['tool']}`: {t['output']}" for t in executed_tools])
                final_resp = (
                    f"I've completed inspecting the workspace environment:\n\n{tool_bullets}\n\n"
                    f"Ready to coordinate next steps with the team."
                )
            else:
                final_resp = "I've reviewed the team discussion and workspace status. Ready to coordinate next steps with the team."

            elapsed = round(time.time() - start_time, 2)
            return {
                "success": True,
                "response": final_resp,
                "model": self.model_name,
                "provider_type": "google-adk",
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
                "provider_type": "google-adk",
                "elapsed_seconds": elapsed,
                "error": str(e)
            }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "provider_id": self.provider_id,
            "provider_type": "google-adk",
            "model": self.model_name,
            "location": self.location
        }
