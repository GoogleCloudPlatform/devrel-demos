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


if __name__ == "__main__":
    unittest.main()
