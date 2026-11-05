#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit test suite (`tests/test_harness.py`) for the Breaking News Lab harness."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "grades"))
sys.path.insert(0, str(ROOT / "memory"))

from dream import dream  # noqa: E402
from run_all_grades import grade_draft  # noqa: E402


class TestBreakingNewsLabHarness(unittest.TestCase):
    def test_good_draft_passes_all_three_grades(self) -> None:
        good_path = ROOT / "examples" / "sample_good_draft.md"
        report = grade_draft(good_path)
        self.assertTrue(report["overall_passed"], msg=json.dumps(report, indent=2))
        self.assertEqual(report["truth"]["score"], 100)
        self.assertEqual(report["safety"]["score"], 100)
        self.assertEqual(report["reading"]["score"], 100)
        self.assertLessEqual(report["reading"]["flesch_kincaid_grade"], 6.5)

    def test_bad_draft_fails_all_three_grades(self) -> None:
        bad_path = ROOT / "examples" / "sample_bad_draft.md"
        report = grade_draft(bad_path)
        self.assertFalse(report["overall_passed"])
        self.assertFalse(report["truth"]["passed"])
        self.assertFalse(report["safety"]["passed"])
        self.assertFalse(report["reading"]["passed"])

        truth_codes = " ".join(report["truth"]["violations"])
        safety_codes = " ".join(report["safety"]["violations"])
        reading_codes = " ".join(report["reading"]["violations"])

        self.assertIn("RUMOR_MILL_SOURCE", truth_codes)
        self.assertIn("UNVERIFIED_CLAIM", truth_codes)
        self.assertIn("PROMPT_INJECTION", safety_codes)
        self.assertIn("SPOOFED_WAIVER", safety_codes)
        self.assertIn("SECRET_LEAK", safety_codes)
        self.assertIn("BANNED_SLOP", reading_codes)

    def test_dreaming_promotes_verified_and_prunes_rumors(self) -> None:
        orig_graph = json.loads((ROOT / "memory" / "memory_graph.json").read_text(encoding="utf-8"))
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tmp:
            tmp.write(json.dumps(orig_graph))
            tmp_path = Path(tmp.name)

        try:
            summary = dream(graph_path=tmp_path, dry_run=False)
            self.assertEqual(summary["promoted_count"], 1)
            self.assertEqual(summary["pruned_count"], 1)

            updated = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertEqual(len(updated["scratchpad"]), 0)
            self.assertEqual(len(updated["nodes"]), len(orig_graph["nodes"]) + 1)
        finally:
            tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
