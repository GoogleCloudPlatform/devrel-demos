#!/usr/bin/env python3
"""
OllamaLocalProvider implementing AgentProvider.
Communicates with local Ollama inference daemon (http://localhost:11434) for open-weights models.
Provides automated history formatting, system prompt conditioning, and graceful connection failure handling.
"""

import time
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, List, Optional
from providers.base import AgentProvider
from core.history import format_history_block


class OllamaLocalProvider(AgentProvider):
    """
    AgentProvider adapter for local open-weights inference via Ollama.
    """
    def __init__(self, provider_id: str = "ollama", config: Optional[Dict[str, Any]] = None):
        super().__init__(provider_id, config)
        self.model_name = self.config.get("model", "llama3.3:70b")
        raw_loc = self.config.get("location") or "http://localhost:11434"
        self.base_url = raw_loc.rstrip("/")
        if not self.base_url.startswith("http://") and not self.base_url.startswith("https://"):
            self.base_url = f"http://{self.base_url}"
        self.temperature = float(self.config.get("temperature", 0.7))
        self.timeout = int(self.config.get("timeout", 60))

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        self_name = context.get("self_name") if context else None
        
        full_system = system_prompt or ""
        if context and context.get("self_context") and context["self_context"] not in full_system:
            full_system = context["self_context"] + "\n\n" + full_system

        bridge_dir = context.get("bridge_dir") if context else None
        history_block = format_history_block(messages, self_name=self_name, bridge_dir=bridge_dir)
        if history_block:
            full_system = f"{full_system}\n\n{history_block}" if full_system else history_block

        ollama_messages = []
        if full_system:
            ollama_messages.append({"role": "system", "content": full_system})
            
        ollama_messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }

        endpoint = f"{self.base_url}/api/chat"
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_bytes = resp.read()
                resp_data = json.loads(resp_bytes.decode("utf-8"))
                
                msg_content = resp_data.get("message", {}).get("content", "")
                elapsed = round(time.time() - start_time, 2)
                
                return {
                    "success": True,
                    "response": msg_content,
                    "model": self.model_name,
                    "elapsed_seconds": elapsed,
                    "thinking_blocks": [
                        f"Executed local inference via Ollama ({self.model_name}) at {self.base_url}.",
                        f"Completed in {elapsed}s."
                    ]
                }
        except urllib.error.URLError as ue:
            elapsed = round(time.time() - start_time, 2)
            err_msg = f"Ollama daemon unreachable at {self.base_url} ({ue.reason}). Please ensure 'ollama serve' is active."
            return {
                "success": False,
                "response": None,
                "model": self.model_name,
                "elapsed_seconds": elapsed,
                "error": err_msg,
                "thinking_blocks": [f"Connection error: {err_msg}"]
            }
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": False,
                "response": None,
                "model": self.model_name,
                "elapsed_seconds": elapsed,
                "error": str(e),
                "thinking_blocks": [f"Execution error: {e}"]
            }
