#!/usr/bin/env python3
"""
VertexAnthropicProvider implementing AgentProvider.
Wraps GCPModelClient / Claude Opus 5 calls into standardized AgentProvider interface.
"""

import time
from typing import Dict, Any, List, Optional
from providers.base import AgentProvider

try:
    from model_client import GCPModelClient
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from model_client import GCPModelClient


class VertexAnthropicProvider(AgentProvider):
    def __init__(self, provider_id: str = "vertex-anthropic", config: Optional[Dict[str, Any]] = None):
        super().__init__(provider_id, config)
        model_name = self.config.get("model", "claude-opus-5")
        loc = self.config.get("location", "global")
        if not loc or loc in ["local", "None", ""]:
            loc = "global"
        proj = self.config.get("project_id") or self.config.get("project")
        self.client = GCPModelClient(
            project_id=proj,
            location=loc,
            model_name=model_name
        )

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        model_name = self.config.get("model", "claude-opus-5")
        
        try:
            full_system = system_prompt or ""
            if context and context.get("self_context") and context["self_context"] not in full_system:
                full_system = context["self_context"] + "\n\n" + full_system
                
            self_name = context.get("self_name") if context else None
            bridge_dir = context.get("bridge_dir") if context else None
            allowed_dirs = (context.get("directories") if context else None) or self.config.get("access_read") or []
            resp_text = self.client.generate(
                prompt=prompt,
                system_prompt=full_system,
                messages_list=messages,
                self_name=self_name,
                bridge_dir=bridge_dir,
                allowed_roots=allowed_dirs
            )
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": True,
                "response": resp_text,
                "model": model_name,
                "elapsed_seconds": elapsed,
                "error": None
            }
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": False,
                "response": None,
                "model": model_name,
                "elapsed_seconds": elapsed,
                "error": str(e)
            }
