#!/usr/bin/env python3
"""
AgentProvider Abstract Base Class for Multi-Vendor Agent Integration.
Defines the standard interface for Vertex/Anthropic, Antigravity Queue, Google ADK, and external HTTP agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class AgentProvider(ABC):
    def __init__(self, provider_id: str, config: Optional[Dict[str, Any]] = None):
        self.provider_id = provider_id
        self.config = config or {}

    @abstractmethod
    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invokes the agent provider with given prompt, system instructions, message history, and context.
        Returns a standardized response dictionary:
        {
            "success": bool,
            "response": str,
            "model": str,
            "elapsed_seconds": float,
            "error": Optional[str]
        }
        """
        pass

    def supports_streaming(self) -> bool:
        return False

    def health(self) -> Dict[str, Any]:
        return {"status": "ok", "provider_id": self.provider_id}
