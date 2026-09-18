#!/usr/bin/env python3
"""
Three-Tier Memory Store for Bridge Deck.
Implements Bridge-owned persistent memory:
  - Episodic Memory: full turn records per project (history_<proj>.json)
  - Semantic Memory: per-agent distilled facts (memory/semantic/<agent_id>/facts.jsonl)
  - Shared Common Ground: project decisions & roster history (memory/shared/<project_id>.json)
"""

import json
import time
import os
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent


class MemoryStore:
    def __init__(self, bridge_dir: Optional[Path] = None, storage_adapter: Optional[Any] = None):
        from core.tenant import get_tenant_dir, sanitize_tenant_id, DEFAULT_TENANT_ID
        self.bridge_dir = bridge_dir or get_tenant_dir()
        self.memory_dir = self.bridge_dir / "memory"
        self.semantic_dir = self.memory_dir / "semantic"
        self.shared_dir = self.memory_dir / "shared"
        self._lock = threading.Lock()
        self._storage_adapter = storage_adapter
        if self.bridge_dir.parent.name == "tenants":
            self.tenant_id = sanitize_tenant_id(self.bridge_dir.name)
        else:
            self.tenant_id = "__direct__"
        self.ensure_dirs()

    @property
    def storage(self):
        if self._storage_adapter is None:
            from core.tenant import get_storage_adapter, LocalStorageAdapter
            if self.tenant_id == "__direct__":
                self._storage_adapter = LocalStorageAdapter(base_dir=self.bridge_dir)
            else:
                self._storage_adapter = get_storage_adapter()
        return self._storage_adapter

    def ensure_dirs(self):
        from core.tenant import LocalStorageAdapter, use_gcs_storage
        # A6: No-op for non-local adapters to decouple completely from FUSE mount
        if use_gcs_storage():
            return
        if getattr(self, "_storage_adapter", None) is not None and not isinstance(self._storage_adapter, LocalStorageAdapter):
            return
        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            self.semantic_dir.mkdir(parents=True, exist_ok=True)
            self.shared_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # 1. Semantic Memory (Per-Agent Distilled Facts)
    def append_semantic_fact(self, agent_id: str, fact: str, source: str = "user") -> Dict[str, Any]:
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "agent_id": agent_id,
            "fact": fact,
            "source": source
        }
        rel_key = f"memory/semantic/{agent_id}/facts.jsonl"
        self.storage.append_line(self.tenant_id, rel_key, json.dumps(record))
        return record

    def get_semantic_facts(self, agent_id: str, max_items: int = 20) -> List[Dict[str, Any]]:
        rel_key = f"memory/semantic/{agent_id}/facts.jsonl"
        lines = self.storage.read_lines(self.tenant_id, rel_key)
        facts = []
        for line in lines:
            line_str = line.strip()
            if line_str:
                try:
                    facts.append(json.loads(line_str))
                except Exception as e:
                    print(f"[!] Error parsing semantic fact for {agent_id}: {e}")
        return facts[-max_items:]

    # 2. Shared Common Ground (Per-Project Common Memory)
    def save_shared_decision(self, project_id: str, decision: str, author: str) -> Dict[str, Any]:
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "project_id": project_id,
            "decision": decision,
            "author": author
        }
        rel_key = f"memory/shared/{project_id}.json"
        self.storage.append_json_list(
            self.tenant_id,
            rel_key,
            list_field="decisions",
            item=record,
            default={"decisions": []}
        )
        return record

    def get_shared_decisions(self, project_id: str) -> List[Dict[str, Any]]:
        rel_key = f"memory/shared/{project_id}.json"
        doc = self.storage.read_json(self.tenant_id, rel_key)
        if doc and isinstance(doc, dict):
            return doc.get("decisions", [])
        return []
