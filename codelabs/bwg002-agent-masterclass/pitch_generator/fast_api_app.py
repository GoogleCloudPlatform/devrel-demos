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
 * @file fast_api_app.py
 * @description Cloud Run HTTP, REST, A2A, and static frontend server for the
 *   Agentic Pitch Generator.
 *
 * Why: Exposes all required REST endpoints (`/api/health`, `/api/config`, `/api/pitch`,
 * `/api/approve`, `/api/route`), A2A v0.3 protocol routes
 * (`/a2a/pitch_generator/.well-known/agent-card.json` and `/a2a/pitch_generator`),
 * and plain HTML5/CSS3/ES6 JS frontend routes (`/`, `/index.html`, `/styles.css`,
 * `/app.js`). Includes a self-contained ASGI 3.0 application class and `TestClient`
 * so the application runs identically under `uvicorn` in Cloud Run and in offline
 * `pytest` suites without requiring external `fastapi` or `httpx` wheels.
 */
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any
import urllib.parse

# Ensure repo root is on sys.path when executed directly
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from pitch_generator.agent import (
    resume_pitch_workflow,
    root_agent,
    run_pitch_workflow,
    select_routing_decision,
)
from pitch_generator.app_utils.a2a import (
    A2aAgentExecutor,
    A2aAgentExecutorConfig,
    AgentCardBuilder,
    DefaultRequestHandler,
    include_artifacts_in_a2a_event_interceptor,
)
from pitch_generator.app_utils.services import (
    ServiceContainer,
    get_default_services,
)

FRONTEND_DIR: Path = Path(__file__).resolve().parent.parent / "frontend"


@dataclass
class RouteInfo:
    """
    /**
     * Metadata descriptor for a registered HTTP route on `PitchFastAPIApp`.
     *
     * Why: Allows tests inspecting `app.routes` to verify registered paths and HTTP
     * methods just like a Starlette/FastAPI application.
     *
     * @param path Route URL path pattern.
     * @param methods Tuple of allowed HTTP methods (e.g., `("GET",)` or `("POST",)`).
     * @param name Human-readable route handler name.
     */
    """

    path: str
    methods: tuple[str, ...]
    name: str


class _AppState:
    """
    /**
     * Mutable application state container attached to `app.state`.
     *
     * Why: Mirrors `fastapi.FastAPI.state` so test fixtures can assign or inspect
     * `app.state.services`.
     */
    """

    def __init__(self, services: ServiceContainer) -> None:
        """
        /**
         * Initialize application state with an injected `ServiceContainer`.
         *
         * @param services Active `ServiceContainer` instance.
         */
        """
        self.services: ServiceContainer = services


class TestResponse:
    """
    /**
     * HTTP response wrapper returned by `TestClient` requests.
     *
     * Why: Provides `.status_code`, `.headers`, `.content`, `.text`, and `.json()`
     * matching `httpx.Response` / `starlette.testclient.TestClient` semantics for
     * offline functional and E2E tests.
     */
    """

    def __init__(
        self,
        status_code: int,
        body: Any,
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        /**
         * Construct a `TestResponse` from status code, body payload, and headers.
         *
         * @param status_code HTTP status code integer.
         * @param body Dict, list, string, or raw bytes response body.
         * @param headers Optional HTTP response headers dictionary.
         */
        """
        self.status_code = int(status_code)
        self.headers: dict[str, str] = {
            k.lower(): str(v) for k, v in (headers or {}).items()
        }
        if isinstance(body, (bytes, bytearray)):
            self.content = bytes(body)
            self.text = self.content.decode("utf-8", errors="replace")
            self._json_cache: Any = None
            self.headers.setdefault("content-type", "application/octet-stream")
        elif isinstance(body, str):
            self.text = body
            self.content = body.encode("utf-8")
            self._json_cache = None
            self.headers.setdefault("content-type", "text/plain; charset=utf-8")
        else:
            self._json_cache = body
            self.text = json.dumps(body)
            self.content = self.text.encode("utf-8")
            self.headers.setdefault("content-type", "application/json")

    def json(self) -> Any:
        """
        /**
         * Parse and return the response body as a JSON structure.
         *
         * Why: Standardizes response inspection across REST and A2A endpoint tests.
         *
         * @return Decoded JSON object (`dict` or `list`).
         */
        """
        if self._json_cache is not None:
            return self._json_cache
        return json.loads(self.text)


class PitchFastAPIApp:
    """
    /**
     * ASGI-compatible web application serving REST, A2A, and static frontend routes.
     *
     * Why: Provides a zero-dependency in-process request router (`handle_request`) AND
     * a full ASGI 3.0 `__call__(scope, receive, send)` interface so both `TestClient`
     * and `uvicorn pitch_generator.fast_api_app:app` work out of the box.
     */
    """

    def __init__(self, services: ServiceContainer | None = None) -> None:
        """
        /**
         * Initialize the Pitch Generator web application and A2A request handler.
         *
         * @param services Optional injected `ServiceContainer`.
         */
        """
        resolved_services = services or get_default_services()
        self.title = "Agentic Pitch Generator"
        self.version = "0.2.0"
        self.state = _AppState(services=resolved_services)
        self._a2a_rpc_path = "/a2a/pitch_generator"
        self._rebuild_a2a_handler()
        self.routes: list[RouteInfo] = [
            RouteInfo(path="/", methods=("GET",), name="serve_index"),
            RouteInfo(path="/index.html", methods=("GET",), name="serve_index_html"),
            RouteInfo(path="/styles.css", methods=("GET",), name="serve_styles_css"),
            RouteInfo(path="/app.js", methods=("GET",), name="serve_app_js"),
            RouteInfo(path="/api/health", methods=("GET",), name="api_health"),
            RouteInfo(path="/api/config", methods=("GET",), name="api_config"),
            RouteInfo(path="/api/pitch", methods=("POST",), name="api_pitch"),
            RouteInfo(path="/api/approve", methods=("POST",), name="api_approve"),
            RouteInfo(path="/api/route", methods=("POST",), name="api_route"),
            RouteInfo(
                path="/a2a/pitch_generator/.well-known/agent-card.json",
                methods=("GET",),
                name="a2a_agent_card",
            ),
            RouteInfo(
                path="/a2a/pitch_generator",
                methods=("POST",),
                name="a2a_jsonrpc",
            ),
        ]

    def _rebuild_a2a_handler(self) -> None:
        """
        /**
         * Build the default A2A `AgentCardBuilder` and `DefaultRequestHandler`.
         *
         * Why: Keeps the A2A Agent Card URL synchronized with the active `PitchConfig`.
         */
        """
        base_url = self.state.services.config.pitch_generator_url.rstrip("/")
        rpc_url = f"{base_url}{self._a2a_rpc_path}"
        self._agent_card = dict(
            AgentCardBuilder(agent=root_agent, rpc_url=rpc_url).build()
        )
        executor = A2aAgentExecutor(
            config=A2aAgentExecutorConfig(
                execute_interceptors=[include_artifacts_in_a2a_event_interceptor]
            )
        )
        self._a2a_handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store={},
            agent_card=self._agent_card,
        )

    def register_a2a_handler(
        self,
        rpc_path: str,
        handler: DefaultRequestHandler,
        agent_card: dict[str, Any],
    ) -> None:
        """
        /**
         * Register a custom A2A `DefaultRequestHandler` and Agent Card at `rpc_path`.
         *
         * Why: Called by `attach_a2a_routes(app, ...)` when mounting A2A endpoints.
         *
         * @param rpc_path URL path prefix (e.g., `"/a2a/pitch_generator"`).
         * @param handler Configured `DefaultRequestHandler`.
         * @param agent_card Built A2A Agent Card dictionary.
         */
        """
        self._a2a_rpc_path = "/" + rpc_path.strip("/")
        self._a2a_handler = handler
        self._agent_card = dict(agent_card)

    def handle_request(
        self,
        method: str,
        path: str,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> TestResponse:
        """
        /**
         * Dispatch an HTTP request in-process and return a `TestResponse`.
         *
         * Why: Enables fast, deterministic testing of all REST, A2A, and static UI
         * routes without opening network sockets.
         *
         * @param method HTTP method (`"GET"`, `"POST"`, etc.).
         * @param path Request URL path (with optional query string).
         * @param json_body Optional parsed JSON body or raw string/bytes.
         * @param headers Optional HTTP request headers.
         * @param query_params Optional query parameter dictionary.
         * @return `TestResponse` containing status code, headers, and payload.
         */
        """
        del headers, query_params
        method_upper = (method or "GET").upper()
        parsed_url = urllib.parse.urlparse(path or "/")
        clean_path = parsed_url.path or "/"

        payload: dict[str, Any] = {}
        if isinstance(json_body, dict):
            payload = json_body
        elif isinstance(json_body, (str, bytes, bytearray)) and json_body:
            try:
                raw_str = (
                    json_body.decode("utf-8")
                    if isinstance(json_body, (bytes, bytearray))
                    else json_body
                )
                decoded = json.loads(raw_str)
                if isinstance(decoded, dict):
                    payload = decoded
            except Exception:
                return TestResponse(
                    400,
                    {"error": "Malformed JSON request body", "detail": "Malformed JSON request body"},
                )

        services = self.state.services

        # 1. Health check endpoint
        if method_upper == "GET" and clean_path == "/api/health":
            return TestResponse(
                200,
                {
                    "status": "ok",
                    "service": "pitch-generator",
                    "version": self.version,
                    "agent": root_agent.name,
                },
            )

        # 2. Public runtime configuration endpoint
        if method_upper == "GET" and clean_path == "/api/config":
            return TestResponse(200, services.config.to_public_dict())

        # 3. Campaign pitch workflow execution endpoint
        if method_upper == "POST" and clean_path == "/api/pitch":
            brief = str(payload.get("brief") or payload.get("prompt") or "").strip()
            if not brief:
                return TestResponse(
                    400,
                    {
                        "error": "Campaign brief must not be empty",
                        "detail": "Campaign brief must not be empty",
                    },
                )
            session_id = str(payload.get("session_id") or "default").strip() or "default"
            routing_mode = str(payload.get("routing_mode") or "auto").strip()
            require_approval = bool(payload.get("require_approval", False))
            approved_val = payload.get("approved", None if require_approval else True)

            try:
                result = run_pitch_workflow(
                    brief,
                    session_id=session_id,
                    services=services,
                    approved=approved_val,
                    routing_mode=routing_mode,
                    require_approval=require_approval,
                )
                return TestResponse(200, result)
            except ValueError as exc:
                return TestResponse(400, {"error": str(exc), "detail": str(exc)})
            except RuntimeError as exc:
                return TestResponse(502, {"error": str(exc), "detail": str(exc)})

        # 4. Human-in-the-Loop concept approval endpoint
        if method_upper == "POST" and clean_path == "/api/approve":
            session_id = str(payload.get("session_id") or "").strip()
            if not session_id:
                return TestResponse(
                    400,
                    {"error": "session_id is required", "detail": "session_id is required"},
                )
            if "approved" not in payload or not isinstance(payload.get("approved"), bool):
                return TestResponse(
                    400,
                    {
                        "error": "Boolean 'approved' field is required",
                        "detail": "Boolean 'approved' field is required",
                    },
                )
            feedback = str(payload.get("feedback") or "")
            try:
                resumed = resume_pitch_workflow(
                    session_id,
                    approved=bool(payload["approved"]),
                    feedback=feedback,
                    services=services,
                )
                return TestResponse(200, resumed)
            except KeyError as exc:
                return TestResponse(404, {"error": str(exc), "detail": str(exc)})
            except ValueError as exc:
                return TestResponse(400, {"error": str(exc), "detail": str(exc)})
            except RuntimeError as exc:
                return TestResponse(502, {"error": str(exc), "detail": str(exc)})

        # 5. Hybrid model routing decision endpoint
        if method_upper == "POST" and clean_path == "/api/route":
            brief = str(
                payload.get("brief") or payload.get("prompt") or payload.get("task") or ""
            )
            routing_mode = str(payload.get("routing_mode") or "auto")
            complexity = str(payload.get("complexity") or "medium")
            privacy_level = str(payload.get("privacy_level") or "standard")
            requires_multimodal = bool(payload.get("requires_multimodal", False))
            browser_webgpu = bool(payload.get("browser_webgpu_available", False))
            local_gpu = bool(payload.get("local_gpu_available", False))
            try:
                decision = select_routing_decision(
                    brief=brief,
                    routing_mode=routing_mode,
                    complexity=complexity,
                    privacy_level=privacy_level,
                    requires_multimodal=requires_multimodal,
                    browser_webgpu_available=browser_webgpu,
                    local_gpu_available=local_gpu,
                    config=services.config,
                )
                return TestResponse(200, decision)
            except ValueError as exc:
                return TestResponse(400, {"error": str(exc), "detail": str(exc)})

        # 6. Artifact binary retrieval endpoint
        if method_upper == "GET" and clean_path.startswith("/api/artifacts/"):
            parts = [p for p in clean_path.split("/") if p]
            if len(parts) >= 4:
                sess_id = parts[2]
                fname = parts[3]
                record = services.artifacts.get_artifact(fname, session_id=sess_id)
                if record is not None:
                    return TestResponse(
                        200,
                        record.data,
                        headers={"content-type": record.mime_type},
                    )
            return TestResponse(404, {"error": "Artifact not found"})

        # 7. A2A Agent Card discovery endpoint
        card_paths = {
            f"{self._a2a_rpc_path}/.well-known/agent-card.json",
            "/.well-known/agent-card.json",
        }
        if method_upper == "GET" and clean_path in card_paths:
            return TestResponse(200, self._agent_card)

        # 8. A2A JSON-RPC 2.0 endpoint
        if method_upper == "POST" and clean_path == self._a2a_rpc_path:
            rpc_resp = self._a2a_handler.handle_rpc(payload, services=services)
            return TestResponse(200, rpc_resp)

        # 9. Static plain HTML/CSS/JS frontend files
        static_map = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/index.html": ("index.html", "text/html; charset=utf-8"),
            "/frontend/index.html": ("index.html", "text/html; charset=utf-8"),
            "/static/index.html": ("index.html", "text/html; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/frontend/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/static/styles.css": ("styles.css", "text/css; charset=utf-8"),
            "/app.js": ("app.js", "application/javascript; charset=utf-8"),
            "/frontend/app.js": ("app.js", "application/javascript; charset=utf-8"),
            "/static/app.js": ("app.js", "application/javascript; charset=utf-8"),
        }
        if method_upper == "GET" and clean_path in static_map:
            rel_name, content_type = static_map[clean_path]
            file_path = FRONTEND_DIR / rel_name
            if file_path.is_file():
                return TestResponse(
                    200,
                    file_path.read_text(encoding="utf-8"),
                    headers={"content-type": content_type},
                )

        return TestResponse(404, {"error": f"Not Found: {clean_path}", "detail": "Not Found"})

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        """
        /**
         * Standard ASGI 3.0 callable interface for running under `uvicorn`.
         *
         * Why: Allows `uvicorn pitch_generator.fast_api_app:app` to serve HTTP requests
         * in Cloud Run or local VM terminals using the exact same route logic tested
         * by `TestClient`.
         *
         * @param scope ASGI connection scope dictionary.
         * @param receive ASGI receive awaitable.
         * @param send ASGI send awaitable.
         */
        """
        scope_type = scope.get("type")
        if scope_type == "lifespan":
            while True:
                msg = await receive()
                if msg["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif msg["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope_type != "http":
            return

        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        body_chunks: list[bytes] = []
        while True:
            message = await receive()
            if message.get("type") == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if chunk:
                body_chunks.append(chunk)
            if not message.get("more_body", False):
                break
        raw_body = b"".join(body_chunks)

        resp = await asyncio.to_thread(
            self.handle_request, method=method, path=path, json_body=raw_body
        )
        asgi_headers = [
            (k.encode("latin-1"), v.encode("latin-1")) for k, v in resp.headers.items()
        ]
        await send(
            {
                "type": "http.response.start",
                "status": resp.status_code,
                "headers": asgi_headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": resp.content,
            }
        )


class TestClient:
    """
    /**
     * In-process HTTP client for testing `PitchFastAPIApp` offline.
     *
     * Why: Mirrors `fastapi.testclient.TestClient` (`.get()`, `.post()`, `.request()`,
     * and context manager `with TestClient(app) as client:`) without requiring
     * third-party `httpx` or `starlette` packages.
     */
    """

    def __init__(self, target_app: PitchFastAPIApp | None = None) -> None:
        """
        /**
         * Initialize the test client bound to `target_app`.
         *
         * @param target_app `PitchFastAPIApp` instance (defaults to module `app`).
         */
        """
        self.app: PitchFastAPIApp = target_app or app

    def __enter__(self) -> "TestClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        del exc_type, exc_val, exc_tb

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        data: bytes | str | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> TestResponse:
        """
        /**
         * Send an in-process HTTP request to `self.app`.
         *
         * @param method HTTP method string.
         * @param path Target endpoint path.
         * @param json Optional JSON-serializable payload.
         * @param data Optional raw body bytes or string.
         * @param params Optional query parameters.
         * @param headers Optional HTTP headers.
         * @return `TestResponse` instance.
         */
        """
        body_payload = json if json is not None else data
        return self.app.handle_request(
            method=method,
            path=path,
            json_body=body_payload,
            headers=headers,
            query_params=params,
        )

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> TestResponse:
        """
        /**
         * Execute an in-process HTTP `GET` request.
         *
         * @param path URL path to fetch.
         * @param params Optional query string parameters.
         * @param headers Optional request headers.
         * @return `TestResponse` instance.
         */
        """
        return self.request("GET", path, params=params, headers=headers)

    def post(
        self,
        path: str,
        *,
        json: Any = None,
        data: bytes | str | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> TestResponse:
        """
        /**
         * Execute an in-process HTTP `POST` request.
         *
         * @param path URL path to post to.
         * @param json Optional JSON payload dictionary.
         * @param data Optional raw request body.
         * @param params Optional query parameters.
         * @param headers Optional request headers.
         * @return `TestResponse` instance.
         */
        """
        return self.request(
            "POST", path, json=json, data=data, params=params, headers=headers
        )


def create_app(services: ServiceContainer | None = None) -> PitchFastAPIApp:
    """
    /**
     * Application factory creating a fresh `PitchFastAPIApp` bound to `services`.
     *
     * Why: Enables isolated test cases to instantiate dedicated app instances with
     * custom `ServiceContainer` mocks.
     *
     * @param services Optional injected `ServiceContainer`.
     * @return Configured `PitchFastAPIApp` instance.
     */
    """
    return PitchFastAPIApp(services=services)


app: PitchFastAPIApp = create_app()


def configure_app_services(services: ServiceContainer) -> None:
    """
    /**
     * Replace the active `ServiceContainer` on the module-level `app` instance.
     *
     * Why: Used by the `api_client` fixture in `tests/conftest.py` to inject fresh
     * per-test mocks into `fast_api_app.app`.
     *
     * @param services New `ServiceContainer` to bind to `app.state.services`.
     * @return None.
     */
    """
    app.state.services = services
    app._rebuild_a2a_handler()


if __name__ == "__main__":
    """
    /**
     * Standalone local server runner for development without Docker or external wheels.
     *
     * Why: Enables learners and developers to start the complete Pitch Generator web app
     * and frontend locally using pure Python standard library (`http.server`) or `uvicorn`.
     */
    """
    import os
    import sys

    port = int(os.environ.get("PORT", 8080))
    host = "127.0.0.1"

    try:
        import uvicorn

        uvicorn.run(app, host=host, port=port)
    except ImportError:
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class _LocalPitchHandler(BaseHTTPRequestHandler):
            """
            /**
             * Internal HTTP request handler dispatching requests to `PitchFastAPIApp`.
             *
             * Why: Allows running the application via Python standard library `http.server`
             * when third-party ASGI web servers like `uvicorn` are not installed.
             */
            """

            def log_message(self, fmt: str, *args: Any) -> None:
                """
                /**
                 * Format and log an HTTP request line to standard error.
                 *
                 * Why: Provides real-time visibility into incoming web and API traffic.
                 */
                """
                sys.stderr.write(
                    f"{self.client_address[0]} - [{self.log_date_time_string()}] "
                    + (fmt % args)
                    + "\n"
                )

            def do_GET(self) -> None:
                """
                /**
                 * Handle HTTP GET requests for static assets and API read endpoints.
                 *
                 * Why: Routes GET requests to `PitchFastAPIApp.handle_request`.
                 */
                """
                self._handle("GET")

            def do_POST(self) -> None:
                """
                /**
                 * Handle HTTP POST requests for pitch generation and A2A calls.
                 *
                 * Why: Routes POST requests to `PitchFastAPIApp.handle_request`.
                 */
                """
                self._handle("POST")

            def _handle(self, method: str) -> None:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length > 0 else None
                resp = app.handle_request(method, self.path, json_body=body)
                self.send_response(resp.status_code)
                for k, v in resp.headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.content)

        print("==================================================")
        print("Agentic Pitch Generator Web App Running Locally")
        print(f"Open in browser: http://{host}:{port}")
        print("==================================================")
        server = HTTPServer((host, port), _LocalPitchHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")

