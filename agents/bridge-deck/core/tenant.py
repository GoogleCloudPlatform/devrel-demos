#!/usr/bin/env python3
"""
Tenant Context Manager & Storage Abstraction for Bridge Deck.
Enables isolated, multi-tenant workspace partitions (profiles, projects, history,
agents, memory, and A2A dispatchers) decoupled from the platform engine.
"""

import os
import re
import sys
import shutil
import threading
from pathlib import Path
from typing import Dict, Any, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Auto-load .env configuration if present
_env_file = ROOT_DIR / ".env"
if _env_file.exists():
    try:
        with open(_env_file, "r", encoding="utf-8") as _ef:
            for _line in _ef:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _k = _k.strip()
                    _v = _v.strip().strip("'").strip('"')
                    if _k not in os.environ:
                        os.environ[_k] = _v
    except Exception:
        pass

from core.router import AgentRouter
from memory.store import MemoryStore


DEFAULT_TENANT_ID = os.environ.get("BRIDGE_DEFAULT_TENANT", "default_workspace")


def sanitize_tenant_id(tenant_id: Optional[str]) -> str:
    """
    Sanitizes tenant IDs into safe alphanumeric directory slugs.
    Defaults to DEFAULT_TENANT_ID. Max 64 chars.
    """
    if not tenant_id:
        return DEFAULT_TENANT_ID
    s = str(tenant_id).strip().lower()
    # Remove path traversal characters
    s = s.replace("..", "").replace("/", "").replace("\\", "")
    # Allow only alphanumeric, underscore, hyphen
    s = re.sub(r"[^a-z0-9_-]+", "_", s)
    s = re.sub(r"[-_]+", "_", s)
    s = s.strip("_").strip("-")
    if not s or s == "default":
        return DEFAULT_TENANT_ID
    return s[:64]


def get_tenant_dir(tenant_id: Optional[str] = None, base_dir: Optional[Path] = None) -> Path:
    """
    Resolves the root directory for a given tenant.
    All tenants resolve strictly to base_dir / 'data' / 'tenants' / <clean_id>.
    """
    b_dir = base_dir or ROOT_DIR
    clean_id = sanitize_tenant_id(tenant_id)
    return b_dir / "data" / "tenants" / clean_id


def ensure_tenant_initialized(tenant_id: Optional[str] = None, base_dir: Optional[Path] = None) -> Path:
    """
    Initializes a tenant workspace directory from seed templates if not already present.
    """
    b_dir = base_dir or ROOT_DIR
    clean_id = sanitize_tenant_id(tenant_id)
    t_dir = get_tenant_dir(clean_id, base_dir=b_dir)

    t_dir.mkdir(parents=True, exist_ok=True)
    (t_dir / "history").mkdir(parents=True, exist_ok=True)
    (t_dir / "memory").mkdir(parents=True, exist_ok=True)
    t_agents_dir = t_dir / "agents"
    t_agents_dir.mkdir(parents=True, exist_ok=True)

    seed_dir = b_dir / "seed"
    if seed_dir.exists():
        # Copy core files if missing
        for fname in ["profiles.json", "projects.json", "engines.json", "models.json", "skill_usage.json"]:
            src_f = seed_dir / fname
            dst_f = t_dir / fname
            if src_f.exists() and not dst_f.exists():
                shutil.copy2(src_f, dst_f)

        # Copy starter agents if directory is empty
        seed_agents = seed_dir / "agents"
        if seed_agents.exists() and not list(t_agents_dir.glob("*.agent.json")):
            for af in seed_agents.glob("*"):
                if af.is_file():
                    shutil.copy2(af, t_agents_dir / af.name)

    return t_dir


class TenantRegistry:
    """
    Thread-safe registry caching per-tenant AgentRouter, MemoryStore, and A2ADispatcher instances.
    """
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or ROOT_DIR
        self._routers: Dict[str, AgentRouter] = {}
        self._memory_stores: Dict[str, MemoryStore] = {}
        self._dispatchers: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def get_router(self, tenant_id: Optional[str] = None) -> AgentRouter:
        t_dir = ensure_tenant_initialized(tenant_id, base_dir=self.base_dir)
        key = str(t_dir.resolve())
        with self._lock:
            if key not in self._routers:
                self._routers[key] = AgentRouter(bridge_dir=t_dir)
            return self._routers[key]

    def get_memory_store(self, tenant_id: Optional[str] = None) -> MemoryStore:
        t_dir = ensure_tenant_initialized(tenant_id, base_dir=self.base_dir)
        key = str(t_dir.resolve())
        with self._lock:
            if key not in self._memory_stores:
                self._memory_stores[key] = MemoryStore(bridge_dir=t_dir)
            return self._memory_stores[key]

    def get_dispatcher(self, tenant_id: Optional[str] = None, **dispatcher_kwargs) -> Any:
        t_dir = ensure_tenant_initialized(tenant_id, base_dir=self.base_dir)
        key = str(t_dir.resolve())
        with self._lock:
            if key not in self._dispatchers:
                from core.a2a_dispatcher import A2ADispatcher
                r_inst = self.get_router(tenant_id)
                import bridge_runner
                self._dispatchers[key] = A2ADispatcher(
                    bridge_dir=t_dir,
                    agent_router=r_inst,
                    load_history_fn=dispatcher_kwargs.get("load_history_fn") or (lambda pid: bridge_runner.load_history(pid, bridge_dir=t_dir)),
                    save_history_fn=dispatcher_kwargs.get("save_history_fn") or (lambda pid, data: bridge_runner.save_history(pid, data, bridge_dir=t_dir)),
                    load_projects_fn=dispatcher_kwargs.get("load_projects_fn") or (lambda: bridge_runner.load_projects(bridge_dir=t_dir)),
                    build_messages_fn=dispatcher_kwargs.get("build_messages_fn") or (lambda *args, **kw: bridge_runner.build_anthropic_messages_and_system(*args, bridge_dir=t_dir, **kw)),
                    build_self_context_fn=dispatcher_kwargs.get("build_self_context_fn") or (lambda *args, **kw: bridge_runner.build_agent_self_context(*args, bridge_dir=t_dir, **kw)),
                    append_transaction_fn=dispatcher_kwargs.get("append_transaction_fn") or (lambda pid, tx: bridge_runner.append_transaction(pid, tx, bridge_dir=t_dir)),
                )
            return self._dispatchers[key]

    def reload_tenant(self, tenant_id: Optional[str] = None):
        t_dir = get_tenant_dir(tenant_id, base_dir=self.base_dir)
        key = str(t_dir.resolve())
        with self._lock:
            if key in self._routers:
                self._routers[key].reload_registry(force=True)
            if key in self._memory_stores:
                del self._memory_stores[key]
            if key in self._dispatchers:
                try:
                    self._dispatchers[key].task_queue = None
                except Exception:
                    pass
                del self._dispatchers[key]


# Global default tenant registry
tenant_manager = TenantRegistry()
