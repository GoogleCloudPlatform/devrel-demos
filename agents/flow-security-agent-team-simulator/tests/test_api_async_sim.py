# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unit tests for Asynchronous Simulation Execution and Status Polling API.
"""

import unittest
import json
import time
import threading
from urllib.request import urlopen, Request
from http.server import ThreadingHTTPServer
from flow_cli import FlowAppState


class TestAsyncSimulationAPI(unittest.TestCase):
    def setUp(self):
        self.state = FlowAppState(seed=42)
        self.state.reset(seed=42, preseed=False)

    def test_sim_job_lifecycle_state(self):
        """Verify that FlowAppState properly transitions sim_job state."""
        self.assertEqual(self.state.sim_job["status"], "idle")

        res = self.state.run_simulation(
            days=2,
            seed=42,
            force_simulation=True,
            auto_resolve=True,
            max_workers=2,
        )

        self.assertEqual(self.state.sim_job["status"], "completed")
        self.assertGreater(self.state.sim_job["evaluated_contracts"], 0)
        self.assertIsNotNone(self.state.sim_job["result"])
        self.assertTrue(len(self.state.sim_job["recent_logs"]) > 0)


class TestAsyncSimulationHTTPServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from flow_cli import create_flow_handler
        cls.state = FlowAppState(seed=42)
        cls.state.reset(seed=42, preseed=False)
        handler_cls = create_flow_handler(cls.state)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        deadline = time.time() + 5.0
        while self.state._sim_lock.locked() and time.time() < deadline:
            time.sleep(0.05)
        self.state.reset(seed=42, preseed=False)

    def test_http_status_endpoint(self):
        url = f"{self.base_url}/api/simulation/status"
        with urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("simulation_ready"))
            self.assertIn("job_status", data)
            self.assertIn("evaluated_contracts", data)
            self.assertIn("recent_logs", data)

    def test_http_run_async_and_poll(self):
        # Trigger background run
        run_url = f"{self.base_url}/api/simulation/run"
        payload = {
            "days": 2,
            "seed": 42,
            "max_workers": 2,
            "sync": False,
            "auto_resolve": True,
            "live": False,
        }
        req = Request(run_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_data.get("status"), "started")
            self.assertEqual(res_data.get("max_workers"), 2)

        # Poll status until completed or timeout
        status_url = f"{self.base_url}/api/simulation/status"
        deadline = time.time() + 10.0
        completed = False
        while time.time() < deadline:
            with urlopen(status_url) as resp:
                s_data = json.loads(resp.read().decode("utf-8"))
                if s_data.get("job_status") == "completed":
                    completed = True
                    self.assertIsNotNone(s_data.get("result"))
                    self.assertGreater(s_data.get("evaluated_contracts", 0), 0)
                    break
            time.sleep(0.1)

        self.assertTrue(completed, "Async simulation should complete within polling window")

    def test_http_run_sync(self):
        run_url = f"{self.base_url}/api/simulation/run"
        payload = {
            "days": 7,
            "seed": 99,
            "max_workers": 2,
            "sync": True,
            "auto_resolve": True,
            "live": False,
        }
        req = Request(run_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(res_data.get("success"))
            self.assertEqual(res_data.get("days_simulated"), 7)

    def test_http_run_conflict_when_locked(self):
        # Acquire lock manually
        self.assertTrue(self.state._sim_lock.acquire(blocking=False))
        try:
            run_url = f"{self.base_url}/api/simulation/run"
            payload = {"days": 1, "sync": False}
            req = Request(run_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            import urllib.error
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urlopen(req)
            self.assertEqual(ctx.exception.code, 409)
        finally:
            self.state._sim_lock.release()

    def test_http_cancel_when_idle(self):
        cancel_url = f"{self.base_url}/api/simulation/cancel"
        req = Request(cancel_url, data=b"{}", headers={"Content-Type": "application/json"})
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("status"), "idle")

    def test_http_cancel_simulation(self):
        # Start a multi-day background run
        run_url = f"{self.base_url}/api/simulation/run"
        payload = {
            "days": 14,
            "seed": 123,
            "max_workers": 2,
            "sync": False,
            "auto_resolve": True,
            "live": False,
        }
        req = Request(run_url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)

        # Call cancel endpoint
        cancel_url = f"{self.base_url}/api/simulation/cancel"
        c_req = Request(cancel_url, data=b"{}", headers={"Content-Type": "application/json"})
        with urlopen(c_req) as c_resp:
            self.assertEqual(c_resp.status, 200)
            c_data = json.loads(c_resp.read().decode("utf-8"))
            self.assertIn(c_data.get("status"), ["cancelling", "cancelled", "idle"])

        # Poll status until cancelled
        status_url = f"{self.base_url}/api/simulation/status"
        deadline = time.time() + 10.0
        cancelled = False
        while time.time() < deadline:
            with urlopen(status_url) as resp:
                s_data = json.loads(resp.read().decode("utf-8"))
                if s_data.get("job_status") == "cancelled":
                    cancelled = True
                    self.assertIsNotNone(s_data.get("result"))
                    self.assertTrue(s_data["result"].get("cancelled"))
                    break
            time.sleep(0.1)

        self.assertTrue(cancelled, "Simulation should transition to cancelled status")


if __name__ == "__main__":
    unittest.main()

