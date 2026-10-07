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
 * @file step_1c_skill_evals.py
 * @description Module 1 Step 1c reference solution: Deterministic and rubric-based
 *   Skill Evaluation harness (`evaluate_brand_skill` and `run_eval_suite`) for
 *   verifying agent adherence to `brand-guidelines/SKILL.md`.
 *
 * Why: Authoring a skill is not sufficient on its own; teams need automated pre-deployment
 * evaluations to verify that (1) the agent actually invoked `load_skill("brand-guidelines")`,
 * (2) required positive elements (indigo/slate ground, warm amber/terracotta accent, low
 * raking light with long shadows, off-center negative space, single realistic subject with
 * shallow depth of field) are present, and (3) forbidden elements (`Never` list: neon,
 * cyan, magenta, logos, watermarks, text overlays, 3D renders, fisheye, Dutch tilt,
 * chrome, lens flare, ring light) are absent.
 */
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

REQUIRED_SKILL_NAME: str = "brand-guidelines"

# Forbidden terms from `skills/brand-guidelines/SKILL.md` (`## Palette`, `## Light`,
# `## Composition`, `## Subject`, and `## Never` sections).
FORBIDDEN_BRAND_PATTERNS: tuple[tuple[str, str], ...] = (
    ("neon", "Forbidden neon palette element ('neon') violates Palette/Never rules"),
    ("fluorescent", "Forbidden fluorescent palette element ('fluorescent') violates Palette rules"),
    ("cyan", "Forbidden cool-toned cyan ('cyan') violates Never rules"),
    ("magenta", "Forbidden cool-toned magenta ('magenta') violates Never rules"),
    ("watermark", "Forbidden watermark in frame ('watermark') violates Never rules"),
    ("logo", "Forbidden logo in frame ('logo') violates Never rules"),
    ("text overlay", "Forbidden text overlay in frame ('text overlay') violates Never rules"),
    ("signage", "Forbidden signage in frame ('signage') violates Never rules"),
    ("3d render", "Forbidden non-photographic style ('3D render') violates Subject rules"),
    ("pixel art", "Forbidden non-photographic style ('pixel art') violates Subject rules"),
    ("fisheye", "Forbidden lens distortion ('fisheye') violates Composition rules"),
    ("dutch tilt", "Forbidden camera tilt ('Dutch tilt') violates Composition rules"),
    ("flat lay", "Forbidden camera angle ('flat lay') violates Composition rules"),
    ("top-down", "Forbidden camera angle ('top-down') violates Composition rules"),
    ("chrome", "Forbidden visual effect ('chrome') violates Never rules"),
    ("lens flare", "Forbidden visual effect ('lens flare') violates Never rules"),
    ("bokeh sparkle", "Forbidden visual effect ('bokeh sparkle') violates Never rules"),
    ("ring light", "Forbidden lighting setup ('ring light') violates Light rules"),
    ("flat overhead", "Forbidden lighting setup ('flat overhead') violates Light rules"),
    ("collage", "Forbidden layout ('collage') violates Never rules"),
    ("split-screen", "Forbidden layout ('split-screen') violates Never rules"),
)


@dataclass
class SkillEvalResult:
    """
    /**
     * Structured outcome of evaluating an agent's art direction against `brand-guidelines`.
     *
     * Why: Provides a JSON-serializable evaluation record (`score`, `passed`,
     * `loaded_skill`, `violations`) that works in local pytest gates and aligns with
     * downstream Module 2 BigQuery `AI.SCORE` brand drift audits.
     *
     * @param score Normalized compliance score in `[0.0, 1.0]`.
     * @param passed True if and only if `loaded_skill` is True, `violations` is empty,
     *   and `score >= min_score`.
     * @param loaded_skill Whether the agent loaded `"brand-guidelines"` via `SkillToolset`.
     * @param violations List of human-readable rule violation descriptions.
     * @param pillar_scores Per-pillar boolean compliance breakdown (`palette`, `light`,
     *   `composition`, `subject`).
     */
    """

    score: float
    passed: bool
    loaded_skill: bool
    violations: list[str] = field(default_factory=list)
    pillar_scores: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Convert the evaluation result into a JSON-serializable dictionary.
         *
         * Why: Facilitates structured reporting in CI suites and `extract_field` helpers.
         *
         * @return Dictionary containing `score`, `passed`, `loaded_skill`, `violations`,
         *   and `pillar_scores`.
         */
        """
        return {
            "score": self.score,
            "passed": self.passed,
            "loaded_skill": self.loaded_skill,
            "violations": list(self.violations),
            "pillar_scores": dict(self.pillar_scores),
        }


def evaluate_brand_skill(
    art_direction: str,
    loaded_skills: Sequence[str] | None = None,
    *,
    required_skill: str = REQUIRED_SKILL_NAME,
    min_score: float = 0.8,
) -> SkillEvalResult:
    """
    /**
     * Evaluate whether an agent loaded `brand-guidelines` and produced compliant art direction.
     *
     * Why: Enforces both behavioral tool-use verification (`required_skill in loaded_skills`)
     * and content rubric verification across the 5 sections of `brand-guidelines/SKILL.md`
     * (`Palette`, `Light`, `Composition`, `Subject`, and `Never`).
     *
     * @param art_direction Candidate art direction text produced by the Visual Director.
     * @param loaded_skills Sequence of skill names loaded during the agent turn.
     * @param required_skill Name of the required brand skill (defaults to `"brand-guidelines"`).
     * @param min_score Minimum normalized score required to pass (defaults to `0.8`).
     * @return Populated `SkillEvalResult` instance.
     */
    """
    skill_list = [str(s).strip() for s in (loaded_skills or []) if str(s).strip()]
    loaded_skill = required_skill in skill_list
    violations: list[str] = []

    if not loaded_skill:
        violations.append(
            f"Agent did not load required skill {required_skill!r} prior to writing art direction"
        )

    if not isinstance(art_direction, str) or not art_direction.strip():
        violations.append("Art direction text is empty")
        return SkillEvalResult(
            score=0.0,
            passed=False,
            loaded_skill=loaded_skill,
            violations=violations,
            pillar_scores={
                "palette": False,
                "light": False,
                "composition": False,
                "subject": False,
            },
        )

    text_lower = art_direction.strip().lower()

    # Check forbidden terms first (`Never` and negative rules)
    forbidden_hits = 0
    for pattern, reason in FORBIDDEN_BRAND_PATTERNS:
        if pattern in text_lower:
            violations.append(reason)
            forbidden_hits += 1

    # Check positive house brand pillars
    has_ground_palette = "indigo" in text_lower or "slate" in text_lower
    has_warm_accent = "amber" in text_lower or "terracotta" in text_lower
    palette_ok = has_ground_palette and has_warm_accent
    if not palette_ok:
        violations.append(
            "Missing house palette: requires deep indigo/slate ground with warm amber or terracotta accent"
        )

    light_ok = (
        "raking" in text_lower
        or "golden hour" in text_lower
        or "golden-hour" in text_lower
        or "long shadow" in text_lower
    )
    if not light_ok:
        violations.append(
            "Missing house lighting: requires single low raking light source or golden hour with long shadows"
        )

    has_off_center = "off-center" in text_lower or "one-third" in text_lower or "third" in text_lower
    has_negative_space = "negative space" in text_lower
    composition_ok = has_off_center and has_negative_space
    if not composition_ok:
        violations.append(
            "Missing house composition: requires off-center placement with generous negative space"
        )

    subject_ok = (
        "realistic" in text_lower
        or "photographic" in text_lower
        or "shallow depth of field" in text_lower
    )
    if not subject_ok:
        violations.append(
            "Missing house subject treatment: requires single realistic photographic subject with shallow depth of field"
        )

    pillar_scores = {
        "palette": palette_ok,
        "light": light_ok,
        "composition": composition_ok,
        "subject": subject_ok,
    }

    positive_score = sum(0.25 for ok in pillar_scores.values() if ok)
    penalty = 0.25 * forbidden_hits
    if not loaded_skill:
        penalty += 0.25
    final_score = round(max(0.0, min(1.0, positive_score - penalty)), 4)

    passed = bool(loaded_skill and len(violations) == 0 and final_score >= min_score)
    return SkillEvalResult(
        score=final_score,
        passed=passed,
        loaded_skill=loaded_skill,
        violations=violations,
        pillar_scores=pillar_scores,
    )


evaluate_skill_compliance = evaluate_brand_skill
run_skill_eval = evaluate_brand_skill


BENCHMARK_EVAL_CASES: list[dict[str, Any]] = [
    {
        "id": "compliant_commuter_bike",
        "art_direction": (
            "A single realistic commuter cyclist positioned off-center at eye level with "
            "generous empty negative space on the left, lit by a single low raking golden-hour "
            "key light casting long shadows across a deep indigo and slate street with a warm "
            "terracotta jacket accent and shallow depth of field."
        ),
        "loaded_skills": ["brand-guidelines"],
        "expected_passed": True,
    },
    {
        "id": "compliant_studio_product",
        "art_direction": (
            "One realistic photographic subject placed off-center one-third into the frame "
            "with generous negative space opposite, shallow depth of field, deep indigo and slate "
            "ground with warm amber accent, low raking studio key light with long shadows."
        ),
        "loaded_skills": ["brand-guidelines"],
        "expected_passed": True,
    },
    {
        "id": "drifted_neon_watermark",
        "art_direction": (
            "Bright neon cyan and magenta glowing cat on a 3D render skateboard with a "
            "company logo watermark and flat overhead ring light."
        ),
        "loaded_skills": ["brand-guidelines"],
        "expected_passed": False,
    },
    {
        "id": "unloaded_skill_violation",
        "art_direction": (
            "Single realistic subject off-center with generous negative space, deep indigo and slate "
            "palette with warm amber accent, low raking golden hour light with long shadows."
        ),
        "loaded_skills": [],
        "expected_passed": False,
    },
]


def run_eval_suite(
    cases: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    /**
     * Execute a batch of positive and negative Skill Evaluation benchmark cases.
     *
     * Why: Enables developers and CI pipelines to verify deterministically that the
     * evaluation harness passes compliant art direction and rejects off-brand or
     * unloaded-skill outputs.
     *
     * @param cases Optional sequence of benchmark case dicts (defaults to `BENCHMARK_EVAL_CASES`).
     * @return Summary dictionary with `total`, `passed`, `failed`, `benchmark_expectations_met`,
     *   and `results`.
     */
    """
    active_cases = list(cases) if cases is not None else list(BENCHMARK_EVAL_CASES)
    results: list[dict[str, Any]] = []
    passed_count = 0
    expectations_met = 0

    for case in active_cases:
        res = evaluate_brand_skill(
            str(case.get("art_direction", "")),
            loaded_skills=case.get("loaded_skills", ["brand-guidelines"]),
        )
        if res.passed:
            passed_count += 1
        expected = case.get("expected_passed")
        matched_expectation = (expected is None) or (res.passed == bool(expected))
        if matched_expectation:
            expectations_met += 1
        results.append(
            {
                "id": case.get("id", f"case_{len(results) + 1}"),
                "passed": res.passed,
                "score": res.score,
                "loaded_skill": res.loaded_skill,
                "violations": res.violations,
                "matched_expectation": matched_expectation,
            }
        )

    total = len(results)
    return {
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "expectations_met": expectations_met,
        "all_expectations_met": expectations_met == total,
        "results": results,
    }


evaluate_all = run_eval_suite
run_benchmark_evals = run_eval_suite

__all__ = [
    "BENCHMARK_EVAL_CASES",
    "FORBIDDEN_BRAND_PATTERNS",
    "REQUIRED_SKILL_NAME",
    "SkillEvalResult",
    "evaluate_all",
    "evaluate_brand_skill",
    "evaluate_skill_compliance",
    "run_benchmark_evals",
    "run_eval_suite",
    "run_skill_eval",
]
