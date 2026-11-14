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

"""Local CHARM dev server: serves static web assets and proxies POST /api/decisions to live Gemini Decision 1."""

from __future__ import annotations

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from charm_gemini.client import call_gemini_decisions_api

MAX_POST_BYTES: int = 1_048_576  # 1 MiB ceiling to prevent unbounded body reads
_ALLOWED_STATIC_FILES: set[str] = {
    "index.html",
    "styles.css",
    "app.js",
    "ocean-core.js",
    "llms.txt",
    "README.md",
}
_ALLOWED_LATEST_RESULT_KEYS: set[str] = {
    "status",
    "protocol",
    "decision_model",
    "agent_id",
    "agent_model",
    "agent_harness",
    "raw_decisions",
    "profile",
    "request_payload",
}

_STATE_VERSION: int = 0
_STAGED_PREFILL: dict | None = None
_LATEST_RESULT: dict = {
    "status": "awaiting_submission",
    "protocol": "charm.v1",
    "decision_model": "gemini-decision-1",
}


def _sanitize_error_message(message: str) -> str:
    """Redact API keys or credential query params from surfaced error messages."""
    cleaned = re.sub(r"AIza[0-9A-Za-z_-]{10,}", "[REDACTED_KEY]", message)
    return re.sub(r"([?&](?:key|api_key|apiKey)=)[^&\s]+", r"\1[REDACTED]", cleaned)


def _extract_questionnaire_schema() -> dict:
    index_path = REPO_ROOT / "index.html"
    if not index_path.is_file():
        return {"protocol": "charm.v1", "prompts": []}
    html = index_path.read_text(encoding="utf-8")
    match = re.search(
        r'<script[^>]*id="agent-questionnaire-schema"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return {"protocol": "charm.v1", "prompts": []}
    return json.loads(match.group(1).strip())


def _load_dotenv_key() -> str:
    env_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if env_key:
        return env_key
    dotenv_path = Path.home() / ".env"
    if dotenv_path.is_file():
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


class CharmDevHandler(SimpleHTTPRequestHandler):
    """Serves static files (no-cache) and proxies POST /api/decisions using ~/.env GEMINI_API_KEY."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(REPO_ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/llms.txt":
            llms_path = REPO_ROOT / "llms.txt"
            if llms_path.exists():
                body = llms_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
        if path == "/api/questions":
            self._write_json(HTTPStatus.OK, _extract_questionnaire_schema())
            return
        if path == "/api/prefill":
            self._write_json(HTTPStatus.OK, _STAGED_PREFILL or {"status": "empty"})
            return
        if path == "/api/latest-result":
            self._write_json(HTTPStatus.OK, _LATEST_RESULT)
            return
        if path == "/api/state":
            self._write_json(
                HTTPStatus.OK,
                {
                    "version": _STATE_VERSION,
                    "prefill": _STAGED_PREFILL,
                    "request_payload": None,
                    "result": _LATEST_RESULT,
                },
            )
            return
        rel = path.lstrip("/")
        if path == "/" or rel in _ALLOWED_STATIC_FILES:
            super().do_GET()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:  # noqa: N802
        global _STATE_VERSION, _STAGED_PREFILL, _LATEST_RESULT
        path = self.path.split("?", 1)[0]
        if path not in ("/api/decisions", "/api/prefill", "/api/latest-result", "/api/submit", "/api/reset"):
            self.send_error(HTTPStatus.NOT_FOUND, "Unsupported POST endpoint")
            return

        raw_len = self.headers.get("Content-Length", "0") or "0"
        try:
            content_len = int(raw_len)
        except ValueError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid Content-Length header"})
            return
        if content_len < 0:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Negative Content-Length header"})
            return
        if content_len > MAX_POST_BYTES:
            self._write_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": f"Request body exceeds {MAX_POST_BYTES} byte limit"},
            )
            return

        raw_body = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON request body"})
            return

        if path == "/api/reset":
            _STAGED_PREFILL = None
            _LATEST_RESULT = {
                "status": "awaiting_submission",
                "protocol": "charm.v1",
                "decision_model": "gemini-decision-1",
            }
            _STATE_VERSION += 1
            self._write_json(HTTPStatus.OK, {"status": "reset", "version": _STATE_VERSION})
            return

        if path == "/api/prefill":
            if not isinstance(payload, dict):
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": "JSON object required"})
                return
            _STAGED_PREFILL = payload
            _STATE_VERSION += 1
            self._write_json(
                HTTPStatus.OK,
                {"status": "staged", "version": _STATE_VERSION, "prefill": _STAGED_PREFILL},
            )
            return

        if path == "/api/latest-result":
            if not isinstance(payload, dict):
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": "JSON object required"})
                return
            _LATEST_RESULT = {
                k: v for k, v in payload.items() if k in _ALLOWED_LATEST_RESULT_KEYS
            }
            _STATE_VERSION += 1
            self._write_json(HTTPStatus.OK, {"status": "recorded", "version": _STATE_VERSION})
            return

        if path == "/api/submit":
            if not isinstance(payload, dict):
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": "JSON object required"})
                return
            answers = payload.get("answers") if isinstance(payload.get("answers"), dict) else payload
            missing = [
                f"q{i}"
                for i in range(1, 16)
                if not isinstance(answers.get(f"q{i}"), str) or not answers.get(f"q{i}").strip()
            ]
            if missing:
                self._write_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": f"Missing or empty scenario responses: {', '.join(missing)}"},
                )
                return

            agent_id = str(payload.get("agent_id") or "external-agent").strip() or "external-agent"
            agent_model = str(payload.get("agent_model") or "External Agent").strip() or "External Agent"
            agent_harness = str(payload.get("agent_harness") or "").strip()
            responses = {f"q{i}": answers[f"q{i}"].strip() for i in range(1, 16)}

            _STAGED_PREFILL = {
                "agent_id": agent_id,
                "agent_model": agent_model,
                "agent_harness": agent_harness,
                "answers": responses,
                "auto_score": False,
            }
            _LATEST_RESULT = {
                "status": "awaiting_submission",
                "protocol": "charm.v1",
                "decision_model": "gemini-decision-1",
            }
            _STATE_VERSION += 1
            self._write_json(
                HTTPStatus.OK,
                {
                    "status": "staged",
                    "version": _STATE_VERSION,
                    "agent_id": agent_id,
                    "agent_model": agent_model,
                    "agent_harness": agent_harness,
                    "message": "Answers staged on the CHARM mat. Ask a human to click 'Score Your Persona!' in the app to reveal your traits.",
                },
            )
            return

        api_key = _load_dotenv_key()
        try:
            result = call_gemini_decisions_api(payload, api_key=api_key, timeout=30.0)
            self._write_json(HTTPStatus.OK, result)
        except Exception as exc:
            self._write_json(HTTPStatus.BAD_GATEWAY, {"error": _sanitize_error_message(str(exc))})

    def _write_json(self, status: HTTPStatus, body: dict) -> None:
        encoded = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    port_env = os.environ.get("PORT") or os.environ.get("CHARM_PORT") or "8787"
    host = os.environ.get("CHARM_HOST") or ("0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    port = int(port_env)
    server = ThreadingHTTPServer((host, port), CharmDevHandler)
    print(f"CHARM server listening on http://{host}:{port} (live /api/decisions proxy enabled)")
    server.serve_forever()


if __name__ == "__main__":
    main()
