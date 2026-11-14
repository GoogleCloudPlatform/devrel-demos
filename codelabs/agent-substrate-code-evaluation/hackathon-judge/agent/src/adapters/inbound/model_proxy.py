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

"""Model Proxy inbound adapter for credential-free Judge Actors.

Proxies Gemini model requests from isolated Judge Actors to Gemini on Agent
Platform, enforcing a strict path allowlist and injecting the Judge
Orchestrator's Workload Identity access token on the wire.
"""

import asyncio
from collections.abc import AsyncIterator, Callable
import re
import sys

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
import httpx

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

ALLOWED_UPSTREAM_PATH_RE = re.compile(
    r"^v1(beta1)?/projects/[a-zA-Z0-9_-]+/locations/(?P<location>[a-zA-Z0-9_-]+)/publishers/google/models/[a-zA-Z0-9._-]+:(generateContent|streamGenerateContent)$"
)

_EXCLUDED_REQUEST_HEADERS = frozenset(
    {
        "authorization",
        "connection",
        "content-length",
        "host",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)


def get_access_token() -> str:
    """Acquire a fresh Google Cloud access token via Application Default Credentials."""
    credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
    if not credentials.valid or not credentials.token:
        credentials.refresh(GoogleAuthRequest())
    if not credentials.token:
        raise RuntimeError(
            "Failed to obtain access token from Application Default Credentials"
        )
    return str(credentials.token)


def default_client_factory() -> httpx.AsyncClient:
    """Create an async HTTP client configured for streaming model responses."""
    return httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=30.0))


def _resolve_default_token_provider() -> Callable[[], str]:
    compat_mod = sys.modules.get("src.vertex_proxy")
    if compat_mod is not None:
        candidate = getattr(compat_mod, "get_access_token", None)
        if callable(candidate) and candidate is not get_access_token:
            return candidate
    return get_access_token


def _resolve_default_client_factory() -> Callable[[], httpx.AsyncClient]:
    compat_mod = sys.modules.get("src.vertex_proxy")
    if compat_mod is not None:
        candidate = getattr(compat_mod, "default_client_factory", None)
        if callable(candidate) and candidate is not default_client_factory:
            return candidate
    return default_client_factory


def _build_upstream_url(upstream_path: str, location: str) -> str:
    if location == "global":
        base_host = "https://aiplatform.googleapis.com"
    else:
        base_host = f"https://{location}-aiplatform.googleapis.com"
    return f"{base_host}/{upstream_path}"


def create_vertex_proxy_router(
    token_provider: Callable[[], str] | None = None,
    client_factory: Callable[[], httpx.AsyncClient] | None = None,
) -> APIRouter:
    """Create a FastAPI router mounting POST /vertex-proxy/{upstream_path:path}."""
    proxy_router = APIRouter()

    @proxy_router.post("/vertex-proxy/{upstream_path:path}")
    async def proxy_vertex_model_request(
        upstream_path: str,
        request: Request,
    ) -> StreamingResponse:
        match = ALLOWED_UPSTREAM_PATH_RE.fullmatch(upstream_path)
        if not match:
            raise HTTPException(
                status_code=403,
                detail="Forbidden upstream path for Model Proxy",
            )

        location = match.group("location")
        upstream_url = _build_upstream_url(upstream_path, location)

        resolve_token = token_provider or _resolve_default_token_provider()
        token = await asyncio.to_thread(resolve_token)

        outbound_headers: dict[str, str] = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in _EXCLUDED_REQUEST_HEADERS
        }
        outbound_headers["Authorization"] = f"Bearer {token}"
        if not any(k.lower() == "content-type" for k in outbound_headers):
            outbound_headers["Content-Type"] = "application/json"

        body = await request.body()
        make_client = client_factory or _resolve_default_client_factory()
        client = make_client()
        try:
            upstream_req = client.build_request(
                method="POST",
                url=upstream_url,
                params=request.query_params,
                headers=outbound_headers,
                content=body,
            )
            upstream_resp = await client.send(upstream_req, stream=True)
        except Exception:
            await client.aclose()
            raise

        async def stream_upstream_body() -> AsyncIterator[bytes]:
            try:
                async for chunk in upstream_resp.aiter_bytes():
                    yield chunk
            finally:
                await upstream_resp.aclose()
                await client.aclose()

        media_type = upstream_resp.headers.get("content-type", "application/json")
        return StreamingResponse(
            stream_upstream_body(),
            status_code=upstream_resp.status_code,
            media_type=media_type,
        )

    return proxy_router


router = create_vertex_proxy_router()

__all__ = [
    "ALLOWED_UPSTREAM_PATH_RE",
    "CLOUD_PLATFORM_SCOPE",
    "GoogleAuthRequest",
    "_EXCLUDED_REQUEST_HEADERS",
    "_build_upstream_url",
    "create_vertex_proxy_router",
    "default_client_factory",
    "get_access_token",
    "google",
    "router",
]
