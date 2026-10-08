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
 * @file a2a.py
 * @description Agent2Agent (A2A) protocol v0.3 card builder, artifact event interceptor,
 *   executor, and JSON-RPC 2.0 request handler.
 *
 * Why: Enables both the coordinator `pitch_generator` service and the remote
 * `visual_director` specialist service to publish standardized discovery cards at
 * `/.well-known/agent-card.json`, exchange JSON-RPC 2.0 `message/send` and HITL
 * approval tasks, and stream binary key visual artifacts across service boundaries
 * (`en.md` L682-750) while executing 100% offline in local test suites.
 */
"""

from __future__ import annotations

import base64
import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Generator
import uuid

from pitch_generator.app_utils.services import (
    ArtifactRecord,
    ServiceContainer,
    get_default_services,
)

AGENT_CARD_WELL_KNOWN_PATH = "/.well-known/agent-card.json"


class TaskState:
    """
    /**
     * Standard A2A protocol task lifecycle state constants.
     *
     * Why: Mirrors `a2a.types.TaskState` (`TASK_STATE_COMPLETED`,
     * `TASK_STATE_INPUT_REQUIRED`, `TASK_STATE_FAILED`, `TASK_STATE_REJECTED`) so
     * `call_agent.py` and remote A2A clients can inspect task states without
     * requiring external protobuf wheels in offline environments.
     */
    """

    TASK_STATE_SUBMITTED = "TASK_STATE_SUBMITTED"
    TASK_STATE_WORKING = "TASK_STATE_WORKING"
    TASK_STATE_INPUT_REQUIRED = "TASK_STATE_INPUT_REQUIRED"
    TASK_STATE_COMPLETED = "TASK_STATE_COMPLETED"
    TASK_STATE_FAILED = "TASK_STATE_FAILED"
    TASK_STATE_CANCELED = "TASK_STATE_CANCELED"
    TASK_STATE_REJECTED = "TASK_STATE_REJECTED"


class _DualSyncAsyncDict(dict):
    """
    /**
     * Dictionary subclass that is ALSO awaitable (`await builder.build()`).
     *
     * Why: Part 1's `attach_a2a_routes` calls `await AgentCardBuilder(...).build()`
     * asynchronously, whereas synchronous unit tests often call `builder.build()`
     * directly. Returning a `_DualSyncAsyncDict` satisfies both calling conventions
     * with zero friction.
     */
    """

    def __await__(self) -> Generator[Any, None, dict[str, Any]]:
        """
        /**
         * Yield control once and return `dict(self)` when awaited inside a coroutine.
         *
         * Why: Implements Python's awaitable protocol on top of a standard `dict`.
         *
         * @return Standard dictionary copy of the agent card.
         */
        """
        async def _coro() -> dict[str, Any]:
            return dict(self)

        return _coro().__await__()


class AgentCardBuilder:
    """
    /**
     * Builder that introspects an ADK `Agent` or `Workflow` and produces an A2A v0.3
     * Agent Card JSON dictionary.
     *
     * Why: Automates creation of the `/.well-known/agent-card.json` discovery payload
     * (including agent name, description, RPC endpoint URL, capabilities, and tool
     * skills) so remote `RemoteA2aAgent` clients can discover specialist capabilities
     * dynamically (`en.md` L690-715).
     */
    """

    def __init__(
        self,
        agent: Any,
        rpc_url: str,
        protocol_version: str = "0.3",
    ) -> None:
        """
        /**
         * Initialize the Agent Card builder.
         *
         * Why: Captures the target agent and its public JSON-RPC endpoint URL.
         *
         * @param agent ADK `Agent` or `Workflow` instance to introspect.
         * @param rpc_url Public URL where JSON-RPC 2.0 requests are handled.
         * @param protocol_version A2A protocol version string (default `"0.3"`).
         */
        """
        if agent is None:
            raise ValueError("agent must not be None")
        if not isinstance(rpc_url, str) or not rpc_url.strip():
            raise ValueError("rpc_url must not be empty")
        self.agent = agent
        self.rpc_url = rpc_url.strip()
        self.protocol_version = protocol_version

    def build(self) -> _DualSyncAsyncDict:
        """
        /**
         * Construct the A2A Agent Card dictionary (usable both sync and via `await`).
         *
         * Why: Inspects the agent's `name`, `description`, `instruction`, and attached
         * `tools` (or workflow nodes) to populate the `skills` array expected by A2A
         * discovery checks.
         *
         * @return `_DualSyncAsyncDict` representing the A2A Agent Card.
         */
        """
        agent_name = getattr(self.agent, "name", None) or "pitch_generator"
        agent_desc = (
            getattr(self.agent, "description", None)
            or "Multi-agent campaign pitch generator on Gemini Enterprise Agent Platform."
        )

        skills: list[dict[str, Any]] = [
            {
                "id": agent_name,
                "name": agent_name,
                "description": f"{agent_desc} {getattr(self.agent, 'instruction', '')}".strip(),
                "tags": ["llm", "adk", "pitch-generator"],
            }
        ]

        raw_tools = getattr(self.agent, "tools", None) or []
        for tool_item in raw_tools:
            if callable(tool_item):
                t_name = getattr(tool_item, "__name__", "custom_tool")
                t_doc = (getattr(tool_item, "__doc__", "") or "").strip()
                skills.append(
                    {
                        "id": f"{agent_name}-{t_name}",
                        "name": t_name,
                        "description": t_doc or f"Tool {t_name}",
                        "tags": ["custom_tool"],
                    }
                )
            elif hasattr(tool_item, "skills"):
                for sk in getattr(tool_item, "skills", []):
                    sk_name = getattr(sk, "name", "agent_skill")
                    sk_desc = getattr(sk, "description", "Agent skill")
                    skills.append(
                        {
                            "id": f"{agent_name}-{sk_name}",
                            "name": sk_name,
                            "description": sk_desc,
                            "tags": ["skill_toolset"],
                        }
                    )

        card = {
            "name": agent_name,
            "description": agent_desc,
            "url": self.rpc_url,
            "preferredTransport": "JSONRPC",
            "protocolVersion": self.protocol_version,
            "capabilities": {
                "streaming": False,
                "artifacts": True,
                "hitl": True,
            },
            "defaultInputModes": ["text/plain", "application/json"],
            "defaultOutputModes": ["text/plain", "image/png", "application/json"],
            "skills": skills,
        }
        return _DualSyncAsyncDict(card)


def include_artifacts_in_a2a_event_interceptor(
    event: dict[str, Any],
    artifacts: list[Any] | None = None,
) -> dict[str, Any]:
    """
    /**
     * A2A execution interceptor that attaches saved binary artifacts onto outgoing
     * A2A task events.
     *
     * Why: By default, `ctx.save_artifact()` persists binary images (like `key_visual.png`)
     * to the local or GCS artifact store, but does not automatically inline them into
     * the outgoing A2A JSON-RPC response. This interceptor bridges the artifact store
     * to the A2A wire payload so remote callers receive both the text pitch and the
     * rendered image (`en.md` L735-748).
     *
     * @param event Outgoing A2A event or task result dictionary.
     * @param artifacts Optional list of `ArtifactRecord` or metadata dicts to attach.
     * @return Enriched A2A event dictionary containing `artifacts`.
     */
    """
    if not isinstance(event, dict):
        raise ValueError("event must be a dictionary")

    updated = copy.deepcopy(event)
    existing_artifacts = list(updated.get("artifacts", []))

    for art in artifacts or []:
        if isinstance(art, ArtifactRecord):
            encoded = base64.b64encode(art.data).decode("ascii")
            existing_artifacts.append(
                {
                    "name": art.filename,
                    "version": art.version,
                    "mimeType": art.mime_type,
                    "uri": art.gcs_uri,
                    "parts": [
                        {
                            "type": "data",
                            "mimeType": art.mime_type,
                            "data": encoded,
                            "bytes": len(art.data),
                        }
                    ],
                }
            )
        elif isinstance(art, dict):
            raw_bytes = art.get("data")
            if isinstance(raw_bytes, (bytes, bytearray)):
                encoded = base64.b64encode(bytes(raw_bytes)).decode("ascii")
            else:
                encoded = str(raw_bytes or "")
            existing_artifacts.append(
                {
                    "name": art.get("filename") or art.get("name") or "key_visual.png",
                    "version": int(art.get("version", 1)),
                    "mimeType": art.get("mime_type") or art.get("mimeType") or "image/png",
                    "uri": art.get("gcs_uri") or art.get("uri"),
                    "parts": [
                        {
                            "type": "data",
                            "mimeType": art.get("mime_type") or "image/png",
                            "data": encoded,
                            "bytes": art.get("bytes", 0),
                        }
                    ],
                }
            )

    updated["artifacts"] = existing_artifacts
    return updated


@dataclass
class A2aAgentExecutorConfig:
    """
    /**
     * Configuration container for `A2aAgentExecutor`.
     *
     * Why: Allows registering post-execution event interceptors such as
     * `include_artifacts_in_a2a_event_interceptor` (`en.md` L737).
     *
     * @param execute_interceptors List of interceptor callables applied to A2A events.
     */
    """

    execute_interceptors: list[Callable[..., Any]] = field(default_factory=list)


class A2aAgentExecutor:
    """
    /**
     * Executor that bridges an ADK `Runner` / workflow to the A2A request handler.
     *
     * Why: Runs the multi-agent workflow for incoming A2A requests and passes the
     * resulting event and session artifacts through configured `execute_interceptors`.
     */
    """

    def __init__(
        self,
        runner: Any = None,
        force_new_version: bool = True,
        config: A2aAgentExecutorConfig | None = None,
    ) -> None:
        """
        /**
         * Initialize the A2A agent executor.
         *
         * Why: Stores the ADK runner (or workflow callable) and interceptor pipeline.
         *
         * @param runner Optional ADK runner or agent callable.
         * @param force_new_version Whether artifact saves always increment version numbers.
         * @param config Optional `A2aAgentExecutorConfig` with interceptors.
         */
        """
        self.runner = runner
        self.force_new_version = force_new_version
        self.config = config or A2aAgentExecutorConfig(
            execute_interceptors=[include_artifacts_in_a2a_event_interceptor]
        )

    def execute(
        self,
        brief: str,
        *,
        session_id: str = "default",
        approved: bool | None = True,
        require_approval: bool = False,
        routing_mode: str = "auto",
        services: ServiceContainer | None = None,
    ) -> dict[str, Any]:
        """
        /**
         * Execute the Pitch Generator workflow for an A2A task and apply interceptors.
         *
         * Why: Invokes `run_pitch_workflow` with the injected `ServiceContainer` and
         * attaches binary artifacts via `self.config.execute_interceptors`.
         *
         * @param brief Campaign brief text extracted from the A2A message.
         * @param session_id Session identifier for Memory Bank continuity.
         * @param approved Approval flag (`True`, `False`, or `None` for pending).
         * @param require_approval Whether to pause at the HITL concept gate.
         * @param routing_mode Model routing strategy.
         * @param services Optional injected `ServiceContainer`.
         * @return Enriched workflow and A2A event dictionary.
         */
        """
        from pitch_generator.agent import run_pitch_workflow

        active_services = services or get_default_services()
        workflow_result = run_pitch_workflow(
            brief,
            session_id=session_id,
            services=active_services,
            approved=approved,
            routing_mode=routing_mode,
            require_approval=require_approval,
        )

        session_artifacts = active_services.artifacts.list_artifacts(session_id=session_id)
        event_payload = dict(workflow_result)
        for interceptor in self.config.execute_interceptors:
            event_payload = interceptor(event_payload, session_artifacts)
        return event_payload


class DefaultRequestHandler:
    """
    /**
     * JSON-RPC 2.0 request dispatcher for A2A protocol endpoints.
     *
     * Why: Handles standard A2A methods (`message/send`, `tasks/send`, `tasks/get`,
     * `tasks/approval`) including Human-in-the-Loop `TASK_STATE_INPUT_REQUIRED` pauses
     * and resumption over a single `/a2a/pitch_generator` endpoint.
     */
    """

    def __init__(
        self,
        agent_executor: A2aAgentExecutor | None = None,
        task_store: dict[str, dict[str, Any]] | None = None,
        agent_card: dict[str, Any] | None = None,
    ) -> None:
        """
        /**
         * Initialize the A2A request handler.
         *
         * Why: Maintains an in-memory `task_store` mapping `task_id` to task state so
         * follow-up HITL approval messages can resume paused tasks.
         *
         * @param agent_executor `A2aAgentExecutor` instance.
         * @param task_store Optional dictionary backing task persistence.
         * @param agent_card Optional pre-built A2A Agent Card dictionary.
         */
        """
        self.agent_executor = agent_executor or A2aAgentExecutor()
        self.task_store: dict[str, dict[str, Any]] = task_store if task_store is not None else {}
        self.agent_card = agent_card or {}

    def handle_rpc(
        self,
        payload: dict[str, Any],
        services: ServiceContainer | None = None,
    ) -> dict[str, Any]:
        """
        /**
         * Process a JSON-RPC 2.0 request dictionary and return a JSON-RPC 2.0 response.
         *
         * Why: Validates JSON-RPC framing, extracts prompt parts or approval decisions,
         * delegates execution to `self.agent_executor`, and formats the response with
         * standard A2A task status and artifacts.
         *
         * @param payload Parsed JSON-RPC 2.0 request dictionary.
         * @param services Optional injected `ServiceContainer`.
         * @return JSON-RPC 2.0 response dictionary (`{"jsonrpc": "2.0", "id": ..., "result": ...}`).
         */
        """
        if not isinstance(payload, dict):
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32600, "message": "Invalid Request: expected JSON object"},
            }

        req_id = payload.get("id", "req-1")
        method = str(payload.get("method", "message/send"))
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        if method not in {
            "message/send",
            "tasks/send",
            "tasks/resubscribe",
            "tasks/get",
            "tasks/approval",
        }:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        task_id = str(params.get("id") or params.get("taskId") or f"task-{uuid.uuid4().hex[:8]}")
        session_id = str(
            params.get("sessionId")
            or params.get("session_id")
            or params.get("contextId")
            or task_id
        )

        if method == "tasks/get":
            stored = self.task_store.get(task_id)
            if stored is None:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32001, "message": f"Task not found: {task_id}"},
                }
            return {"jsonrpc": "2.0", "id": req_id, "result": stored}

        text_input = self._extract_message_text(params)
        require_approval = bool(params.get("require_approval", False))
        routing_mode = str(params.get("routing_mode", "auto"))

        # Check if this message is resuming a paused HITL task
        existing_task = self.task_store.get(task_id)
        if (
            method == "tasks/approval"
            or (
                existing_task is not None
                and existing_task.get("status", {}).get("state")
                == TaskState.TASK_STATE_INPUT_REQUIRED
            )
        ):
            from pitch_generator.agent import resume_pitch_workflow

            active_services = services or get_default_services()
            if "approved" in params:
                is_approved = bool(params["approved"])
            else:
                normalized_reply = text_input.strip().lower()
                is_approved = normalized_reply in {"yes", "y", "true", "approve", "approved"}

            try:
                resumed = resume_pitch_workflow(
                    session_id,
                    approved=is_approved,
                    feedback=str(params.get("feedback", text_input)),
                    services=active_services,
                )
            except (ValueError, RuntimeError) as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(exc)},
                }
            session_artifacts = active_services.artifacts.list_artifacts(session_id=session_id)
            enriched = include_artifacts_in_a2a_event_interceptor(resumed, session_artifacts)
            task_result = self._build_task_object(task_id, session_id, enriched)
            self.task_store[task_id] = task_result
            return {"jsonrpc": "2.0", "id": req_id, "result": task_result}

        if not text_input.strip():
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": "Invalid params: message text must not be empty"},
            }

        approved_param: bool | None = params.get("approved", None if require_approval else True)
        try:
            event_data = self.agent_executor.execute(
                text_input,
                session_id=session_id,
                approved=approved_param,
                require_approval=require_approval,
                routing_mode=routing_mode,
                services=services,
            )
        except (ValueError, RuntimeError) as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32000, "message": str(exc)},
            }
        task_result = self._build_task_object(task_id, session_id, event_data)
        self.task_store[task_id] = task_result
        return {"jsonrpc": "2.0", "id": req_id, "result": task_result}

    def _extract_message_text(self, params: dict[str, Any]) -> str:
        """
        /**
         * Extract plain text from an A2A `params.message.parts` array or fallback fields.
         *
         * Why: A2A clients may send parts as `[{"type": "text", "text": "..."}]`,
         * `[{"text": "..."}]`, or top-level `prompt`/`brief` keys.
         *
         * @param params JSON-RPC `params` dictionary.
         * @return Extracted text string.
         */
        """
        msg = params.get("message")
        if isinstance(msg, dict):
            parts = msg.get("parts") or []
            texts: list[str] = []
            for part in parts:
                if isinstance(part, dict) and "text" in part and part["text"]:
                    texts.append(str(part["text"]))
            if texts:
                return "\n".join(texts)
        for fallback_key in ("brief", "prompt", "text"):
            if fallback_key in params and params[fallback_key]:
                return str(params[fallback_key])
        return ""

    def _build_task_object(
        self,
        task_id: str,
        session_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        /**
         * Format workflow execution output into a standard A2A `Task` dictionary.
         *
         * Why: Maps internal workflow status (`"completed"`, `"input_required"`,
         * `"rejected"`) onto `TaskState` constants and populates `status.message.parts`
         * (including `adk_request_input` metadata when paused for HITL approval).
         *
         * @param task_id Unique A2A task identifier.
         * @param session_id Memory Bank session identifier.
         * @param event_data Workflow execution result dictionary.
         * @return A2A task dictionary.
         */
        """
        wf_status = event_data.get("status", "completed")
        if wf_status == "input_required":
            state_str = TaskState.TASK_STATE_INPUT_REQUIRED
            parts = [
                {
                    "type": "text",
                    "text": str(event_data.get("concept", "")),
                    "metadata": {"adk_type": "draft_concept"},
                },
                {
                    "type": "text",
                    "text": str(
                        event_data.get("prompt", "Please approve the campaign concept (yes/no).")
                    ),
                    "metadata": {"adk_request_input": True},
                },
            ]
        elif wf_status == "rejected":
            state_str = TaskState.TASK_STATE_REJECTED
            parts = [{"type": "text", "text": "User rejected the concept."}]
        else:
            state_str = TaskState.TASK_STATE_COMPLETED
            pitch_text = str(
                event_data.get("pitch_text")
                or f"CONCEPT\n{event_data.get('concept', '')}\n\nCOPY\n{event_data.get('copy', '')}"
            )
            parts = [{"type": "text", "text": pitch_text}]

        return {
            "id": task_id,
            "sessionId": session_id,
            "status": {
                "state": state_str,
                "message": {
                    "role": "agent",
                    "parts": parts,
                },
            },
            "artifacts": event_data.get("artifacts", []),
            "metadata": {
                "status": wf_status,
                "concept": event_data.get("concept", ""),
                "copy": event_data.get("copy", ""),
                "art_direction": event_data.get("art_direction", ""),
                "key_visual_uri": event_data.get("key_visual_uri"),
                "routing_decision": event_data.get("routing_decision", {}),
            },
        }


async def attach_a2a_routes(
    app: Any,
    agent: Any,
    runner: Any = None,
    rpc_path: str = "/a2a/pitch_generator",
    app_url: str | None = None,
) -> DefaultRequestHandler:
    """
    /**
     * Build the A2A Agent Card and register discovery + JSON-RPC routes on `app`.
     *
     * Why: Replicates the Part 1 `attach_a2a_routes` helper (`en.md` L688-748) so
     * FastAPI apps expose both `GET <rpc_path>/.well-known/agent-card.json` and
     * `POST <rpc_path>` with artifact interception enabled.
     *
     * @param app FastAPI (or FastAPIShim) application instance.
     * @param agent Root ADK `Agent` or `Workflow` to expose over A2A.
     * @param runner Optional ADK `Runner` instance.
     * @param rpc_path URL path prefix for the A2A endpoint.
     * @param app_url Optional public base URL for the service.
     * @return Configured `DefaultRequestHandler` instance.
     */
    """
    base_url = (app_url or "http://localhost:8000").rstrip("/")
    clean_rpc_path = "/" + rpc_path.strip("/")
    full_rpc_url = f"{base_url}{clean_rpc_path}"

    card = await AgentCardBuilder(agent=agent, rpc_url=full_rpc_url).build()
    executor_config = A2aAgentExecutorConfig(
        execute_interceptors=[include_artifacts_in_a2a_event_interceptor]
    )
    executor = A2aAgentExecutor(
        runner=runner,
        force_new_version=True,
        config=executor_config,
    )
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store={},
        agent_card=card,
    )
    if hasattr(app, "register_a2a_handler"):
        app.register_a2a_handler(clean_rpc_path, handler, card)
    return handler
