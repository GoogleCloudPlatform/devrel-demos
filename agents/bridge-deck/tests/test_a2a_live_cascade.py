#!/usr/bin/env python3
"""
Integration test for live A2A autonomous handoffs.
"""

import time
import json
import urllib.request
import urllib.parse
import unittest
from pathlib import Path


def is_server_reachable(url="http://localhost:8080/api/a2a/status") -> bool:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


class TestA2ALiveCascade(unittest.TestCase):
    def test_a2a_status_and_pause_resume(self):
        if not is_server_reachable():
            self.skipTest("Bridge Deck live server (port 8080) is offline; skipping live HTTP integration test.")

        # 1. Status
        req = urllib.request.Request("http://localhost:8080/api/a2a/status")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            self.assertTrue(data.get("success"))

        # 2. Pause
        pause_req = urllib.request.Request(
            "http://localhost:8080/api/a2a/pause",
            data=json.dumps({"project_id": "test_proj"}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(pause_req) as resp:
            p_data = json.loads(resp.read().decode())
            self.assertTrue(p_data.get("paused"))

        # 3. Resume
        resume_req = urllib.request.Request(
            "http://localhost:8080/api/a2a/resume",
            data=json.dumps({"project_id": "test_proj"}).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(resume_req) as resp:
            r_data = json.loads(resp.read().decode())
            self.assertFalse(r_data.get("paused"))


if __name__ == "__main__":
    unittest.main()
