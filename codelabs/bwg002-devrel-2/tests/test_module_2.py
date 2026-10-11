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
 * @file test_module_2.py
 * @description Offline unit tests for Module 2 reference solutions (`F12`, `F14`):
 *   Step 2a BigQuery Agent Analytics & `bwg.key_visuals` (`step_2a_bigquery_analytics.py`),
 *   Step 2b Multimodal Brand Drift Detection & Prompt/Skill Tuning (`step_2b_drift_detection_and_tuning.py`),
 *   and SQL scripts (`create_key_visuals.sql`, `score_brand_fit.sql`).
 *
 * Why: Verifies that every Module 2 deliverable satisfies all happy-path, boundary, and
 * cross-step data contracts offline with zero live GCP calls.
 */
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest

APP_ROOT: Path = Path(__file__).resolve().parents[1]
MODULE_2_DIR: Path = APP_ROOT / ".agents" / "solutions" / "module_2"


def _load_module_2_file(filename: str) -> ModuleType:
    """
    /**
     * Load a Python module from `.agents/solutions/module_2/` by filename.
     *
     * Why: Dynamically imports Module 2 reference solutions for isolated unit verification.
     *
     * @param filename Name of the Python file inside `.agents/solutions/module_2/`.
     * @return Loaded Python module object.
     */
    """
    target = MODULE_2_DIR / filename
    module_name = f"solutions_module_2_{target.stem}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, target)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestModule2Step2aBigQueryAnalytics(unittest.TestCase):
    """
    /**
     * Unit tests for Step 2a (`F12`): `step_2a_bigquery_analytics.py` and `sql/create_key_visuals.sql`.
     *
     * Why: Ensures BigQuery `ObjectRef` SQL generation, URI validation, permission-error
     * simulation, and agent telemetry aggregation work deterministically offline.
     */
    """

    def test_create_key_visuals_sql_file_and_builder(self) -> None:
        """
        /**
         * Verifies `sql/create_key_visuals.sql` and `build_key_visuals_sql` emit `OBJ.FETCH_METADATA(OBJ.MAKE_REF(`.
         *
         * Why: Confirms exact DDL alignment with the BigQuery multimodal ObjectRef pattern.
         *
         * @return None.
         */
        """
        sql_file = MODULE_2_DIR / "sql" / "create_key_visuals.sql"
        self.assertTrue(sql_file.is_file())
        sql_text = sql_file.read_text(encoding="utf-8")
        self.assertIn("CREATE OR REPLACE TABLE bwg.key_visuals", sql_text)
        self.assertIn("OBJ.FETCH_METADATA(OBJ.MAKE_REF(", sql_text)

        step_2a = _load_module_2_file("step_2a_bigquery_analytics.py")
        rendered = step_2a.build_key_visuals_sql(
            project_id="unit-proj",
            region="us-central1",
            bucket_name="gs://unit-proj-bwg/",
        )
        self.assertIn("OBJ.FETCH_METADATA(OBJ.MAKE_REF(", rendered)
        self.assertIn("gs://unit-proj-bwg/key-visuals/cats.png", rendered)
        self.assertNotIn("gs://gs://", rendered)

    def test_step_2a_boundary_validations_and_telemetry(self) -> None:
        """
        /**
         * Verifies `step_2a` rejects empty project/region, non-`gs://` URIs, and empty telemetry dicts.
         *
         * Why: Guards BigQuery analytics helpers against misconfigured environment variables.
         *
         * @return None.
         */
        """
        step_2a = _load_module_2_file("step_2a_bigquery_analytics.py")
        with self.assertRaises(ValueError):
            step_2a.build_key_visuals_sql(project_id="", region="us-central1", bucket_name="b")
        with self.assertRaises(ValueError):
            step_2a.register_key_visuals(
                [{"campaign": "cats", "concept": "Cats", "uri": "https://example.com/cats.png"}]
            )

        svc = step_2a.BigQueryAnalyticsService()
        with self.assertRaises(ValueError):
            svc.record_telemetry({})
        svc.record_telemetry({"agent": "creative_director", "tokens": 210, "latency_ms": 95})
        summary = svc.get_analytics_summary()
        self.assertEqual(summary["total_events"], 1)
        self.assertEqual(summary["total_tokens"], 210)


class TestModule2Step2bDriftDetectionAndTuning(unittest.TestCase):
    """
    /**
     * Unit tests for Step 2b (`F14`): `step_2b_drift_detection_and_tuning.py` and `sql/score_brand_fit.sql`.
     *
     * Why: Validates `AI.SCORE` SQL generation, exact `6.99` vs `7.00` threshold classification,
     * drift violation diagnostics, and closed-loop prompt/skill remediation.
     */
    """

    def test_score_brand_compliance_boundaries_and_tuning(self) -> None:
        """
        /**
         * Verifies `6.99` is `'needs another pass'`, `7.00` is `'on brand'`, and `tune_prompt_and_skill` restores compliance.
         *
         * Why: Tests the exact `IF(brand_fit >= 7, 'on brand', 'needs another pass')` threshold and remediation loop.
         *
         * @return None.
         */
        """
        sql_file = MODULE_2_DIR / "sql" / "score_brand_fit.sql"
        self.assertTrue(sql_file.is_file())
        self.assertIn(
            "IF(brand_fit >= 7, 'on brand', 'needs another pass') AS verdict",
            sql_file.read_text(encoding="utf-8"),
        )

        step_2b = _load_module_2_file("step_2b_drift_detection_and_tuning.py")
        scored = step_2b.score_brand_compliance(
            [
                {"campaign": "low", "concept": "Low", "brand_fit": 6.99},
                {"campaign": "high", "concept": "High", "brand_fit": 7.00},
            ]
        )
        self.assertEqual(scored[0]["verdict"], "needs another pass")
        self.assertEqual(scored[1]["verdict"], "on brand")

        drifted = {
            "campaign": "cats",
            "concept": "Flying skateboards for cats",
            "art_direction": "Neon cyan cat with watermark logo and flat overhead ring light.",
        }
        report = step_2b.detect_brand_drift([drifted])
        self.assertTrue(report["has_drift"])
        tuned = step_2b.tune_prompt_and_skill(drifted)
        self.assertGreaterEqual(float(tuned["brand_fit"]), 7.0)
        self.assertEqual(tuned["verdict"], "on brand")


if __name__ == "__main__":
    unittest.main()
