#!/usr/bin/env python3
"""
Unit and integration tests for Phase 4: Durable Distributed A2A Queue.
Verifies InMemoryQueueBackend, CloudTasksQueueBackend, HTTP delivery endpoints (/api/a2a/task),
and storage conflict retry signaling (409 Conflict).
"""

import os
import sys
import json
import base64
import time
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.a2a_dispatcher import (
    A2ADispatcher,
    InMemoryQueueBackend,
    CloudTasksQueueBackend
)
from core.tenant import StorageConflictError


class TestA2ADurableQueue(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_a2a_queue_"))

    def tearDown(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_in_memory_queue_backend_lifecycle(self):
        processed = []

        def worker_fn(task):
            processed.append(task["id"])

        backend = InMemoryQueueBackend(process_task_fn=worker_fn)
        self.assertFalse(backend.is_durable)
        self.assertEqual(backend.qsize, 0)

        # Enqueue tasks
        backend.enqueue({"id": "task_1"}, tenant_id="t1")
        backend.enqueue({"id": "task_2"}, tenant_id="t1")

        # Wait briefly for worker thread to process
        timeout = time.time() + 2.0
        while len(processed) < 2 and time.time() < timeout:
            time.sleep(0.02)

        self.assertEqual(processed, ["task_1", "task_2"])
        backend.stop()

    def test_cloud_tasks_queue_backend_payload_construction(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_session.post.return_value = mock_response

        backend = CloudTasksQueueBackend(
            project_id="my-gcp-project",
            location="us-central1",
            queue_name="a2a-tasks",
            service_url="https://bridge-deck-xyz.run.app",
            service_account_email="bridge-sa@my-gcp-project.iam.gserviceaccount.com",
            bridge_auth_token="secret-token-123",
            session=mock_session
        )
        self.assertTrue(backend.is_durable)
        self.assertIsNone(backend.qsize)
        self.assertIsNone(backend.clear())

        test_task = {
            "id": "a2a_12345_vector",
            "target_agent_id": "vector",
            "sender_id": "astra",
            "sender_name": "Astra",
            "sender_role": "Lead",
            "project_id": "lantern",
            "prompt": "@vector review the code",
            "cascade_depth": 1,
            "original_root_tx": "tx_root"
        }

        success = backend.enqueue(test_task, tenant_id="corp_alpha")
        self.assertTrue(success)

        # Verify API URL
        expected_api_url = "https://cloudtasks.googleapis.com/v2/projects/my-gcp-project/locations/us-central1/queues/a2a-tasks/tasks"
        mock_session.post.assert_called_once()
        args, kwargs = mock_session.post.call_args
        self.assertEqual(args[0], expected_api_url)

        # Verify httpRequest structure
        self.assertEqual(kwargs["json"]["task"]["dispatchDeadline"], "1800s")
        task_body = kwargs["json"]["task"]["httpRequest"]
        self.assertEqual(task_body["httpMethod"], "POST")
        self.assertEqual(task_body["url"], "https://bridge-deck-xyz.run.app/api/a2a/task")
        self.assertEqual(task_body["headers"]["Content-Type"], "application/json")
        self.assertEqual(task_body["headers"]["X-Bridge-Auth"], "secret-token-123")

        # Verify OIDC token config
        self.assertEqual(
            task_body["oidcToken"]["serviceAccountEmail"],
            "bridge-sa@my-gcp-project.iam.gserviceaccount.com"
        )
        self.assertEqual(task_body["oidcToken"]["audience"], "https://bridge-deck-xyz.run.app")

        # Verify body payload decoding
        raw_b64 = task_body["body"]
        decoded_json = json.loads(base64.b64decode(raw_b64.encode("utf-8")).decode("utf-8"))
        self.assertEqual(decoded_json["tenant_id"], "corp_alpha")
        self.assertEqual(decoded_json["task"]["id"], "a2a_12345_vector")
        self.assertEqual(decoded_json["task"]["prompt"], "@vector review the code")

    def test_cloud_tasks_queue_backend_error_handling(self):
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "PermissionDenied: Cloud Tasks enqueuer role missing"
        mock_session.post.return_value = mock_response

        backend = CloudTasksQueueBackend(
            project_id="test-proj",
            location="us-central1",
            queue_name="a2a-tasks",
            service_url="https://example.run.app",
            bridge_auth_token="test-token",
            session=mock_session
        )

        with self.assertRaises(RuntimeError) as ctx:
            backend.enqueue({"id": "task_fail"}, tenant_id="t1")
        self.assertIn("Cloud Tasks API returned HTTP 403", str(ctx.exception))

    def test_cloud_tasks_queue_backend_session_caching(self):
        from unittest.mock import patch
        backend = CloudTasksQueueBackend(
            project_id="test-proj",
            location="us-central1",
            queue_name="a2a-tasks",
            service_url="https://example.run.app",
            bridge_auth_token="test-token"
        )
        self.assertIsNone(backend._session)

        mock_creds = MagicMock()
        mock_creds.token = "mock-token-xyz"

        with patch("google.auth.default", return_value=(mock_creds, "test-proj")), \
             patch("google.auth.transport.requests.Request", return_value=MagicMock()):
            s1 = backend._get_session()
            self.assertIsNotNone(s1)
            self.assertIs(backend._session, s1)
            self.assertEqual(s1.headers.get("Authorization"), "Bearer mock-token-xyz")
            self.assertEqual(mock_creds.refresh.call_count, 1)

            # Second call should return cached session without refreshing credentials again
            s2 = backend._get_session()
            self.assertIs(s2, s1)
            self.assertEqual(mock_creds.refresh.call_count, 1)

    def test_dispatcher_environment_auto_detection(self):
        old_env = dict(os.environ)
        try:
            os.environ["A2A_QUEUE_BACKEND"] = "cloud_tasks"
            os.environ["CLOUD_TASKS_PROJECT"] = "env-proj"
            os.environ["CLOUD_TASKS_QUEUE"] = "env-queue"
            os.environ["CLOUD_TASKS_SERVICE_URL"] = "https://auto-detected.run.app"
            os.environ["BRIDGE_AUTH_TOKEN"] = "env-token"

            mock_router = MagicMock()
            mock_router.manifests = {}
            dispatcher = A2ADispatcher(
                bridge_dir=self.test_dir,
                agent_router=mock_router,
                load_history_fn=lambda p: {"transactions": []},
                save_history_fn=lambda d, p: None,
                load_projects_fn=lambda: {"projects": []},
                build_messages_fn=lambda *args, **kw: ([], ""),
                build_self_context_fn=lambda *args, **kw: "",
                append_transaction_fn=lambda p, tx: None
            )

            self.assertTrue(isinstance(dispatcher.queue_backend, CloudTasksQueueBackend))
            self.assertTrue(dispatcher.queue_backend.is_durable)
            status = dispatcher.get_status()
            self.assertTrue(status["durable"])
            dispatcher.stop()
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_dispatcher_process_task_synchronous_execution(self):
        mock_router = MagicMock()
        mock_provider = MagicMock()
        mock_provider.invoke.return_value = {
            "success": True,
            "response": "Here is the response from vector.",
            "thinking_blocks": []
        }
        mock_router.manifests = {
            "vector": {
                "name": "Vector",
                "role": "Implementation Lead",
                "provider": {"type": "anthropic", "model": "claude-3-5-sonnet"}
            }
        }
        mock_router.resolve.return_value = {"provider": mock_provider}

        saved_txs = []

        def mock_append(pid, tx):
            saved_txs.append(tx)

        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda p: {"transactions": []},
            save_history_fn=lambda d, p, **kw: None,
            load_projects_fn=lambda: {"projects": [{"id": "lantern", "allow_subagents": True}]},
            build_messages_fn=lambda *args, **kw: ([], "system"),
            build_self_context_fn=lambda *args, **kw: "self",
            append_transaction_fn=mock_append
        )

        task = {
            "id": "a2a_sync_1",
            "target_agent_id": "vector",
            "sender_id": "astra",
            "sender_name": "Astra",
            "sender_role": "Lead",
            "project_id": "lantern",
            "prompt": "@vector review this task",
            "cascade_depth": 0,
            "original_root_tx": "tx_root_sync"
        }

        result = dispatcher.process_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["task_id"], "a2a_sync_1")
        self.assertEqual(len(saved_txs), 1)
        self.assertEqual(saved_txs[0]["recipient"], "Vector")
        self.assertEqual(saved_txs[0]["claude_response"], "Here is the response from vector.")
        dispatcher.stop()

    def test_dispatcher_process_task_honors_pause(self):
        mock_router = MagicMock()
        mock_router.manifests = {}
        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda p: {"transactions": []},
            save_history_fn=lambda d, p: None,
            load_projects_fn=lambda: {"projects": []},
            build_messages_fn=lambda *args, **kw: ([], ""),
            build_self_context_fn=lambda *args, **kw: "",
            append_transaction_fn=lambda p, tx: None
        )
        dispatcher.pause("paused_project")

        task = {
            "id": "a2a_paused_1",
            "target_agent_id": "vector",
            "sender_id": "astra",
            "sender_name": "Astra",
            "sender_role": "Lead",
            "project_id": "paused_project",
            "prompt": "@vector run",
            "cascade_depth": 0
        }

        result = dispatcher.process_task(task)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "paused")
        dispatcher.stop()

    def test_http_endpoint_a2a_task_execution(self):
        """Verify POST /api/a2a/task executes task and returns 200 OK."""
        from http.server import ThreadingHTTPServer
        import threading
        import requests
        import bridge_runner
        from unittest.mock import patch

        bridge_runner.BRIDGE_AUTH_TOKEN = "test-token"
        bridge_runner.BRIDGE_DIR = self.test_dir
        bridge_runner.BASE_DIR = self.test_dir

        server = ThreadingHTTPServer(("127.0.0.1", 0), bridge_runner.BridgeRequestHandler)
        port = server.server_address[1]
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            mock_dispatcher = MagicMock()
            mock_dispatcher.process_task.return_value = {
                "status": "completed",
                "task_id": "task_http_123",
                "target": "Vector",
                "elapsed": 0.42
            }

            with patch("core.tenant.TenantRegistry.get_dispatcher", return_value=mock_dispatcher):
                url = f"http://127.0.0.1:{port}/api/a2a/task"
                headers = {"X-Bridge-Auth": "test-token", "Content-Type": "application/json"}
                payload = {
                    "tenant_id": "test_tenant",
                    "task": {
                        "id": "task_http_123",
                        "target_agent_id": "vector",
                        "sender_id": "astra",
                        "sender_name": "Astra",
                        "sender_role": "Lead",
                        "project_id": "lantern",
                        "prompt": "@vector check",
                        "cascade_depth": 0
                    }
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=5)
                self.assertEqual(resp.status_code, 200)
                data = resp.json()
                self.assertTrue(data["success"])
                self.assertEqual(data["task_id"], "task_http_123")
                self.assertEqual(data["status"], "completed")
                mock_dispatcher.process_task.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()

    def test_http_endpoint_a2a_task_conflict_returns_409(self):
        """Verify POST /api/a2a/task returns 409 Conflict with retryable=True on StorageConflictError."""
        from http.server import ThreadingHTTPServer
        import threading
        import requests
        import bridge_runner
        from unittest.mock import patch

        bridge_runner.BRIDGE_AUTH_TOKEN = "test-token"
        bridge_runner.BRIDGE_DIR = self.test_dir
        bridge_runner.BASE_DIR = self.test_dir

        server = ThreadingHTTPServer(("127.0.0.1", 0), bridge_runner.BridgeRequestHandler)
        port = server.server_address[1]
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            mock_dispatcher = MagicMock()
            mock_dispatcher.process_task.side_effect = StorageConflictError("Generation precondition failed")

            with patch("core.tenant.TenantRegistry.get_dispatcher", return_value=mock_dispatcher):
                url = f"http://127.0.0.1:{port}/api/a2a/task"
                headers = {"X-Bridge-Auth": "test-token", "Content-Type": "application/json"}
                payload = {
                    "tenant_id": "test_tenant",
                    "task": {
                        "id": "task_conflict_123",
                        "target_agent_id": "vector"
                    }
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=5)
                self.assertEqual(resp.status_code, 409)
                data = resp.json()
                self.assertFalse(data["success"])
                self.assertTrue(data["retryable"])
                self.assertIn("Generation precondition failed", data["error"])
        finally:
            server.shutdown()
            server.server_close()

    def test_http_endpoint_a2a_task_malformed_returns_400(self):
        """Verify POST /api/a2a/task returns 400 on malformed or empty task."""
        from http.server import ThreadingHTTPServer
        import threading
        import requests
        import bridge_runner

        bridge_runner.BRIDGE_AUTH_TOKEN = "test-token"
        bridge_runner.BRIDGE_DIR = self.test_dir
        bridge_runner.BASE_DIR = self.test_dir

        server = ThreadingHTTPServer(("127.0.0.1", 0), bridge_runner.BridgeRequestHandler)
        port = server.server_address[1]
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            url = f"http://127.0.0.1:{port}/api/a2a/task"
            headers = {"X-Bridge-Auth": "test-token", "Content-Type": "application/json"}
            # Send payload missing task ID
            resp = requests.post(url, headers=headers, json={"tenant_id": "t1"}, timeout=5)
            self.assertEqual(resp.status_code, 400)
            data = resp.json()
            self.assertFalse(data["success"])
            self.assertIn("Missing or invalid", data["error"])
        finally:
            server.shutdown()
            server.server_close()

    def test_cloud_tasks_queue_backend_fail_fast_validation(self):
        # Assert non-empty project_id, service_url, and bridge_auth_token
        with self.assertRaises(ValueError):
            CloudTasksQueueBackend(project_id="", location="us-central1", queue_name="q", service_url="https://example.run.app", bridge_auth_token="tok")
        with self.assertRaises(ValueError):
            CloudTasksQueueBackend(project_id="my-proj", location="us-central1", queue_name="q", service_url="", bridge_auth_token="tok")
        with self.assertRaises(ValueError):
            CloudTasksQueueBackend(project_id="my-proj", location="us-central1", queue_name="q", service_url="https://example.run.app", bridge_auth_token="")

    def test_process_task_depth_limit_returns_explicit_dict(self):
        mock_router = MagicMock()
        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda pid: {"transactions": []},
            save_history_fn=lambda d, **kw: None,
            load_projects_fn=lambda: {"projects": []},
            build_messages_fn=lambda **kw: ([], "sys"),
            build_self_context_fn=lambda *a, **kw: "",
            append_transaction_fn=lambda pid, tx: None,
            max_depth=2,
            queue_backend=InMemoryQueueBackend(process_task_fn=lambda t: None)
        )
        task = {
            "id": "a2a_over_depth",
            "target_agent_id": "test_agent",
            "sender_name": "tester",
            "sender_role": "lead",
            "prompt": "hello",
            "project_id": "lantern",
            "cascade_depth": 2,
        }
        res = dispatcher.process_task(task)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("status"), "depth_limited")
        self.assertEqual(res.get("task_id"), "a2a_over_depth")

    def test_process_task_midflight_pause_returns_explicit_dict(self):
        mock_router = MagicMock()
        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda pid: {"transactions": []},
            save_history_fn=lambda d, **kw: None,
            load_projects_fn=lambda: {"projects": []},
            build_messages_fn=lambda **kw: ([], "sys"),
            build_self_context_fn=lambda *a, **kw: "",
            append_transaction_fn=lambda pid, tx: None,
            max_depth=5,
            queue_backend=InMemoryQueueBackend(process_task_fn=lambda t: None)
        )
        # Mock provider that pauses the project during invoke
        mock_provider = MagicMock()
        def mock_invoke(**kw):
            dispatcher.pause("lantern")
            return {"success": True, "response": "done"}
        mock_provider.invoke.side_effect = mock_invoke

        mock_router.manifests = {"agent_paused": {"name": "Agent Paused", "role": "tester"}}
        mock_router.resolve.return_value = {"provider": mock_provider}

        task = {
            "id": "a2a_pause_midflight",
            "target_agent_id": "agent_paused",
            "sender_name": "tester",
            "sender_role": "lead",
            "prompt": "hello",
            "project_id": "lantern",
            "cascade_depth": 0,
        }
        res = dispatcher.process_task(task)
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get("status"), "aborted_paused")

    def test_enqueue_if_mentions_rollback_on_failure(self):
        failing_backend = MagicMock()
        failing_backend.enqueue.side_effect = RuntimeError("Cloud Tasks API 503")

        mock_router = MagicMock()
        mock_router.manifests = {"target_agent": {}}
        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda pid: {"transactions": []},
            save_history_fn=lambda d, **kw: None,
            load_projects_fn=lambda: {"projects": []},
            build_messages_fn=lambda **kw: ([], "sys"),
            build_self_context_fn=lambda *a, **kw: "",
            append_transaction_fn=lambda pid, tx: None,
            queue_backend=failing_backend
        )

        enqueued = dispatcher.enqueue_if_mentions(
            text="@target_agent please review",
            sender_id="sender_1",
            sender_name="Sender",
            sender_role="Lead",
            project_id="lantern",
            original_root_tx="tx_root_fail"
        )
        # Verify target was not marked as enqueued
        self.assertEqual(enqueued, [])
        # Verify dedup cache was NOT committed
        task_key = ("tx_root_fail", "target_agent", 0, hashlib.sha256("@target_agent please review".encode("utf-8")).hexdigest()[:8])
        self.assertNotIn(task_key, dispatcher._seen_tasks)
        self.assertEqual(len(dispatcher._seen_tasks), 0)

    def test_a2a_sibling_mention_dedup_distinct_readsets(self):
        """
        Verify A2A-1 fix: Distinct sibling messages mentioning the same target agent
        at the same cascade depth are BOTH dispatched, while identical messages are deduplicated.
        """
        queue_backend = MagicMock()
        queue_backend.enqueue.return_value = True
        mock_router = MagicMock()
        mock_router.manifests = {"target_agent": {}}
        dispatcher = A2ADispatcher(
            bridge_dir=self.test_dir,
            agent_router=mock_router,
            load_history_fn=lambda pid: {"transactions": []},
            save_history_fn=lambda d, **kw: None,
            load_projects_fn=lambda: {"projects": []},
            build_messages_fn=lambda **kw: ([], "sys"),
            build_self_context_fn=lambda *a, **kw: "",
            append_transaction_fn=lambda pid, tx: None,
            queue_backend=queue_backend
        )

        # Sibling 1 from Agent A to @target_agent
        enqueued_1 = dispatcher.enqueue_if_mentions(
            text="@target_agent question from sibling A",
            sender_id="agent_a",
            sender_name="Agent A",
            sender_role="Advisor",
            project_id="lantern",
            cascade_depth=1,
            original_root_tx="tx_root_123"
        )
        self.assertEqual(enqueued_1, ["target_agent"])
        self.assertEqual(queue_backend.enqueue.call_count, 1)

        # Sibling 2 from Agent B to @target_agent (same root_tx, same depth, different text)
        enqueued_2 = dispatcher.enqueue_if_mentions(
            text="@target_agent question from sibling B",
            sender_id="agent_b",
            sender_name="Agent B",
            sender_role="Researcher",
            project_id="lantern",
            cascade_depth=1,
            original_root_tx="tx_root_123"
        )
        # In A2A-1, Sibling 2 MUST NOT be dropped!
        self.assertEqual(enqueued_2, ["target_agent"])
        self.assertEqual(queue_backend.enqueue.call_count, 2)

        # Exact duplicate of Sibling 1 MUST be deduplicated
        enqueued_dup = dispatcher.enqueue_if_mentions(
            text="@target_agent question from sibling A",
            sender_id="agent_a",
            sender_name="Agent A",
            sender_role="Advisor",
            project_id="lantern",
            cascade_depth=1,
            original_root_tx="tx_root_123"
        )
        self.assertEqual(enqueued_dup, [])
        self.assertEqual(queue_backend.enqueue.call_count, 2)


if __name__ == "__main__":
    unittest.main()
