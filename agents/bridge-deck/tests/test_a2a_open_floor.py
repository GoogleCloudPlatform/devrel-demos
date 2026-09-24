#!/usr/bin/env python3
"""
Unit and integration tests for A2A Collaboration Modes:
[ ⏸ Pause | ▶ Mentions | 🌐 Open Floor ]
Verifies mode switching, immediate open floor handoffs, silence token suppression, and HTTP endpoints.
"""

import os
import sys
import json
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.a2a_dispatcher import A2ADispatcher, InMemoryQueueBackend


class TestA2AOpenFloorMode(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_a2a_open_floor_"))

    def tearDown(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_mode_transitions(self):
        """Verify set_mode and get_mode across paused, mentions, and open_floor."""
        mock_router = MagicMock()
        mock_router.manifests = {}

        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda p: {"transactions": []},
            save_history_fn=lambda d, p: None,
            load_projects_fn=lambda: {"projects": [{"id": "proj_flow", "members": ["astra", "vector"]}]},
            build_messages_fn=lambda *args, **kw: ([], ""),
            build_self_context_fn=lambda *args, **kw: "",
            append_transaction_fn=lambda p, tx: None
        )

        try:
            # Default mode is mentions
            self.assertEqual(dispatcher.get_mode("proj_flow"), "mentions")
            self.assertFalse(dispatcher.is_paused("proj_flow"))

            # Switch to open_floor
            dispatcher.set_mode("proj_flow", "open_floor")
            self.assertEqual(dispatcher.get_mode("proj_flow"), "open_floor")
            self.assertFalse(dispatcher.is_paused("proj_flow"))

            # Switch to paused
            dispatcher.set_mode("proj_flow", "paused")
            self.assertEqual(dispatcher.get_mode("proj_flow"), "paused")
            self.assertTrue(dispatcher.is_paused("proj_flow"))

            # Resume switches back to mentions
            dispatcher.resume("proj_flow")
            self.assertEqual(dispatcher.get_mode("proj_flow"), "mentions")
            self.assertFalse(dispatcher.is_paused("proj_flow"))

            # Status contains project_modes
            status = dispatcher.get_status()
            self.assertIn("project_modes", status)
            self.assertEqual(status["project_modes"].get("proj_flow"), "mentions")
        finally:
            dispatcher.stop()

    def test_open_floor_handoff_triggered_when_no_mentions(self):
        """Verify open floor handoff triggers when agent finishes without explicit @mention."""
        mock_provider = MagicMock()
        mock_provider.invoke.return_value = {
            "success": True,
            "response": "Batch 2a is committed to git. Ready for review."
        }

        mock_router = MagicMock()
        mock_router.manifests = {
            "jared": {
                "name": "Jared",
                "role": "ADK Simulation Specialist",
                "provider": {"type": "google-adk"}
            },
            "vector": {
                "name": "Vector",
                "role": "Systems Specialist",
                "provider": {"type": "vertex-ai"}
            }
        }
        mock_router.resolve.return_value = {"provider": mock_provider}

        enqueued_tasks = []
        mock_backend = MagicMock()
        mock_backend.qsize = 0
        mock_backend.is_durable = False
        mock_backend.enqueue.side_effect = lambda t, tenant_id: enqueued_tasks.append(t)

        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda p: {"transactions": []},
            save_history_fn=lambda d, p: None,
            load_projects_fn=lambda: {
                "projects": [
                    {"id": "proj_flow", "name": "Flow Simulation", "members": ["jared", "vector"]}
                ]
            },
            build_messages_fn=lambda *args, **kw: ([], "System Prompt"),
            build_self_context_fn=lambda *args, **kw: "Self Context",
            append_transaction_fn=lambda p, tx: None,
            queue_backend=mock_backend
        )

        try:
            # First in 'mentions' mode: should NOT trigger open floor handoff
            dispatcher.set_mode("proj_flow", "mentions")
            task_mentions = {
                "id": "task_1",
                "target_agent_id": "jared",
                "sender_id": "astra",
                "sender_name": "Astra",
                "sender_role": "Lead Architect",
                "project_id": "proj_flow",
                "prompt": "Please write the enums",
                "cascade_depth": 0
            }
            dispatcher.process_task(task_mentions)
            self.assertEqual(len(enqueued_tasks), 0)

            # Now switch to 'open_floor' mode: SHOULD trigger handoff to Vector
            dispatcher.set_mode("proj_flow", "open_floor")
            task_open_floor = {
                "id": "task_2",
                "target_agent_id": "jared",
                "sender_id": "astra",
                "sender_name": "Astra",
                "sender_role": "Lead Architect",
                "project_id": "proj_flow",
                "prompt": "Please write the enums",
                "cascade_depth": 0
            }
            dispatcher.process_task(task_open_floor)
            self.assertEqual(len(enqueued_tasks), 1)
            handoff = enqueued_tasks[0]
            self.assertEqual(handoff["target_agent_id"], "vector")
            self.assertTrue(handoff["is_pulse"])
            self.assertIn("Batch 2a is committed", handoff["prompt"])
        finally:
            dispatcher.stop()

    def test_silence_token_suppressed(self):
        """Verify [NO_CONTRIBUTION_NEEDED] from handoff/pulse is suppressed without writing to history."""
        mock_provider = MagicMock()
        mock_provider.invoke.return_value = {
            "success": True,
            "response": "[NO_CONTRIBUTION_NEEDED]"
        }

        mock_router = MagicMock()
        mock_router.manifests = {
            "vector": {
                "name": "Vector",
                "role": "Systems Specialist",
                "provider": {"type": "vertex-ai"}
            }
        }
        mock_router.resolve.return_value = {"provider": mock_provider}

        appended_transactions = []
        def mock_append(pid, tx):
            appended_transactions.append(tx)

        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda p: {"transactions": []},
            save_history_fn=lambda d, p: None,
            load_projects_fn=lambda: {"projects": [{"id": "proj_flow", "members": ["vector"]}]},
            build_messages_fn=lambda *args, **kw: ([], "System Prompt"),
            build_self_context_fn=lambda *args, **kw: "Self Context",
            append_transaction_fn=mock_append
        )

        try:
            pulse_task = {
                "id": "openfloor_123_vector",
                "target_agent_id": "vector",
                "sender_id": "jared",
                "sender_name": "Jared",
                "sender_role": "Specialist",
                "project_id": "proj_flow",
                "prompt": "Open floor prompt",
                "cascade_depth": 1,
                "is_pulse": True
            }

            result = dispatcher.process_task(pulse_task)
            self.assertEqual(result["status"], "suppressed_no_contribution")
            self.assertEqual(len(appended_transactions), 0)
        finally:
            dispatcher.stop()

    def test_http_api_mode_endpoint(self):
        """Verify POST /api/a2a/mode sets open_floor mode and persists."""
        from http.server import ThreadingHTTPServer
        import threading
        import requests
        import bridge_runner

        bridge_runner.BRIDGE_AUTH_TOKEN = "test-token"
        bridge_runner.BRIDGE_DIR = self.test_dir
        bridge_runner.BASE_DIR = self.test_dir

        t_dir = bridge_runner.ensure_tenant_initialized("default", base_dir=self.test_dir)
        projects_file = t_dir / "projects.json"
        projects_file.write_text(json.dumps({
            "projects": [
                {"id": "proj_flow", "name": "Flow Workspace", "members": ["jared", "vector"]}
            ]
        }))

        server = ThreadingHTTPServer(("127.0.0.1", 0), bridge_runner.BridgeRequestHandler)
        port = server.server_address[1]
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            mock_dispatcher = MagicMock()
            with patch("core.tenant.TenantRegistry.get_dispatcher", return_value=mock_dispatcher):
                url = f"http://127.0.0.1:{port}/api/a2a/mode"
                headers = {"X-Bridge-Auth": "test-token", "Content-Type": "application/json"}

                res = requests.post(url, headers=headers, json={"project_id": "proj_flow", "mode": "open_floor"})
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertTrue(data["success"])
                self.assertEqual(data["mode"], "open_floor")
                self.assertFalse(data["paused"])
                mock_dispatcher.set_mode.assert_called_with("proj_flow", "open_floor")

                # Verify saved to projects.json
                saved = json.loads(projects_file.read_text())
                p_saved = next(p for p in saved["projects"] if p["id"] == "proj_flow")
                self.assertEqual(p_saved.get("a2a_mode"), "open_floor")
                self.assertFalse(p_saved.get("a2a_paused"))
        finally:
            server.shutdown()
            server.server_close()

    def test_http_api_delete_atomic_message(self):
        """Verify POST /api/delete-message deletes atomic messages from history."""
        from http.server import ThreadingHTTPServer
        import threading
        import requests
        import bridge_runner

        bridge_runner.BRIDGE_AUTH_TOKEN = "test-token"
        bridge_runner.BRIDGE_DIR = self.test_dir
        bridge_runner.BASE_DIR = self.test_dir

        t_dir = bridge_runner.ensure_tenant_initialized("default", base_dir=self.test_dir)
        hist_dir = t_dir / "history"
        hist_dir.mkdir(parents=True, exist_ok=True)
        hist_file = hist_dir / "history_proj_flow.json"

        # Populate with atomic message pair
        initial_history = {
            "messages": [
                {
                    "id": "tx_test_user_p",
                    "tx_id": "tx_test_user",
                    "type": "user_message",
                    "sender_id": "lead",
                    "sender_name": "Team Lead",
                    "text": "@jared what's blocking you?"
                },
                {
                    "id": "tx_test_agent_r",
                    "tx_id": "tx_test_user",
                    "type": "agent_message",
                    "sender_id": "jared",
                    "sender_name": "Jared",
                    "text": "Investigating write surfaces."
                }
            ],
            "transactions": [
                {
                    "id": "tx_test_user",
                    "prompt_text": "@jared what's blocking you?",
                    "claude_response": "Investigating write surfaces."
                }
            ]
        }
        hist_file.write_text(json.dumps(initial_history))

        server = ThreadingHTTPServer(("127.0.0.1", 0), bridge_runner.BridgeRequestHandler)
        port = server.server_address[1]
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            url = f"http://127.0.0.1:{port}/api/delete-message"
            headers = {"X-Bridge-Auth": "test-token", "Content-Type": "application/json"}

            # Delete the user message by its atomic id
            res = requests.post(url, headers=headers, json={"project_id": "proj_flow", "tx_id": "tx_test_user_p", "target_sub": "message"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["deleted_tx_id"], "tx_test_user_p")

            # Verify history file updated
            updated = json.loads(hist_file.read_text())
            msg_ids = [m["id"] for m in updated.get("messages", [])]
            self.assertNotIn("tx_test_user_p", msg_ids)
            self.assertIn("tx_test_agent_r", msg_ids)

            # Deleting again returns 404
            res2 = requests.post(url, headers=headers, json={"project_id": "proj_flow", "tx_id": "tx_test_user_p", "target_sub": "message"})
            self.assertEqual(res2.status_code, 404)
        finally:
            server.shutdown()
            server.server_close()

    def test_no_double_post_invariant(self):
        """Verify an agent cannot post consecutively without an intervening speaker."""
        mock_provider = MagicMock()
        mock_provider.invoke.return_value = {
            "success": True,
            "response": "Here is my new update."
        }

        mock_router = MagicMock()
        mock_router.manifests = {
            "vector": {
                "name": "Vector (ADK Opus)",
                "role": "Systems Specialist",
                "provider": {"type": "vertex-ai"}
            }
        }
        mock_router.resolve.return_value = {"provider": mock_provider}

        current_history = {
            "messages": [
                {
                    "id": "msg_prev",
                    "type": "agent_message",
                    "sender_id": "vector",
                    "sender_name": "Vector (ADK Opus)",
                    "text": "Previous post from Vector."
                }
            ],
            "transactions": []
        }

        appended_txs = []
        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda p: current_history,
            save_history_fn=lambda d, p: None,
            load_projects_fn=lambda: {"projects": [{"id": "proj_flow", "members": ["vector"]}]},
            build_messages_fn=lambda *args, **kw: ([], "System Prompt"),
            build_self_context_fn=lambda *args, **kw: "Self Context",
            append_transaction_fn=lambda p, tx: appended_txs.append(tx)
        )

        try:
            # 1. Attempt dispatch for Vector when Vector was the last speaker
            task_dup = {
                "id": "task_dup_vector",
                "target_agent_id": "vector",
                "sender_id": "system_pulse",
                "sender_name": "Ambient Pulse",
                "sender_role": "Collaboration Supervisor",
                "project_id": "proj_flow",
                "prompt": "Ambient check-in",
                "cascade_depth": 0
            }
            res = dispatcher.process_task(task_dup)
            self.assertEqual(res["status"], "skipped")
            self.assertEqual(res["reason"], "no_double_post")
            self.assertEqual(mock_provider.invoke.call_count, 0)
            self.assertEqual(len(appended_txs), 0)

            # 2. Intervening message arrives from user / Team Lead
            current_history["messages"].append({
                "id": "msg_user",
                "type": "user_message",
                "sender_id": "lead",
                "sender_name": "Team Lead",
                "text": "@vector please verify the logs."
            })

            # 3. Now Vector is allowed to post
            task_allowed = {
                "id": "task_allowed_vector",
                "target_agent_id": "vector",
                "sender_id": "lead",
                "sender_name": "Team Lead",
                "sender_role": "Team Lead",
                "project_id": "proj_flow",
                "prompt": "please verify the logs.",
                "cascade_depth": 0
            }
            res_allowed = dispatcher.process_task(task_allowed)
            self.assertEqual(res_allowed["status"], "completed")
            self.assertEqual(mock_provider.invoke.call_count, 1)
            self.assertEqual(len(appended_txs), 1)
        finally:
            dispatcher.stop()

    def test_fair_rotation_candidate_selection(self):
        """Verify candidate selection round-robins across eligible members based on recency."""
        mock_router = MagicMock()
        mock_router.manifests = {
            "vector": {"name": "Vector (ADK Opus)", "role": "Systems", "provider": {"type": "vertex-ai"}},
            "jared": {"name": "Jared (ADK Opus)", "role": "Simulation", "provider": {"type": "vertex-ai"}},
            "irisadkgemini": {"name": "Iris (ADK Gemini)", "role": "Research", "provider": {"type": "google-adk"}}
        }

        history_store = {"messages": [], "transactions": []}
        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda p: history_store,
            save_history_fn=lambda d, p: None,
            load_projects_fn=lambda: {"projects": [{"id": "proj_flow", "members": ["vector", "jared", "irisadkgemini"]}]},
            build_messages_fn=lambda *args, **kw: ([], ""),
            build_self_context_fn=lambda *args, **kw: "",
            append_transaction_fn=lambda p, tx: None
        )

        try:
            eligible = ["vector", "jared", "irisadkgemini"]

            # Scenario 1: Jared spoke, then Vector spoke
            history_store["messages"] = [
                {"id": "1", "type": "agent_message", "sender_id": "jared", "sender_name": "Jared (ADK Opus)", "text": "Jared update"},
                {"id": "2", "type": "agent_message", "sender_id": "vector", "sender_name": "Vector (ADK Opus)", "text": "Vector update"}
            ]

            # Vector just spoke -> open floor excludes Vector -> Iris has never spoken, so Iris must be chosen over Jared
            cand1 = dispatcher._select_candidate_agent("proj_flow", eligible, exclude_ids=["vector"])
            self.assertEqual(cand1, "irisadkgemini")

            # Scenario 2: Iris speaks next
            history_store["messages"].append(
                {"id": "3", "type": "agent_message", "sender_id": "irisadkgemini", "sender_name": "Iris (ADK Gemini)", "text": "Iris update"}
            )
            # Iris just spoke -> Iris excluded -> between Jared (spoke at #1) and Vector (spoke at #2), Jared spoke least recently
            cand2 = dispatcher._select_candidate_agent("proj_flow", eligible, exclude_ids=["irisadkgemini"])
            self.assertEqual(cand2, "jared")

            # Scenario 3: Jared speaks next
            history_store["messages"].append(
                {"id": "4", "type": "agent_message", "sender_id": "jared", "sender_name": "Jared (ADK Opus)", "text": "Jared next"}
            )
            # Jared excluded -> between Vector (spoke at #2) and Iris (spoke at #3), Vector spoke least recently
            cand3 = dispatcher._select_candidate_agent("proj_flow", eligible, exclude_ids=["jared"])
            self.assertEqual(cand3, "vector")
        finally:
            dispatcher.stop()


if __name__ == "__main__":
    unittest.main()
