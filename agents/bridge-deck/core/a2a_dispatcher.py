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
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path


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
        max_depth: int = 5,
        append_transaction_fn: Optional[Any] = None
    ):
        self.bridge_dir = Path(bridge_dir)
        self.agent_router = agent_router
        self.load_history = load_history_fn
        self.save_history = save_history_fn
        self.append_transaction_fn = append_transaction_fn
        self.load_projects = load_projects_fn
        self.build_messages = build_messages_fn
        self.build_self_context = build_self_context_fn
        self.max_depth = max_depth

        self.task_queue: queue.Queue = queue.Queue()
        self.paused_projects: Set[str] = set()
        self.global_paused: bool = False
        self.active_task: Optional[Dict[str, Any]] = None
        self.recent_dispatches: List[Dict[str, Any]] = []
        self._root_task_counts: Dict[str, int] = {}
        self._seen_tasks: Set[Tuple[str, str, int]] = set()
        self._lock = threading.Lock()

        # Start background worker daemon
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="A2A-Dispatcher-Worker")
        self._worker_thread.start()

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
                # Check fan-out budget (max 20 autonomous turns per root_tx)
                current_count = self._root_task_counts.get(root_tx, 0)
                if current_count >= 20:
                    print(f"[*] A2A fan-out limit reached for root_tx {root_tx} (count: {current_count}). Skipping @{target_id}.")
                    continue

                # Task deduplication
                task_key = (root_tx, target_id, cascade_depth)
                if task_key in self._seen_tasks:
                    continue

                self._seen_tasks.add(task_key)
                self._root_task_counts[root_tx] = current_count + 1

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
                self.task_queue.put(task)
                enqueued_targets.append(target_id)

        return enqueued_targets

    def stop(self):
        """Signals the background worker to exit cleanly."""
        self._running = False
        try:
            self.task_queue.put_nowait(None)
        except Exception:
            pass
        if hasattr(self, "_worker_thread") and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=0.5)

    def _worker_loop(self):
        """Continuous background execution loop for A2A turns."""
        while self._running:
            try:
                task = self.task_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if not self._running or task is None:
                try:
                    self.task_queue.task_done()
                except Exception:
                    pass
                break

            try:
                self._process_task(task)
            except Exception as e:
                print(f"[!] Error processing A2A task {task.get('id')}: {e}")
            finally:
                with self._lock:
                    self.active_task = None
                try:
                    self.task_queue.task_done()
                except Exception:
                    pass

    def _process_task(self, task: Dict[str, Any]):
        project_id = task["project_id"]
        target_agent_id = task["target_agent_id"]
        sender_name = task["sender_name"]
        sender_role = task["sender_role"]
        prompt = task["prompt"]
        cascade_depth = task["cascade_depth"]

        if self.is_paused(project_id):
            return

        with self._lock:
            self.active_task = {
                "id": task["id"],
                "target": target_agent_id,
                "sender": sender_name,
                "project_id": project_id,
                "cascade_depth": cascade_depth,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }

        # Check cascade depth budget
        if cascade_depth >= self.max_depth:
            self._post_depth_limit_notice(project_id, target_agent_id, cascade_depth)
            return

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

        tx_id = f"tx_{int(time.time() * 1000)}"
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
            return

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

            if self.append_transaction_fn:
                self.append_transaction_fn(project_id, new_tx)
            else:
                history.setdefault("transactions", []).append(new_tx)
                self.save_history(history, project_id=project_id)

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
        if self.append_transaction_fn:
            self.append_transaction_fn(project_id, notice_tx)
        else:
            with self._lock:
                history = self.load_history(project_id)
                history.setdefault("transactions", []).append(notice_tx)
                self.save_history(history, project_id=project_id)

    def pause(self, project_id: Optional[str] = None):
        with self._lock:
            if project_id:
                self.paused_projects.add(project_id)
            else:
                self.global_paused = True

    def resume(self, project_id: Optional[str] = None):
        with self._lock:
            if project_id:
                self.paused_projects.discard(project_id)
            else:
                self.global_paused = False

    def is_paused(self, project_id: Optional[str] = None) -> bool:
        with self._lock:
            if self.global_paused:
                return True
            if project_id and project_id in self.paused_projects:
                return True
            return False

    def clear_queue(self) -> int:
        count = 0
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
                self.task_queue.task_done()
                count += 1
            except queue.Empty:
                break
        return count

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "global_paused": self.global_paused,
                "paused_projects": list(self.paused_projects),
                "queue_size": self.task_queue.qsize(),
                "active_task": self.active_task,
                "recent_dispatches": self.recent_dispatches[-10:]
            }
