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

import os
from collections.abc import AsyncIterator

import httpx
import pytest

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ.setdefault("TASKS_SUBSCRIPTION", "test-sub")
os.environ.setdefault("RESULTS_TOPIC", "test-topic")
os.environ["USE_MOCK_PUBSUB"] = "true"

from fastapi.testclient import TestClient
from src import vertex_proxy
from src.main import app


class _ChunkedAsyncStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


@pytest.mark.parametrize(
    "invalid_path",
    [
        "v1/projects/my-proj/locations/global/publishers/google/models/gemini-3.8-flash:countTokens",
        "v1/projects/my-proj/locations/global/publishers/custom/models/gemini-3.8-flash:generateContent",
        "v1beta1/projects/my-proj/locations/global/../../iam/serviceAccounts",
        "compute/v1/projects/my-proj/zones/us-central1-a/instances",
        "v2/projects/my-proj/locations/global/publishers/google/models/gemini-3.8-flash:generateContent",
    ],
)
def test_vertex_proxy_rejects_disallowed_paths_with_403(invalid_path: str):
    client = TestClient(app)
    response = client.post(f"/vertex-proxy/{invalid_path}", json={"contents": []})
    assert response.status_code == 403


def test_vertex_proxy_injects_bearer_token_and_streams_sse_from_global_endpoint(monkeypatch):
    captured: list[httpx.Request] = []
    sse_chunks = [
        b'data: {"candidates":[{"content":{"parts":[{"text":"part-1"}]}}]}\n\n',
        b'data: {"candidates":[{"content":{"parts":[{"text":"part-2"}]}}]}\n\n',
    ]

    async def handler(request: httpx.Request) -> httpx.Response:
        await request.aread()
        captured.append(request)
        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/event-stream; charset=utf-8"},
            stream=_ChunkedAsyncStream(sse_chunks),
        )

    monkeypatch.setattr(vertex_proxy, "get_access_token", lambda: "orchestrator-wi-token")
    monkeypatch.setattr(
        vertex_proxy,
        "default_client_factory",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    client = TestClient(app)
    response = client.post(
        "/vertex-proxy/v1beta1/projects/my-proj/locations/global/publishers/google/models/gemini-3.8-flash:streamGenerateContent?alt=sse",
        headers={
            "Authorization": "Bearer untrusted-actor-token",
            "X-Goog-Api-Client": "antigravity/0.1.23",
            "Accept": "text/event-stream",
        },
        json={"contents": [{"role": "user", "parts": [{"text": "evaluate repo"}]}]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.content == b"".join(sse_chunks)

    assert len(captured) == 1
    upstream_req = captured[0]
    assert (
        str(upstream_req.url)
        == "https://aiplatform.googleapis.com/v1beta1/projects/my-proj/locations/global/publishers/google/models/gemini-3.8-flash:streamGenerateContent?alt=sse"
    )
    assert upstream_req.headers["authorization"] == "Bearer orchestrator-wi-token"
    assert upstream_req.headers["x-goog-api-client"] == "antigravity/0.1.23"
    assert upstream_req.headers["accept"] == "text/event-stream"
    assert b"evaluate repo" in upstream_req.content


def test_vertex_proxy_routes_regional_location_and_forwards_upstream_error_status(monkeypatch):
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        await request.aread()
        captured.append(request)
        return httpx.Response(
            status_code=429,
            headers={"content-type": "application/json"},
            content=b'{"error":{"code":429,"message":"Resource exhausted"}}',
        )

    monkeypatch.setattr(vertex_proxy, "get_access_token", lambda: "regional-wi-token")
    monkeypatch.setattr(
        vertex_proxy,
        "default_client_factory",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    client = TestClient(app)
    response = client.post(
        "/vertex-proxy/v1/projects/my-proj/locations/us-central1/publishers/google/models/gemini-2.5-pro:generateContent",
        json={"contents": []},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == 429
    assert len(captured) == 1
    assert (
        str(captured[0].url)
        == "https://us-central1-aiplatform.googleapis.com/v1/projects/my-proj/locations/us-central1/publishers/google/models/gemini-2.5-pro:generateContent"
    )
    assert captured[0].headers["authorization"] == "Bearer regional-wi-token"


def test_create_vertex_proxy_router_accepts_injectable_providers():
    from fastapi import FastAPI

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={"content-type": "application/json"},
            content=b'{"candidates":[]}',
        )

    custom_app = FastAPI()
    custom_app.include_router(
        vertex_proxy.create_vertex_proxy_router(
            token_provider=lambda: "injected-token",
            client_factory=lambda: httpx.AsyncClient(
                transport=httpx.MockTransport(handler)
            ),
        )
    )
    client = TestClient(custom_app)
    resp = client.post(
        "/vertex-proxy/v1/projects/p/locations/global/publishers/google/models/gemini-3.8-flash:generateContent",
        json={"contents": []},
    )
    assert resp.status_code == 200
    assert resp.json() == {"candidates": []}


def test_get_access_token_refreshes_expired_credentials(monkeypatch):
    class FakeCreds:
        def __init__(self) -> None:
            self.valid = False
            self.token: str | None = None
            self.refreshed = False

        def refresh(self, _request) -> None:
            self.refreshed = True
            self.valid = True
            self.token = "refreshed-adc-token"

    fake_creds = FakeCreds()
    captured_scopes: list[list[str] | None] = []

    def fake_default(scopes=None):
        captured_scopes.append(scopes)
        return fake_creds, "test-proj"

    monkeypatch.setattr(vertex_proxy.google.auth, "default", fake_default)
    token = vertex_proxy.get_access_token()
    assert token == "refreshed-adc-token"
    assert fake_creds.refreshed is True
    assert captured_scopes == [["https://www.googleapis.com/auth/cloud-platform"]]
