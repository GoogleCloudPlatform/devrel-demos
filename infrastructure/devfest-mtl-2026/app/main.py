# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Lightweight FastAPI Web Application for the DevFest Montréal ADK + AlloyDB MCP Agent.

Run locally:
    uvicorn app.main:app --reload --port 8080
"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field

load_dotenv()

from support_agent.agent import root_agent  # noqa: E402

APP_NAME = "montreal_support_triage"
STATIC_DIR = Path(__file__).parent / "static"
SKILL_TOOL_NAMES = {"load_skill", "load_skill_resource", "list_skills"}

app = FastAPI(title="From Data to Action — ADK + AlloyDB MCP Triage Console")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


class ChatRequest(BaseModel):
    message: str
    user_id: str = "devfest_demo_user"
    session_id: str = Field(default_factory=lambda: f"session-{uuid.uuid4().hex[:10]}")


def _extract_event_steps(event: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """Extract skill/MCP tool calls, tool responses, and final text chunks from an ADK Event."""
    steps: list[dict[str, Any]] = []
    text_chunks: list[str] = []

    for fc in event.get_function_calls() or []:
        kind = "skill" if fc.name in SKILL_TOOL_NAMES else "mcp_tool"
        steps.append(
            {
                "type": kind,
                "name": fc.name,
                "args": dict(fc.args) if fc.args else {},
            }
        )

    for fr in event.get_function_responses() or []:
        preview = str(fr.response)
        steps.append(
            {
                "type": "tool_result",
                "name": fr.name,
                "preview": preview[:600] + ("..." if len(preview) > 600 else ""),
            }
        )

    if event.is_final_response() and event.content and event.content.parts:
        for part in event.content.parts:
            if getattr(part, "text", None):
                text_chunks.append(part.text)

    return steps, text_chunks


async def _ensure_session(user_id: str, session_id: str) -> None:
    existing = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@app.get("/api/status")
async def status() -> dict[str, Any]:
    mcp_mode = os.getenv("MCP_MODE", "toolbox").lower()
    return {
        "agent": "support_data_agent",
        "model": os.getenv("ADK_MODEL", "gemini-2.5-flash"),
        "mcp_mode": mcp_mode,
        "endpoint": (
            os.getenv("ALLOYDB_MCP_URL", "https://alloydb.googleapis.com/mcp")
            if mcp_mode == "remote"
            else os.getenv("TOOLBOX_URL", "http://127.0.0.1:5000")
        ),
        "alloydb_cluster": os.getenv("ALLOYDB_CLUSTER", "devfest-cluster"),
        "alloydb_region": os.getenv("ALLOYDB_REGION", "us-west1"),
        "read_only": os.getenv("MCP_READ_ONLY", "false").lower() == "true",
    }


@app.post("/api/chat")
async def chat(req: ChatRequest) -> dict[str, Any]:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    await _ensure_session(req.user_id, req.session_id)
    user_content = types.Content(
        role="user", parts=[types.Part.from_text(text=req.message)]
    )

    trace_steps: list[dict[str, Any]] = []
    final_chunks: list[str] = []

    async for event in runner.run_async(
        user_id=req.user_id,
        session_id=req.session_id,
        new_message=user_content,
    ):
        steps, texts = _extract_event_steps(event)
        trace_steps.extend(steps)
        final_chunks.extend(texts)

    return {
        "reply": "\n".join(final_chunks).strip() or "(No text response returned)",
        "trace": trace_steps,
        "session_id": req.session_id,
        "mcp_mode": os.getenv("MCP_MODE", "toolbox").lower(),
    }


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message must not be empty.")

    await _ensure_session(req.user_id, req.session_id)
    user_content = types.Content(
        role="user", parts=[types.Part.from_text(text=req.message)]
    )

    async def event_generator() -> AsyncIterator[str]:
        final_chunks: list[str] = []
        step_count = 0
        try:
            async for event in runner.run_async(
                user_id=req.user_id,
                session_id=req.session_id,
                new_message=user_content,
            ):
                steps, texts = _extract_event_steps(event)
                for step in steps:
                    step_count += 1
                    yield json.dumps({"event": "trace", "step": step}) + "\n"
                final_chunks.extend(texts)

            yield json.dumps(
                {
                    "event": "final",
                    "reply": "\n".join(final_chunks).strip() or "(No text response returned)",
                    "step_count": step_count,
                    "session_id": req.session_id,
                    "mcp_mode": os.getenv("MCP_MODE", "toolbox").lower(),
                }
            ) + "\n"
        except Exception as exc:
            yield json.dumps({"event": "error", "message": str(exc)}) + "\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
