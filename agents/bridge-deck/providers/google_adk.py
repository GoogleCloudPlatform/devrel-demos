#!/usr/bin/env python3
"""
Google GenAI & ADK Provider Adapter for Bridge Deck.
Implements the AgentProvider interface for Google Vertex GenAI / ADK agents with
epistemic grounding, dynamic 3-tier memory context, and multi-turn history synthesis.
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from providers.base import AgentProvider
from core.history import format_history_block

ROOT_DIR = Path(__file__).resolve().parent.parent


class GoogleADKProvider(AgentProvider):
    """
    AgentProvider adapter for Google GenAI / Agent Development Kit agents.
    Provides Vertex AI execution, memory grounding, and multi-agent coordination.
    """
    def __init__(self, provider_id: str = "google-adk", config: Optional[Dict[str, Any]] = None):
        super().__init__(provider_id, config)
        self.model_name = self.config.get("model", "gemini-3.7-flash")
        self.project_id = self.config.get("project_id") or self.config.get("project") or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        default_loc = "global" if ("3.7" in self.model_name or "gemini-3" in self.model_name) else "us-central1"
        self.location = self.config.get("location") or default_loc
        self.temperature = float(self.config.get("temperature", 0.2))
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

            # 2. Add Collaboration & ACL Directives (truthful, no unbacked tool claims)
            a2a_directive = (
                "\n=== MULTI-AGENT COLLABORATION & ACL DIRECTIVES ===\n"
                "- You are operating via the Google GenAI / Vertex AI Runtime.\n"
                "- Respect ACL boundaries: perform read actions strictly within authorized paths.\n"
                "- Maintain concise, rigorous, and actionable communication across the multi-agent roster.\n"
                "=================================================="
            )
            full_system = f"{full_system}\n{a2a_directive}"

            # 3. Centralized Multi-Agent History Synthesis (with self-marking)
            bridge_dir = context.get("bridge_dir") if context else None
            history_block = format_history_block(messages, self_name=self_name, bridge_dir=bridge_dir)
            if history_block:
                full_system = f"{full_system}\n\n{history_block}"

            # 4. Generate with Google GenAI
            client = self._get_client()
            if client is None:
                from model_client import GCPModelClient
                fallback_client = GCPModelClient(project_id=self.project_id, location=self.location, model_name=self.model_name)
                resp_text = fallback_client.generate(prompt=prompt, system_prompt=full_system, messages_list=messages, self_name=self_name)
            else:
                from google.genai import types
                config = types.GenerateContentConfig(
                    max_output_tokens=8192,
                    temperature=self.temperature,
                    system_instruction=full_system
                )
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                resp_text = response.text or ""

            elapsed = round(time.time() - start_time, 2)
            return {
                "success": True,
                "response": resp_text,
                "model": self.model_name,
                "provider_type": "google-adk",
                "elapsed_seconds": elapsed,
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
