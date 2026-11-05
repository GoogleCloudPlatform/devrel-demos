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
"""Master Referee Scoreboard (`grades/run_all_grades.py`) for the Breaking News Lab harness.

Runs all three deterministic grades (Truth, Safety, Reading) on a draft file
or acts as a lifecycle `Stop` hook handler (`--hook-stop`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

GRADE_DIR = Path(__file__).resolve().parent
if str(GRADE_DIR) not in sys.path:
    sys.path.insert(0, str(GRADE_DIR))

from check_reading import evaluate_reading  # noqa: E402
from check_safety import evaluate_safety  # noqa: E402
from check_truth import DEFAULT_GRAPH_PATH, evaluate_truth  # noqa: E402


def grade_draft(draft_path: Path, graph_path: Path = DEFAULT_GRAPH_PATH) -> Dict[str, Any]:
    text = draft_path.read_text(encoding="utf-8")
    truth = evaluate_truth(text, graph_path=graph_path)
    safety = evaluate_safety(text)
    reading = evaluate_reading(text)

    overall_passed = truth["passed"] and safety["passed"] and reading["passed"]
    overall_score = round((truth["score"] + safety["score"] + reading["score"]) / 3, 1)

    return {
        "draft": str(draft_path),
        "overall_passed": overall_passed,
        "overall_score": overall_score,
        "truth": truth,
        "safety": safety,
        "reading": reading,
    }


def print_scoreboard(report: Dict[str, Any]) -> None:
    overall_tag = "PASS" if report["overall_passed"] else "FAIL"
    t = report["truth"]
    s = report["safety"]
    r = report["reading"]

    print(f"=== Breaking News Lab Harness Scoreboard [{overall_tag}] ({report['overall_score']}/100) ===")
    print(f"  1. Truth Grade:   [{'PASS' if t['passed'] else 'FAIL'}] {t['score']}/100 (Sources cited: {len(t['sources_cited'])})")
    print(f"  2. Safety Grade:  [{'PASS' if s['passed'] else 'FAIL'}] {s['score']}/100")
    print(
        f"  3. Reading Grade: [{'PASS' if r['passed'] else 'FAIL'}] {r['score']}/100 "
        f"(Reading Level: Grade {r['flesch_kincaid_grade']}, target <= 6.5)"
    )

    all_violations = t["violations"] + s["violations"] + r["violations"]
    if all_violations:
        print("\nReferee Diagnostics (Must fix before finishing):")
        for v in all_violations:
            print(f"  - {v}")
    else:
        print("\nAll 3 harness grades passed! Story is cleared for the editor.")


def handle_stop_hook() -> int:
    """Handle Antigravity / Claude Code Stop hook JSON contract."""
    drafts_dir = GRADE_DIR.parent / "drafts"
    examples_dir = GRADE_DIR.parent / "examples"
    candidates = []
    if drafts_dir.exists():
        candidates.extend(drafts_dir.glob("*.md"))
    if examples_dir.exists():
        candidates.extend(
            [
                p
                for p in examples_dir.glob("*.md")
                if p.name not in ("sample_bad_draft.md", "sample_good_draft.md")
            ]
        )
    candidates = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print(json.dumps({"decision": "allow"}))
        return 0

    report = grade_draft(candidates[0])
    if report["overall_passed"]:
        print(json.dumps({"decision": "allow"}))
        return 0

    violations = report["truth"]["violations"] + report["safety"]["violations"] + report["reading"]["violations"]
    print(
        json.dumps(
            {
                "decision": "continue",
                "reason": f"Breaking News Lab Referee blocked stop on {candidates[0].name}: " + "; ".join(violations),
            }
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all 3 Breaking News Lab harness grades.")
    parser.add_argument("draft", nargs="?", type=Path, help="Path to markdown draft")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--hook-stop", action="store_true", help="Run in Stop-hook JSON contract mode")
    args = parser.parse_args()

    if args.hook_stop:
        return handle_stop_hook()

    if not args.draft:
        parser.error("Please provide a path to a markdown draft.")

    report = grade_draft(args.draft)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_scoreboard(report)
    return 0 if report["overall_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
