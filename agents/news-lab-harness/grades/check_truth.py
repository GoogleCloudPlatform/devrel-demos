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
"""Truth Grade referee (`grades/check_truth.py`) for the Breaking News Lab harness.

Checks a markdown draft for:
1. Explicit `[Source: <Name>]` citations on paragraphs with numeric/factual claims.
2. Zero citations to `known_rumor_mills` from `memory/memory_graph.json`.
3. Zero unverified rumor markers (`[UNVERIFIED]`, `sources say`, `rumor has it`, `reportedly`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Dict, List

DEFAULT_GRAPH_PATH = Path(__file__).resolve().parent.parent / "memory" / "memory_graph.json"

WEASEL_PATTERNS = [
    (r"\[unverified\]", "Contains an explicit `[UNVERIFIED]` claim marker."),
    (r"\banonymous sources say\b", "Relies on 'anonymous sources say' instead of a named source."),
    (r"\brumor has it\b", "Uses 'rumor has it' instead of verified facts."),
    (r"\breportedly\b", "Uses hedging word 'reportedly' without a primary receipt."),
    (r"\btrust me bro\b", "Uses unverified 'trust me bro' phrasing."),
]


def evaluate_truth(text: str, graph_path: Path = DEFAULT_GRAPH_PATH) -> Dict[str, Any]:
    """Return a Truth Grade scorecard (0-100) and list of violations."""
    rumor_mills = set()
    verified_sources = set()
    if graph_path.exists():
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        rumor_mills = {s.lower() for s in data.get("known_rumor_mills", [])}
        verified_sources = {s.lower() for s in data.get("verified_sources", [])}

    violations: List[str] = []
    score = 100

    for pattern, msg in WEASEL_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            violations.append(f"UNVERIFIED_CLAIM: {msg}")
            score -= 25

    sources_found = [s.strip() for s in re.findall(r"\[Source:\s*([^\]]+)\]", text, flags=re.IGNORECASE)]
    if not sources_found:
        violations.append("MISSING_SOURCES: Draft has 0 `[Source: ...]` tags. Every bulletin must cite its sources.")
        score -= 40

    for src in sources_found:
        if src.lower() in rumor_mills:
            violations.append(f"RUMOR_MILL_SOURCE: `[Source: {src}]` is flagged as a known rumor mill in memory_graph.json.")
            score -= 40

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip() and not p.strip().startswith("#")]
    for idx, para in enumerate(paragraphs, start=1):
        has_number = bool(re.search(r"\b\d+(?:\.\d+)?%?\b", para))
        has_source = bool(re.search(r"\[Source:\s*[^\]]+\]", para, flags=re.IGNORECASE))
        if has_number and not has_source:
            violations.append(
                f"UNBACKED_STAT (Paragraph {idx}): Contains numbers/stats without a `[Source: ...]` receipt."
            )
            score -= 15

    score = max(0, score)
    passed = score >= 80 and len(violations) == 0
    return {
        "grade_name": "Truth Grade",
        "score": score,
        "passed": passed,
        "sources_cited": sources_found,
        "known_verified_matches": [s for s in sources_found if s.lower() in verified_sources],
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Breaking News Lab Truth Grade check.")
    parser.add_argument("draft", type=Path, help="Path to markdown draft")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    result = evaluate_truth(args.draft.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"Truth Grade [{status}] — Score: {result['score']}/100 | Sources Cited: {len(result['sources_cited'])}")
        for v in result["violations"]:
            print(f"  [!] {v}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
