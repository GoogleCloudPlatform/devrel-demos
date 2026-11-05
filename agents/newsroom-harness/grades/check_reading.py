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
"""Reading Grade referee (`grades/check_reading.py`) for the Newsroom harness.

Enforces 5th-to-6th grade readability and punchy journalistic style:
1. Flesch-Kincaid Grade Level <= 6.5 (easy enough for a 5th/6th grader to understand).
2. No walls of text (every paragraph <= 75 words).
3. Zero corporate PR spin or AI slop words (`delve`, `game-changer`, `synergy`, `tapestry`, etc.).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any, Dict, List

BANNED_SLOP = [
    "delve",
    "tapestry",
    "testament",
    "game-changer",
    "game changer",
    "synergy",
    "moreover",
    "furthermore",
    "paradigm shift",
    "revolutionary",
    "unlock the potential",
    "in conclusion",
]

MAX_FK_GRADE = 6.5
MAX_PARA_WORDS = 75


def count_syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    groups = re.findall(r"[aeiouy]{1,2}", w)
    return max(1, len(groups))


def strip_markdown_tags(text: str) -> str:
    """Strip headings, [Source: ...] tags, and markdown links before computing reading grade."""
    lines = [line for line in text.splitlines() if not line.strip().startswith("#")]
    clean = "\n".join(lines)
    clean = re.sub(r"\[Source:\s*[^\]]+\]", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
    clean = re.sub(r"[#*_`>]", "", clean)
    return clean


def evaluate_reading(text: str) -> Dict[str, Any]:
    """Return a Reading Grade scorecard (0-100), Flesch-Kincaid grade level, and violations."""
    clean = strip_markdown_tags(text)
    words = re.findall(r"[A-Za-z]+", clean)
    sentences = [s.strip() for s in re.split(r"[.!?]+", clean) if len(re.findall(r"[A-Za-z]+", s)) > 0]

    word_count = max(1, len(words))
    sent_count = max(1, len(sentences))
    syllable_count = sum(count_syllables(w) for w in words)

    fk_grade = round(0.39 * (word_count / sent_count) + 11.8 * (syllable_count / word_count) - 15.59, 1)
    fk_grade = max(1.0, fk_grade)

    violations: List[str] = []
    score = 100

    if fk_grade > MAX_FK_GRADE:
        over = round(fk_grade - MAX_FK_GRADE, 1)
        penalty = min(45, int(over * 12) + 10)
        score -= penalty
        violations.append(
            f"GRADE_TOO_HIGH: Reading level is Grade {fk_grade} (target <= {MAX_FK_GRADE} for 5th/6th-grade clarity). "
            f"Use shorter sentences and simpler words."
        )

    paragraphs = [
        strip_markdown_tags(p).strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip() and not p.strip().startswith("#")
    ]
    for idx, para in enumerate(paragraphs, start=1):
        p_words = re.findall(r"\S+", para)
        if len(p_words) > MAX_PARA_WORDS:
            score -= 15
            violations.append(
                f"WALL_OF_TEXT (Paragraph {idx}): {len(p_words)} words exceeds the {MAX_PARA_WORDS}-word limit."
            )

    lower_text = text.lower()
    for phrase in BANNED_SLOP:
        if re.search(rf"\b{re.escape(phrase)}\b", lower_text):
            score -= 15
            violations.append(f"BANNED_SLOP: Found banned AI/PR buzzword `{phrase}`.")

    score = max(0, score)
    passed = score >= 80 and len(violations) == 0
    return {
        "grade_name": "Reading Grade",
        "score": score,
        "passed": passed,
        "flesch_kincaid_grade": fk_grade,
        "word_count": len(words),
        "sentence_count": len(sentences),
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Newsroom Reading Grade check.")
    parser.add_argument("draft", type=Path, help="Path to markdown draft")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    result = evaluate_reading(args.draft.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"Reading Grade [{status}] — Score: {result['score']}/100 | "
            f"Flesch-Kincaid Grade: {result['flesch_kincaid_grade']} (target <= {MAX_FK_GRADE})"
        )
        for v in result["violations"]:
            print(f"  [!] {v}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
