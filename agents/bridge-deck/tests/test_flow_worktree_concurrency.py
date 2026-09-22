#!/usr/bin/env python3
"""
Unit and Concurrency Tests for Flow Cloud Workspace and Git Worktree Isolation.
Verifies that multiple agents (agent_alpha, agent_beta, agent_gamma) can work in parallel
without clobbering each other, and verifies strict project containment.
"""

import os
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

from core.worktree import (
    ensure_git_repo,
    get_or_create_agent_worktree,
    list_agent_worktrees
)
from providers.voyager_harness import VoyagerHarnessProvider


class TestFlowWorktreeConcurrency(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_flow_workspace_"))
        self.flow_repo = self.test_dir / "flow"
        self.flow_repo.mkdir(parents=True, exist_ok=True)
        ensure_git_repo(self.flow_repo)

    def tearDown(self):
        try:
            subprocess.run(["git", "worktree", "prune"], cwd=str(self.flow_repo), capture_output=True)
            shutil.rmtree(self.test_dir, ignore_errors=True)
        except Exception:
            pass

    def test_worktree_provisioning_and_branch_isolation(self):
        """Verifies each agent gets their own isolated worktree and branch."""
        alpha_wt = get_or_create_agent_worktree(self.flow_repo, "agent_alpha")
        beta_wt = get_or_create_agent_worktree(self.flow_repo, "agent_beta")

        self.assertTrue(alpha_wt.exists())
        self.assertTrue(beta_wt.exists())
        self.assertNotEqual(alpha_wt, beta_wt)

        # Check branches
        alpha_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(alpha_wt),
            capture_output=True,
            text=True
        ).stdout.strip()
        beta_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(beta_wt),
            capture_output=True,
            text=True
        ).stdout.strip()

        self.assertEqual(alpha_branch, "feature/agent_alpha")
        self.assertEqual(beta_branch, "feature/agent_beta")

    def test_concurrent_writes_do_not_clobber(self):
        """
        Verifies that agent_alpha and agent_beta can modify the exact same file in their worktrees
        without clobbering or overwriting each other's work.
        """
        alpha_wt = get_or_create_agent_worktree(self.flow_repo, "agent_alpha")
        beta_wt = get_or_create_agent_worktree(self.flow_repo, "agent_beta")

        target_rel = "src/flow/engine.py"
        (alpha_wt / "src" / "flow").mkdir(parents=True, exist_ok=True)
        (beta_wt / "src" / "flow").mkdir(parents=True, exist_ok=True)

        alpha_file = alpha_wt / target_rel
        beta_file = beta_wt / target_rel

        alpha_code = "# Alpha UI-friendly simulation state\nclass FlowSimulation:\n    state = 'alpha_flow'\n"
        beta_code = "# Beta high-speed differential tensor engine\nclass FlowSimulation:\n    state = 'beta_flow'\n"

        # Alpha writes
        alpha_file.write_text(alpha_code, encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(alpha_wt), check=True)
        subprocess.run(["git", "commit", "-m", "Alpha simulation update"], cwd=str(alpha_wt), check=True)

        # Beta writes to the same file path simultaneously
        beta_file.write_text(beta_code, encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(beta_wt), check=True)
        subprocess.run(["git", "commit", "-m", "Beta simulation update"], cwd=str(beta_wt), check=True)

        # Assert no clobbering: both files retain their distinct contents
        self.assertEqual(alpha_file.read_text(encoding="utf-8"), alpha_code)
        self.assertEqual(beta_file.read_text(encoding="utf-8"), beta_code)

        # Assert main branch in root remains unaffected until merged
        main_file = self.flow_repo / target_rel
        self.assertFalse(main_file.exists())

    def test_voyager_harness_write_file_within_worktree(self):
        """Verifies VoyagerHarness write_file tool operates securely within worktree."""
        provider = VoyagerHarnessProvider(
            provider_id="agent_alpha",
            config={
                "project_id": "test-project",
                "model": "gemini-3.7-flash",
                "tools_enabled": ["write_file", "read_file", "list_dir"]
            }
        )

        alpha_wt = get_or_create_agent_worktree(self.flow_repo, "agent_alpha")
        allowed_dirs = [str(alpha_wt)]
        write_allowed_dirs = [str(alpha_wt)]

        # 1. Successful write inside authorized worktree
        success, msg = provider._execute_tool(
            "write_file",
            {"path": "src/flow/notes.txt", "content": "Simulation parameters validated."},
            allowed_dirs=allowed_dirs,
            write_allowed_dirs=write_allowed_dirs
        )
        self.assertTrue(success, f"Tool failed: {msg}")
        self.assertTrue((alpha_wt / "src" / "flow" / "notes.txt").exists())

        # 2. Rejection when attempting to write outside worktree
        outside_path = str(self.test_dir / "rogue_file.txt")
        success_out, msg_out = provider._execute_tool(
            "write_file",
            {"path": outside_path, "content": "Attempted breakout"},
            allowed_dirs=allowed_dirs,
            write_allowed_dirs=write_allowed_dirs
        )
        self.assertFalse(success_out)
        self.assertIn("ACL Permission Denied", msg_out)

    def test_voyager_harness_enforces_write_permission_revocation(self):
        """Verifies that an agent without write_allowed_dirs cannot write even if in allowed_dirs."""
        provider = VoyagerHarnessProvider(
            provider_id="agent_gamma_readonly",
            config={
                "project_id": "test-project",
                "model": "gemini-3.7-flash",
                "tools_enabled": ["write_file", "read_file"]
            }
        )

        gamma_wt = get_or_create_agent_worktree(self.flow_repo, "agent_gamma")
        # Allowed to read, but NOT allowed to write
        allowed_dirs = [str(gamma_wt)]
        write_allowed_dirs = []

        success, msg = provider._execute_tool(
            "write_file",
            {"path": "unauthorized.py", "content": "print('bad')"},
            allowed_dirs=allowed_dirs,
            write_allowed_dirs=write_allowed_dirs
        )
        self.assertFalse(success)
        self.assertIn("ACL Permission Denied: write access not granted", msg)


if __name__ == "__main__":
    unittest.main()
