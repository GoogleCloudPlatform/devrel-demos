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
 * @file conftest.py
 * @description Shared pytest fixtures and offline dependency injection wiring for
 *   the Pitch Generator automated test suite.
 *
 * Why: Centralizes test isolation (`offline_env`), dependency-injected cloud service
 * mocks (`InMemoryArtifactService`, `GcsArtifactService`, `MemoryBankService`,
 * `BigQueryAnalyticsService`, `ServiceContainer`), and a unified HTTP/ASGI test
 * client wrapper so every unit and functional test executes deterministically
 * offline with zero live GCP network calls.
 */
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

import pytest

# Why: Ensure the `pitch-generator/` package root is first on `sys.path` even when
# `pytest` is invoked from the repository root (`gcp-ce-content/`).
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pitch_generator.app_utils.memory_bank import MemoryBankService
from pitch_generator.app_utils.services import (
    BigQueryAnalyticsService,
    GcsArtifactService,
    InMemoryArtifactService,
    MockLLMClient,
    ServiceContainer,
)
from pitch_generator.config import PitchConfig, get_config


@pytest.fixture(autouse=True)
def offline_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """
    /**
     * Automatically sanitize environment variables for every test run.
     *
     * Why: Prevents ambient workstation environment variables or GCP credentials
     * from leaking into unit tests and guarantees deterministic offline behavior.
     *
     * @param monkeypatch Pytest MonkeyPatch fixture for scoped environment mutation.
     * @return Dictionary of baseline test environment variables applied.
     */
    """
    defaults = {
        "GOOGLE_CLOUD_PROJECT": "test-project-bwg",
        "PROJECT_ID": "test-project-bwg",
        "GOOGLE_CLOUD_REGION": "us-central1",
        "REGION": "us-central1",
        "GOOGLE_CLOUD_LOCATION": "global",
        "GOOGLE_GENAI_USE_ENTERPRISE": "TRUE",
        "LOGS_BUCKET_NAME": "",
        "VISUAL_DIRECTOR_URL": "http://localhost:8801",
        "PITCH_GENERATOR_URL": "http://localhost:8000",
        "MEMORY_BANK_ID": "test-memory-bank",
    }
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    return defaults


@pytest.fixture
def test_config(offline_env: dict[str, str]) -> PitchConfig:
    """
    /**
     * Provide a deterministic `PitchConfig` instance for unit tests.
     *
     * Why: Allows tests to inspect or override configuration fields without
     * re-parsing `os.environ`.
     *
     * @param offline_env Baseline sanitized environment dictionary.
     * @return Resolved `PitchConfig` object.
     */
    """
    return get_config(offline_env)


@pytest.fixture
def in_memory_artifacts() -> InMemoryArtifactService:
    """
    /**
     * Provide a fresh `InMemoryArtifactService` per test.
     *
     * Why: Isolates binary artifact storage across tests so version counters and
     * session artifacts never collide.
     *
     * @return Fresh `InMemoryArtifactService` instance.
     */
    """
    return InMemoryArtifactService()


@pytest.fixture
def gcs_artifacts() -> GcsArtifactService:
    """
    /**
     * Provide an offline-capable `GcsArtifactService` backed by an in-memory mock bucket.
     *
     * Why: Verifies `gs://<bucket>/...` URI generation and GCS upload semantics
     * without making live Google Cloud Storage API calls.
     *
     * @return Configured `GcsArtifactService` instance for `test-project-bwg-bwg`.
     */
    """
    return GcsArtifactService(bucket_name="test-project-bwg-bwg")


@pytest.fixture
def memory_bank() -> MemoryBankService:
    """
    /**
     * Provide an isolated `MemoryBankService` instance for session and memory tests.
     *
     * Why: Guarantees each test starts with an empty session store and memory namespace.
     *
     * @return Fresh `MemoryBankService` instance.
     */
    """
    return MemoryBankService(memory_bank_id="test-memory-bank")


@pytest.fixture
def bq_analytics() -> BigQueryAnalyticsService:
    """
    /**
     * Provide an offline `BigQueryAnalyticsService` for telemetry and SQL generation tests.
     *
     * Why: Enables testing `OBJ.MAKE_REF`, `OBJ.FETCH_METADATA`, `AI.SCORE` SQL
     * builders and telemetry recording without a live BigQuery connection.
     *
     * @return Configured `BigQueryAnalyticsService` instance.
     */
    """
    return BigQueryAnalyticsService(project_id="test-project-bwg", region="us-central1")


@pytest.fixture
def service_container(
    test_config: PitchConfig,
    in_memory_artifacts: InMemoryArtifactService,
    memory_bank: MemoryBankService,
    bq_analytics: BigQueryAnalyticsService,
) -> ServiceContainer:
    """
    /**
     * Provide a fully wired `ServiceContainer` with deterministic offline mocks.
     *
     * Why: Supplies `run_pitch_workflow` and FastAPI endpoints with injected LLM,
     * Artifact, Memory Bank, and BigQuery services for fast, hermetic tests.
     *
     * @param test_config Resolved test configuration.
     * @param in_memory_artifacts In-memory artifact store.
     * @param memory_bank Session and long-term memory store.
     * @param bq_analytics Offline BigQuery telemetry and SQL service.
     * @return Populated `ServiceContainer` instance.
     */
    """
    return ServiceContainer(
        config=test_config,
        llm_client=MockLLMClient(config=test_config),
        artifact_service=in_memory_artifacts,
        memory_bank=memory_bank,
        analytics=bq_analytics,
    )


class _UnifiedTestResponse:
    """
    /**
     * Normalized HTTP response object returned by `_UnifiedTestClient`.
     *
     * Why: Provides a consistent `.status_code`, `.json()`, `.text`, and `.headers`
     * interface whether backed by Starlette/FastAPI `TestClient` or the offline
     * ASGI/handler shim in `fast_api_app.py`.
     */
    """

    def __init__(
        self,
        status_code: int,
        body: Any,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = int(status_code)
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        if isinstance(body, (bytes, bytearray)):
            self.content = bytes(body)
            self.text = self.content.decode("utf-8", errors="replace")
            self._json_data = None
        elif isinstance(body, str):
            self.text = body
            self.content = body.encode("utf-8")
            self._json_data = None
        else:
            self._json_data = body
            self.text = json.dumps(body)
            self.content = self.text.encode("utf-8")

    def json(self) -> Any:
        """
        /**
         * Parse and return the JSON payload from the HTTP response body.
         *
         * Why: Matches the `httpx.Response.json()` / `TestClient` response API.
         *
         * @return Decoded JSON object or dictionary.
         */
        """
        if self._json_data is not None:
            return self._json_data
        return json.loads(self.text)


class _UnifiedTestClient:
    """
    /**
     * Adapter wrapping `pitch_generator.fast_api_app` for offline HTTP endpoint testing.
     *
     * Why: Decouples functional API tests from third-party `httpx`/`starlette` wheels
     * while preserving standard `client.get(path)` and `client.post(path, json=...)` calls.
     */
    """

    def __init__(self, app_module: Any) -> None:
        self._app_module = app_module
        self._app = getattr(app_module, "app", None)
        self._native_client: Any = None
        if hasattr(app_module, "TestClient"):
            self._native_client = app_module.TestClient(self._app)
        elif hasattr(self._app, "test_client"):
            self._native_client = self._app.test_client()

    def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> _UnifiedTestResponse:
        """
        /**
         * Dispatch an HTTP request against the FastAPI application or offline router.
         *
         * Why: Normalizes responses across native Starlette `TestClient` and the
         * built-in `handle_request` dispatcher.
         *
         * @param method HTTP verb (`GET`, `POST`, etc.).
         * @param path Request path (e.g., `/api/pitch`).
         * @param json_body Optional JSON request body.
         * @param params Optional query parameters.
         * @param headers Optional HTTP headers.
         * @return `_UnifiedTestResponse` instance.
         */
        """
        if self._native_client is not None:
            resp = self._native_client.request(
                method, path, json=json_body, params=params, headers=headers
            )
            if hasattr(resp, "status_code") and hasattr(resp, "json"):
                return resp  # type: ignore[return-value]
        if hasattr(self._app, "handle_request"):
            raw = self._app.handle_request(
                method=method,
                path=path,
                json_body=json_body,
                query_params=params,
                headers=headers,
            )
            if isinstance(raw, tuple):
                status, payload = raw[0], raw[1]
                hdrs = raw[2] if len(raw) > 2 else {}
                return _UnifiedTestResponse(status, payload, hdrs)
            if hasattr(raw, "status_code"):
                return raw  # type: ignore[return-value]
        raise RuntimeError("fast_api_app.app does not expose TestClient or handle_request")

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> _UnifiedTestResponse:
        """
        /**
         * Execute an offline HTTP GET request against `path`.
         *
         * Why: Convenience method mirroring `TestClient.get()`.
         */
        """
        return self.request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> _UnifiedTestResponse:
        """
        /**
         * Execute an offline HTTP POST request against `path`.
         *
         * Why: Convenience method mirroring `TestClient.post()`.
         */
        """
        return self.request("POST", path, json_body=json, headers=headers)


@pytest.fixture
def api_client(service_container: ServiceContainer) -> _UnifiedTestClient:
    """
    /**
     * Provide an offline HTTP test client bound to `pitch_generator.fast_api_app`.
     *
     * Why: Enables end-to-end testing of `/api/health`, `/api/config`, `/api/pitch`,
     * `/api/approve`, `/a2a/pitch_generator`, and static frontend routes
     * without binding a network socket.
     *
     * @param service_container Injected offline service container.
     * @return Configured `_UnifiedTestClient` instance.
     */
    """
    from pitch_generator import fast_api_app

    if hasattr(fast_api_app, "configure_app_services"):
        fast_api_app.configure_app_services(service_container)
    elif hasattr(fast_api_app.app, "state"):
        setattr(fast_api_app.app.state, "services", service_container)
    return _UnifiedTestClient(fast_api_app)
