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
    def __init__(self, bridge_dir: Optional[Path] = None):
        from core.tenant import get_tenant_dir
        self.bridge_dir = bridge_dir or get_tenant_dir()
        self.memory_dir = self.bridge_dir / "memory"
        self.semantic_dir = self.memory_dir / "semantic"
        self.shared_dir = self.memory_dir / "shared"
        self._lock = threading.Lock()
        self.ensure_dirs()

    def ensure_dirs(self):
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.semantic_dir.mkdir(parents=True, exist_ok=True)
        self.shared_dir.mkdir(parents=True, exist_ok=True)

    # 1. Semantic Memory (Per-Agent Distilled Facts)
    def append_semantic_fact(self, agent_id: str, fact: str, source: str = "user") -> Dict[str, Any]:
        agent_dir = self.semantic_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        facts_file = agent_dir / "facts.jsonl"
        
        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "agent_id": agent_id,
            "fact": fact,
            "source": source
        }
        with self._lock:
            with open(facts_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        return record

    def get_semantic_facts(self, agent_id: str, max_items: int = 20) -> List[Dict[str, Any]]:
        facts_file = self.semantic_dir / agent_id / "facts.jsonl"
        if not facts_file.exists():
            return []
        
        facts = []
        try:
            with self._lock:
                with open(facts_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            facts.append(json.loads(line.strip()))
        except Exception as e:
            print(f"[!] Error reading semantic facts for {agent_id}: {e}")
            
        return facts[-max_items:]

    # 2. Shared Common Ground (Per-Project Common Memory)
    def save_shared_decision(self, project_id: str, decision: str, author: str) -> Dict[str, Any]:
        proj_file = self.shared_dir / f"{project_id}.json"
        data = {"decisions": []}
        temp_file = proj_file.with_name(proj_file.name + ".tmp")
        
        with self._lock:
            if proj_file.exists():
                try:
                    with open(proj_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass
                    
            record = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "project_id": project_id,
                "decision": decision,
                "author": author
            }
            data.setdefault("decisions", []).append(record)
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, proj_file)
            return record

    def get_shared_decisions(self, project_id: str) -> List[Dict[str, Any]]:
        proj_file = self.shared_dir / f"{project_id}.json"
        if not proj_file.exists():
            return []
        try:
            with self._lock:
                with open(proj_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("decisions", [])
        except Exception:
            return []
