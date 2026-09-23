#!/usr/bin/env python3
"""
Autonomous Agent-to-Agent (A2A) Event Dispatcher & Message Bus for Project Bridge Deck.

Provides asynchronous, mention-triggered turn handoffs across all active agents
(Vertex AI Claude/Gemini, Model Garden Gemma, Google ADK, and Antigravity).
Enforces cascade depth budgets, loop prevention, and human pause/resume controls.
"""

import os
import re
import time
import json
import queue
import threading
import base64
import requests
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
from core.tenant import StorageConflictError


class A2AQueueBackend(ABC):
    """Abstract interface for queuing A2A autonomous turns across local and cloud environments."""

    @abstractmethod
    def enqueue(self, task: Dict[str, Any], tenant_id: str) -> bool:
        """Enqueues an A2A task for asynchronous execution."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stops local workers or cleans up background resources."""
        pass

    @property
    @abstractmethod
    def is_durable(self) -> bool:
        """Returns True if tasks survive instance shutdown/scaling."""
        pass

    @abstractmethod
    def clear(self) -> Optional[int]:
        """Clears pending tasks if supported by backend."""
        pass

    @property
    def qsize(self) -> int:
        """Returns number of pending tasks if known."""
        return 0


class InMemoryQueueBackend(A2AQueueBackend):
    """Local in-memory FIFO queue with background worker thread."""

    def __init__(self, process_task_fn: Any):
        self.process_task_fn = process_task_fn
        self.queue: queue.Queue = queue.Queue()
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="A2A-InMemory-Worker"
        )
        self._worker_thread.start()

    @property
    def is_durable(self) -> bool:
        return False

    def enqueue(self, task: Dict[str, Any], tenant_id: str) -> bool:
        self.queue.put(task)
        return True

    def clear(self) -> int:
        count = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
                count += 1
            except queue.Empty:
                break
        return count

    @property
    def qsize(self) -> int:
        return self.queue.qsize()

    def stop(self) -> None:
        self._running = False
        try:
            self.queue.put_nowait(None)
        except Exception:
            pass
        if hasattr(self, "_worker_thread") and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.5)

    def _worker_loop(self):
        while self._running:
            try:
                task = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not self._running or task is None:
                try:
                    self.queue.task_done()
                except Exception:
                    pass
                break

            try:
                self.process_task_fn(task)
            except Exception as e:
                print(f"[!] InMemoryQueueBackend error processing task {task.get('id') if isinstance(task, dict) else 'unknown'}: {e}")
            finally:
                try:
                    self.queue.task_done()
                except Exception:
                    pass


BOOTSTRAP_PLACEHOLDER_URL = "https://pending-bootstrap.internal"


class CloudTasksQueueBackend(A2AQueueBackend):
    """
    Durable distributed task queue backed by Google Cloud Tasks.
    Dispatches asynchronous HTTP POST tasks to Cloud Run endpoint /api/a2a/task
    with OIDC identity token authentication.
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        queue_name: str,
        service_url: str,
        service_account_email: Optional[str] = None,
        bridge_auth_token: Optional[str] = None,
        session: Optional[Any] = None
    ):
        if not project_id:
            raise ValueError("CloudTasksQueueBackend requires a non-empty project_id (set CLOUD_TASKS_PROJECT or GOOGLE_CLOUD_PROJECT)")
        if not service_url:
            raise ValueError("CloudTasksQueueBackend requires a non-empty service_url (set CLOUD_TASKS_SERVICE_URL or SERVICE_URL)")
        resolved_token = bridge_auth_token or os.environ.get("BRIDGE_AUTH_TOKEN")
        if not resolved_token:
            raise ValueError("CloudTasksQueueBackend requires a non-empty bridge_auth_token (set BRIDGE_AUTH_TOKEN)")
        self.project_id = project_id
        self.location = location
        self.queue_name = queue_name
        self.service_url = service_url
        self.service_account_email = service_account_email
        self.bridge_auth_token = resolved_token
        self._session = session
        self._api_url = (
            f"https://cloudtasks.googleapis.com/v2/projects/{self.project_id}/"
            f"locations/{self.location}/queues/{self.queue_name}/tasks"
        )

    @property
    def is_durable(self) -> bool:
        return True

    def _get_session(self) -> Any:
        if self._session is not None:
            return self._session
        try:
            import google.auth
            import google.auth.transport.requests
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            auth_req = google.auth.transport.requests.Request()
            creds.refresh(auth_req)
            s = requests.Session()
            s.headers["Authorization"] = f"Bearer {creds.token}"
            self._session = s
            return s
        except Exception as e:
            raise RuntimeError(f"Failed to obtain Google Cloud credentials for Cloud Tasks: {e}") from e

    def enqueue(self, task: Dict[str, Any], tenant_id: str) -> bool:
        if self.service_url == BOOTSTRAP_PLACEHOLDER_URL:
            raise RuntimeError(
                "CloudTasksQueueBackend: CLOUD_TASKS_SERVICE_URL is still set to bootstrap placeholder "
                f"({BOOTSTRAP_PLACEHOLDER_URL}). Post-deploy service URL injection has not run."
            )
        payload = {
            "tenant_id": tenant_id,
            "task": task
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        body_b64 = base64.b64encode(body_bytes).decode("utf-8")

        target_url = f"{self.service_url.rstrip('/')}/api/a2a/task"
        headers = {
            "Content-Type": "application/json",
            "X-Bridge-Auth": self.bridge_auth_token
        }

        http_request = {
            "httpMethod": "POST",
            "url": target_url,
            "headers": headers,
            "body": body_b64
        }
        if self.service_account_email:
            http_request["oidcToken"] = {
                "serviceAccountEmail": self.service_account_email,
                "audience": self.service_url.rstrip('/')
            }

        task_payload = {
            "task": {
                "httpRequest": http_request,
                "dispatchDeadline": "1800s"
            }
        }
        session = self._get_session()
        resp = session.post(self._api_url, json=task_payload, timeout=10)
        if resp.status_code == 401:
            # Token expired: invalidate session cache, refresh credentials, and retry once
            self._session = None
            session = self._get_session()
            resp = session.post(self._api_url, json=task_payload, timeout=10)
        if resp.status_code in (200, 201):
            return True
        else:
            raise RuntimeError(f"Cloud Tasks API returned HTTP {resp.status_code}: {resp.text}")

    def clear(self) -> Optional[int]:
        # Purging a distributed Cloud Tasks queue requires cloudtasks.queues.purge.
        # Returning None signals that clear_queue is not supported locally.
        return None

    @property
    def qsize(self) -> Optional[int]:
        """Returns None as distributed queue depth is not tracked locally."""
        return None

    def stop(self) -> None:
        pass


class A2ADispatcher:
    def __init__(
        self,
        bridge_dir: Path,
        agent_router: Any,
        load_history_fn: Any,
        save_history_fn: Any,
        load_projects_fn: Any,
        build_messages_fn: Any,
        build_self_context_fn: Any,
        append_transaction_fn: Any,
        max_depth: Optional[int] = None,
        tenant_id: Optional[str] = None,
        queue_backend: Optional[A2AQueueBackend] = None,
        bridge_auth_token: Optional[str] = None
    ):
        self.bridge_dir = Path(bridge_dir)
        self.tenant_id = tenant_id or (
            self.bridge_dir.name if self.bridge_dir.parent.name == "tenants" else "default"
        )
        self.agent_router = agent_router
        self.load_history = load_history_fn
        self.save_history = save_history_fn
        self.append_transaction_fn = append_transaction_fn
        self.load_projects = load_projects_fn
        self.build_messages = build_messages_fn
        self.build_self_context = build_self_context_fn
        self.max_depth = max_depth
        self.bridge_auth_token = bridge_auth_token or os.environ.get("BRIDGE_AUTH_TOKEN")

        self.paused_projects: Set[str] = set()
        self.global_paused: bool = False
        self.active_task: Optional[Dict[str, Any]] = None
        self.recent_dispatches: List[Dict[str, Any]] = []
        self._root_task_counts: Dict[str, int] = {}
        self._seen_tasks: Set[Tuple[str, str, int]] = set()
        self._lock = threading.RLock()
        self._running = True

        # Initialize Queue Backend
        if queue_backend is not None:
            self.queue_backend = queue_backend
        elif os.environ.get("A2A_QUEUE_BACKEND") == "cloud_tasks" or os.environ.get("CLOUD_TASKS_QUEUE"):
            project_id = os.environ.get("CLOUD_TASKS_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
            location = os.environ.get("CLOUD_TASKS_LOCATION") or os.environ.get("GCP_REGION", "us-central1")
            queue_name = os.environ.get("CLOUD_TASKS_QUEUE", "a2a-tasks")
            service_url = os.environ.get("CLOUD_TASKS_SERVICE_URL") or os.environ.get("SERVICE_URL", "")
            sa_email = os.environ.get("CLOUD_TASKS_SERVICE_ACCOUNT")
            self.queue_backend = CloudTasksQueueBackend(
                project_id=project_id,
                location=location,
                queue_name=queue_name,
                service_url=service_url,
                service_account_email=sa_email,
                bridge_auth_token=self.bridge_auth_token
            )
        else:
            self.queue_backend = InMemoryQueueBackend(process_task_fn=self._worker_process_wrapper)

        # Backward compatibility alias for task_queue
        if isinstance(self.queue_backend, InMemoryQueueBackend):
            self.task_queue = self.queue_backend.queue
        else:
            self.task_queue = queue.Queue()

    def parse_mentions(self, text: str, sender_id: Optional[str] = None) -> List[str]:
        """
        Parses @<agent_handle> tokens from text and matches against registered agents.
        Filters out self-mentions, human contributors (derived from manifests), and non-agent entities.
        """
        if not text:
            return []

        raw_handles = re.findall(r'@([a-zA-Z0-9_-]+)', text)
        manifests = getattr(self.agent_router, "manifests", {})
        known_agent_ids = {k.lower(): k for k in manifests.keys()}

        # Exclude common channel handles and sender
        excluded_handles = {"all", "here", "channel", "room", "team"}
        if sender_id:
            excluded_handles.add(sender_id.lower())

        # Dynamically exclude all human contributors declared in manifests
        for aid, man in manifests.items():
            p_info = man.get("provider", {})
            if str(p_info.get("type", "")).lower() == "human" or str(p_info.get("model", "")).lower() == "human":
                excluded_handles.add(aid.lower())
                name_first = (man.get("name") or "").split()[0].lower()
                if name_first:
                    excluded_handles.add(name_first)

        valid_targets = []
        for handle in raw_handles:
            h_lower = handle.lower()
            if h_lower in excluded_handles:
                continue
            if h_lower in known_agent_ids:
                canonical_id = known_agent_ids[h_lower]
                if canonical_id not in valid_targets:
                    valid_targets.append(canonical_id)

        return valid_targets

    def enqueue_if_mentions(
        self,
        text: str,
        sender_id: str,
        sender_name: str,
        sender_role: str,
        project_id: str,
        cascade_depth: int = 0,
        original_root_tx: Optional[str] = None
    ) -> List[str]:
        """
        Extracts mentions and enqueues autonomous turns for targeted agents
        with fan-out budget bounds and task deduplication.
        """
        if self.is_paused(project_id):
            return []

        targets = self.parse_mentions(text, sender_id=sender_id)
        if not targets:
            return []

        root_tx = original_root_tx or f"tx_{int(time.time() * 1000)}"

        enqueued_targets = []
        with self._lock:
            # Bound memory state over long process lifetimes (keep last 200 roots)
            if len(self._root_task_counts) > 200:
                old_roots = list(self._root_task_counts.keys())[:100]
                for r in old_roots:
                    self._root_task_counts.pop(r, None)
                self._seen_tasks = {k for k in self._seen_tasks if k[0] not in old_roots}

            for target_id in targets:
                current_count = self._root_task_counts.get(root_tx, 0)
                # Check fan-out budget only if depth limiting is explicitly configured
                if self.max_depth is not None and self.max_depth > 0:
                    if current_count >= 20:
                        print(f"[*] A2A fan-out limit reached for root_tx {root_tx} (count: {current_count}). Skipping @{target_id}.")
                        continue

                # Task deduplication (A2A-1: key on read-set identity to preserve sibling turns)
                text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
                task_key = (root_tx, target_id, cascade_depth, text_hash)
                if task_key in self._seen_tasks:
                    continue

                task = {
                    "id": f"a2a_{int(time.time() * 1000)}_{target_id}",
                    "target_agent_id": target_id,
                    "sender_id": sender_id,
                    "sender_name": sender_name,
                    "sender_role": sender_role,
                    "project_id": project_id,
                    "prompt": text,
                    "cascade_depth": cascade_depth,
                    "original_root_tx": root_tx,
                    "enqueued_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
                try:
                    self.queue_backend.enqueue(task, tenant_id=self.tenant_id)
                    self._seen_tasks.add(task_key)
                    self._root_task_counts[root_tx] = current_count + 1
                    enqueued_targets.append(target_id)
                except Exception as eq_err:
                    print(f"[!] Error enqueuing A2A task for @{target_id}: {eq_err}")

        return enqueued_targets

    def stop(self):
        """Signals the queue backend and workers to exit cleanly."""
        self._running = False
        if hasattr(self, "queue_backend") and self.queue_backend:
            self.queue_backend.stop()

    def _worker_process_wrapper(self, task: Dict[str, Any]):
        try:
            self.process_task(task)
        except StorageConflictError as sce:
            # Dual-Policy Retry Architecture:
            # - In-Worker Retry (InMemoryQueueBackend): Handled here via exponential backoff (retries <= 3).
            # - Distributed HTTP 409 Retry (CloudTasksQueueBackend): When invoked via Cloud Tasks HTTP POST /api/a2a/task,
            #   StorageConflictError propagates out to the endpoint handler in bridge_runner.py, which returns HTTP 409 Conflict.
            #   Google Cloud Tasks then manages distributed exponential retry according to queue bounds (--max-attempts=5).
            retries = task.get("_storage_retries", 0) + 1
            task["_storage_retries"] = retries
            if retries <= 3:
                print(f"[!] StorageConflictError processing A2A task {task.get('id')}: {sce}. Requeueing (attempt {retries}/3)...")
                time.sleep(0.05 * (2 ** retries))
                if isinstance(self.queue_backend, InMemoryQueueBackend):
                    self.queue_backend.enqueue(task, tenant_id=self.tenant_id)
            else:
                print(f"[!] StorageConflictError retry limit exceeded for task {task.get('id')}. Marking terminal failure.")
                self._post_failure_notice(task["project_id"], task["target_agent_id"], str(sce))
        except Exception as e:
            print(f"[!] Error processing A2A task {task.get('id')}: {e}")

    def _process_task(self, task: Dict[str, Any]):
        """Legacy internal wrapper calling public process_task."""
        return self.process_task(task)

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single A2A turn synchronously.
        Invoked either by InMemoryQueueBackend worker loop or directly via
        Cloud Run HTTP endpoint (/api/a2a/task) from Google Cloud Tasks.
        """
        project_id = task["project_id"]
        target_agent_id = task["target_agent_id"]
        sender_name = task["sender_name"]
        sender_role = task["sender_role"]
        prompt = task["prompt"]
        cascade_depth = task.get("cascade_depth", 0)

        if self.is_paused(project_id):
            return {"status": "skipped", "reason": "paused", "task_id": task.get("id")}

        with self._lock:
            self.active_task = {
                "id": task["id"],
                "target": target_agent_id,
                "sender": sender_name,
                "project_id": project_id,
                "cascade_depth": cascade_depth,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

        try:
            return self._run_task_turn(task, project_id, target_agent_id, sender_name, sender_role, prompt, cascade_depth)
        finally:
            with self._lock:
                if self.active_task and self.active_task.get("id") == task.get("id"):
                    self.active_task = None

    def _run_task_turn(
        self,
        task: Dict[str, Any],
        project_id: str,
        target_agent_id: str,
        sender_name: str,
        sender_role: str,
        prompt: str,
        cascade_depth: int
    ) -> Dict[str, Any]:
        # Check cascade depth budget only if explicitly configured
        if self.max_depth is not None and self.max_depth > 0 and cascade_depth >= self.max_depth:
            self._post_depth_limit_notice(project_id, target_agent_id, cascade_depth)
            return {
                "status": "depth_limited",
                "task_id": task.get("id"),
                "project_id": project_id,
                "reason": f"cascade depth {cascade_depth} >= max {self.max_depth}"
            }

        # Check project settings
        projects_data = self.load_projects()
        active_proj = next((p for p in projects_data.get("projects", []) if p.get("id") == project_id or p.get("id") == project_id.replace("proj_", "")), None)
        allow_subagents = active_proj.get("allow_subagents", True) if active_proj else True
        directories = active_proj.get("directories", []) if active_proj else []

        # Resolve target agent manifest & provider
        manifest = self.agent_router.manifests.get(target_agent_id, {})
        target_name = manifest.get("name", target_agent_id.capitalize())
        target_role = manifest.get("role", "Collaborator")

        resolved = self.agent_router.resolve(f"{target_agent_id}_direct", target_name)
        provider = resolved.get("provider")

        # Capture context watermark (last transaction visible when prompting)
        initial_hist = self.load_history(project_id)
        txs_before = initial_hist.get("transactions", [])
        context_watermark = txs_before[-1].get("id") if txs_before else None

        agent_self_hdr = self.build_self_context(target_agent_id, project_id=project_id)
        messages_list, system_prompt = self.build_messages(
            prompt=prompt,
            sender=sender_name,
            max_turns=6,
            project_id=project_id,
            target_agent_id=target_agent_id
        )

        task_id = str(task.get("id", ""))
        tx_id = f"tx_{task_id}" if task_id else f"tx_{int(time.time() * 1000)}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        response_text = None
        thinking_blocks = []
        status_code = 200
        start_time = time.time()

        if provider:
            inv_res = provider.invoke(
                prompt=prompt,
                system_prompt=system_prompt,
                messages=messages_list,
                context={
                    "self_context": agent_self_hdr,
                    "self_name": target_name,
                    "directories": directories,
                    "is_a2a": True
                }
            )
            if inv_res.get("success"):
                response_text = inv_res.get("response")
                thinking_blocks = inv_res.get("thinking_blocks", [])
                status_code = 200
            elif inv_res.get("is_pending"):
                response_text = inv_res.get("response")
                status_code = 200
            else:
                err_msg = inv_res.get("error", "Provider execution failed")
                response_text = f"⚠️ **[A2A Dispatch Error]**: {err_msg}"
                status_code = 500
        else:
            response_text = f"⚠️ **[A2A Dispatch Error]**: No provider configured for agent '{target_agent_id}'."
            status_code = 500

        elapsed_sec = round(time.time() - start_time, 2)

        # Mid-flight pause verification (discard turn if operator paused room during inference)
        if self.is_paused(project_id):
            print(f"[*] A2A task {task.get('id')} for {target_agent_id} aborted mid-flight due to operator pause.")
            return {
                "status": "aborted_paused",
                "task_id": task.get("id"),
                "project_id": project_id,
                "reason": "room_paused_during_inference"
            }

        # Determine response attribution derived from provider type rather than hardcoded name list
        p_type = str(manifest.get("provider", {}).get("type", "")).lower()
        is_antigravity = (p_type == "antigravity-queue" or p_type.startswith("antigravity"))

        # Thread-safe append to project history with commit watermark
        # Lock Hierarchy Invariant: A2ADispatcher._lock -> bridge_runner.file_io_lock
        # Calling append_transaction_fn while holding self._lock is safe because file_io_lock is never held
        # across calls into A2ADispatcher methods.
        with self._lock:
            history = self.load_history(project_id)
            curr_txs = history.get("transactions", [])
            commit_watermark = curr_txs[-1].get("id") if curr_txs else None

            # Build transaction object matching Bridge Deck history schema
            new_tx = {
                "id": tx_id,
                "timestamp": timestamp,
                "mode": f"{target_agent_id}_direct",
                "target_agent_id": target_agent_id,
                "sender": sender_name,
                "sender_role": sender_role,
                "recipient": target_name,
                "recipient_role": target_role,
                "subject": f"A2A Autonomous Turn ({sender_name} → {target_name})",
                "prompt_text": prompt,
                "antigravity_response": response_text if is_antigravity else None,
                "claude_response": response_text if not is_antigravity else None,
                "claude_model": manifest.get("provider", {}).get("model", "auto") if not is_antigravity else None,
                "thinking_blocks": thinking_blocks,
                "a2a_meta": {
                    "cascade_depth": cascade_depth,
                    "root_tx": task.get("original_root_tx"),
                    "auto_dispatched": True,
                    "context_watermark": context_watermark,
                    "commit_watermark": commit_watermark
                },
                "raw_request_json": {
                    "mode": f"{target_agent_id}_direct",
                    "sender": sender_name,
                    "sender_role": sender_role,
                    "recipient": target_name,
                    "recipient_role": target_role,
                    "prompt": prompt,
                    "is_a2a": True
                },
                "raw_response_json": {
                    "id": tx_id,
                    "status_code": status_code,
                    "elapsed_seconds": elapsed_sec
                }
            }

            self.append_transaction_fn(project_id, new_tx)

            self.recent_dispatches.append({
                "tx_id": tx_id,
                "target": target_name,
                "sender": sender_name,
                "project_id": project_id,
                "depth": cascade_depth,
                "elapsed": elapsed_sec,
                "timestamp": timestamp,
                "watermark_drift": bool(context_watermark != commit_watermark)
            })
            if len(self.recent_dispatches) > 50:
                self.recent_dispatches.pop(0)

        # Enqueue next cascade hop if the new response mentions further agents
        if response_text and status_code == 200:
            self.enqueue_if_mentions(
                text=response_text,
                sender_id=target_agent_id,
                sender_name=target_name,
                sender_role=target_role,
                project_id=project_id,
                cascade_depth=cascade_depth + 1,
                original_root_tx=task.get("original_root_tx")
            )

        return {
            "status": "completed",
            "task_id": task.get("id"),
            "tx_id": tx_id,
            "target": target_name,
            "elapsed": elapsed_sec
        }

    def _post_depth_limit_notice(self, project_id: str, target_agent_id: str, depth: int):
        """Appends a pause notice when turn depth exceeds max budget."""
        tx_id = f"tx_{int(time.time())}"
        notice_tx = {
            "id": tx_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "mode": "system_notice",
            "target_agent_id": "system",
            "sender": "Bridge Deck A2A Supervisor",
            "sender_role": "Platform System",
            "recipient": "Team",
            "recipient_role": "Workspace Collaborators",
            "subject": "A2A Turn Budget Reached",
            "prompt_text": "",
            "antigravity_response": f"⏸️ **[A2A Turn Limit Reached]**: Autonomous collaboration reached the maximum cascade depth limit ({depth} turns). Paused to preserve quota and invite human direction.",
            "claude_response": None,
            "claude_model": None,
            "thinking_blocks": [],
            "raw_request_json": {"is_a2a_notice": True},
            "raw_response_json": {"id": tx_id, "status_code": 200, "elapsed_seconds": 0.0}
        }
        self.append_transaction_fn(project_id, notice_tx)

    def _post_failure_notice(self, project_id: str, target_agent_id: str, error_msg: str):
        tx_id = f"tx_err_{int(time.time() * 1000)}"
        notice_tx = {
            "id": tx_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "mode": "system_notice",
            "target_agent_id": target_agent_id,
            "sender": "Bridge Deck A2A Supervisor",
            "sender_role": "Platform System",
            "recipient": "Team",
            "recipient_role": "Workspace Collaborators",
            "subject": "A2A Turn Execution Failed",
            "prompt_text": "",
            "antigravity_response": f"⚠️ **[A2A Task Failed]**: Autonomous turn execution failed after retry exhaustion: {error_msg}",
            "claude_response": None,
            "claude_model": None,
            "thinking_blocks": [],
            "raw_request_json": {"is_a2a_failure": True, "error": error_msg},
            "raw_response_json": {"id": tx_id, "status_code": 409, "elapsed_seconds": 0.0}
        }
        try:
            self.append_transaction_fn(project_id, notice_tx)
        except Exception as ne:
            print(f"[!] Notice failure append error: {ne}")

    def reset_active_task(self):
        """Clears current active task indicator state."""
        with self._lock:
            self.active_task = None

    def pause(self, project_id: Optional[str] = None):
        with self._lock:
            if project_id:
                norm_pid = project_id.replace("proj_", "")
                self.paused_projects.add(project_id)
                self.paused_projects.add(norm_pid)
                self.paused_projects.add(f"proj_{norm_pid}")
                if self.active_task and (self.active_task.get("project_id") in [project_id, norm_pid, f"proj_{norm_pid}"]):
                    self.active_task = None
            else:
                self.global_paused = True
                self.active_task = None

    def resume(self, project_id: Optional[str] = None):
        with self._lock:
            if project_id:
                norm_pid = project_id.replace("proj_", "")
                self.paused_projects.discard(project_id)
                self.paused_projects.discard(norm_pid)
                self.paused_projects.discard(f"proj_{norm_pid}")
            else:
                self.global_paused = False

    def is_paused(self, project_id: Optional[str] = None) -> bool:
        with self._lock:
            if self.global_paused:
                return True
            if project_id:
                norm_pid = project_id.replace("proj_", "")
                if project_id in self.paused_projects or norm_pid in self.paused_projects or f"proj_{norm_pid}" in self.paused_projects:
                    return True
                if hasattr(self, "load_projects") and self.load_projects:
                    try:
                        p_data = self.load_projects()
                        for p in p_data.get("projects", []):
                            if p.get("id") == project_id or p.get("id") == norm_pid:
                                if p.get("a2a_paused", False):
                                    return True
                    except Exception:
                        pass
            return False

    def clear_queue(self) -> Optional[int]:
        self.reset_active_task()
        if hasattr(self, "queue_backend") and self.queue_backend:
            return self.queue_backend.clear()
        return 0

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            q_size = self.queue_backend.qsize if hasattr(self, "queue_backend") and self.queue_backend else 0
            is_durable = self.queue_backend.is_durable if hasattr(self, "queue_backend") and self.queue_backend else False
            paused = set(self.paused_projects)
            if hasattr(self, "load_projects") and self.load_projects:
                try:
                    p_data = self.load_projects()
                    for p in p_data.get("projects", []):
                        if p.get("a2a_paused", False):
                            pid = p.get("id")
                            if pid:
                                paused.add(pid)
                                paused.add(f"proj_{pid}" if not str(pid).startswith("proj_") else pid)
                except Exception:
                    pass
            return {
                "running": self._running,
                "durable": is_durable,
                "global_paused": self.global_paused,
                "paused_projects": list(paused),
                "queue_size": q_size,
                "queue_size_known": q_size is not None,
                "active_task": self.active_task,
                "recent_dispatches": self.recent_dispatches[-10:]
            }
