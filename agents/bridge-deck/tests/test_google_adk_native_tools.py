#!/usr/bin/env python3
"""
Unit tests for Google ADK Native Workspace Tools, Worktree Isolation, and Router Invariants.
Verifies:
1. GoogleADKProvider executes read_file, write_file, list_dir, grep_search within ACL boundaries.
2. GoogleADKProvider strictly denies writes outside access_write paths.
3. GoogleADKProvider resolves git worktree sandboxes to prevent clobbering.
4. AgentRouter strictly routes google-adk provider agents to GoogleADKProvider and rejects Voyager hijacking.
"""

import os
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from providers.google_adk import GoogleADKProvider
from core.router import AgentRouter
from core.worktree import ensure_git_repo


class TestGoogleADKNativeTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_adk_tools_"))
        self.workspace_dir = self.test_dir / "workspace"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.unauthorized_dir = self.test_dir / "unauthorized"
        self.unauthorized_dir.mkdir(parents=True, exist_ok=True)

        # Setup sample files
        (self.workspace_dir / "README.md").write_text("# Test Workspace\nLine 2", encoding="utf-8")
        (self.unauthorized_dir / "secret.txt").write_text("Secret content", encoding="utf-8")

        self.config = {
            "model": "gemini-3.7-flash",
            "project_id": "test-project",
            "tools_enabled": ["read_file", "write_file", "list_dir", "grep_search", "run_command"],
            "access_read": [str(self.workspace_dir)],
            "access_write": [str(self.workspace_dir)],
        }
        self.provider = GoogleADKProvider(provider_id="test_adk_agent", config=self.config)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_adk_read_file_within_acl_succeeds(self):
        """ADK provider reads authorized file content successfully."""
        success, output = self.provider._execute_tool(
            "read_file",
            {"path": "README.md"},
            allowed_dirs=[str(self.workspace_dir)],
            write_allowed_dirs=[str(self.workspace_dir)]
        )
        self.assertTrue(success)
        self.assertIn("# Test Workspace", output)

    def test_adk_read_file_outside_acl_denied(self):
        """ADK provider strictly denies reading files outside access_read."""
        success, output = self.provider._execute_tool(
            "read_file",
            {"path": str(self.unauthorized_dir / "secret.txt")},
            allowed_dirs=[str(self.workspace_dir)],
            write_allowed_dirs=[str(self.workspace_dir)]
        )
        self.assertFalse(success)
        self.assertIn("ACL Permission Denied", output)

    def test_adk_write_file_within_acl_succeeds(self):
        """ADK provider writes to authorized path atomically."""
        new_file = self.workspace_dir / "output.txt"
        success, output = self.provider._execute_tool(
            "write_file",
            {"path": "output.txt", "content": "ADK Native Write Success"},
            allowed_dirs=[str(self.workspace_dir)],
            write_allowed_dirs=[str(self.workspace_dir)]
        )
        self.assertTrue(success)
        self.assertIn("Successfully wrote", output)
        self.assertTrue(new_file.exists())
        self.assertEqual(new_file.read_text(encoding="utf-8"), "ADK Native Write Success")

    def test_adk_write_file_without_write_permission_denied(self):
        """ADK provider rejects write_file if write_allowed_dirs is empty or path outside."""
        success, output = self.provider._execute_tool(
            "write_file",
            {"path": "unauthorized.txt", "content": "Forbidden"},
            allowed_dirs=[str(self.workspace_dir)],
            write_allowed_dirs=[]
        )
        self.assertFalse(success)
        self.assertIn("ACL Permission Denied", output)

    def test_adk_list_dir_and_grep_search(self):
        """ADK provider lists directory and greps code within ACL."""
        success_list, list_out = self.provider._execute_tool(
            "list_dir",
            {"path": "."},
            allowed_dirs=[str(self.workspace_dir)],
            write_allowed_dirs=[str(self.workspace_dir)]
        )
        self.assertTrue(success_list)
        self.assertIn("README.md", list_out)

        success_grep, grep_out = self.provider._execute_tool(
            "grep_search",
            {"query": "Test Workspace", "path": "."},
            allowed_dirs=[str(self.workspace_dir)],
            write_allowed_dirs=[str(self.workspace_dir)]
        )
        self.assertTrue(success_grep)
        self.assertIn("README.md:1", grep_out)

    def test_adk_git_worktree_isolation(self):
        """ADK provider resolves dedicated git worktree when target directory is a git repo."""
        repo_dir = self.test_dir / "git_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        ensure_git_repo(repo_dir)

        # Create initial file & commit
        (repo_dir / "init.txt").write_text("initial commit", encoding="utf-8")
        import subprocess
        subprocess.run(["git", "add", "init.txt"], cwd=str(repo_dir), check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=str(repo_dir), check=True, capture_output=True)

        config = {
            "model": "gemini-3.7-flash",
            "project_id": "test-project",
            "tools_enabled": ["write_file"],
            "access_read": [str(repo_dir)],
            "access_write": [str(repo_dir)],
        }
        adk_prov = GoogleADKProvider(provider_id="test_worker_1", config=config)

        # Mock generate to return a single write_file tool call and then final response
        mock_response = MagicMock()
        mock_response.text = '```adk_tool_call\n{"tool": "write_file", "args": {"path": "agent.py", "content": "print(\'hello\')"}}\n```'
        mock_final = MagicMock()
        mock_final.text = "Write complete."

        with patch.object(adk_prov, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = [mock_response, mock_final]
            mock_get_client.return_value = mock_client

            result = adk_prov.invoke(
                prompt="Create agent.py",
                context={"directories": [str(repo_dir)]}
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["provider_type"], "google-adk")
        # Verify file was written in agent's isolated worktree, keeping main clean
        wt_dir = repo_dir / "worktrees" / "test_worker_1"
        self.assertTrue((wt_dir / "agent.py").exists())
        self.assertEqual((wt_dir / "agent.py").read_text(encoding="utf-8"), "print('hello')")

    def test_router_enforces_google_adk_provider_and_rejects_voyager_hijack(self):
        """Router strictly returns GoogleADKProvider for google-adk provider type even if harness is voyager."""
        agents_dir = self.test_dir / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        # Manifest with provider type google-adk but rogue harness voyager
        manifest_data = {
            "id": "jared_test",
            "name": "Jared (ADK Gemini)",
            "role": "Autonomous Systems Engineer",
            "harness": "voyager",  # rogue or legacy field
            "provider": {
                "type": "google-adk",
                "model": "gemini-3.7-flash",
                "project_id": "test-project"
            }
        }
        (agents_dir / "jared_test.agent.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        router = AgentRouter(bridge_dir=self.test_dir)
        provider = router.providers.get("jared_test")

        self.assertIsNotNone(provider)
        self.assertIsInstance(provider, GoogleADKProvider)
        self.assertEqual(provider.provider_id, "jared_test")

    def test_iris_location_forced_to_global_for_gemini_37(self):
        """Even if manifest declares us-central1, Gemini 3.7 Flash models force location to global."""
        agents_dir = self.test_dir / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        manifest_data = {
            "id": "iris_test",
            "name": "Iris",
            "role": "Multimodal Visual Specialist",
            "provider": {
                "type": "google-adk",
                "model": "gemini-3.7-flash",
                "location": "us-central1",
                "project_id": "test-project"
            }
        }
        (agents_dir / "iris_test.agent.json").write_text(json.dumps(manifest_data), encoding="utf-8")

        router = AgentRouter(bridge_dir=self.test_dir)
        provider = router.providers.get("iris_test")
        self.assertIsNotNone(provider)
        self.assertEqual(provider.location, "global")

    def test_adk_tool_call_never_leaks_raw_json_into_response(self):
        """When the model emits raw adk_tool_call until max_iterations, raw JSON is scrubbed and clean summary produced."""
        repo_dir = self.test_dir / "test_workspace"
        repo_dir.mkdir(parents=True, exist_ok=True)
        (repo_dir / "README.md").write_text("Test readme content", encoding="utf-8")

        config = {
            "model": "gemini-3.7-flash",
            "project_id": "test-project",
            "tools_enabled": ["list_dir"],
            "access_read": [str(repo_dir)],
            "max_iterations": 2
        }
        prov = GoogleADKProvider(provider_id="test_worker_scrub", config=config)

        mock_call = MagicMock()
        mock_call.text = '```adk_tool_call\n{"tool": "list_dir", "args": {"path": "."}}\n```'

        with patch.object(prov, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            # Returns tool call for both iterations
            mock_client.models.generate_content.side_effect = [mock_call, mock_call]
            mock_get_client.return_value = mock_client

            result = prov.invoke(prompt="List directory", context={"directories": [str(repo_dir)]})

        self.assertTrue(result["success"])
        # Ensure no raw adk_tool_call block leaked
        self.assertNotIn("```adk_tool_call", result["response"])
        self.assertNotIn('"tool": "list_dir"', result["response"])
        self.assertIn("inspecting the workspace", result["response"])

    def test_adk_tool_call_scrubs_code_blocks_when_narrative_present(self):
        """When model outputs narrative text alongside a tool block, the tool block is scrubbed cleanly."""
        repo_dir = self.test_dir / "test_workspace_2"
        repo_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "model": "gemini-3.7-flash",
            "project_id": "test-project",
            "tools_enabled": ["list_dir"],
            "access_read": [str(repo_dir)],
            "max_iterations": 1
        }
        prov = GoogleADKProvider(provider_id="test_worker_narrative", config=config)

        mock_mixed = MagicMock()
        mock_mixed.text = 'I found the repository is empty.\n```adk_tool_call\n{"tool": "list_dir", "args": {"path": "."}}\n```\nAll set for next steps!'

        with patch.object(prov, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_mixed
            mock_get_client.return_value = mock_client

            result = prov.invoke(prompt="Status check", context={"directories": [str(repo_dir)]})

        self.assertTrue(result["success"])
        self.assertNotIn("```adk_tool_call", result["response"])
        self.assertIn("I found the repository is empty.", result["response"])
        self.assertIn("All set for next steps!", result["response"])


if __name__ == "__main__":
    unittest.main()
