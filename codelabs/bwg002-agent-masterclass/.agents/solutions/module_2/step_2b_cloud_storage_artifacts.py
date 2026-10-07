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
 * @file step_2b_cloud_storage_artifacts.py
 * @description Module 2 — Step 2b: Cloud Storage Artifact Versioning & Persistence (`F13`).
 *
 * Why: Replaces ephemeral `InMemoryArtifactService` storage with `GcsArtifactService`
 * when `LOGS_BUCKET_NAME` is configured so key visual PNGs (`cats.png`, `bike.png`, etc.)
 * receive deterministic `gs://<bucket>/key-visuals/<filename>` URIs and monotonic
 * per-session version tracking (`version = 1, 2, ...`) for BigQuery multimodal audits.
 */
"""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import sys
from typing import Any

_APP_ROOT = Path(__file__).resolve().parents[3]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from pitch_generator.agent import run_pitch_workflow  # noqa: E402
from pitch_generator.app_utils.services import (  # noqa: E402
    MINIMAL_PNG_BYTES,
    ArtifactRecord,
    ArtifactServiceProtocol,
    InMemoryArtifactService,
    ServiceContainer,
    _validate_artifact_inputs,
    get_default_services,
)
from pitch_generator.config import (  # noqa: E402
    PitchConfig,
    get_config,
    normalize_bucket_name,
)


class GcsArtifactService:
    """
    /**
     * Cloud Storage-backed artifact service producing canonical `gs://<bucket>/key-visuals/<filename>` URIs (`F13`).
     *
     * Why: BigQuery's `bwg.key_visuals` table (`OBJ.MAKE_REF`) expects key visuals to be
     * addressable at `gs://<PROJECT_ID>-bwg/key-visuals/<filename>` while ADK sessions track
     * monotonic revision numbers (`version = 1, 2, ...`) across prompt/skill tuning passes.
     *
     * @param bucket_name Target GCS bucket name (with or without `gs://` prefix).
     * @param client Optional injected storage client for custom upload hooks.
     * @param prefix Object key prefix inside the bucket (default `'key-visuals'`).
     */
    """

    def __init__(
        self,
        bucket_name: str,
        client: Any = None,
        prefix: str = "key-visuals",
    ) -> None:
        """
        /**
         * Initializes `GcsArtifactService` with a normalized bucket name and prefix.
         *
         * Why: Strips accidental `gs://` prefixes or trailing slashes from `LOGS_BUCKET_NAME`
         * so constructed URIs never contain malformed `gs://gs://` segments.
         *
         * @param bucket_name Target Cloud Storage bucket name.
         * @param client Optional storage client stub.
         * @param prefix Object path prefix (default `'key-visuals'`).
         */
        """
        normalized = normalize_bucket_name(bucket_name)
        if not normalized:
            raise ValueError("GcsArtifactService requires a non-empty bucket_name.")
        self.bucket_name: str = normalized
        self.client: Any = client
        self.prefix: str = prefix.strip("/") or "key-visuals"
        self._store: dict[tuple[str, str], list[ArtifactRecord]] = {}

    def save_artifact(
        self,
        filename: str,
        data: bytes,
        mime_type: str = "image/png",
        session_id: str = "default",
    ) -> ArtifactRecord:
        """
        /**
         * Saves a binary artifact, increments its per-session version counter, and assigns its `gs://` URI.
         *
         * Why: Enables zero-network unit/E2E testing while optionally forwarding uploads to an
         * injected `client` when running against a mock or custom storage adapter.
         *
         * @param filename Safe artifact filename (e.g., `'cats.png'`, `'bike.png'`).
         * @param data Non-empty binary image bytes.
         * @param mime_type MIME type string (default `'image/png'`).
         * @param session_id Session namespace (default `'default'`).
         * @return Versioned `ArtifactRecord` with `gcs_uri = 'gs://<bucket>/<prefix>/<filename>'`.
         */
        """
        clean_name, clean_session = _validate_artifact_inputs(filename, data, session_id)
        clean_mime = (mime_type or "image/png").strip() or "image/png"
        raw_bytes = bytes(data)

        key = (clean_session, clean_name)
        existing = self._store.setdefault(key, [])
        version = len(existing) + 1
        object_path = f"{self.prefix}/{clean_name}"
        gcs_uri = f"gs://{self.bucket_name}/{object_path}"

        if self.client is not None:
            if hasattr(self.client, "upload_bytes"):
                self.client.upload_bytes(
                    bucket_name=self.bucket_name,
                    object_path=object_path,
                    data=raw_bytes,
                    mime_type=clean_mime,
                )
            elif hasattr(self.client, "bucket"):
                bucket_obj = self.client.bucket(self.bucket_name)
                blob_obj = bucket_obj.blob(object_path)
                if hasattr(blob_obj, "upload_from_string"):
                    blob_obj.upload_from_string(raw_bytes, content_type=clean_mime)

        record = ArtifactRecord(
            filename=clean_name,
            version=version,
            data=raw_bytes,
            mime_type=clean_mime,
            gcs_uri=gcs_uri,
        )
        existing.append(record)
        return record

    def get_artifact(
        self,
        filename: str,
        session_id: str = "default",
        version: int | None = None,
    ) -> ArtifactRecord | None:
        """
        /**
         * Retrieves the latest (or specific version) `ArtifactRecord` for `(session_id, filename)`.
         *
         * Why: Allows callers to verify that saving v2 of `'cats.png'` after prompt tuning
         * returns the updated bytes and `version == 2`.
         *
         * @param filename Artifact filename to look up.
         * @param session_id Session namespace (default `'default'`).
         * @param version Optional 1-based version number; defaults to latest.
         * @return Matching `ArtifactRecord` or `None` if not found.
         */
        """
        if not isinstance(filename, str) or not filename.strip():
            return None
        clean_session = (session_id or "default").strip() or "default"
        versions = self._store.get((clean_session, filename.strip()), [])
        if not versions:
            return None
        if version is None:
            return versions[-1]
        for rec in versions:
            if rec.version == version:
                return rec
        return None

    def list_artifacts(self, session_id: str = "default") -> list[ArtifactRecord]:
        """
        /**
         * Lists all `ArtifactRecord` versions stored under `session_id`.
         *
         * Why: Supports batch inspection of all campaign visuals generated in a session.
         *
         * @param session_id Session namespace (default `'default'`).
         * @return List of `ArtifactRecord` instances in creation order.
         */
        """
        clean_session = (session_id or "default").strip() or "default"
        results: list[ArtifactRecord] = []
        for (sess, _), records in self._store.items():
            if sess == clean_session:
                results.extend(records)
        return results


def get_artifact_service(
    config: PitchConfig | None = None,
    *,
    bucket_name: str | None = None,
    env: Mapping[str, str] | None = None,
    client: Any = None,
) -> ArtifactServiceProtocol:
    """
    /**
     * Selects `GcsArtifactService` when a bucket is configured via `bucket_name`, `env`, or `config`,
     * and falls back to `InMemoryArtifactService` when empty.
     *
     * Why: Implements the Step 2b (`F13`) environment-driven storage toggle (`LOGS_BUCKET_NAME`)
     * so local development works with zero configuration while staging/production persists to GCS.
     *
     * @param config Optional `PitchConfig` instance.
     * @param bucket_name Explicit bucket name override.
     * @param env Optional environment dictionary containing `LOGS_BUCKET_NAME`.
     * @param client Optional storage client stub.
     * @return Configured `GcsArtifactService` or `InMemoryArtifactService`.
     */
    """
    if bucket_name is not None:
        raw_bucket = bucket_name
    elif env is not None:
        raw_bucket = env.get("LOGS_BUCKET_NAME", "")
    elif config is not None:
        raw_bucket = config.logs_bucket_name or ""
    else:
        raw_bucket = os.environ.get("LOGS_BUCKET_NAME", "")

    normalized = normalize_bucket_name(raw_bucket)
    if normalized:
        return GcsArtifactService(bucket_name=normalized, client=client)
    return InMemoryArtifactService()


create_artifact_service = get_artifact_service
select_artifact_service = get_artifact_service


def run_workflow_with_gcs_artifacts(
    brief: str,
    *,
    bucket_name: str = "local-dev-project-bwg",
    session_id: str = "default",
    services: ServiceContainer | None = None,
) -> dict[str, Any]:
    """
    /**
     * Executes the end-to-end Pitch Generator workflow backed by `GcsArtifactService`.
     *
     * Why: Verifies that `generate_key_visual` and the orchestrator pipeline persist
     * `key_visual.png` to `gs://<bucket>/key-visuals/key_visual.png` and surface the
     * `gs://` URI in the packaged output (`F13`).
     *
     * @param brief Product pitch brief text.
     * @param bucket_name Target GCS bucket name (default `'local-dev-project-bwg'`).
     * @param session_id Session identifier (default `'default'`).
     * @param services Optional pre-built `ServiceContainer`.
     * @return Workflow execution result dictionary including `key_visual_uri` and `gcs_uri`.
     */
    """
    cfg = get_config(env={"LOGS_BUCKET_NAME": bucket_name})
    svc_container = services or get_default_services(cfg)
    svc_container.artifacts = GcsArtifactService(bucket_name=bucket_name)
    result = run_pitch_workflow(brief, session_id=session_id, services=svc_container)
    result["gcs_uri"] = result.get("key_visual_uri")
    return result


__all__ = [
    "MINIMAL_PNG_BYTES",
    "ArtifactRecord",
    "ArtifactServiceProtocol",
    "InMemoryArtifactService",
    "GcsArtifactService",
    "get_artifact_service",
    "create_artifact_service",
    "select_artifact_service",
    "run_workflow_with_gcs_artifacts",
]
