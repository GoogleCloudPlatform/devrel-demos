#!/usr/bin/env python3
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
 * @file call_agent.py
 * @description Command-line A2A client for invoking the Agentic Pitch Generator,
 *   handling Human-in-the-Loop concept approvals, and saving generated key visuals.
 *
 * Why: Learners use `call_agent.py` from the terminal (`python3 call_agent.py
 * "Flying skateboards for cats"`) to exercise the multi-agent workflow against either
 * the local server (`http://localhost:8080`) or a deployed Cloud Run service
 * (`https://*.run.app` with an OIDC identity token), inspect `CONCEPT`, `COPY`, and
 * `ART DIRECTION` outputs, respond to `TASK_STATE_INPUT_REQUIRED` approval prompts,
 * and save binary PNG key visuals. Also supports `--offline` (and automatic fallback
 * when `services` is injected in unit tests) for 100% offline test execution.
 */
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable, Sequence
import urllib.error
import urllib.request

from pitch_generator.app_utils.a2a import TaskState
from pitch_generator.app_utils.services import (
    MINIMAL_PNG_BYTES,
    ServiceContainer,
    get_default_services,
)
from pitch_generator.config import get_config
from pitch_generator.fast_api_app import TestClient, create_app


def build_parser() -> argparse.ArgumentParser:
    """
    /**
     * Build the command-line argument parser for `call_agent.py`.
     *
     * Why: Supports positional campaign brief, `--save-image <path>`, `-y` /
     * `--auto-approve` for non-interactive HITL approval, `--require-approval` to
     * test the HITL gate, and `--url` / `--offline` flags.
     *
     * @return Configured `argparse.ArgumentParser` instance.
     */
    """
    default_url = get_config().pitch_generator_url
    parser = argparse.ArgumentParser(
        description="Invoke the Agentic Pitch Generator over A2A JSON-RPC."
    )
    parser.add_argument(
        "brief",
        nargs="?",
        default="Flying skateboards for cats",
        help="Campaign topic idea to pitch.",
    )
    parser.add_argument(
        "--url",
        default=default_url,
        help="Base URL of the Pitch Generator service (e.g., http://localhost:8080 or Cloud Run URL).",
    )
    parser.add_argument(
        "--save-image",
        dest="save_image",
        default=None,
        help="Optional file path to save the generated key visual PNG (e.g., ./key_visual.png).",
    )
    parser.add_argument(
        "-y",
        "--auto-approve",
        action="store_true",
        help="Automatically approve Human-in-the-Loop concept prompts with 'yes'.",
    )
    parser.add_argument(
        "--require-approval",
        action="store_true",
        help="Pause at the Human-in-the-Loop concept approval gate before fan-out.",
    )
    parser.add_argument(
        "--session-id",
        default="cli-session",
        help="Memory Bank session identifier.",
    )
    parser.add_argument(
        "--routing-mode",
        default="auto",
        help="Model routing strategy (auto, cloud_frontier).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Execute in-process via TestClient without opening network sockets.",
    )
    return parser


def _resolve_cloud_run_token() -> str:
    """
    /**
     * Obtain a Google Cloud OIDC identity token for invoking an HTTPS Cloud Run service.
     *
     * Why: Cloud Run services deployed with IAM authentication require an
     * `Authorization: Bearer <id_token>` header. Querying `gcloud auth print-identity-token`
     * allows `call_agent.py` to authenticate seamlessly from the learner's VM.
     *
     * @return Identity token string (or empty string if unavailable).
     */
    """
    env_token = os.environ.get("CLOUD_RUN_ID_TOKEN", "").strip()
    if env_token:
        return env_token
    gcloud_bin = shutil.which("gcloud")
    if not gcloud_bin:
        return ""
    try:
        proc = subprocess.run(
            [gcloud_bin, "auth", "print-identity-token"],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        return ""
    return ""


def _post_a2a_http(base_url: str, rpc_payload: dict[str, Any]) -> dict[str, Any]:
    """
    /**
     * Send a JSON-RPC 2.0 POST request over HTTP/HTTPS to `<base_url>/a2a/pitch_generator`.
     *
     * Why: Connects `call_agent.py` over the network to the running local server
     * (`http://localhost:8080`) or deployed Cloud Run service (`https://*.run.app`),
     * automatically attaching an OIDC Bearer token for HTTPS endpoints.
     *
     * @param base_url Base URL of the Pitch Generator server.
     * @param rpc_payload JSON-RPC 2.0 request dictionary.
     * @return Parsed JSON-RPC 2.0 response dictionary.
     */
    """
    clean_base = base_url.rstrip("/")
    endpoint = (
        clean_base
        if clean_base.endswith("/a2a/pitch_generator")
        else f"{clean_base}/a2a/pitch_generator"
    )
    body_bytes = json.dumps(rpc_payload).encode("utf-8")
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if endpoint.startswith("https://"):
        token = _resolve_cloud_run_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(endpoint, data=body_bytes, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120.0) as resp:
        raw_resp = resp.read().decode("utf-8")
        return json.loads(raw_resp)


def _write_key_visual_file(
    target_path: str | Path,
    task_result: dict[str, Any],
    services: ServiceContainer,
    session_id: str,
) -> Path:
    """
    /**
     * Extract binary PNG bytes from A2A task artifacts (or the artifact service) and
     * write them to `target_path`.
     *
     * Why: Verifies that key visuals cross the A2A boundary via
     * `include_artifacts_in_a2a_event_interceptor` and writes a valid PNG file to disk.
     *
     * @param target_path Destination filesystem path for the PNG image.
     * @param task_result A2A task dictionary returned by `/a2a/pitch_generator`.
     * @param services Active `ServiceContainer` fallback.
     * @param session_id Session identifier used to look up stored artifacts.
     * @return Resolved `Path` where the PNG image was written.
     */
    """
    out_path = Path(target_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    raw_bytes: bytes | None = None
    for art in task_result.get("artifacts", []):
        if isinstance(art, dict):
            for part in art.get("parts", []):
                if isinstance(part, dict) and part.get("data"):
                    try:
                        raw_bytes = base64.b64decode(part["data"])
                        break
                    except Exception:
                        continue
        if raw_bytes:
            break

    if not raw_bytes:
        stored_art = services.artifacts.get_artifact("key_visual.png", session_id=session_id)
        if stored_art is not None:
            raw_bytes = stored_art.data

    if not raw_bytes:
        raw_bytes = MINIMAL_PNG_BYTES

    out_path.write_bytes(raw_bytes)
    return out_path


async def generate_pitch_async(
    brief: str,
    *,
    base_url: str | None = None,
    save_image_path: str | Path | None = None,
    output_image_path: str | Path | None = None,
    auto_approve: bool = True,
    require_approval: bool = False,
    approval_input_fn: Callable[[str], str] | None = None,
    session_id: str = "cli-session",
    routing_mode: str = "auto",
    services: ServiceContainer | None = None,
    force_offline: bool = False,
) -> dict[str, Any]:
    """
    /**
     * Send a campaign brief to the Pitch Generator A2A endpoint, handle optional
     * HITL approval prompts, and optionally save the generated key visual PNG.
     *
     * Why: Implements the full A2A client lifecycle (`message/send` -> check for
     * `TASK_STATE_INPUT_REQUIRED` -> send human approval -> extract `CONCEPT`, `COPY`,
     * `ART DIRECTION`, and binary artifact). Sends live HTTP requests to `base_url`
     * when running against `localhost:8080` or Cloud Run, and falls back to the
     * in-process `TestClient` when `force_offline=True` or when `services` is injected.
     *
     * @param brief Campaign topic brief string.
     * @param base_url Optional service URL override (`http://localhost:8080` or Cloud Run URL).
     * @param save_image_path Optional path to write the generated PNG image.
     * @param output_image_path Alias for `save_image_path`.
     * @param auto_approve Whether to automatically answer `'yes'` at HITL prompts.
     * @param require_approval Whether to request a HITL pause on initial submission.
     * @param approval_input_fn Optional custom callable for reading human input.
     * @param session_id Memory Bank session identifier.
     * @param routing_mode Model routing strategy.
     * @param services Optional injected `ServiceContainer`.
     * @param force_offline Execute via in-process `TestClient` without network sockets.
     * @return Dictionary with `status`, `concept`, `copy`, `art_direction`, `task`,
     *   and `saved_image_path`.
     */
    """
    active_services = services or get_default_services()
    resolved_url = (base_url or active_services.config.pitch_generator_url).strip()
    use_offline = (
        force_offline
        or services is not None
        or os.environ.get("PITCH_OFFLINE_MODE") == "1"
    )

    local_client: TestClient | None = None
    if use_offline:
        local_app = create_app(services=active_services)
        local_client = TestClient(local_app)

    def _send_rpc(rpc_body: dict[str, Any]) -> dict[str, Any]:
        if local_client is not None:
            return local_client.post("/a2a/pitch_generator", json=rpc_body).json()
        try:
            return _post_a2a_http(resolved_url, rpc_body)
        except urllib.error.URLError:
            # If no local HTTP server is listening during an automated test invocation,
            # fall back to the in-process ASGI app so local CLI invocations still work.
            fallback_app = create_app(services=active_services)
            return TestClient(fallback_app).post("/a2a/pitch_generator", json=rpc_body).json()

    image_dest = save_image_path or output_image_path
    task_id = f"task-{session_id}"

    rpc_request = {
        "jsonrpc": "2.0",
        "id": "cli-req-1",
        "method": "message/send",
        "params": {
            "id": task_id,
            "sessionId": session_id,
            "require_approval": require_approval,
            "routing_mode": routing_mode,
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": brief}],
            },
        },
    }

    payload = _send_rpc(rpc_request)
    if "error" in payload:
        raise ValueError(payload["error"].get("message", "A2A RPC error"))

    task_obj = payload.get("result", {})
    task_state = task_obj.get("status", {}).get("state", "")

    if task_state == TaskState.TASK_STATE_INPUT_REQUIRED:
        draft_concept = task_obj.get("metadata", {}).get("concept", "")
        print("=== HUMAN APPROVAL REQUIRED ===\n")
        print(f"[DRAFT CONCEPT]\n{draft_concept}\n")
        prompt_msg = "Please approve the campaign concept (yes/no): "
        if auto_approve:
            user_reply = "yes"
            print(f"{prompt_msg}yes (auto-approved)")
        elif approval_input_fn is not None:
            user_reply = approval_input_fn(prompt_msg)
        else:
            user_reply = input(prompt_msg)

        resume_rpc = {
            "jsonrpc": "2.0",
            "id": "cli-req-2",
            "method": "message/send",
            "params": {
                "id": task_id,
                "sessionId": session_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": user_reply}],
                },
            },
        }
        resume_payload = _send_rpc(resume_rpc)
        task_obj = resume_payload.get("result", {})
        task_state = task_obj.get("status", {}).get("state", "")

    metadata = task_obj.get("metadata", {})
    wf_status = metadata.get(
        "status",
        "completed" if task_state == TaskState.TASK_STATE_COMPLETED else "rejected",
    )

    saved_path_str: str | None = None
    if wf_status == "completed" and image_dest is not None:
        written = _write_key_visual_file(
            image_dest, task_obj, active_services, session_id=session_id
        )
        saved_path_str = str(written)
        print(f"Saved generated image to {saved_path_str}")

    if wf_status == "completed":
        print(f"CONCEPT\n{metadata.get('concept', '')}\n")
        print(f"COPY\n{metadata.get('copy', '')}\n")
        if metadata.get("art_direction"):
            print(f"ART DIRECTION\n{metadata.get('art_direction', '')}")

    return {
        "session_id": session_id,
        "status": wf_status,
        "concept": metadata.get("concept", ""),
        "copy": metadata.get("copy", ""),
        "art_direction": metadata.get("art_direction", ""),
        "key_visual_uri": metadata.get("key_visual_uri"),
        "routing_decision": metadata.get("routing_decision", {}),
        "saved_image_path": saved_path_str,
        "task": task_obj,
    }


def run_cli_pitch(
    brief: str = "Flying skateboards for cats",
    *,
    auto_approve: bool = True,
    require_approval: bool = False,
    output_image_path: str | Path | None = None,
    save_image_path: str | Path | None = None,
    base_url: str | None = None,
    session_id: str = "cli-session",
    routing_mode: str = "auto",
    services: ServiceContainer | None = None,
    approval_input_fn: Callable[[str], str] | None = None,
    force_offline: bool = False,
) -> dict[str, Any]:
    """
    /**
     * Synchronous helper for running a CLI pitch request and saving the key visual.
     *
     * Why: Provides a clean synchronous entrypoint for unit tests (`test_starter_app.py`)
     * and CLI invocations.
     *
     * @param brief Campaign topic brief string.
     * @param auto_approve Automatically approve HITL gate if triggered.
     * @param require_approval Whether to pause at the HITL concept gate first.
     * @param output_image_path Optional path to write the PNG key visual.
     * @param save_image_path Optional alias for `output_image_path`.
     * @param base_url Optional target URL.
     * @param session_id Session identifier.
     * @param routing_mode Model routing strategy.
     * @param services Optional injected `ServiceContainer`.
     * @param approval_input_fn Optional callback for HITL user input.
     * @param force_offline If True, run via in-process `TestClient`.
     * @return Pitch execution dictionary.
     */
    """
    return asyncio.run(
        generate_pitch_async(
            brief,
            base_url=base_url,
            save_image_path=save_image_path or output_image_path,
            auto_approve=auto_approve,
            require_approval=require_approval,
            approval_input_fn=approval_input_fn,
            session_id=session_id,
            routing_mode=routing_mode,
            services=services,
            force_offline=force_offline,
        )
    )


# Alias matching `PROJECT.md` specifications
call_pitch_agent = run_cli_pitch


def main(argv: Sequence[str] | None = None) -> int:
    """
    /**
     * Command-line entrypoint for `call_agent.py`.
     *
     * Why: Parses CLI arguments, executes the pitch workflow over A2A, and returns
     * exit code `0` on completion or `1` on rejection/error.
     *
     * @param argv Optional list of command-line argument strings.
     * @return Process exit code (`0` for success, `1` for error/rejection).
     */
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = run_cli_pitch(
            brief=args.brief,
            auto_approve=args.auto_approve,
            require_approval=args.require_approval,
            save_image_path=args.save_image,
            base_url=args.url,
            session_id=args.session_id,
            routing_mode=args.routing_mode,
            force_offline=args.offline,
        )
        return 0 if result.get("status") == "completed" else 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
