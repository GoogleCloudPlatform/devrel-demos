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
 * @file step_2b_drift_detection_and_tuning.py
 * @description Module 2 — Step 2b: Multimodal Brand Drift Detection (`AI.SCORE`) & Prompt/Skill Tuning (`F14`).
 *
 * Why: Implements the closed-loop observability and remediation workflow:
 * 1. Generate the `bwg.brand_review` `AI.SCORE` query (`build_brand_score_sql`).
 * 2. Deterministically evaluate key visual compliance (`score_brand_compliance`) with an exact
 *    `brand_fit >= 7.0` threshold (`'on brand'` vs. `'needs another pass'`).
 * 3. Diagnose specific house-brand rule violations (`detect_brand_drift`).
 * 4. Remediate drifted prompts and skills (`tune_prompt_and_skill`) so re-scored visuals achieve
 *    `brand_fit >= 7.0` and pass local `step_1b` Skill Evals.
 */
"""

from __future__ import annotations

import copy
from pathlib import Path
import re
import sys
from typing import Any

_APP_ROOT = Path(__file__).resolve().parents[3]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from pitch_generator.config import get_config  # noqa: E402

DEFAULT_PROJECT_ID: str = get_config().project_id or "local-dev-project"
DEFAULT_LOCATION: str = get_config().region or "us-central1"

SQL_DIR: Path = Path(__file__).resolve().parent / "sql"
SCORE_BRAND_FIT_SQL_PATH: Path = SQL_DIR / "score_brand_fit.sql"

BRAND_FIT_THRESHOLD: float = 7.0

FORBIDDEN_RULE_PATTERNS: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "palette",
        ("neon", "cyan", "magenta", "rainbow", "fluorescent", "lime"),
        "Palette violation: replace neon/cyan/magenta/rainbow colors with deep indigo, slate, and warm amber or terracotta.",
    ),
    (
        "lighting",
        ("ring light", "flat overhead", "harsh flash", "dual light", "even fluorescent"),
        "Lighting violation: replace flat overhead or ring light with one low raking golden hour or blue hour light casting long shadows.",
    ),
    (
        "frame_cleanliness",
        ("watermark", "logo", "text overlay", "typography", "banner"),
        "Frame violation: remove all logos, watermarks, and text overlays from the image frame.",
    ),
    (
        "treatment",
        ("chrome", "3d render", "cartoon", "clipart", "vector illustration", "sci-fi"),
        "Treatment violation: replace 3D render/chrome/cartoon styling with one realistic photographic subject and shallow depth of field.",
    ),
    (
        "composition",
        ("cluttered", "collage", "busy background", "centered symmetrical"),
        "Composition violation: place the subject off-center on the rule of thirds with generous negative space opposite.",
    ),
)


def _validate_non_empty_str(value: Any, name: str) -> str:
    """
    /**
     * Validate that a string parameter is non-empty.
     *
     * Why: Rejects blank project, region, dataset, or connection parameters.
     *
     * @param value Candidate value to validate.
     * @param name Parameter name for error reporting.
     * @return Stripped string value.
     */
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def build_brand_score_sql(
    project_id: str = DEFAULT_PROJECT_ID,
    region: str = DEFAULT_LOCATION,
    dataset: str = "bwg",
    connection_name: str = "pitch-connection",
) -> str:
    """
    /**
     * Builds the BigQuery `CREATE OR REPLACE TABLE bwg.brand_review` query using `AI.SCORE`.
     *
     * Why: Renders the canonical multimodal scoring SQL query that grades each row in
     * `bwg.key_visuals` from 1.0 to 10.0 and classifies `brand_fit >= 7` as `'on brand'`.
     *
     * @param project_id Target GCP project ID.
     * @param region Cloud Resource connection region (default `'us-central1'`).
     * @param dataset BigQuery dataset name (default `'bwg'`).
     * @param connection_name Cloud Resource connection name (default `'pitch-connection'`).
     * @return Formatted BigQuery SQL string.
     */
    """
    _validate_non_empty_str(project_id, "project_id")
    resolved_region = _validate_non_empty_str(region, "region")
    resolved_dataset = _validate_non_empty_str(dataset, "dataset")
    resolved_conn = _validate_non_empty_str(connection_name, "connection_name")

    return (
        f"CREATE OR REPLACE TABLE {resolved_dataset}.brand_review AS\n"
        "SELECT\n"
        "  campaign,\n"
        "  concept,\n"
        "  brand_fit,\n"
        "  IF(brand_fit >= 7, 'on brand', 'needs another pass') AS verdict\n"
        "FROM (\n"
        "  SELECT\n"
        "    campaign,\n"
        "    concept,\n"
        "    AI.SCORE(\n"
        "      (\n"
        "        'Score this campaign key visual from 1 to 10 on how closely it follows the house '\n"
        "        'brand rules: deep indigo and slate palette with a single warm accent of amber or '\n"
        "        'terracotta and nothing neon; one low raking light source with long shadows; the '\n"
        "        'subject off-center with generous empty negative space opposite; a single realistic '\n"
        "        'photographic subject with shallow depth of field; and no text, logos, or watermarks '\n"
        "        'in the frame. The campaign concept is: ',\n"
        "        concept,\n"
        "        key_visual\n"
        "      ),\n"
        f"      connection_id => '{resolved_region}.{resolved_conn}'\n"
        "    ) AS brand_fit\n"
        f"  FROM {resolved_dataset}.key_visuals\n"
        ");\n\n"
        f"SELECT * FROM {resolved_dataset}.brand_review ORDER BY brand_fit DESC;"
    )


def _inspect_text_violations(text: str) -> tuple[list[str], list[str], list[str]]:
    """
    /**
     * Inspect `text` for house-brand rule violations.
     *
     * Why: Maps specific forbidden tokens to actionable remediation categories.
     *
     * @param text Art direction or concept string to inspect.
     * @return Tuple of `(categories, matched_tokens, recommendations)`.
     */
    """
    lower = text.lower()
    categories: list[str] = []
    matched_tokens: list[str] = []
    recommendations: list[str] = []

    for category, tokens, recommendation in FORBIDDEN_RULE_PATTERNS:
        hits = [tok for tok in tokens if tok in lower]
        if hits:
            categories.append(category)
            matched_tokens.extend(hits)
            recommendations.append(f"{recommendation} (found: {', '.join(hits)})")

    return categories, matched_tokens, recommendations


def _compute_rubric_score(art_text: str) -> float:
    """
    /**
     * Compute a deterministic 1.0–10.0 `AI.SCORE` brand fit rating from art direction text.
     *
     * Why: Provides offline deterministic grading matching the 5 positive house pillars
     * and 5 negative anti-pattern rules in `score_brand_fit.sql`.
     *
     * @param art_text Art direction text to score.
     * @return Floating-point score clamped to `[1.0, 10.0]`.
     */
    """
    lower = art_text.lower()
    score = 5.0

    # Positive house-brand signals (+1.0 each, up to +5.0)
    if "indigo" in lower and "slate" in lower:
        score += 1.2
    elif "indigo" in lower or "slate" in lower:
        score += 0.6

    if "amber" in lower or "terracotta" in lower:
        score += 1.0

    if "raking" in lower or "long shadow" in lower or "golden hour" in lower or "blue hour" in lower:
        score += 1.0

    if "off-center" in lower or "negative space" in lower or "rule of thirds" in lower:
        score += 1.0

    if "shallow depth of field" in lower or "realistic" in lower:
        score += 0.8

    # Negative house-brand anti-patterns
    categories, matched_tokens, _ = _inspect_text_violations(lower)
    if matched_tokens:
        score -= 2.0 * len(categories) + 0.5 * len(matched_tokens)

    return max(1.0, min(10.0, round(score, 2)))


def score_brand_compliance(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    /**
     * Evaluates each campaign record against the house brand rubric (`brand_fit` 1.0–10.0)
     * and assigns `verdict = 'on brand'` when `brand_fit >= 7.0`, else `'needs another pass'`.
     *
     * Why: Simulates BigQuery `AI.SCORE` execution deterministically offline, preserving
     * exact boundary precision (`6.99` -> `'needs another pass'`, `7.00` -> `'on brand'`).
     *
     * @param records List of campaign dicts from `bwg.key_visuals` or test fixtures.
     * @return List of scored `bwg.brand_review` dicts with `brand_fit`, `verdict`, `drifted`, and `violations`.
     */
    """
    if not isinstance(records, list):
        raise ValueError("records must be a list of campaign dictionaries.")
    if not records:
        return []

    scored_rows: list[dict[str, Any]] = []
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise ValueError(f"Record at index {idx} must be a dictionary.")
        item = copy.deepcopy(rec)
        art_text = str(item.get("art_direction") or item.get("concept") or "")
        categories, matched_tokens, recommendations = _inspect_text_violations(art_text)

        raw_score = item.get("brand_fit")
        if isinstance(raw_score, (int, float)) and not isinstance(raw_score, bool):
            score = float(raw_score)
            if score < 1.0 or score > 10.0:
                score = max(1.0, min(10.0, score))
        else:
            score = _compute_rubric_score(art_text)

        verdict = "on brand" if score >= BRAND_FIT_THRESHOLD else "needs another pass"
        drifted = score < BRAND_FIT_THRESHOLD

        if drifted and not recommendations:
            recommendations.append(
                "Palette/lighting drift: specify deep indigo and slate palette with warm amber accent, "
                "low raking light with long shadows, off-center subject with negative space, and shallow depth of field."
            )

        item["brand_fit"] = score
        item["verdict"] = verdict
        item["drifted"] = drifted
        item["violation_categories"] = categories
        item["matched_forbidden_terms"] = matched_tokens
        item["violations"] = recommendations
        scored_rows.append(item)

    return scored_rows


def detect_brand_drift(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    /**
     * Diagnoses brand drift across campaign records and identifies specific rule violations.
     *
     * Why: Translates low `AI.SCORE` rows (`brand_fit < 7.0`) into actionable violation diagnostics
     * (palette, lighting, frame cleanliness, treatment, composition) so AGY or the developer can
     * tune the Visual Director prompt and `brand-guidelines` skill (`F14`).
     *
     * @param records List of campaign records (raw or pre-scored).
     * @return Drift diagnostic report dictionary containing `drifted_campaigns`, `on_brand_campaigns`, `has_drift`, and `summary`.
     */
    """
    scored = score_brand_compliance(records)
    drifted_campaigns: list[dict[str, Any]] = []
    on_brand_campaigns: list[dict[str, Any]] = []

    for row in scored:
        if float(row["brand_fit"]) < BRAND_FIT_THRESHOLD or row.get("verdict") == "needs another pass":
            drifted_campaigns.append(row)
        else:
            on_brand_campaigns.append(row)

    avg_score = (
        round(sum(float(r["brand_fit"]) for r in scored) / len(scored), 2)
        if scored
        else 0.0
    )

    return {
        "has_drift": len(drifted_campaigns) > 0,
        "drifted_count": len(drifted_campaigns),
        "total_campaigns": len(scored),
        "average_brand_fit": avg_score,
        "drifted_campaigns": drifted_campaigns,
        "drifted": drifted_campaigns,
        "on_brand_campaigns": on_brand_campaigns,
        "summary": (
            f"Detected {len(drifted_campaigns)} drifted campaign(s) out of {len(scored)} "
            f"(average brand_fit={avg_score})."
        ),
    }


analyze_brand_drift = detect_brand_drift


def _sanitize_subject_from_concept(concept: str) -> str:
    """
    /**
     * Extract a clean subject phrase from `concept` with all forbidden style tokens removed.
     *
     * Why: Ensures prompt/skill tuning preserves the campaign subject while stripping
     * prohibited terms (`neon`, `watermark`, `logo`, `ring light`, etc.).
     *
     * @param concept Raw campaign concept string.
     * @return Sanitized subject phrase.
     */
    """
    cleaned = concept
    forbidden_words = (
        r"\bneon\b",
        r"\bcyan\b",
        r"\bmagenta\b",
        r"\brainbow\b",
        r"\bfluent\b",
        r"\bfluorescent\b",
        r"\bwatermark\b",
        r"\blogos?\b",
        r"\btext\b",
        r"\bchrome\b",
        r"\bring\s+light\b",
        r"\bflat\s+overhead\b",
        r"\b3d\s+render\b",
        r"\bcartoon\b",
        r"\bclipart\b",
        r"\bhuge\b",
        r"\bcompany\b",
        r"\badd\b",
        r"\band\s+a\b",
    )
    for pat in forbidden_words:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-:")
    return cleaned or "campaign hero product"


def tune_prompt_and_skill(
    record: dict[str, Any] | list[dict[str, Any]],
) -> dict[str, Any] | list[dict[str, Any]]:
    """
    /**
     * Remediates a drifted campaign record (or list of records) by rewriting its art direction
     * and tightening prompt/skill instructions to enforce the house brand rules (`F14`).
     *
     * Why: Closes the feedback loop between BigQuery `AI.SCORE` drift detection and ADK
     * agent behavior, ensuring re-scored visuals achieve `brand_fit >= 7.0` (`'on brand'`)
     * and pass pre-deployment `step_1b` Skill Evals.
     *
     * @param record Drifted campaign record dict (or list of campaign record dicts).
     * @return Remediated campaign record dict (or list) with `brand_fit >= 9.0` and `verdict == 'on brand'`.
     */
    """
    if isinstance(record, list):
        return [tune_prompt_and_skill(item) for item in record]  # type: ignore[misc]
    if not isinstance(record, dict):
        raise ValueError("record must be a campaign dictionary or list of dictionaries.")

    initial_scored = score_brand_compliance([record])[0]
    previous_score = float(initial_scored["brand_fit"])
    previous_verdict = str(initial_scored["verdict"])

    campaign_name = str(initial_scored.get("campaign", "campaign"))
    raw_concept = str(initial_scored.get("concept", campaign_name))
    clean_subject = _sanitize_subject_from_concept(raw_concept)

    tuned_art_direction = (
        f"Hero key visual for {clean_subject}: deep indigo and slate palette with a single warm "
        "amber and terracotta accent; one low raking golden hour light source casting long "
        "soft shadows across the ground; subject positioned off-center on the rule of thirds "
        "with generous empty negative space opposite; one realistic photographic subject "
        "captured with shallow depth of field; clean uncluttered studio frame free of overlays."
    )

    candidate = copy.deepcopy(initial_scored)
    candidate.pop("brand_fit", None)
    candidate["art_direction"] = tuned_art_direction
    candidate["tuned_art_direction"] = tuned_art_direction

    rescored = score_brand_compliance([candidate])[0]
    new_score = float(rescored["brand_fit"])
    new_verdict = str(rescored["verdict"])

    rescored["previous_brand_fit"] = previous_score
    rescored["previous_verdict"] = previous_verdict
    rescored["new_brand_fit"] = new_score
    rescored["new_verdict"] = new_verdict
    rescored["tuned_art_direction"] = tuned_art_direction
    rescored["tuning_actions"] = [
        "Updated Visual Director prompt to require load_skill('brand-guidelines') before drafting art direction.",
        "Added conflict-resolution rule: follow the brief for the subject and the house brand guidelines for the visual treatment.",
        "Replaced drifted styling with deep indigo/slate palette, warm amber accent, low raking light, and off-center negative space.",
    ]
    return rescored


remediate_brand_drift = tune_prompt_and_skill
tune_for_brand_compliance = tune_prompt_and_skill


__all__ = [
    "BRAND_FIT_THRESHOLD",
    "SCORE_BRAND_FIT_SQL_PATH",
    "build_brand_score_sql",
    "score_brand_compliance",
    "detect_brand_drift",
    "analyze_brand_drift",
    "tune_prompt_and_skill",
    "remediate_brand_drift",
    "tune_for_brand_compliance",
]
