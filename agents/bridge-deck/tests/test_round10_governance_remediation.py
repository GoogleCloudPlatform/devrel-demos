#!/usr/bin/env python3
"""
Unit test suite verifying all Round 10 Architectural Remediation fixes:
- Q1 Governance (access_write not derived from project membership)
- Router Dynamic Endpoint NameError safety
- Voyager & Antigravity Harness ACL path containment (is_relative_to)
- A2A Dispatcher fan-out limit & task deduplication
- Manifest & profile ACL normalization
"""

import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

from core.router import AgentRouter
from core.a2a_dispatcher import A2ADispatcher
from providers.voyager_harness import VoyagerHarnessProvider
import bridge_runner


import os

class TestRound10GovernanceRemediation(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.bridge_dir = Path(__file__).resolve().parent.parent
        self._old_gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        os.environ["GOOGLE_CLOUD_PROJECT"] = "test-governance-project"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if self._old_gcp_project is not None:
            os.environ["GOOGLE_CLOUD_PROJECT"] = self._old_gcp_project
        else:
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

    def test_sync_all_project_member_permissions_does_not_grant_write(self):
        """Verify that sync_all_project_member_permissions never mutates or auto-grants access_write for any agent."""
        mock_profiles = {
            "profiles": [
                {"id": "agent_alpha", "access_read": ["/path/alpha"], "access_write": ["/path/custom_write"], "derived_read": []},
                {"id": "agent_beta", "access_read": ["/path/beta"], "access_write": [], "derived_read": []}
            ]
        }
        mock_projects = {
            "projects": [
                {"id": "proj_1", "directories": ["/proj/dir1"], "members": ["agent_alpha", "agent_beta"]}
            ]
        }
        mock_agents_dir = self.test_dir / "agents"
        mock_agents_dir.mkdir(parents=True, exist_ok=True)
        with unittest.mock.patch("bridge_runner.load_profiles", return_value=mock_profiles), \
             unittest.mock.patch("bridge_runner.load_projects", return_value=mock_projects), \
             unittest.mock.patch("bridge_runner.save_profiles") as mock_save:
            bridge_runner.sync_all_project_member_permissions(bridge_dir=self.test_dir)
            self.assertTrue(mock_save.called)

            p_alpha = next(p for p in mock_profiles["profiles"] if p["id"] == "agent_alpha")
            p_beta = next(p for p in mock_profiles["profiles"] if p["id"] == "agent_beta")

            self.assertEqual(p_alpha.get("access_write"), ["/path/custom_write"], "Operator access_write preserved")
            self.assertEqual(p_beta.get("access_write"), [], "Read-only agent receives no write grants")
            self.assertEqual(p_alpha.get("derived_read"), ["/proj/dir1"], "derived_read populated dynamically")

    def test_router_resolve_dynamic_endpoint_no_nameerror(self):
        """Verify that router.resolve() initializes matched_manifest for unmanifested dynamic endpoints without NameError."""
        # Create an isolated test directory with agents folder and unmanifested profile
        agents_dir = self.test_dir / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        profiles_file = self.test_dir / "profiles.json"
        
        mock_profiles = {
            "profiles": [
                {
                    "id": "synthetic_gardener",
                    "name": "Synthetic Gardener",
                    "model": "mg-endpoint-llama3-70b",
                    "endpoint_id": "projects/123/locations/us-central1/endpoints/456",
                    "access_read": [str(self.test_dir)],
                    "access_write": []
                }
            ]
        }
        with open(profiles_file, "w", encoding="utf-8") as pf:
            json.dump(mock_profiles, pf, indent=2)

        router = AgentRouter(bridge_dir=self.test_dir)
        router.reload_registry(force=True)

        res = router.resolve("synthetic_gardener_direct", "Synthetic Gardener")
        self.assertIsNotNone(res)
        self.assertEqual(res.get("agent_id"), "synthetic_gardener")
        self.assertIsNotNone(res.get("provider"))
        self.assertEqual(res.get("provider").__class__.__name__, "VertexCustomEndpointProvider")

    def test_voyager_harness_path_containment(self):
        """Verify that Voyager Harness uses strict Path.is_relative_to containment."""
        allowed_dir = self.test_dir / "workspace"
        allowed_dir.mkdir(parents=True, exist_ok=True)
        test_file = allowed_dir / "test.txt"
        test_file.write_text("hello world", encoding="utf-8")

        outside_dir = self.test_dir / "workspace_forbidden"
        outside_dir.mkdir(parents=True, exist_ok=True)
        forbidden_file = outside_dir / "secret.txt"
        forbidden_file.write_text("secret", encoding="utf-8")

        harness = VoyagerHarnessProvider(
            provider_id="lumen",
            config={
                "model": "claude-opus-5",
                "access_read": [str(allowed_dir)],
                "tools_enabled": ["read_file", "list_dir", "grep_search", "run_command"]
            }
        )

        # Allowed read
        success, content = harness._execute_tool("read_file", {"path": str(test_file)}, allowed_dirs=[str(allowed_dir)])
        self.assertTrue(success)
        self.assertEqual(content, "hello world")

        # Allowed relative read (e.g. "test.txt", "./test.txt", ".")
        success, rel_content = harness._execute_tool("read_file", {"path": "test.txt"}, allowed_dirs=[str(allowed_dir)])
        self.assertTrue(success)
        self.assertEqual(rel_content, "hello world")

        success, list_content = harness._execute_tool("list_dir", {"path": "."}, allowed_dirs=[str(allowed_dir)])
        self.assertTrue(success)
        self.assertIn("test.txt", list_content)

        # Out-of-bounds read (prefix lookalike check)
        success, msg = harness._execute_tool("read_file", {"path": str(forbidden_file)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("ACL Permission Denied", msg)

    def test_a2a_dispatcher_fanout_limit_and_dedup(self):
        """Verify that A2A Dispatcher enforces max fan-out per root_tx and deduplicates tasks."""
        mock_router = MagicMock()
        mock_router.manifests = {
            f"agent_{i}": {"name": f"Agent {i}", "role": "Worker", "provider": {"type": "vertex-ai"}}
            for i in range(30)
        }

        dispatcher = A2ADispatcher(
            bridge_dir=self.bridge_dir,
            agent_router=mock_router,
            load_history_fn=lambda *args, **kwargs: {"transactions": []},
            save_history_fn=lambda *args, **kwargs: None,
            load_projects_fn=lambda *args, **kwargs: {"projects": []},
            build_messages_fn=lambda *args, **kwargs: ([], ""),
            build_self_context_fn=lambda *args, **kwargs: "",
            max_depth=5
        )

        # Build mention text mentioning 25 agents
        mention_text = " ".join([f"@agent_{i}" for i in range(25)])
        enqueued = dispatcher.enqueue_if_mentions(
            text=mention_text,
            sender_id="operator",
            sender_name="Operator",
            sender_role="Lead",
            project_id="proj_test",
            cascade_depth=0,
            original_root_tx="tx_root_1"
        )

        # Should cap at 20
        self.assertEqual(len(enqueued), 20)

        # Re-enqueuing duplicate turns should be ignored by deduplication
        dup_enqueued = dispatcher.enqueue_if_mentions(
            text=mention_text,
            sender_id="operator",
            sender_name="Operator",
            sender_role="Lead",
            project_id="proj_test",
            cascade_depth=0,
            original_root_tx="tx_root_1"
        )
        self.assertEqual(len(dup_enqueued), 0)

    def test_harness_empty_acl_fails_closed(self):
        """Verify that an empty allowed_dirs fails closed and denies tool execution."""
        harness = VoyagerHarnessProvider(
            provider_id="lumen",
            config={
                "model": "claude-opus-5",
                "access_read": [],
                "tools_enabled": ["read_file", "list_dir", "grep_search", "run_command"]
            }
        )
        success, msg = harness._execute_tool("read_file", {"path": "test.txt"}, allowed_dirs=[])
        self.assertFalse(success)
        self.assertIn("ACL Permission Denied: no authorized directories configured", msg)

    def test_harness_run_command_hardening(self):
        """Verify that run_command rejects interpreters (python, pytest, find) and dangerous escape flags."""
        allowed_dir = self.test_dir / "workspace"
        allowed_dir.mkdir(parents=True, exist_ok=True)
        harness = VoyagerHarnessProvider(
            provider_id="lumen",
            config={
                "model": "claude-opus-5",
                "access_read": [str(allowed_dir)],
                "tools_enabled": ["read_file", "list_dir", "grep_search", "run_command"]
            }
        )

        # Python interpreter rejected
        success, msg = harness._execute_tool("run_command", {"command": "python -c 'print(1)'", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("not in allowed inspection set", msg)

        # Pytest rejected
        success, msg = harness._execute_tool("run_command", {"command": "pytest", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("not in allowed inspection set", msg)

        # Find rejected
        success, msg = harness._execute_tool("run_command", {"command": "find .", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("not in allowed inspection set", msg)

        # Directory escape flag -C rejected
        success, msg = harness._execute_tool("run_command", {"command": "git -C /tmp/workspace status", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("directory escape or code execution flag", msg)

        # Equals-form escape flag rejected
        success, msg = harness._execute_tool("run_command", {"command": "git --git-dir=/secret/.git status", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("directory escape or code execution flag", msg)

        # Git mutating subcommands rejected
        success, msg = harness._execute_tool("run_command", {"command": "git push --force", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("not in allowed inspection set", msg)

        success, msg = harness._execute_tool("run_command", {"command": "git reset --hard", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("not in allowed inspection set", msg)

        # Allowed command (git status) succeeds
        success, msg = harness._execute_tool("run_command", {"command": "git status", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertTrue(success)

    def test_harness_intersection_normalization(self):
        """Verify that intersection normalization handles trailing slashes properly."""
        harness = VoyagerHarnessProvider(
            provider_id="lumen",
            config={"model": "claude-opus-5", "access_read": ["/tmp/test_workspace"]}
        )
        harness.client.generate = MagicMock(return_value="I have inspected the project.")
        
        # Context has trailing slash
        res = harness.invoke(
            prompt="Hello",
            context={"directories": ["/tmp/test_workspace/"]}
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.get("response"), "I have inspected the project.")

    def test_derived_read_recomputed_on_project_membership_change(self):
        """Verify D17: derived_read recomputes strictly from current project memberships and prunes on departure."""
        mock_projects = {
            "projects": [
                {
                    "id": "proj_alpha",
                    "directories": ["/path/alpha"],
                    "members": ["agent_alpha"]
                },
                {
                    "id": "proj_beta",
                    "directories": ["/path/beta"],
                    "members": ["agent_alpha", "agent_beta"]
                }
            ]
        }
        mock_profiles = {
            "profiles": [
                {"id": "agent_alpha", "access_read": ["/base/alpha"], "derived_read": []},
                {"id": "agent_beta", "access_read": ["/base/beta"], "derived_read": []}
            ]
        }

        with unittest.mock.patch("bridge_runner.load_projects", return_value=mock_projects), \
             unittest.mock.patch("bridge_runner.load_profiles", return_value=mock_profiles), \
             unittest.mock.patch("bridge_runner.save_profiles") as mock_save:
            bridge_runner.sync_all_project_member_permissions()
            self.assertTrue(mock_save.called)
            
            p_alpha = next(p for p in mock_profiles["profiles"] if p["id"] == "agent_alpha")
            p_beta = next(p for p in mock_profiles["profiles"] if p["id"] == "agent_beta")
            
            self.assertEqual(p_alpha.get("derived_read"), ["/path/alpha", "/path/beta"])
            self.assertEqual(p_beta.get("derived_read"), ["/path/beta"])
            self.assertEqual(p_alpha.get("access_read"), ["/base/alpha"], "Base access_read remains unmutated")

    def test_non_loopback_auth_guard(self):
        """Verify D15-b: Non-loopback interface requires BRIDGE_AUTH_TOKEN."""
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SystemExit):
                bridge_runner.run_server(port=8888, host="0.0.0.0")

    def test_voyager_harness_tools_enabled_enforcement(self):
        """Verify that Voyager Harness enforces operator-explicit tools_enabled."""
        allowed_dir = self.test_dir / "workspace"
        allowed_dir.mkdir(parents=True, exist_ok=True)
        test_file = allowed_dir / "test.txt"
        test_file.write_text("sample content", encoding="utf-8")

        # 1. Agent with ONLY read_file enabled cannot run_command or list_dir
        harness_read_only = VoyagerHarnessProvider(
            provider_id="read_bot",
            config={
                "model": "gemini-2.5-flash",
                "access_read": [str(allowed_dir)],
                "tools_enabled": ["read_file"]
            }
        )
        success, msg = harness_read_only._execute_tool("read_file", {"path": str(test_file)}, allowed_dirs=[str(allowed_dir)])
        self.assertTrue(success)
        self.assertEqual(msg, "sample content")

        success, msg = harness_read_only._execute_tool("run_command", {"command": "git status", "cwd": str(allowed_dir)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("not in authorized tools_enabled list", msg)

        # 2. Agent with empty tools_enabled [] cannot call any tools
        harness_no_tools = VoyagerHarnessProvider(
            provider_id="no_tool_bot",
            config={
                "model": "gemini-2.5-flash",
                "access_read": [str(allowed_dir)],
                "tools_enabled": []
            }
        )
        success, msg = harness_no_tools._execute_tool("read_file", {"path": str(test_file)}, allowed_dirs=[str(allowed_dir)])
        self.assertFalse(success)
        self.assertIn("not in authorized tools_enabled list", msg)


if __name__ == "__main__":
    unittest.main()

