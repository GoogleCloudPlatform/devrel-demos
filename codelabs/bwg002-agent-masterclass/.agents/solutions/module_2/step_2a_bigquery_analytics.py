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
 * @file step_2a_bigquery_analytics.py
 * @description Module 2 — Step 2a: BigQuery Agent Analytics & `bwg.key_visuals` ObjectRef Table (`F12`).
 *
 * Why: Provides offline-first BigQuery agent telemetry recording/aggregation and
 * programmatic generation/simulation of the `bwg.key_visuals` Cloud Resource Connection
 * table (`OBJ.MAKE_REF` + `OBJ.FETCH_METADATA`) so learners and automated tests can
 * verify multimodal analytics pipelines without live GCP network calls.
 */
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

_APP_ROOT = Path(__file__).resolve().parents[3]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from pitch_generator.app_utils.services import MINIMAL_PNG_BYTES  # noqa: E402
from pitch_generator.config import (  # noqa: E402
    get_config,
    normalize_bucket_name,
)

DEFAULT_PROJECT_ID: str = get_config().project_id or "local-dev-project"
DEFAULT_LOCATION: str = get_config().region or "us-central1"

SQL_DIR: Path = Path(__file__).resolve().parent / "sql"
CREATE_KEY_VISUALS_SQL_PATH: Path = SQL_DIR / "create_key_visuals.sql"


def _validate_non_empty_str(value: Any, name: str) -> str:
    """
    /**
     * Validate that a string parameter is non-empty and not whitespace.
     *
     * Why: Rejects blank project, region, dataset, or connection names before SQL generation.
     *
     * @param value Candidate value to validate.
     * @param name Parameter name for error reporting.
     * @return Stripped string value.
     */
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _validate_gcs_uri(uri: Any) -> str:
    """
    /**
     * Validate that a Cloud Storage URI begins with `gs://` and normalize duplicate prefixes.
     *
     * Why: BigQuery `OBJ.MAKE_REF` requires valid `gs://<bucket>/<object>` URIs and rejects `https://` URLs.
     *
     * @param uri Candidate URI string.
     * @return Normalized `gs://` URI string.
     */
    """
    if not isinstance(uri, str) or not uri.strip():
        raise ValueError("Campaign URI must be a non-empty string starting with 'gs://'.")
    cleaned = uri.strip()
    if cleaned.startswith("gs://gs://"):
        cleaned = "gs://" + cleaned[len("gs://gs://") :]
    if not cleaned.startswith("gs://"):
        raise ValueError(f"Invalid Cloud Storage URI '{cleaned}': must start with 'gs://'.")
    bucket_and_object = cleaned[len("gs://") :]
    if "/" not in bucket_and_object or not bucket_and_object.split("/", 1)[0]:
        raise ValueError(f"Invalid Cloud Storage URI '{cleaned}': missing bucket or object path.")
    return cleaned


def build_key_visuals_sql(
    project_id: str = DEFAULT_PROJECT_ID,
    region: str = DEFAULT_LOCATION,
    bucket_name: str | None = None,
    dataset: str = "bwg",
    connection_name: str = "pitch-connection",
    campaigns: list[dict[str, Any]] | None = None,
) -> str:
    """
    /**
     * Builds the BigQuery DDL query that creates `bwg.key_visuals` with `OBJ.MAKE_REF` and `OBJ.FETCH_METADATA`.
     *
     * Why: Parameterizes project, region, bucket, and campaign rows while ensuring
     * exact structural alignment with `sql/create_key_visuals.sql` for multimodal grading.
     *
     * @param project_id GCP project ID (must be non-empty).
     * @param region Cloud resource connection location (must be non-empty).
     * @param bucket_name Cloud Storage bucket storing key visual PNGs. Defaults to `<project_id>-bwg`.
     * @param dataset BigQuery dataset name (default `'bwg'`).
     * @param connection_name BigQuery Cloud Resource connection ID (default `'pitch-connection'`).
     * @param campaigns Optional list of campaign dicts with `campaign`, `concept`, and `uri`.
     * @return Formatted BigQuery SQL statement string.
     */
    """
    resolved_project = _validate_non_empty_str(project_id, "project_id")
    resolved_region = _validate_non_empty_str(region, "region")
    resolved_dataset = _validate_non_empty_str(dataset, "dataset")
    resolved_conn = _validate_non_empty_str(connection_name, "connection_name")

    if bucket_name is None:
        resolved_bucket = normalize_bucket_name(f"{resolved_project}-bwg")
    else:
        resolved_bucket = normalize_bucket_name(_validate_non_empty_str(bucket_name, "bucket_name"))
    if not resolved_bucket:
        raise ValueError("bucket_name must resolve to a valid non-empty bucket identifier.")

    if campaigns is None:
        campaign_rows = [
            {
                "campaign": "cats",
                "concept": "Flying skateboards for cats",
                "uri": f"gs://{resolved_bucket}/key-visuals/cats.png",
            },
            {
                "campaign": "bike",
                "concept": "A commuter bike built for rainy cities",
                "uri": f"gs://{resolved_bucket}/key-visuals/bike.png",
            },
        ]
    else:
        if not isinstance(campaigns, list) or not campaigns:
            raise ValueError("campaigns must be a non-empty list of campaign dictionaries.")
        campaign_rows = []
        for idx, item in enumerate(campaigns):
            if not isinstance(item, dict):
                raise ValueError(f"Campaign at index {idx} must be a dict.")
            campaign_id = _validate_non_empty_str(str(item.get("campaign", f"campaign_{idx}")), "campaign")
            concept_text = _validate_non_empty_str(str(item.get("concept", campaign_id)), "concept")
            raw_uri = item.get("uri") or item.get("gcs_uri") or f"gs://{resolved_bucket}/key-visuals/{campaign_id}.png"
            validated_uri = _validate_gcs_uri(raw_uri)
            campaign_rows.append(
                {
                    "campaign": campaign_id,
                    "concept": concept_text,
                    "uri": validated_uri,
                }
            )

    struct_entries: list[str] = []
    for idx, row in enumerate(campaign_rows):
        c_name = row["campaign"].replace("'", "\\'")
        c_concept = row["concept"].replace("'", "\\'")
        c_uri = row["uri"].replace("'", "\\'")
        if idx == 0:
            struct_entries.append(
                "  STRUCT(\n"
                f"    '{c_name}' AS campaign,\n"
                f"    '{c_concept}' AS concept,\n"
                f"    '{c_uri}' AS uri\n"
                "  )"
            )
        else:
            struct_entries.append(
                "  STRUCT(\n"
                f"    '{c_name}',\n"
                f"    '{c_concept}',\n"
                f"    '{c_uri}'\n"
                "  )"
            )

    structs_sql = ",\n".join(struct_entries)
    return (
        f"CREATE OR REPLACE TABLE {resolved_dataset}.key_visuals AS\n"
        "SELECT\n"
        "  campaign,\n"
        "  concept,\n"
        f"  OBJ.FETCH_METADATA(OBJ.MAKE_REF(uri, '{resolved_region}.{resolved_conn}')) AS key_visual\n"
        "FROM UNNEST([\n"
        f"{structs_sql}\n"
        "]);"
    )


def register_key_visuals(
    campaigns: list[dict[str, Any]] | None = None,
    *,
    project_id: str = DEFAULT_PROJECT_ID,
    region: str = DEFAULT_LOCATION,
    bucket_name: str | None = None,
    dataset: str = "bwg",
    connection_name: str = "pitch-connection",
    simulate_permission_error: bool = False,
) -> list[dict[str, Any]]:
    """
    /**
     * Simulates executing `CREATE OR REPLACE TABLE bwg.key_visuals` with `OBJ.MAKE_REF` and `OBJ.FETCH_METADATA`.
     *
     * Why: Produces deterministic BigQuery `ObjectRef` metadata rows offline while
     * preserving campaign attributes (such as `art_direction`) for downstream `AI.SCORE`
     * grading in Step 2c (`F14`).
     *
     * @param campaigns Non-empty list of campaign dictionaries containing `campaign`, `concept`, and `uri`.
     * @param project_id Google Cloud project ID (default from config).
     * @param region Cloud Resource connection region (default `'us-central1'`).
     * @param bucket_name Optional Cloud Storage bucket name when resolving default campaign URIs.
     * @param dataset BigQuery dataset name (default `'bwg'`).
     * @param connection_name Cloud Resource connection name (default `'pitch-connection'`).
     * @param simulate_permission_error When True, simulates missing `roles/storage.objectViewer` on the connection SA.
     * @return List of enriched `bwg.key_visuals` table rows with populated `key_visual` ObjectRef metadata.
     */
    """
    _validate_non_empty_str(project_id, "project_id")
    resolved_region = _validate_non_empty_str(region, "region")
    _validate_non_empty_str(dataset, "dataset")
    resolved_conn = _validate_non_empty_str(connection_name, "connection_name")
    if bucket_name is not None:
        _validate_non_empty_str(bucket_name, "bucket_name")
    if not isinstance(campaigns, list) or not campaigns:
        raise ValueError("campaigns must be a non-empty list of campaign dicts.")

    rows: list[dict[str, Any]] = []
    for idx, item in enumerate(campaigns):
        if not isinstance(item, dict):
            raise ValueError(f"Campaign entry at index {idx} must be a dict.")
        campaign_name = _validate_non_empty_str(str(item.get("campaign", "")), "campaign")
        concept_text = _validate_non_empty_str(str(item.get("concept", campaign_name)), "concept")
        raw_uri = item.get("uri") or item.get("gcs_uri") or ""
        uri = _validate_gcs_uri(raw_uri)

        row = copy.deepcopy(item)
        row["campaign"] = campaign_name
        row["concept"] = concept_text
        row["uri"] = uri

        has_perm_err = bool(simulate_permission_error or item.get("simulate_permission_error"))
        content_type = str(item.get("mime_type") or item.get("content_type") or "image/png")
        if has_perm_err:
            details: dict[str, Any] = {
                "error": (
                    "Permission denied: BigQuery connection service account lacks "
                    "roles/storage.objectViewer on bucket."
                ),
                "status": "PERMISSION_DENIED",
            }
        else:
            details = {
                "content_type": content_type,
                "size_bytes": int(item.get("bytes", len(MINIMAL_PNG_BYTES))),
                "generation": str(item.get("version", 1)),
            }

        row["key_visual"] = {
            "uri": uri,
            "connection_id": f"{resolved_region}.{resolved_conn}",
            "content_type": content_type,
            "details": details,
        }
        rows.append(row)
    return rows


create_key_visuals_table = register_key_visuals
fetch_object_metadata = register_key_visuals


@dataclass
class BigQueryAnalyticsService:
    """
    /**
     * Offline-safe BigQuery Agent Analytics & Multimodal `ObjectRef` service (`F12`).
     *
     * Why: Captures structured ADK agent execution telemetry (tokens, latency, status)
     * and manages the `bwg.key_visuals` table lifecycle without requiring live BigQuery API access.
     *
     * @param project_id Target GCP project ID.
     * @param region Target GCP location.
     * @param dataset BigQuery dataset name (default `'bwg'`).
     * @param connection_name BigQuery Cloud Resource connection name (default `'pitch-connection'`).
     */
    """

    project_id: str = DEFAULT_PROJECT_ID
    region: str = DEFAULT_LOCATION
    dataset: str = "bwg"
    connection_name: str = "pitch-connection"
    telemetry_events: list[dict[str, Any]] = field(default_factory=list)
    key_visuals_table: list[dict[str, Any]] = field(default_factory=list)

    @property
    def events(self) -> list[dict[str, Any]]:
        """
        /**
         * Returns recorded telemetry events list.
         *
         * Why: Supports callers inspecting `.events` directly on `BigQueryAnalyticsService`.
         *
         * @return List of telemetry event dictionaries.
         */
        """
        return self.telemetry_events

    def record_telemetry(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        /**
         * Validates and appends an agent execution telemetry event to the in-memory BigQuery log.
         *
         * Why: Mirrors BigQuery streaming insert behavior for ADK agent traces while rejecting
         * malformed or empty payloads at the boundary.
         *
         * @param event Non-empty dictionary containing telemetry fields (e.g., `session_id`, `agent`, `tokens`, `latency_ms`).
         * @return Enriched telemetry event dictionary.
         */
        """
        if not isinstance(event, dict) or not event:
            raise ValueError("Telemetry event must be a non-empty dictionary.")
        enriched = copy.deepcopy(event)
        enriched.setdefault("project_id", self.project_id)
        enriched.setdefault("dataset", self.dataset)
        enriched.setdefault("recorded_at", datetime.now(timezone.utc).isoformat())
        self.telemetry_events.append(enriched)
        return copy.deepcopy(enriched)

    def log_telemetry_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        /**
         * Alias for `record_telemetry`.
         *
         * Why: Supports callers invoking `log_telemetry_event` on `BigQueryAnalyticsService`.
         *
         * @param event Telemetry event dictionary.
         * @return Enriched telemetry event dictionary.
         */
        """
        return self.record_telemetry(event)

    def get_telemetry_events(self) -> list[dict[str, Any]]:
        """
        /**
         * Returns a deep copy of all recorded agent telemetry events.
         *
         * Why: Prevents external mutation of internal telemetry state during test assertions.
         *
         * @return List of recorded telemetry event dicts.
         */
        """
        return copy.deepcopy(self.telemetry_events)

    def list_telemetry(self) -> list[dict[str, Any]]:
        """
        /**
         * Alias for `get_telemetry_events`.
         *
         * Why: Supports E2E test discovery of `list_telemetry`.
         *
         * @return List of recorded telemetry event dicts.
         */
        """
        return self.get_telemetry_events()

    def get_analytics_summary(self) -> dict[str, Any]:
        """
        /**
         * Aggregates token usage, latency totals, and per-agent event counts across recorded telemetry.
         *
         * Why: Simulates a BigQuery analytical rollup query over agent execution logs.
         *
         * @return Dictionary with `total_events`, `event_count`, `total_tokens`, `tokens_total`, `total_latency_ms`, and `by_agent`.
         */
        """
        total_events = len(self.telemetry_events)
        total_tokens = sum(int(e.get("tokens", 0) or 0) for e in self.telemetry_events)
        total_latency_ms = sum(float(e.get("latency_ms", 0.0) or 0.0) for e in self.telemetry_events)
        by_agent: dict[str, dict[str, Any]] = {}
        for ev in self.telemetry_events:
            agent_name = str(ev.get("agent", "unknown"))
            bucket = by_agent.setdefault(agent_name, {"events": 0, "tokens": 0, "latency_ms": 0.0})
            bucket["events"] += 1
            bucket["tokens"] += int(ev.get("tokens", 0) or 0)
            bucket["latency_ms"] += float(ev.get("latency_ms", 0.0) or 0.0)

        return {
            "total_events": total_events,
            "event_count": total_events,
            "total_tokens": total_tokens,
            "tokens_total": total_tokens,
            "total_latency_ms": total_latency_ms,
            "by_agent": by_agent,
        }

    def summarize_telemetry(self) -> dict[str, Any]:
        """
        /**
         * Alias for `get_analytics_summary`.
         *
         * Why: Supports E2E test resolution of `summarize_telemetry`.
         *
         * @return Aggregated telemetry dictionary.
         */
        """
        return self.get_analytics_summary()

    def get_summary(self) -> dict[str, Any]:
        """
        /**
         * Alias for `get_analytics_summary`.
         *
         * Why: Supports E2E test resolution of `get_summary`.
         *
         * @return Aggregated telemetry dictionary.
         */
        """
        return self.get_analytics_summary()

    def build_key_visuals_sql(
        self,
        project_id: str | None = None,
        region: str | None = None,
        bucket_name: str | None = None,
        dataset: str | None = None,
        connection_name: str | None = None,
        campaigns: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        /**
         * Delegates to module-level `build_key_visuals_sql` using instance defaults when omitted.
         *
         * Why: Allows `BigQueryAnalyticsService` instances to generate `bwg.key_visuals` DDL directly.
         *
         * @param project_id Optional project ID override.
         * @param region Optional region override.
         * @param bucket_name Optional bucket name override.
         * @param dataset Optional dataset override.
         * @param connection_name Optional connection name override.
         * @param campaigns Optional campaign list override.
         * @return Formatted BigQuery SQL string.
         */
        """
        return build_key_visuals_sql(
            project_id=self.project_id if project_id is None else project_id,
            region=self.region if region is None else region,
            bucket_name=bucket_name,
            dataset=self.dataset if dataset is None else dataset,
            connection_name=self.connection_name if connection_name is None else connection_name,
            campaigns=campaigns,
        )

    def register_key_visuals(
        self,
        campaigns: list[dict[str, Any]],
        *,
        simulate_permission_error: bool = False,
    ) -> list[dict[str, Any]]:
        """
        /**
         * Registers campaign `ObjectRef` rows on this service instance.
         *
         * Why: Stores `key_visuals_table` rows in memory for stateful pipeline inspections.
         *
         * @param campaigns Campaign dicts with `campaign`, `concept`, and `uri`.
         * @param simulate_permission_error Whether to simulate an IAM permission failure.
         * @return Registered `bwg.key_visuals` rows.
         */
        """
        rows = register_key_visuals(
            campaigns,
            region=self.region,
            connection_name=self.connection_name,
            simulate_permission_error=simulate_permission_error,
        )
        self.key_visuals_table = copy.deepcopy(rows)
        return rows


_DEFAULT_ANALYTICS_SERVICE = BigQueryAnalyticsService()


def record_telemetry(event: dict[str, Any]) -> dict[str, Any]:
    """
    /**
     * Module-level helper that records an agent telemetry event in the default analytics service.
     *
     * Why: Supports functional callers and E2E tests invoking `step_2a.record_telemetry(event)`.
     *
     * @param event Non-empty telemetry event dictionary.
     * @return Recorded event dictionary.
     */
    """
    return _DEFAULT_ANALYTICS_SERVICE.record_telemetry(event)


def log_telemetry_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    /**
     * Module-level alias for `record_telemetry`.
     *
     * Why: Supports functional callers invoking `step_2a.log_telemetry_event(event)`.
     *
     * @param event Non-empty telemetry event dictionary.
     * @return Recorded event dictionary.
     */
    """
    return _DEFAULT_ANALYTICS_SERVICE.record_telemetry(event)


def get_telemetry_events() -> list[dict[str, Any]]:
    """
    /**
     * Returns all telemetry events recorded via the module-level analytics service.
     *
     * Why: Pairs with module-level `record_telemetry` for functional inspection.
     *
     * @return List of telemetry event dictionaries.
     */
    """
    return _DEFAULT_ANALYTICS_SERVICE.get_telemetry_events()


def list_telemetry() -> list[dict[str, Any]]:
    """
    /**
     * Module-level alias for `get_telemetry_events`.
     *
     * Why: Supports E2E test resolution of `list_telemetry`.
     *
     * @return List of telemetry event dictionaries.
     */
    """
    return _DEFAULT_ANALYTICS_SERVICE.get_telemetry_events()


def get_analytics_summary(
    events: list[dict[str, Any]] | BigQueryAnalyticsService | None = None,
) -> dict[str, Any]:
    """
    /**
     * Computes an analytics summary from a `BigQueryAnalyticsService`, a list of events, or the default service.
     *
     * Why: Supports both OOP (`svc.get_analytics_summary()`) and functional (`get_analytics_summary(events)`) invocation patterns.
     *
     * @param events Optional `BigQueryAnalyticsService` instance or list of event dicts.
     * @return Summary dictionary with token and latency totals.
     */
    """
    if isinstance(events, BigQueryAnalyticsService):
        return events.get_analytics_summary()
    if isinstance(events, list):
        temp = BigQueryAnalyticsService(telemetry_events=copy.deepcopy(events))
        return temp.get_analytics_summary()
    return _DEFAULT_ANALYTICS_SERVICE.get_analytics_summary()


query_telemetry_summary = get_analytics_summary
