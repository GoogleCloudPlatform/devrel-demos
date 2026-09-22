#!/usr/bin/env python3
"""
Unit test suite verifying runtime sync endpoints:
- POST /api/adk/sync
- POST /api/antigravity/sync
- POST /api/vertex/sync
"""

import os
import json
import shutil
import tempfile
import unittest
import threading
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

import bridge_runner
from core.tenant import ensure_tenant_initialized, get_storage_adapter, tenant_manager


class TestSyncEndpoints(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.orig_data_dir = os.environ.get("BRIDGE_DATA_DIR")
        os.environ["BRIDGE_DATA_DIR"] = str(self.test_dir / "data")

        self.tenant_id = "test_sync_tenant"
        self.t_dir = ensure_tenant_initialized(self.tenant_id, base_dir=self.test_dir)
        self.adapter = get_storage_adapter(base_dir=self.test_dir)
        self.orig_bridge_dir = bridge_runner.BRIDGE_DIR
        self.orig_base_dir = bridge_runner.BASE_DIR
        bridge_runner.BRIDGE_DIR = self.test_dir
        bridge_runner.BASE_DIR = self.test_dir

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), bridge_runner.BridgeRequestHandler)
        self.port = self.server.server_address[1]
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        bridge_runner.BRIDGE_DIR = self.orig_bridge_dir
        bridge_runner.BASE_DIR = self.orig_base_dir
        if self.orig_data_dir is not None:
            os.environ["BRIDGE_DATA_DIR"] = self.orig_data_dir
        else:
            os.environ.pop("BRIDGE_DATA_DIR", None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _post_json(self, path, payload):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Bridge-Tenant": self.tenant_id
            }
        )
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    def test_adk_sync_endpoint(self):
        """Verifies that /api/adk/sync successfully discovers and synchronizes ADK agents without variable scoping errors."""
        status, res = self._post_json("/api/adk/sync", {
            "location": "us-central1",
            "auto_sync_specialists": True
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertGreater(res.get("synced_count", 0), 0)
        self.assertIn("agents", res)

        # Verify agents were written to the tenant's agents directory
        agents_dir = self.t_dir / "agents"
        agent_files = list(agents_dir.glob("*.agent.json"))
        self.assertGreaterEqual(len(agent_files), 1)

    def test_antigravity_sync_endpoint(self):
        """Verifies that /api/antigravity/sync successfully syncs models."""
        status, res = self._post_json("/api/antigravity/sync", {
            "models": [
                {"id": "ag-test-model", "name": "Antigravity Test Model"}
            ]
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("synced_count"), 1)

    def test_vertex_sync_endpoint(self):
        """Verifies that /api/vertex/sync successfully syncs Vertex frontier models."""
        status, res = self._post_json("/api/vertex/sync", {
            "models": [
                {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash", "category": "Frontier"}
            ]
        })
        self.assertEqual(status, 200)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("synced_count"), 1)


if __name__ == "__main__":
    unittest.main()
