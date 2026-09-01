#!/usr/bin/env python3
"""
GCP Model Client Module for Bridge Deck.
Provides a unified interface for calling Google Gemini models (via google.genai SDK)
and Anthropic Claude models (via anthropic.AnthropicVertex SDK) on GCP Vertex AI.
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

class GCPModelClient:
    """
    Unified client for invoking GCP Vertex AI models (Gemini & Anthropic Claude).
    """
    def __init__(
        self,
        project_id: Optional[str] = None,
        location: str = "global",
        model_name: str = "gemini-3.7-flash",
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 8192
    ):
        try:
            from core.router import MODEL_ALIASES, DEFAULT_MODEL
        except ImportError:
            MODEL_ALIASES = {}
            DEFAULT_MODEL = "gemini-3.7-flash"

        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("GCP_LOCATION", "us-central1")
        
        # Standardize and sanitize model name
        raw_name = (model_name or DEFAULT_MODEL).strip()
        model_name_clean = MODEL_ALIASES.get(raw_name.lower(), raw_name)
        self.model_name = model_name_clean

        if "claude" in model_name_clean.lower():
            self.provider = "anthropic"
            if not self.location or self.location in ["local", "None", ""]:
                self.location = "global"
            if not model_name_clean.startswith("publishers/anthropic/models/"):
                clean_name = model_name_clean.replace("anthropic-", "").replace("publishers/anthropic/models/", "")
                self.anthropic_model_id = clean_name
            else:
                self.anthropic_model_id = model_name_clean.split("/")[-1]
        else:
            self.provider = "google"
            if not model_name_clean.startswith("publishers/google/models/"):
                self.gemini_model_id = f"publishers/google/models/{model_name_clean}"
            else:
                self.gemini_model_id = model_name_clean

        if not self.project_id:
            raise ValueError("No GCP project_id configured or resolvable via GOOGLE_CLOUD_PROJECT / GCP_PROJECT environment variables.")
        self.client = None

    def _get_client(self):
        if self.client is not None:
            return self.client
        if not self.project_id:
            raise ValueError("No GCP project_id configured or resolvable via GOOGLE_CLOUD_PROJECT / GCP_PROJECT environment variables.")
        if self.provider == "anthropic":
            try:
                from anthropic import AnthropicVertex
                self.client = AnthropicVertex(
                    project_id=self.project_id,
                    region=self.location
                )
                print(f"[+] AnthropicVertex client initialized for '{self.anthropic_model_id}' in region '{self.location}'")
            except ImportError:
                raise ImportError("Anthropic SDK is not installed. Install with: pip install anthropic")
        else:
            try:
                from google import genai
                self.client = genai.Client(
                    vertexai=True,
                    project=self.project_id,
                    location=self.location
                )
                print(f"[+] Google GenAI client initialized for '{self.gemini_model_id}' in region '{self.location}'")
            except ImportError:
                raise ImportError("Google GenAI SDK is not installed. Install with: pip install google-genai")
        return self.client

    def _init_sdk(self):
        return self._get_client()

    def _get_repo_sitemap(self) -> str:
        """Returns a clean text sitemap of the bridge_deck repository."""
        root = Path(__file__).resolve().parent
        sitemap = []
        for p in sorted(root.rglob("*")):
            if any(part.startswith(".") or part in ["venv", "node_modules", "__pycache__"] for part in p.parts):
                continue
            if p.is_file():
                try:
                    rel = p.relative_to(root)
                    sitemap.append(str(rel))
                except ValueError:
                    pass
        return "\n".join(sitemap[:120])

    def _auto_inject_mentioned_files(self, prompt: str) -> str:
        """Scans prompt for filenames/directories and auto-injects their content if found."""
        root = Path(__file__).resolve().parent
        injected = []
        
        # If user asks generally about bridge_deck or codebase, inject key overview files
        if any(term in prompt.lower() for term in ["bridge_deck", "codebase", "repository", "files", "see"]):
            key_files = ["README.md", "bridge_runner.py"]
            for kf in key_files:
                kp = root / kf
                if kp.exists() and kp.is_file():
                    try:
                        content = kp.read_text(encoding="utf-8")
                        if len(content) > 8000:
                            content = content[:8000] + "\n... [Truncated]"
                        injected.append(f"\n--- [AUTO-INJECTED FILE: {kf}] ---\n{content}\n--- [END FILE: {kf}] ---")
                    except Exception:
                        pass

        for p in root.rglob("*"):
            if p.is_file() and not any(part.startswith(".") or part in ["venv", "__pycache__"] for part in p.parts):
                if p.name in prompt or str(p.relative_to(root)) in prompt:
                    try:
                        content = p.read_text(encoding="utf-8")
                        if len(content) > 10000:
                            content = content[:10000] + "\n... [Truncated due to size]"
                        rel_path = p.relative_to(root)
                        injected.append(f"\n--- [AUTO-INJECTED FILE: {rel_path}] ---\n{content}\n--- [END FILE: {rel_path}] ---")
                    except Exception:
                        pass
        if injected:
            return prompt + "\n\n" + "\n".join(injected)
        return prompt

    def _handle_tool_call(self, tool_name: str, tool_args: Dict[str, Any], allowed_roots: Optional[List[Path]] = None) -> str:
        """Executes tool calls within authorized workspace boundaries (read_file, list_dir, grep_search, fetch_url, search_web)."""
        if not allowed_roots:
            allowed_roots = [Path(__file__).resolve().parent]
        else:
            allowed_roots = [Path(d).resolve() for d in allowed_roots if d]
            if not allowed_roots:
                allowed_roots = [Path(__file__).resolve().parent]

        primary_root = allowed_roots[0]

        def is_path_allowed(p: Path) -> bool:
            return any(p.is_relative_to(r) for r in allowed_roots)

        def resolve_target_path(raw: str) -> Path:
            if not raw or raw.strip() in [".", "./"]:
                return primary_root
            raw_p = Path(raw.strip())
            if raw_p.is_absolute():
                return raw_p.resolve()
            # If relative, check if exists in any allowed root
            for r in allowed_roots:
                cand = (r / raw_p).resolve()
                if cand.exists():
                    return cand
            return (primary_root / raw_p).resolve()

        if tool_name == "fetch_url":
            url = tool_args.get("url", "").strip()
            if not url:
                return "Error: URL parameter is required."
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url
            try:
                import urllib.request
                import re
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")
                    text = re.sub(r'<script.*?>.*?</script>', '', raw, flags=re.DOTALL)
                    text = re.sub(r'<style.*?>.*?</style>', '', text, flags=re.DOTALL)
                    text = re.sub(r'<.*?>', ' ', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if len(text) > 500000:
                        text = text[:500000] + "\n... [Truncated to 500,000 bytes (~0.5 MB) for prompt efficiency]"
                    return f"=== WEB CONTENT FROM {url} ===\n{text}"
            except Exception as e:
                return f"Error fetching URL '{url}': {e}"

        elif tool_name == "search_web":
            query = tool_args.get("query", "").strip()
            if not query:
                return "Error: query parameter is required."
            try:
                import urllib.request
                import urllib.parse
                import re
                encoded = urllib.parse.quote(query)
                search_url = f"https://html.duckduckgo.com/html/?q={encoded}"
                req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"})
                with urllib.request.urlopen(req, timeout=12) as resp:
                    raw = resp.read().decode("utf-8", errors="ignore")
                    snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', raw, flags=re.DOTALL)
                    clean_snippets = [re.sub(r'<.*?>', '', s).strip() for s in snippets[:5]]
                    if clean_snippets:
                        res_str = "\n\n".join([f"Result {i+1}: {s}" for i, s in enumerate(clean_snippets)])
                        return f"=== WEB SEARCH RESULTS FOR '{query}' ===\n{res_str}"
                    return f"Search executed for '{query}', but no snippets extracted."
            except Exception as e:
                return f"Error searching web for '{query}': {e}"

        raw_path = tool_args.get("relative_path") or tool_args.get("path") or tool_args.get("file_path") or tool_args.get("filepath") or ""
        raw_path = raw_path.strip()

        target_path = resolve_target_path(raw_path)

        if not is_path_allowed(target_path):
            return f"Error: Access denied. Path '{raw_path}' is outside authorized workspace directories ({[str(r) for r in allowed_roots]})."

        if tool_name == "read_file":
            if not target_path.exists():
                return f"Notice: File '{raw_path}' does not exist. Use list_dir or grep_search to inspect available files."
            if not target_path.is_file():
                return f"Notice: '{raw_path}' is a directory, not a file. Use list_dir instead."
            try:
                lines = target_path.read_text(encoding="utf-8", errors="replace").splitlines()
                start_line = tool_args.get("start_line")
                end_line = tool_args.get("end_line")
                
                if start_line is not None or end_line is not None:
                    s_idx = max(0, (int(start_line) if start_line else 1) - 1)
                    e_idx = int(end_line) if end_line else len(lines)
                    sliced_lines = lines[s_idx:e_idx]
                    content = "\n".join(sliced_lines)
                    return f"=== FILE: {target_path.name} (Lines {s_idx+1}-{min(e_idx, len(lines))} of {len(lines)}) ===\n{content}"
                else:
                    content = "\n".join(lines)
                    if len(content) > 500000:
                        content = content[:500000] + f"\n... [Truncated to 500,000 bytes (~0.5 MB) out of {len(content)} total bytes. Use start_line/end_line parameters to read remaining lines]"
                    return f"=== FILE: {target_path.name} ({len(lines)} lines) ===\n{content}"
            except Exception as e:
                return f"Error reading file '{raw_path}': {e}"

        elif tool_name == "list_dir":
            if not target_path.exists():
                return f"Notice: Directory '{raw_path}' does not exist. Try list_dir with relative_path='' for workspace root."
            if not target_path.is_dir():
                return f"Notice: '{raw_path}' is a file, not a directory."
            try:
                items = [p.name + ("/" if p.is_dir() else "") for p in target_path.iterdir() if not p.name.startswith(".")]
                return "\n".join(sorted(items))
            except Exception as e:
                return f"Error listing directory '{raw_path}': {e}"

        elif tool_name == "grep_search":
            query = tool_args.get("query", "").strip()
            if not query:
                return "Error: query parameter is required for grep_search."
            
            if target_path.exists() and target_path.is_file():
                files_to_search = [target_path]
            elif target_path.exists() and target_path.is_dir():
                files_to_search = [p for p in target_path.rglob("*") if p.is_file()]
            else:
                files_to_search = [p for r in allowed_roots for p in r.rglob("*") if p.is_file()]

            matches = []
            try:
                import re
                pattern = re.compile(query, re.IGNORECASE)
                for p in files_to_search:
                    if not any(part.startswith(".") or part in ["venv", "__pycache__", "node_modules"] for part in p.parts):
                        try:
                            for idx, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                                if pattern.search(line):
                                    matches.append(f"{p}:{idx}: {line.strip()}")
                                    if len(matches) >= 30:
                                        break
                        except Exception:
                            pass
                    if len(matches) >= 30:
                        break
                if matches:
                    return f"=== GREP SEARCH RESULTS FOR '{query}' ({len(matches)} matches) ===\n" + "\n".join(matches)
                return f"No matches found for '{query}' in specified target path."
            except Exception as e:
                return f"Error executing grep_search: {e}"

        return f"Error: Unknown tool '{tool_name}'"

    def _sanitize_messages_for_tools(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sanitizes multi-turn message history for Anthropic API tool calling compatibility.
        Converts all historical turns into plain text blocks to eliminate orphaned tool_use/tool_result validation errors.
        """
        sanitized = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # If content is a list of blocks, extract text components
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif "text" in block:
                            text_parts.append(str(block["text"]))
                    elif hasattr(block, "text") and getattr(block, "type", "") == "text":
                        text_parts.append(block.text)
                clean_text = "\n".join(text_parts).strip()
            else:
                clean_text = str(content)

            # Skip empty historical turns
            if clean_text or role == "user":
                sanitized.append({"role": role, "content": clean_text if clean_text else "."})
        return sanitized

    def _get_repo_context(self) -> str:
        """
        Pre-fetches key repository documentation and configuration files into context for instant single-pass analysis.
        """
        context_parts = []
        repo_root = Path(__file__).resolve().parent
        files_to_prefetch = [
            ("README.md", repo_root / "README.md"),
            ("docs/agent_user_guide.md", repo_root / "docs" / "agent_user_guide.md"),
            ("docs/human_user_guide.md", repo_root / "docs" / "human_user_guide.md")
        ]
        for name, p in files_to_prefetch:
            if p.exists() and p.is_file():
                try:
                    txt = p.read_text(encoding="utf-8")
                    if len(txt) > 8000:
                        txt = txt[:8000] + "\n... [Truncated for prompt efficiency]"
                    context_parts.append(f"--- FILE: {name} ---\n{txt}")
                except Exception:
                    pass
        return "\n\n".join(context_parts)

    def generate(self, prompt: str, max_output_tokens: int = 16384, temperature: float = 0.2, messages_list: Optional[List[Dict[str, str]]] = None, system_prompt: Optional[str] = None, self_name: Optional[str] = None, bridge_dir: Optional[Path] = None, allowed_roots: Optional[List[str]] = None) -> str:
        """
        Generates completion for prompt using the configured GCP Vertex AI model.
        Supports multi-turn messages list, automated file context injection, and Anthropic tool calls (read_file, list_dir).
        """
        try:
            from core.history import format_history_block
        except ImportError:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from core.history import format_history_block

        history_context = format_history_block(messages_list, self_name=self_name, bridge_dir=bridge_dir)
        norm_allowed_roots = [Path(d).resolve() for d in allowed_roots if d] if allowed_roots else [Path(__file__).resolve().parent]

        if self.provider == "anthropic":
            try:
                client = self._get_client()
                last_user_prompt = prompt
                if not last_user_prompt and messages_list and len(messages_list) > 0:
                    last_content = messages_list[-1].get("content", "")
                    if isinstance(last_content, str) and last_content:
                        last_user_prompt = last_content

                processed_prompt = last_user_prompt or "Please continue."
                msg_payload = [{"role": "user", "content": processed_prompt}]

                base_system = system_prompt or "You are an AI collaborator working on Project Bridge Deck."
                full_system = f"{base_system}{history_context}"

                kwargs = {
                    "model": self.anthropic_model_id,
                    "max_tokens": max_output_tokens,
                    "system": full_system,
                    "messages": msg_payload,
                    "tools": [
                        {
                            "name": "read_file",
                            "description": "Reads text content of any file inside the active workspace directory. Supports optional start_line and end_line parameters to view exact line ranges.",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "relative_path": {"type": "string", "description": "Relative path, e.g. 'github/src/activation_patching.py' or 'README.md'"},
                                    "start_line": {"type": "integer", "description": "Optional 1-indexed starting line number"},
                                    "end_line": {"type": "integer", "description": "Optional 1-indexed ending line number"}
                                },
                                "required": ["relative_path"]
                            }
                        },
                        {
                            "name": "list_dir",
                            "description": "Lists contents of any directory inside the active workspace directory.",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "relative_path": {"type": "string", "description": "Relative path, e.g. '.' or 'github/src'"}
                                },
                                "required": ["relative_path"]
                            }
                        },
                        {
                            "name": "grep_search",
                            "description": "Searches for text or regex patterns across files inside the active workspace directory.",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Text or regex pattern to search for"},
                                    "relative_path": {"type": "string", "description": "Optional subdirectory to restrict search to, e.g. '.' or 'github/src'"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "fetch_url",
                            "description": "Fetches and parses text from an online URL or webpage.",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string", "description": "URL to fetch, e.g. 'https://transformer-circuits.pub/2026/workspace'"}
                                },
                                "required": ["url"]
                            }
                        },
                        {
                            "name": "search_web",
                            "description": "Searches DuckDuckGo web search engine for a given query string.",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Search query string"}
                                },
                                "required": ["query"]
                            }
                        }
                    ]
                }

                response = self.client.messages.create(**kwargs)
                
                # Active Tool Execution Loop
                turn_count = 0
                max_tool_turns = 8
                tool_execution_logs = []
                final_text_parts = []
                all_thinking = []

                # Tool use loop
                while hasattr(response, "stop_reason") and response.stop_reason == "tool_use" and turn_count < max_tool_turns:
                    turn_count += 1
                    
                    tool_use_blocks = []
                    assistant_blocks = []
                    if response.content:
                        for block in response.content:
                            b_type = getattr(block, "type", None)
                            if not b_type and isinstance(block, dict):
                                b_type = block.get("type")
                            if b_type in ["text", "tool_use", "thinking"]:
                                if hasattr(block, "model_dump"):
                                    assistant_blocks.append(block.model_dump())
                                else:
                                    assistant_blocks.append(block)
                            if b_type == "tool_use":
                                tool_use_blocks.append(block)

                    if not tool_use_blocks:
                        break

                    tool_results = []
                    for tub in tool_use_blocks:
                        t_name = getattr(tub, "name", None) or (tub.get("name") if isinstance(tub, dict) else None)
                        t_args = getattr(tub, "input", None) or (tub.get("input") if isinstance(tub, dict) else {})
                        t_id = getattr(tub, "id", None) or (tub.get("id") if isinstance(tub, dict) else None)
                        
                        t_res = self._handle_tool_call(t_name, t_args, allowed_roots=norm_allowed_roots)
                        tool_execution_logs.append(f"### Tool Execution: `{t_name}` ({t_args})\n```\n{t_res[:250000]}\n```")
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": t_id,
                            "content": t_res
                        })

                    msg_payload.append({"role": "assistant", "content": assistant_blocks})
                    msg_payload.append({"role": "user", "content": tool_results})

                    kwargs["messages"] = msg_payload

                    try:
                        response = client.messages.create(**kwargs)
                    except Exception as err:
                        print(f"Tool turn {turn_count} API warning: {err}")
                        break

                # If the loop ended while model still wanted to call tools, do concluding turn without tools
                if hasattr(response, "stop_reason") and response.stop_reason == "tool_use":
                    tool_use_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use" or (isinstance(b, dict) and b.get("type") == "tool_use")]
                    assistant_blocks = [b.model_dump() if hasattr(b, "model_dump") else b for b in response.content]
                    tool_results = []
                    for tub in tool_use_blocks:
                        t_name = getattr(tub, "name", None) or (tub.get("name") if isinstance(tub, dict) else None)
                        t_args = getattr(tub, "input", None) or (tub.get("input") if isinstance(tub, dict) else {})
                        t_id = getattr(tub, "id", None) or (tub.get("id") if isinstance(tub, dict) else None)
                        t_res = self._handle_tool_call(t_name, t_args, allowed_roots=norm_allowed_roots)
                        tool_results.append({"type": "tool_result", "tool_use_id": t_id, "content": t_res})
                    msg_payload.append({"role": "assistant", "content": assistant_blocks})
                    
                    concluding_content = list(tool_results)
                    concluding_content.append({
                        "type": "text",
                        "text": "Based on all files and code inspected above, please provide your complete, detailed findings, architectural review, and response now."
                    })
                    msg_payload.append({"role": "user", "content": concluding_content})
                    kwargs["messages"] = msg_payload
                    kwargs.pop("tools", None)
                    try:
                        response = client.messages.create(**kwargs)
                    except Exception as final_tool_err:
                        print(f"Final tool conclusion warning: {final_tool_err}")

                # Collect the final response text
                if hasattr(response, "content") and response.content:
                    for block in response.content:
                        if hasattr(block, "text") and block.text:
                            txt = block.text.strip()
                            if txt:
                                final_text_parts.append(txt)
                        elif hasattr(block, "thinking") and block.thinking:
                            th = block.thinking.strip()
                            if th:
                                all_thinking.append(th)

                # Fallback if model did not produce text yet
                if not final_text_parts:
                    assistant_blocks = [b.model_dump() if hasattr(b, "model_dump") else b for b in response.content] if hasattr(response, "content") and response.content else []
                    if assistant_blocks:
                        msg_payload.append({"role": "assistant", "content": assistant_blocks})
                    msg_payload.append({"role": "user", "content": "Please synthesize and present your full, complete architectural review and response now."})
                    kwargs["messages"] = msg_payload
                    kwargs.pop("tools", None)
                    try:
                        fallback_resp = client.messages.create(**kwargs)
                        if hasattr(fallback_resp, "content") and fallback_resp.content:
                            for block in fallback_resp.content:
                                if hasattr(block, "text") and block.text:
                                    txt = block.text.strip()
                                    if txt:
                                        final_text_parts.append(txt)
                    except Exception as fb_err:
                        print(f"Fallback synthesis warning: {fb_err}")

                # Automatic continuation loop if final response hit max_tokens limit
                cont_turns = 0
                while hasattr(response, "stop_reason") and response.stop_reason == "max_tokens" and cont_turns < 3:
                    cont_turns += 1
                    last_text = ""
                    if hasattr(response, "content") and response.content:
                        for b in response.content:
                            if hasattr(b, "text") and b.text:
                                last_text += b.text
                    if not last_text:
                        break
                    msg_payload.append({"role": "assistant", "content": last_text})
                    msg_payload.append({"role": "user", "content": "Please continue your response seamlessly from where you left off."})
                    kwargs["messages"] = msg_payload
                    kwargs.pop("tools", None)
                    try:
                        response = client.messages.create(**kwargs)
                        if hasattr(response, "content") and response.content:
                            for b in response.content:
                                if hasattr(b, "text") and b.text:
                                    txt = b.text.strip()
                                    if txt:
                                        final_text_parts.append(txt)
                    except Exception as cont_err:
                        print(f"Continuation step warning: {cont_err}")
                        break

                final_text = "\n\n".join(final_text_parts).strip()
                return final_text
            except Exception as e:
                raise RuntimeError(f"Anthropic Vertex API Error ({self.anthropic_model_id}): {e}")
        else:
            try:
                client = self._get_client()
                from google.genai import types
                config = types.GenerateContentConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                )
                if system_prompt:
                    config.system_instruction = system_prompt

                response = client.models.generate_content(
                    model=self.gemini_model_id,
                    contents=prompt,
                    config=config,
                )
                return response.text
            except Exception as e:
                raise RuntimeError(f"Google GenAI API Error ({self.gemini_model_id}): {e}")

if __name__ == "__main__":
    print("Testing GCPModelClient with multi-turn messages...")
    client = GCPModelClient(model_name="gemini-3.6-flash")
    result = client.generate("State the primary research objective of Bridge Deck in one sentence.")
    print("\nModel Output:\n", result)
