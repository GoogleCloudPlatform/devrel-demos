#!/usr/bin/env python3
"""
Tenant Context Manager & Storage Abstraction for Bridge Deck.
Enables isolated, multi-tenant workspace partitions (profiles, projects, history,
agents, memory, and A2A dispatchers) decoupled from the platform engine.
"""

import os
import re
import sys
import json
import copy
import time
import random
import shutil
import threading
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple

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


def get_data_root(base_dir: Optional[Path] = None) -> Path:
    """
    Returns the root directory for data storage.
    If base_dir is explicitly provided, base_dir / 'data' is returned.
    If BRIDGE_DATA_DIR environment variable is set, it overrides the root directory.
    Otherwise defaults dynamically to ROOT_DIR / 'data'.
    """
    if base_dir is not None:
        return base_dir / "data"
    env_dir = os.environ.get("BRIDGE_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    return ROOT_DIR / "data"


def get_tenant_dir(tenant_id: Optional[str] = None, base_dir: Optional[Path] = None) -> Path:
    """
    Resolves the root directory for a given tenant.
    When BRIDGE_DATA_DIR is set, resolves to BRIDGE_DATA_DIR / 'tenants' / <clean_id>.
    Otherwise resolves to (base_dir or ROOT_DIR) / 'data' / 'tenants' / <clean_id>.
    """
    clean_id = sanitize_tenant_id(tenant_id)
    return get_data_root(base_dir) / "tenants" / clean_id


def ensure_tenant_initialized(tenant_id: Optional[str] = None, base_dir: Optional[Path] = None) -> Path:
    """
    Initializes a tenant workspace directory from seed templates if not already present.
    """
    clean_id = sanitize_tenant_id(tenant_id)
    t_dir = get_tenant_dir(clean_id, base_dir=base_dir)

    try:
        t_dir.mkdir(parents=True, exist_ok=True)
        (t_dir / "history").mkdir(parents=True, exist_ok=True)
        (t_dir / "memory").mkdir(parents=True, exist_ok=True)
        t_agents_dir = t_dir / "agents"
        t_agents_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    seed_dir = (base_dir if base_dir is not None and base_dir != ROOT_DIR else ROOT_DIR) / "seed"
    if seed_dir.exists():
        try:
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
        except Exception:
            pass

    return t_dir


class StorageConflictError(Exception):
    """Raised when atomic compare-and-swap (CAS) retries are exhausted due to concurrent writes."""
    pass


class StorageCorruptError(Exception):
    """Raised when a storage document exists on disk or blob store but contains invalid/unparseable JSON."""
    pass


UNCONDITIONAL: int = -1  # Explicit sentinel to bypass generation precondition


class StorageAdapter(ABC):
    """
    Abstract storage backend for tenant files.
    Supports atomic compare-and-swap (CAS) updates, appends, and line-streaming
    across local POSIX disk and Google Cloud Storage.
    Enforces tenant scoping directly at the interface level.
    """

    @abstractmethod
    def read_json(self, tenant_id: str, rel_key: str) -> Optional[dict]:
        """Reads and parses JSON document at rel_key within tenant. Returns None if absent."""
        pass

    @abstractmethod
    def read_json_with_gen(self, tenant_id: str, rel_key: str) -> Tuple[Optional[dict], int]:
        """Reads JSON document and returns (doc, generation). Returns (None, 0) if absent."""
        pass

    @abstractmethod
    def replace_json(
        self,
        tenant_id: str,
        rel_key: str,
        data: dict,
        *,
        default: Optional[dict] = None,
        expected_generation: int
    ) -> Tuple[dict, int]:
        """
        Preconditioned whole-document replace.
        Callers must provide expected_generation (e.g. from read_json_with_gen),
        or UNCONDITIONAL to explicitly bypass generation preconditions.
        Raises StorageConflictError on ANY generation mismatch.
        """
        pass

    @abstractmethod
    def update_json(
        self,
        tenant_id: str,
        rel_key: str,
        mutator_fn: Callable[[dict], dict],
        *,
        default: Optional[dict] = None,
        max_retries: int = 5
    ) -> Tuple[dict, int]:
        """
        Atomically reads, mutates, and writes back the JSON document.
        - mutator_fn receives a fresh deep copy of the document on every attempt and
          must return the complete new document. It MUST be a pure function of its input.
        - Local implementation: executes under file/thread lock + atomic os.replace.
        - GCS implementation: fetches blob with generation number, applies mutator_fn,
          and uploads with if_generation_match precondition. If generation conflict occurs,
          retries with exponential backoff up to max_retries.
        - If retries exhausted, raises StorageConflictError.
        - Returns (committed_doc, generation_number).
        """
        pass

    @abstractmethod
    def append_json_list(
        self,
        tenant_id: str,
        rel_key: str,
        list_field: str,
        item: dict,
        *,
        id_field: str = "id",
        default: Optional[dict] = None
    ) -> Tuple[dict, int]:
        """
        Convenience wrapper around update_json for append-only transaction logs.
        Appends or updates the item in the specified list_field, ensuring idempotency on id_field.
        """
        pass

    @abstractmethod
    def append_line(self, tenant_id: str, rel_key: str, line: str) -> None:
        """Appends a line to a streaming log or JSONL file (e.g., facts.jsonl)."""
        pass

    @abstractmethod
    def read_lines(self, tenant_id: str, rel_key: str) -> List[str]:
        """Reads all lines from a text/JSONL file within tenant. Returns empty list if absent."""
        pass

    @abstractmethod
    def exists(self, tenant_id: str, rel_key: str) -> bool:
        """Checks if key exists within tenant."""
        pass

    @abstractmethod
    def delete(self, tenant_id: str, rel_key: str) -> None:
        """Deletes key within tenant."""
        pass

    @abstractmethod
    def list_keys(self, tenant_id: str, prefix: str = "") -> List[str]:
        """Lists relative keys within tenant matching prefix."""
        pass


class LocalStorageAdapter(StorageAdapter):
    """
    POSIX local disk implementation of StorageAdapter with atomic replace and thread locks.
    """
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir
        self._lock = threading.RLock()
        self._lock_degraded = False

    def _resolve_path(self, tenant_id: str, rel_key: str) -> Path:
        clean_key = str(rel_key).strip().lstrip("/").replace("\\", "/")
        parts = [p for p in clean_key.split("/") if p and p != "." and p != ".."]
        safe_rel = Path(*parts)
        if not tenant_id or tenant_id == "__direct__":
            b = self.base_dir or get_data_root()
            return b / safe_rel
        clean_tid = sanitize_tenant_id(tenant_id)
        t_dir = get_tenant_dir(clean_tid, base_dir=self.base_dir)
        return t_dir / safe_rel

    def _get_gen(self, path: Path) -> int:
        if path.exists():
            st = path.stat()
            return int(st.st_mtime_ns)
        return 0

    def read_json_with_gen(self, tenant_id: str, rel_key: str) -> Tuple[Optional[dict], int]:
        path = self._resolve_path(tenant_id, rel_key)
        with self._lock:
            if not path.exists():
                return None, 0
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f), self._get_gen(path)
            except json.JSONDecodeError as jde:
                raise StorageCorruptError(f"Corrupt JSON in {path}: {jde}") from jde
            except FileNotFoundError:
                return None, 0

    def read_json(self, tenant_id: str, rel_key: str) -> Optional[dict]:
        """Reads JSON document at rel_key. Returns None if absent or corrupt."""
        try:
            doc, _ = self.read_json_with_gen(tenant_id, rel_key)
            return doc
        except StorageCorruptError:
            return None

    def replace_json(
        self,
        tenant_id: str,
        rel_key: str,
        data: dict,
        *,
        default: Optional[dict] = None,
        expected_generation: int
    ) -> Tuple[dict, int]:
        if expected_generation is None:
            raise ValueError(f"replace_json on {rel_key} requires expected_generation: int (or UNCONDITIONAL)")
        path = self._resolve_path(tenant_id, rel_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = path.with_name(f"{path.name}.{int(time.time()*1000)}.tmp")
        with self._lock:
            lock_f = self._flock_open(path)
            try:
                current_gen = self._get_gen(path)
                if expected_generation != UNCONDITIONAL and current_gen != expected_generation:
                    raise StorageConflictError(
                        f"Local CAS conflict on {rel_key}: expected gen {expected_generation}, actual {current_gen}"
                    )
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(temp_file, path)
                gen = self._get_gen(path)
                return data, gen
            finally:
                self._flock_close(lock_f)

    def read_lines(self, tenant_id: str, rel_key: str) -> List[str]:
        path = self._resolve_path(tenant_id, rel_key)
        with self._lock:
            if not path.exists():
                return []
            lock_f = self._flock_open(path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().splitlines()
            finally:
                self._flock_close(lock_f)

    def _flock_open(self, path: Path):
        try:
            import fcntl
            lock_path = path.with_name(f".{path.name}.flock")
            lock_f = open(lock_path, "a")
            fcntl.flock(lock_f.fileno(), fcntl.LOCK_EX)
            return lock_f
        except Exception as e:
            self._lock_degraded = True
            warnings.warn(f"Failed to acquire flock on {path}: {e}. Operating in degraded lock mode.", RuntimeWarning)
            return None

    def _flock_close(self, lock_f):
        if lock_f is not None:
            try:
                import fcntl
                fcntl.flock(lock_f.fileno(), fcntl.LOCK_UN)
                lock_f.close()
            except Exception:
                pass

    def update_json(
        self,
        tenant_id: str,
        rel_key: str,
        mutator_fn: Callable[[dict], dict],
        *,
        default: Optional[dict] = None,
        max_retries: int = 5
    ) -> Tuple[dict, int]:
        path = self._resolve_path(tenant_id, rel_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_file = path.with_name(f"{path.name}.{int(time.time()*1000)}.tmp")

        # Note: Under LocalStorageAdapter, _flock_open + threading.RLock serialize all local writes.
        # Retry loop executes iteration 0 and commits atomically.
        for _attempt in range(max_retries):
            with self._lock:
                lock_f = self._flock_open(path)
                try:
                    current_doc = None
                    if path.exists():
                        try:
                            with open(path, "r", encoding="utf-8") as f:
                                current_doc = json.load(f)
                        except Exception as e:
                            raise StorageCorruptError(f"Corrupt JSON at {path}: {e}")
                    else:
                        current_doc = copy.deepcopy(default) if default is not None else {}

                    mutated_doc = mutator_fn(copy.deepcopy(current_doc))
                    with open(temp_file, "w", encoding="utf-8") as f:
                        json.dump(mutated_doc, f, indent=2)
                    os.replace(temp_file, path)
                    gen = self._get_gen(path)
                    return mutated_doc, gen
                finally:
                    self._flock_close(lock_f)

        raise StorageConflictError(f"Local storage conflict on {rel_key} after {max_retries} retries")

    def append_json_list(
        self,
        tenant_id: str,
        rel_key: str,
        list_field: str,
        item: dict,
        *,
        id_field: str = "id",
        default: Optional[dict] = None
    ) -> Tuple[dict, int]:
        def mutator(doc: dict) -> dict:
            items = doc.setdefault(list_field, [])
            item_id = item.get(id_field)
            if item_id:
                idx = next((i for i, x in enumerate(items) if isinstance(x, dict) and x.get(id_field) == item_id), -1)
                if idx >= 0:
                    if "reactions" in items[idx] and "reactions" not in item:
                        item["reactions"] = items[idx]["reactions"]
                    items[idx] = item
                else:
                    items.append(item)
            else:
                items.append(item)
            return doc

        base_default = default if default is not None else {list_field: []}
        return self.update_json(tenant_id, rel_key, mutator, default=base_default)

    def append_line(self, tenant_id: str, rel_key: str, line: str) -> None:
        path = self._resolve_path(tenant_id, rel_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        text_line = line if line.endswith("\n") else line + "\n"
        with self._lock:
            with open(path, "a", encoding="utf-8") as f:
                f.write(text_line)

    def exists(self, tenant_id: str, rel_key: str) -> bool:
        path = self._resolve_path(tenant_id, rel_key)
        return path.exists()

    def delete(self, tenant_id: str, rel_key: str) -> None:
        path = self._resolve_path(tenant_id, rel_key)
        with self._lock:
            if path.exists():
                path.unlink()

    def list_keys(self, tenant_id: str, prefix: str = "") -> List[str]:
        if not tenant_id or tenant_id == "__direct__":
            t_dir = self.base_dir
        else:
            clean_tid = sanitize_tenant_id(tenant_id)
            t_dir = get_tenant_dir(clean_tid, base_dir=self.base_dir)
        if not t_dir.exists():
            return []
        keys = []
        norm_prefix = prefix.strip().lstrip("/").replace("\\", "/")
        for p in t_dir.rglob("*"):
            if p.is_file():
                rel = str(p.relative_to(t_dir)).replace("\\", "/")
                if not norm_prefix or rel.startswith(norm_prefix):
                    keys.append(rel)
        return sorted(keys)


class GCSStorageAdapter(StorageAdapter):
    """
    Google Cloud Storage implementation of StorageAdapter with generation-precondition CAS.
    Uses blob.generation and if_generation_match for optimistic concurrency control.
    """
    def __init__(self, bucket_name: str, client: Optional[Any] = None, project_id: Optional[str] = None):
        self.bucket_name = bucket_name
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._client = client
        self._bucket = None
        self._lock = threading.RLock()

    @property
    def client(self):
        if self._client is None:
            from google.cloud import storage
            self._client = storage.Client(project=self.project_id)
        return self._client

    @property
    def bucket(self):
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket

    def _blob_name(self, tenant_id: str, rel_key: str) -> str:
        clean_tid = sanitize_tenant_id(tenant_id)
        clean_key = str(rel_key).strip().lstrip("/").replace("\\", "/")
        parts = [p for p in clean_key.split("/") if p and p != "." and p != ".."]
        return f"tenants/{clean_tid}/{'/'.join(parts)}"

    def read_json_with_gen(self, tenant_id: str, rel_key: str) -> Tuple[Optional[dict], int]:
        blob_name = self._blob_name(tenant_id, rel_key)
        blob = self.bucket.get_blob(blob_name)
        if not blob:
            return None, 0
        try:
            content = blob.download_as_text(encoding="utf-8")
            return json.loads(content), int(blob.generation)
        except json.JSONDecodeError as jde:
            raise StorageCorruptError(f"Corrupt JSON in GCS blob {blob_name}: {jde}") from jde
        except Exception as e:
            # Only return None, 0 if genuinely NotFound from GCS
            from google.api_core.exceptions import NotFound
            if isinstance(e, NotFound):
                return None, 0
            raise

    def read_json(self, tenant_id: str, rel_key: str) -> Optional[dict]:
        """Reads JSON document at rel_key. Returns None if absent or corrupt."""
        try:
            doc, _ = self.read_json_with_gen(tenant_id, rel_key)
            return doc
        except StorageCorruptError:
            return None

    def replace_json(
        self,
        tenant_id: str,
        rel_key: str,
        data: dict,
        *,
        default: Optional[dict] = None,
        expected_generation: int
    ) -> Tuple[dict, int]:
        if expected_generation is None:
            raise ValueError(f"replace_json on {rel_key} requires expected_generation: int (or UNCONDITIONAL)")
        from google.api_core.exceptions import PreconditionFailed
        blob_name = self._blob_name(tenant_id, rel_key)

        payload = json.dumps(data, indent=2)
        target_blob = self.bucket.blob(blob_name)
        try:
            if expected_generation == UNCONDITIONAL:
                target_blob.upload_from_string(
                    payload,
                    content_type="application/json"
                )
            else:
                target_blob.upload_from_string(
                    payload,
                    content_type="application/json",
                    if_generation_match=expected_generation
                )
            target_blob.reload()
            return data, int(target_blob.generation)
        except PreconditionFailed:
            raise StorageConflictError(
                f"GCS CAS conflict on {blob_name}: expected generation {expected_generation}"
            )

    def read_lines(self, tenant_id: str, rel_key: str) -> List[str]:
        blob_name = self._blob_name(tenant_id, rel_key)
        blob = self.bucket.get_blob(blob_name)
        if not blob:
            return []
        try:
            return blob.download_as_text(encoding="utf-8").splitlines()
        except Exception:
            return []

    def update_json(
        self,
        tenant_id: str,
        rel_key: str,
        mutator_fn: Callable[[dict], dict],
        *,
        default: Optional[dict] = None,
        max_retries: int = 5
    ) -> Tuple[dict, int]:
        from google.api_core.exceptions import PreconditionFailed
        blob_name = self._blob_name(tenant_id, rel_key)

        for attempt in range(max_retries):
            blob = self.bucket.get_blob(blob_name)
            if blob is not None:
                current_gen = int(blob.generation)
                try:
                    content = blob.download_as_text(encoding="utf-8")
                    current_doc = json.loads(content)
                except Exception as e:
                    raise StorageCorruptError(f"Corrupt JSON in GCS blob {blob_name}: {e}")
            else:
                current_gen = 0
                current_doc = copy.deepcopy(default) if default is not None else {}

            mutated_doc = mutator_fn(copy.deepcopy(current_doc))
            payload = json.dumps(mutated_doc, indent=2)

            target_blob = self.bucket.blob(blob_name)
            try:
                target_blob.upload_from_string(
                    payload,
                    content_type="application/json",
                    if_generation_match=current_gen
                )
                target_blob.reload()
                return mutated_doc, int(target_blob.generation)
            except PreconditionFailed:
                if attempt == max_retries - 1:
                    raise StorageConflictError(
                        f"GCS CAS conflict on {blob_name} after {max_retries} attempts (expected generation {current_gen})"
                    )
                sleep_sec = (0.05 * (2 ** attempt)) + random.uniform(0, 0.05)
                time.sleep(sleep_sec)

        raise StorageConflictError(f"GCS CAS conflict on {blob_name} exhausted {max_retries} retries")

    def append_json_list(
        self,
        tenant_id: str,
        rel_key: str,
        list_field: str,
        item: dict,
        *,
        id_field: str = "id",
        default: Optional[dict] = None
    ) -> Tuple[dict, int]:
        def mutator(doc: dict) -> dict:
            items = doc.setdefault(list_field, [])
            item_id = item.get(id_field)
            if item_id:
                idx = next((i for i, x in enumerate(items) if isinstance(x, dict) and x.get(id_field) == item_id), -1)
                if idx >= 0:
                    if "reactions" in items[idx] and "reactions" not in item:
                        item["reactions"] = items[idx]["reactions"]
                    items[idx] = item
                else:
                    items.append(item)
            else:
                items.append(item)
            return doc

        base_default = default if default is not None else {list_field: []}
        return self.update_json(tenant_id, rel_key, mutator, default=base_default)

    def append_line(self, tenant_id: str, rel_key: str, line: str) -> None:
        from google.api_core.exceptions import PreconditionFailed
        blob_name = self._blob_name(tenant_id, rel_key)
        text_line = line if line.endswith("\n") else line + "\n"
        for attempt in range(5):
            blob = self.bucket.get_blob(blob_name)
            if blob is not None:
                current_gen = int(blob.generation)
                current_text = blob.download_as_text(encoding="utf-8")
            else:
                current_gen = 0
                current_text = ""
            new_text = current_text + text_line
            target_blob = self.bucket.blob(blob_name)
            try:
                target_blob.upload_from_string(
                    new_text,
                    content_type="text/plain",
                    if_generation_match=current_gen
                )
                return
            except PreconditionFailed:
                if attempt == 4:
                    raise StorageConflictError(f"GCS CAS conflict on {blob_name} exhausted retries")
                time.sleep(0.05 * (2 ** attempt) + random.uniform(0, 0.05))
        raise StorageConflictError(f"GCS CAS conflict on {blob_name} exhausted retries")

    def exists(self, tenant_id: str, rel_key: str) -> bool:
        blob_name = self._blob_name(tenant_id, rel_key)
        return self.bucket.blob(blob_name).exists()

    def delete(self, tenant_id: str, rel_key: str) -> None:
        blob_name = self._blob_name(tenant_id, rel_key)
        blob = self.bucket.get_blob(blob_name)
        if blob:
            blob.delete()

    def list_keys(self, tenant_id: str, prefix: str = "") -> List[str]:
        clean_tid = sanitize_tenant_id(tenant_id)
        base_prefix = f"tenants/{clean_tid}/"
        norm_prefix = prefix.strip().lstrip("/").replace("\\", "/")
        full_prefix = f"{base_prefix}{norm_prefix}"
        blobs = self.bucket.list_blobs(prefix=full_prefix)
        keys = []
        for b in blobs:
            rel = b.name[len(base_prefix):]
            keys.append(rel)
        return sorted(keys)


class TenantRegistry:
    """
    Thread-safe registry caching per-tenant AgentRouter, MemoryStore, and A2ADispatcher instances.
    """
    def __init__(self, base_dir: Optional[Path] = None, storage_adapter: Optional[StorageAdapter] = None):
        self.base_dir = base_dir
        self._routers: Dict[str, AgentRouter] = {}
        self._memory_stores: Dict[str, MemoryStore] = {}
        self._dispatchers: Dict[str, Any] = {}
        self._storage_adapter = storage_adapter
        self._lock = threading.RLock()

    def get_storage_adapter(self, tenant_id: Optional[str] = None) -> StorageAdapter:
        if self._storage_adapter is not None:
            return self._storage_adapter
        with self._lock:
            if self._storage_adapter is None:
                self._storage_adapter = get_storage_adapter(base_dir=self.base_dir)
            return self._storage_adapter

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
                adapter = self.get_storage_adapter(tenant_id)
                self._memory_stores[key] = MemoryStore(bridge_dir=t_dir, storage_adapter=adapter)
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
                    tenant_id=tenant_id or sanitize_tenant_id(tenant_id),
                    agent_router=r_inst,
                    queue_backend=dispatcher_kwargs.get("queue_backend"),
                    load_history_fn=dispatcher_kwargs.get("load_history_fn") or (lambda pid: bridge_runner.load_history(pid, bridge_dir=t_dir)),
                    save_history_fn=dispatcher_kwargs.get("save_history_fn") or (lambda data, project_id="lantern", **kw: bridge_runner.save_history(data, project_id=project_id, bridge_dir=t_dir, expected_generation=kw["expected_generation"])),
                    load_projects_fn=dispatcher_kwargs.get("load_projects_fn") or (lambda: bridge_runner.load_projects(bridge_dir=t_dir)),
                    build_messages_fn=dispatcher_kwargs.get("build_messages_fn") or (lambda *args, **kw: bridge_runner.build_anthropic_messages_and_system(*args, bridge_dir=t_dir, **kw)),
                    build_self_context_fn=dispatcher_kwargs.get("build_self_context_fn") or (lambda *args, **kw: bridge_runner.build_agent_self_context(*args, bridge_dir=t_dir, **kw)),
                    append_transaction_fn=dispatcher_kwargs.get("append_transaction_fn") or (lambda pid, tx: bridge_runner.append_transaction(pid, tx, bridge_dir=t_dir)),
                    bridge_auth_token=dispatcher_kwargs.get("bridge_auth_token") or os.environ.get("BRIDGE_AUTH_TOKEN"),
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
                    dispatcher = self._dispatchers[key]
                    if hasattr(dispatcher, "queue_backend") and hasattr(dispatcher.queue_backend, "stop"):
                        dispatcher.queue_backend.stop()
                    elif hasattr(dispatcher, "stop"):
                        dispatcher.stop()
                    dispatcher.task_queue = None
                except Exception:
                    pass
                del self._dispatchers[key]


def is_cloud() -> bool:
    """Returns True if running in cloud shared environment (fail-closed tenancy)."""
    return bool(os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN"))


def use_gcs_storage() -> bool:
    """Returns True if storage mutations should route directly to GCS bucket."""
    return bool(os.environ.get("GCS_DATA_BUCKET")) and (
        os.environ.get("K_SERVICE") or os.environ.get("CLOUD_RUN_DIRECT_GCS")
    )


def get_storage_adapter(base_dir: Optional[Path] = None, bucket_name: Optional[str] = None) -> StorageAdapter:
    """
    Factory function returning the appropriate StorageAdapter based on environment.
    """
    if bucket_name:
        return GCSStorageAdapter(bucket_name=bucket_name)
    bucket = os.environ.get("GCS_DATA_BUCKET")
    if bucket and use_gcs_storage():
        return GCSStorageAdapter(bucket_name=bucket)
    return LocalStorageAdapter(base_dir=base_dir)


# Global default tenant registry
tenant_manager = TenantRegistry()

