#!/usr/bin/env python3
"""
Unit tests for Phase 3: Source Control, Cold Backup Depot (M1–M3), and Cloud Build CI/CD.
Verifies scripts/sync_backup_depot.sh governance invariants and cloudbuild.yaml configuration.
"""

import os
import sys
import subprocess
import unittest
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class TestColdBackupDepotAndCloudBuild(unittest.TestCase):
    def setUp(self):
        self.script_path = ROOT_DIR / "scripts" / "sync_backup_depot.sh"
        self.cloudbuild_path = ROOT_DIR / "cloudbuild.yaml"

    def tearDown(self):
        # Ensure temporary test remote is not left behind
        try:
            subprocess.run(
                ["git", "remote", "remove", "backup-depot"],
                cwd=str(ROOT_DIR),
                capture_output=True,
                check=False
            )
        except Exception:
            pass

    def test_backup_script_exists_and_is_executable(self):
        self.assertTrue(self.script_path.exists(), f"Missing {self.script_path}")
        self.assertTrue(
            os.access(self.script_path, os.X_OK),
            f"{self.script_path} must be executable (chmod +x)"
        )

    def test_backup_script_help_flag(self):
        res = subprocess.run(
            [str(self.script_path), "--help"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Usage: scripts/sync_backup_depot.sh", res.stdout)
        self.assertIn("--dry-run", res.stdout)
        self.assertIn("--strict", res.stdout)
        self.assertIn("--branch", res.stdout)

    def test_backup_script_graceful_exit_when_unset(self):
        env = dict(os.environ)
        env["BACKUP_REPO_URL"] = ""
        env["DEPLOY_ENV_FILE"] = "/dev/null"
        res = subprocess.run(
            [str(self.script_path)],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            env=env
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("BACKUP_REPO_URL is not configured", res.stdout)
        self.assertIn("Exiting without error", res.stdout)

    def test_backup_script_strict_mode_when_unset(self):
        env = dict(os.environ)
        env["BACKUP_REPO_URL"] = ""
        env["DEPLOY_ENV_FILE"] = "/dev/null"
        res = subprocess.run(
            [str(self.script_path), "--strict"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            env=env
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("ERROR: BACKUP_REPO_URL is not configured", res.stdout)

    def test_backup_script_dry_run_verifies_m1_m2_m3(self):
        env = dict(os.environ)
        env["BACKUP_REPO_URL"] = "https://example.org/test-mirror.git"
        env["DEPLOY_ENV_FILE"] = "/dev/null"
        res = subprocess.run(
            [str(self.script_path), "--dry-run", "--skip-tests"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            env=env
        )
        self.assertEqual(res.returncode, 0, f"Dry-run failed: {res.stdout}\n{res.stderr}")
        self.assertIn("Invariant M1 satisfied", res.stdout)
        self.assertIn("Invariant M2 satisfied", res.stdout)
        self.assertIn("Invariant M3", res.stdout)
        self.assertIn("Dry run successful", res.stdout)

    def test_cloudbuild_yaml_structure_and_invariants(self):
        self.assertTrue(self.cloudbuild_path.exists(), f"Missing {self.cloudbuild_path}")
        with open(self.cloudbuild_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIn("steps", data)
        steps = data["steps"]
        step_ids = [s.get("id") for s in steps]

        # Invariant: Must have unit-tests, docker-build, verify-container-hygiene, docker-push, and cloud-run-deploy
        self.assertIn("unit-tests", step_ids)
        self.assertIn("docker-build", step_ids)
        self.assertIn("verify-container-hygiene", step_ids)
        self.assertIn("docker-push", step_ids)
        self.assertIn("cloud-run-deploy", step_ids)

        # Invariant: unit-tests step executes unittest discover
        unit_step = next(s for s in steps if s.get("id") == "unit-tests")
        self.assertIn("python:3.11", unit_step["name"])
        args_str = " ".join(unit_step.get("args", []))
        self.assertIn("unittest discover -s tests", args_str)

        # Invariant: verify-container-hygiene asserts container filesystem cleanliness
        hygiene_step = next(s for s in steps if s.get("id") == "verify-container-hygiene")
        hygiene_args = " ".join(hygiene_step.get("args", []))
        self.assertIn("test ! -e /app/data", hygiene_args)
        self.assertIn("test ! -e /app/.env", hygiene_args)

        # Invariant: cloud-run-deploy preserves G1 and G2 governance
        deploy_step = next(s for s in steps if s.get("id") == "cloud-run-deploy")
        deploy_args = " ".join(deploy_step.get("args", []))
        self.assertIn("--no-allow-unauthenticated", deploy_args)
        self.assertIn("--max-instances=1", deploy_args)
        self.assertIn("/mnt/bridge-data", deploy_args)

        # Invariant: substitutions define sensible defaults
        self.assertIn("substitutions", data)
        subs = data["substitutions"]
        self.assertEqual(subs.get("_LOCATION"), "us-central1")
        self.assertEqual(subs.get("_SERVICE_NAME"), "bridge-deck")


if __name__ == "__main__":
    unittest.main()
