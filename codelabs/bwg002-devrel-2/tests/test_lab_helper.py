# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
/**
 * @file test_lab_helper.py
 * @description Comprehensive unit tests for Feature F20: Lab Helper Agent Skill & Verification CLI.
 *
 * Why: Verifies that the progressive Lab Helper agent skill, hints catalog, drift inspection
 * engine, and auto-remediation mechanisms work with 100% determinism offline, adhering strictly
 * to Jetski/CLS frontmatter rules, Interface Contract 4, and progressive disclosure principles.
 */
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import unittest
import pytest

APP_ROOT: Path = Path(__file__).resolve().parents[1]
SKILL_DIR: Path = APP_ROOT / ".agents" / "skills" / "lab-helper"
VERIFY_SCRIPT: Path = SKILL_DIR / "scripts" / "verify_workspace.py"
HINTS_CATALOG: Path = SKILL_DIR / "references" / "hints_catalog.json"


def _load_verify_workspace_module() -> Any:
    """
    /**
     * Dynamically imports the verify_workspace module from its script location.
     *
     * Why: Tests the programmatic Python API defined by Interface Contract 4 in PROJECT.md.
     *
     * @return Loaded module object for verify_workspace.py.
     */
    """
    spec = importlib.util.spec_from_file_location("verify_workspace_unit", VERIFY_SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["verify_workspace_unit"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestLabHelperSkillStructure(unittest.TestCase):
    """
    /**
     * Validates file layout, YAML frontmatter, and Jetski skill compliance for Lab Helper.
     *
     * Why: Guarantees that the agent skill conforms to creating-agent-skill standards,
     * including line-count limits, frontmatter format, 3rd-person description, and lack
     * of stray scripts at the skill root.
     */
    """

    def test_skill_files_and_frontmatter_compliance(self) -> None:
        """
        /**
         * Verifies required documentation files, frontmatter rules, and directory cleanliness.
         *
         * Why: Enforces Jetski skill architecture: SKILL.md (<500 lines, YAML frontmatter with
         * 'name: lab-helper' and 'Use when'), REFERENCE.md (with TOC), TEMPLATES.md, and scripts/.
         */
        """
        self.assertTrue(SKILL_DIR.is_dir(), f"Missing skill directory: {SKILL_DIR}")
        for rel in ("SKILL.md", "REFERENCE.md", "TEMPLATES.md", "references/hints_catalog.json", "scripts/verify_workspace.py"):
            target = SKILL_DIR / rel
            self.assertTrue(target.is_file(), f"Missing required skill file: {target}")

        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertLess(len(skill_text.splitlines()), 500, "SKILL.md must be under 500 lines")
        self.assertTrue(skill_text.startswith("---\n"), "SKILL.md must start with YAML frontmatter delimiter")
        frontmatter = skill_text.split("---", 2)[1]
        self.assertIn("name: lab-helper", frontmatter)
        self.assertIn("Use when", frontmatter)
        self.assertIn("REFERENCE.md", skill_text)
        self.assertIn("TEMPLATES.md", skill_text)

        ref_text = (SKILL_DIR / "REFERENCE.md").read_text(encoding="utf-8")
        self.assertIn("## Table of Contents", ref_text, "REFERENCE.md must include a Table of Contents")
        self.assertGreater(len(ref_text.splitlines()), 100, "REFERENCE.md should be thorough (>100 lines)")

        root_scripts = list(SKILL_DIR.glob("*.py")) + list(SKILL_DIR.glob("*.sh"))
        self.assertEqual(root_scripts, [], "No .py or .sh scripts should be at the root of lab-helper/")

    def test_hints_catalog_covers_all_9_steps_with_progressive_tiers(self) -> None:
        """
        /**
         * Verifies hints_catalog.json contains all 9 steps and enforces strictly increasing hint lengths.
         *
         * Why: Guarantees deterministic progressive disclosure: len(tier_3) > len(tier_2) > len(tier_1).
         */
        """
        self.assertTrue(HINTS_CATALOG.is_file(), f"Missing hints catalog: {HINTS_CATALOG}")
        data = json.loads(HINTS_CATALOG.read_text(encoding="utf-8"))
        steps = data.get("steps", data)
        expected = ["1a", "1b", "1c", "2a", "2b", "3a", "3b", "3c", "4a"]

        for sid in expected:
            self.assertIn(sid, steps, f"Step '{sid}' missing from hints_catalog.json")
            entry = steps[sid]
            self.assertIn("step_id", entry)
            self.assertIn("module", entry)
            self.assertIn("title", entry)
            t1 = entry["tier_1_hint"]
            t2 = entry["tier_2_hint"]
            t3 = entry["tier_3_hint"]
            self.assertTrue(t1 and t2 and t3, f"Empty hint found in step {sid}")
            self.assertGreater(
                len(t3),
                len(t2),
                f"Tier 3 hint must be longer than Tier 2 hint for step {sid}",
            )
            self.assertGreater(
                len(t2),
                len(t1),
                f"Tier 2 hint must be longer than Tier 1 hint for step {sid}",
            )


class TestWorkspaceVerificationEngine(unittest.TestCase):
    """
    /**
     * Tests inspect_step_drift, get_progressive_hint, and remediate_step API functions.
     *
     * Why: Validates the core inspection logic against empty workspaces, corrupted code,
     * missing symbols, and gold-standard reference implementations.
     */
    """

    def setUp(self) -> None:
        """
        /**
         * Loads the verify_workspace module before each test.
         *
         * Why: Ensures a clean module instance for every test execution.
         */
        """
        self.vw = _load_verify_workspace_module()

    def test_inspect_step_drift_clean_on_reference_workspace_all_9_steps(self) -> None:
        """
        /**
         * Verifies that the authoritative repository workspace has 0 drift across all 9 steps.
         *
         * Why: Ensures that our reference solutions in .agents/solutions/ are complete and accurate.
         */
        """
        for sid in ("1a", "1b", "1c", "2a", "2b", "3a", "3b", "3c", "4a"):
            rep = self.vw.inspect_step_drift(sid, workspace_dir=APP_ROOT)
            self.assertFalse(rep["has_drift"], f"Reference solution for {sid} has unexpected drift: {rep}")
            self.assertFalse(rep["drifted"])
            self.assertEqual(rep["status"], "clean")

        all_rep = self.vw.inspect_step_drift("all", workspace_dir=APP_ROOT)
        self.assertFalse(all_rep["has_drift"])
        self.assertEqual(len(all_rep["steps"]), 9)

    def test_inspect_step_drift_detects_missing_files_syntax_errors_and_missing_symbols(self) -> None:
        """
        /**
         * Verifies that drift detection accurately identifies missing files, syntax errors, and missing symbols.
         *
         * Why: Confirms that learners receive specific diagnostics when code is missing or broken.
         */
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Empty workspace -> missing files
            rep_empty = self.vw.inspect_step_drift("3b", workspace_dir=tmpdir)
            self.assertTrue(rep_empty["has_drift"])
            self.assertIn("module_3/step_3b_pii_scrubbing.py", rep_empty["missing_files"])

            # 2. Syntax error
            target = Path(tmpdir) / ".agents" / "solutions" / "module_3" / "step_3b_pii_scrubbing.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("def broken(:\n    pass\n", encoding="utf-8")
            rep_syn = self.vw.inspect_step_drift("3b", workspace_dir=tmpdir)
            self.assertTrue(rep_syn["has_drift"])
            self.assertTrue(rep_syn["syntax_errors"])

            # 3. Missing symbol
            target.write_text('"""Valid module."""\nx = 1\n', encoding="utf-8")
            rep_sym = self.vw.inspect_step_drift("3b", workspace_dir=tmpdir)
            self.assertTrue(rep_sym["has_drift"])
            self.assertTrue(rep_sym["missing_symbols"])
            self.assertIn("PIIScrubber", rep_sym["missing_symbols"])

    def test_progressive_hints_tier_1_2_3_do_not_mutate_workspace(self) -> None:
        """
        /**
         * Verifies that get_progressive_hint returns calibrated hints without modifying any files.
         *
         * Why: Enforces the read-only safety invariant for Tiers 1-3.
         */
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            wip_file = Path(tmpdir) / ".agents" / "solutions" / "module_3" / "step_3c_hitl_authorizations.py"
            wip_file.parent.mkdir(parents=True, exist_ok=True)
            wip_bytes = b"# learner draft implementation\n"
            wip_file.write_bytes(wip_bytes)
            orig_hash = hashlib.sha256(wip_bytes).hexdigest()

            h1 = self.vw.get_progressive_hint("3c", tier=1, workspace_dir=tmpdir)
            h2 = self.vw.get_progressive_hint("3c", tier=2, workspace_dir=tmpdir)
            h3 = self.vw.get_progressive_hint("3c", tier=3, workspace_dir=tmpdir)

            self.assertTrue(h1 and h2 and h3)
            self.assertGreater(len(h3), len(h2))
            self.assertGreater(len(h2), len(h1))

            current_hash = hashlib.sha256(wip_file.read_bytes()).hexdigest()
            self.assertEqual(orig_hash, current_hash, "Progressive hints must never mutate learner files")

    def test_remediate_step_restores_all_modules_including_sql_skill_and_js(self) -> None:
        """
        /**
         * Verifies that remediate_step successfully restores step implementations to zero drift.
         *
         * Why: Validates the recovery mechanism for Python, SQL, and Markdown files.
         */
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test step 1a (includes brand-guidelines/SKILL.md)
            res_1a = self.vw.remediate_step("1a", workspace_dir=tmpdir)
            self.assertTrue(res_1a["remediated"])
            self.assertFalse(res_1a["has_drift"])
            self.assertTrue((Path(tmpdir) / ".agents" / "solutions" / "module_1" / "skills" / "brand-guidelines" / "SKILL.md").is_file())

            # Test step 2a (includes sql/create_key_visuals.sql)
            res_2a = self.vw.remediate_step("2a", workspace_dir=tmpdir)
            self.assertTrue(res_2a["remediated"])
            self.assertFalse(res_2a["has_drift"])
            self.assertTrue((Path(tmpdir) / ".agents" / "solutions" / "module_2" / "sql" / "create_key_visuals.sql").is_file())

            # Test step 4a (tokenomics)
            res_4a = self.vw.remediate_step("4a", workspace_dir=tmpdir)
            self.assertTrue(res_4a["remediated"])
            self.assertFalse(res_4a["has_drift"])
            self.assertTrue((Path(tmpdir) / ".agents" / "solutions" / "module_4" / "step_4a_tokenomics.py").is_file())


class TestVerifyWorkspaceCLI(unittest.TestCase):
    """
    /**
     * Tests CLI argument parsing, execution flags, and exit codes.
     *
     * Why: Verifies that verify_workspace.py behaves correctly when invoked from shell or scripts.
     */
    """

    def test_cli_flags_and_invalid_argument_rejection(self) -> None:
        """
        /**
         * Exercises subprocess CLI execution and tests boundary/error conditions.
         *
         * Why: Enforces exit code 2 on invalid arguments and exit code 0 on valid executions.
         */
        """
        # Test invalid module number
        p_mod = subprocess.run([sys.executable, str(VERIFY_SCRIPT), "--module", "99", "--step", "1a"], capture_output=True, text=True)
        self.assertEqual(p_mod.returncode, 2)

        # Test invalid step ID
        p_step = subprocess.run([sys.executable, str(VERIFY_SCRIPT), "--module", "3", "--step", "3z"], capture_output=True, text=True)
        self.assertEqual(p_step.returncode, 2)

        # Test mismatched module and step
        p_mismatch = subprocess.run([sys.executable, str(VERIFY_SCRIPT), "--module", "1", "--step", "3a"], capture_output=True, text=True)
        self.assertEqual(p_mismatch.returncode, 2)

        # Test invalid tier
        p_tier = subprocess.run([sys.executable, str(VERIFY_SCRIPT), "--tier", "unknown"], capture_output=True, text=True)
        self.assertEqual(p_tier.returncode, 2)

        # Test valid JSON execution
        p_valid = subprocess.run([sys.executable, str(VERIFY_SCRIPT), "--step", "1a", "--tier", "1", "--json"], capture_output=True, text=True)
        self.assertEqual(p_valid.returncode, 0)
        data = json.loads(p_valid.stdout)
        self.assertEqual(data["step"], "1a")
        self.assertFalse(data["has_drift"])


if __name__ == "__main__":
    unittest.main()
