#!/usr/bin/env python3
"""
Unit test suite verifying Phase 2: Local <-> Cloud Relay Endpoints & bridge_relay.py.
Tests:
- Atomic lease acquisition (lease_pending_task)
- Lease renewal with TTL heartbeat (renew_pending_lease)
- Lease release back to queue (release_pending_lease)
- Lease expiration and re-leasing by new workers
- Task resolution with CAS history updates (resolve_pending_task)
- Conflict detection on active lease mismatches
- Mention-triggered A2A dispatcher handoff upon resolution
- End-to-end HTTP client interactions via BridgeRelayClient
"""

import os
import json
import time
import shutil
import tempfile
import unittest
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch
from http.server import ThreadingHTTPServer

import bridge_runner
from core.tenant import ensure_tenant_initialized, get_storage_adapter, tenant_manager
from bridge_relay import BridgeRelayClient


class TestBridgeRelayEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.tenant_id = "test_relay_tenant"
        self.t_dir = ensure_tenant_initialized(self.tenant_id, base_dir=self.test_dir)
        self.adapter = get_storage_adapter(base_dir=self.test_dir)
        bridge_runner.BRIDGE_DIR = self.test_dir
        bridge_runner.BASE_DIR = self.test_dir

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_pending_task(self, tx_id: str, prompt: str = "Test prompt", project_id: str = "lantern") -> dict:
        task = {
            "id": tx_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "sender": "Lead Operator",
            "sender_role": "Operator",
            "recipient": "Astra",
            "recipient_role": "Bridge Deck Lead",
            "prompt": prompt,
            "allow_subagents": False,
            "directories": [str(self.t_dir)],
            "status": "waiting",
            "project_id": project_id,
            "lease_id": None,
            "lease_expires_at": None,
            "leased_by": None
        }
        def _add(doc):
            doc.setdefault("pending", {})[tx_id] = task
            return doc
        bridge_runner.update_pending(_add, bridge_dir=self.t_dir)
        return task

    def _seed_history_tx(self, tx_id: str, prompt: str = "Test prompt", project_id: str = "lantern"):
        tx = {
            "id": tx_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "mode": "antigravity_direct",
            "sender": "Lead Operator",
            "sender_role": "Operator",
            "recipient": "Astra",
            "recipient_role": "Bridge Deck Lead",
            "prompt_text": prompt,
            "antigravity_response": "⏳ (Relayed to Astra in the Antigravity Engine — awaiting response...)",
            "claude_response": None,
            "is_pending": True,
            "raw_request_json": {},
            "raw_response_json": {"status_code": 200}
        }
        def _add_hist(doc):
            doc.setdefault("transactions", []).append(tx)
            return doc
        self.adapter.update_json(self.tenant_id, f"history/history_{project_id}.json", _add_hist, default={"transactions": []})

    def test_lease_pending_task_basic(self):
        """Verify atomic task leasing assigns lease_id, TTL, and leased_by."""
        self._seed_pending_task("tx_001", prompt="Analyze system logs")
        leased = bridge_runner.lease_pending_task(worker_id="worker-a", lease_seconds=60, bridge_dir=self.t_dir)

        self.assertIsNotNone(leased)
        self.assertEqual(leased["id"], "tx_001")
        self.assertEqual(leased["status"], "leased")
        self.assertEqual(leased["leased_by"], "worker-a")
        self.assertTrue(leased["lease_id"].startswith("lease_"))
        self.assertGreater(leased["lease_expires_at"], time.time())

        # Second attempt immediately after should return None since task is already leased
        second_lease = bridge_runner.lease_pending_task(worker_id="worker-b", lease_seconds=60, bridge_dir=self.t_dir)
        self.assertIsNone(second_lease)

    def test_lease_pending_task_empty_queue(self):
        """Verify leasing from empty queue returns None without error."""
        leased = bridge_runner.lease_pending_task(worker_id="worker-a", bridge_dir=self.t_dir)
        self.assertIsNone(leased)

    def test_lease_pending_task_re_leases_expired_lease(self):
        """Verify that an expired lease can be re-leased by a new worker."""
        self._seed_pending_task("tx_002", prompt="Long running task")

        # Force an expired lease
        def _expire(doc):
            t = doc["pending"]["tx_002"]
            t["status"] = "leased"
            t["lease_id"] = "lease_old"
            t["lease_expires_at"] = time.time() - 10.0  # 10s in the past
            t["leased_by"] = "crashed-worker"
            return doc
        bridge_runner.update_pending(_expire, bridge_dir=self.t_dir)

        # New worker attempts to lease: should successfully pick up the expired task
        new_lease = bridge_runner.lease_pending_task(worker_id="active-worker", lease_seconds=120, bridge_dir=self.t_dir)
        self.assertIsNotNone(new_lease)
        self.assertEqual(new_lease["id"], "tx_002")
        self.assertEqual(new_lease["leased_by"], "active-worker")
        self.assertNotEqual(new_lease["lease_id"], "lease_old")

    def test_renew_pending_lease(self):
        """Verify renewing an active lease extends lease_expires_at."""
        self._seed_pending_task("tx_003")
        leased = bridge_runner.lease_pending_task(worker_id="worker-a", lease_seconds=30, bridge_dir=self.t_dir)
        old_expiry = leased["lease_expires_at"]
        lease_id = leased["lease_id"]

        time.sleep(0.05)
        ok, renewed, err = bridge_runner.renew_pending_lease("tx_003", lease_id=lease_id, lease_seconds=100, bridge_dir=self.t_dir)
        self.assertTrue(ok)
        self.assertGreater(renewed["lease_expires_at"], old_expiry)

        # Mismatched lease_id fails renewal
        bad_ok, bad_renewed, bad_err = bridge_runner.renew_pending_lease("tx_003", lease_id="lease_wrong", lease_seconds=100, bridge_dir=self.t_dir)
        self.assertFalse(bad_ok)
        self.assertIn("mismatch", bad_err)

    def test_release_pending_lease(self):
        """Verify releasing a lease resets status to 'waiting' and clears lease fields."""
        self._seed_pending_task("tx_004")
        leased = bridge_runner.lease_pending_task(worker_id="worker-a", lease_seconds=60, bridge_dir=self.t_dir)
        lease_id = leased["lease_id"]

        ok, err = bridge_runner.release_pending_lease("tx_004", lease_id=lease_id, bridge_dir=self.t_dir)
        self.assertTrue(ok)

        # Verify task is back to waiting in pending queue
        pending_doc = bridge_runner.load_pending(bridge_dir=self.t_dir)
        task = pending_doc["pending"]["tx_004"]
        self.assertEqual(task["status"], "waiting")
        self.assertIsNone(task["lease_id"])
        self.assertIsNone(task["leased_by"])

    def test_resolve_pending_task(self):
        """Verify resolve_pending_task removes task from queue and updates history via CAS."""
        tx_id = "tx_005"
        self._seed_pending_task(tx_id, prompt="Please calculate pi", project_id="lantern")
        self._seed_history_tx(tx_id, prompt="Please calculate pi", project_id="lantern")

        leased = bridge_runner.lease_pending_task(worker_id="worker-a", lease_seconds=60, bridge_dir=self.t_dir)
        lease_id = leased["lease_id"]

        response_text = "Pi is approximately 3.14159265."
        ok, res, err = bridge_runner.resolve_pending_task(
            tx_id=tx_id,
            response_text=response_text,
            lease_id=lease_id,
            project_id="lantern",
            bridge_dir=self.t_dir
        )

        self.assertTrue(ok, f"Resolve failed: {err}")
        self.assertEqual(res["status"], "resolved")
        self.assertEqual(res["tx_id"], tx_id)

        # Task must be pruned from pending_queries.json
        pending_doc = bridge_runner.load_pending(bridge_dir=self.t_dir)
        self.assertNotIn(tx_id, pending_doc["pending"])

        # History must be updated with response
        history = self.adapter.read_json(self.tenant_id, "history/history_lantern.json")
        matching_tx = next(t for t in history["transactions"] if t["id"] == tx_id)
        self.assertEqual(matching_tx["antigravity_response"], response_text)
        self.assertFalse(matching_tx["is_pending"])
        self.assertEqual(matching_tx["raw_response_json"]["status_code"], 200)

    def test_resolve_lease_conflict(self):
        """Verify resolving with an invalid lease_id returns a conflict error."""
        tx_id = "tx_006"
        self._seed_pending_task(tx_id)
        self._seed_history_tx(tx_id)

        leased = bridge_runner.lease_pending_task(worker_id="worker-a", lease_seconds=60, bridge_dir=self.t_dir)

        # Attempt resolve with different lease_id
        ok, res, err = bridge_runner.resolve_pending_task(
            tx_id=tx_id,
            response_text="Unauthorized reply",
            lease_id="lease_impostor",
            bridge_dir=self.t_dir
        )
        self.assertFalse(ok)
        self.assertIn("conflict", err.lower())

    def test_resolve_triggers_a2a_dispatcher(self):
        """Verify that resolve_pending_task triggers A2A dispatcher if response contains @mentions."""
        tx_id = "tx_007"
        self._seed_pending_task(tx_id, project_id="lantern")
        self._seed_history_tx(tx_id, project_id="lantern")

        mock_dispatcher = MagicMock()
        with patch("core.tenant.TenantRegistry.get_dispatcher", return_value=mock_dispatcher):
            response_text = "Good findings! @lumen could you please verify this calculation?"
            ok, res, err = bridge_runner.resolve_pending_task(
                tx_id=tx_id,
                response_text=response_text,
                project_id="lantern",
                bridge_dir=self.t_dir
            )
            self.assertTrue(ok)
            mock_dispatcher.enqueue_if_mentions.assert_called_once()
            call_kwargs = mock_dispatcher.enqueue_if_mentions.call_args.kwargs
            self.assertEqual(call_kwargs["text"], response_text)
            self.assertEqual(call_kwargs["project_id"], "lantern")

    def test_bridge_relay_client_http_lifecycle(self):
        """End-to-end integration test of BridgeRelayClient against a local HTTP server."""
        # Set up a test HTTP server on an ephemeral port
        server = ThreadingHTTPServer(("127.0.0.1", 0), bridge_runner.BridgeRequestHandler)
        port = server.server_address[1]
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            # Seed test data
            tx_id = "tx_http_001"
            self._seed_pending_task(tx_id, prompt="Compute checksum of dataset", project_id="lantern")
            self._seed_history_tx(tx_id, prompt="Compute checksum of dataset", project_id="lantern")

            client = BridgeRelayClient(
                server_url=f"http://127.0.0.1:{port}",
                auth_token="test-token",
                tenant_id=self.tenant_id
            )

            # 1. List pending
            listing = client.list_pending()
            self.assertTrue(listing.get("success"))
            self.assertGreaterEqual(listing.get("count", 0), 1)

            # 2. Lease task
            leased = client.lease_task(worker_id="test-http-worker", lease_seconds=60)
            self.assertIsNotNone(leased)
            self.assertEqual(leased["id"], tx_id)
            lease_id = leased["lease_id"]

            # 3. Renew lease
            renewed = client.renew_lease(tx_id, lease_id=lease_id, lease_seconds=120)
            self.assertIsNotNone(renewed)
            self.assertEqual(renewed["id"], tx_id)

            # 4. Resolve task
            res = client.resolve_task(
                tx_id=tx_id,
                response_text="Checksum is a1b2c3d4e5",
                lease_id=lease_id,
                project_id="lantern"
            )
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("status"), "resolved")

            # 5. List pending again: should be empty
            listing_after = client.list_pending(status="waiting")
            waiting_ids = [t["id"] for t in listing_after.get("tasks", [])]
            self.assertNotIn(tx_id, waiting_ids)

        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
