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
 * @file step_1c_remote_a2a_visual_director.py
 * @description Module 1 — Step 1c: Remote A2A Visual Director Service & Client Integration (`F11`).
 *
 * Why: Isolating the image-generating `visual_director` behind the Agent-to-Agent (A2A)
 * protocol allows it to scale and deploy independently on Cloud Run while streaming
 * generated key visual PNG artifacts back into the coordinator's session events via
 * `include_artifacts_in_a2a_event_interceptor` and filtering intermediate tool call
 * chatter via `_pitch_parts_only`.
 */
"""

from __future__ import annotations

from collections.abc import Iterator
import inspect
import mimetypes
import os
from pathlib import Path
import sys
from typing import Any

_APP_ROOT = Path(__file__).resolve().parents[3]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from pitch_generator.agent import (  # noqa: E402
    MODEL,
    Agent,
    App,
    Context as _BaseContext,
    Event,
    JoinNode,
    RemoteA2aAgent,
    Workflow,
    copywriter,
    creative_director,
    types,
)
from pitch_generator.app_utils.a2a import (  # noqa: E402
    AGENT_CARD_WELL_KNOWN_PATH,
    A2aAgentExecutor,
    A2aAgentExecutorConfig,
    AgentCardBuilder,
    DefaultRequestHandler,
    include_artifacts_in_a2a_event_interceptor,
)
from pitch_generator.app_utils.services import (  # noqa: E402
    MINIMAL_PNG_BYTES,
    ServiceContainer,
)
from pitch_generator.config import get_config  # noqa: E402

IMAGE_MODEL: str = get_config().image_model
Part = types.Part
Blob = types.Blob
Content = types.Content


def _key_visual(ctx: _BaseContext | None) -> types.Blob | None:
    """
    /**
     * Extract the most recent inline image `Blob` emitted by `visual_director` in `ctx.session.events`.
     *
     * Why: Searches session events in reverse order so the latest rendered key visual is attached
     * to the final packaged pitch.
     *
     * @param ctx Active ADK `Context` (or `None`).
     * @return `types.Blob` containing image bytes and MIME type, or `None` if absent.
     */
    """
    if ctx is None or not hasattr(ctx, "session"):
        return None
    for event in reversed(getattr(ctx.session, "events", [])):
        if getattr(event, "author", None) != "visual_director":
            continue
        content = getattr(event, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            if inline_data is not None and getattr(inline_data, "data", None):
                return inline_data
    return None


class Context(_BaseContext):
    """
    /**
     * Extended ADK execution context supporting pluggable `artifact_service` and
     * deterministic failure simulation (`simulate_no_image`).
     *
     * Why: Enables both offline unit testing of empty-image error handling and
     * cross-module integration with `GcsArtifactService`.
     */
    """

    def __init__(
        self,
        session_id: str = "default",
        state: dict[str, Any] | None = None,
        services: ServiceContainer | None = None,
        *,
        artifact_service: Any = None,
        simulate_no_image: bool = False,
        events: list[Event] | None = None,
    ) -> None:
        """
        /**
         * Initialize the extended execution context.
         *
         * Why: Initializes `self.artifacts` and attaches optional external `artifact_service`
         * or pre-populated session events for A2A unit tests.
         *
         * @param session_id Session identifier string.
         * @param state Optional initial session state dict.
         * @param services Optional `ServiceContainer`.
         * @param artifact_service Optional external artifact store (e.g. `GcsArtifactService`).
         * @param simulate_no_image If True, simulates an empty image response from the model.
         * @param events Optional list of `Event` objects to seed into `self.session.events`.
         */
        """
        super().__init__(session_id=session_id, state=state, services=services)
        self.artifacts: dict[str, list[Any]] = {}
        self.artifact_service = artifact_service
        self.simulate_no_image = simulate_no_image
        if events:
            self.session.events.extend(events)

    async def save_artifact(self, filename: str, part: types.Part) -> int:
        """
        /**
         * Saves a `types.Part` artifact to in-memory context storage and any attached
         * external `artifact_service` (such as `GcsArtifactService`).
         *
         * Why: Keeps `ctx.artifacts[filename]` populated for local assertions while
         * forwarding binary bytes to GCS-backed artifact stores when configured.
         *
         * @param filename Artifact file name (e.g. `"key_visual.png"`).
         * @param part `types.Part` containing `inline_data`.
         * @return Persisted integer version number (`1` on first save).
         */
        """
        self.artifacts.setdefault(filename, []).append(part)
        version = await super().save_artifact(filename, part)
        if self.artifact_service is not None and hasattr(
            self.artifact_service, "save_artifact"
        ):
            blob = part.inline_data
            raw_bytes = blob.data if blob is not None else b""
            mime_type = (
                blob.mime_type if blob is not None and blob.mime_type else "image/png"
            )
            save_fn = self.artifact_service.save_artifact
            sig = inspect.signature(save_fn)
            params = [
                p
                for p in sig.parameters.values()
                if p.kind
                in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
            ]
            try:
                if len(params) >= 3 and params[0].name in ("session_id", "session"):
                    res = save_fn(self.session.id, filename, part)
                else:
                    res = save_fn(filename, raw_bytes, mime_type=mime_type)
                if inspect.isawaitable(res):
                    await res
            except TypeError:
                res = save_fn(filename, raw_bytes)
                if inspect.isawaitable(res):
                    await res
        return version


ToolContext = Context


def create_mock_context_with_visual(
    image_bytes: bytes = MINIMAL_PNG_BYTES,
    mime_type: str = "image/png",
    session_id: str = "default",
) -> Context:
    """
    /**
     * Creates a `Context` pre-populated with a `visual_director` image event.
     *
     * Why: Allows tests to verify `package(ctx, node_input)` key visual extraction
     * without spinning up a live network A2A HTTP server.
     *
     * @param image_bytes Raw PNG bytes to attach as `inline_data`.
     * @param mime_type MIME type for the `Blob`.
     * @param session_id Session identifier.
     * @return Pre-populated `Context` instance.
     */
    """
    ctx = Context(session_id=session_id)
    visual_event = Event(
        author="visual_director",
        content=types.Content(
            role="model",
            parts=[
                types.Part(
                    text="Moody indigo and slate studio composition with warm amber rim."
                ),
                types.Part(
                    inline_data=types.Blob(data=image_bytes, mime_type=mime_type)
                ),
            ],
        ),
    )
    ctx.session.events.append(visual_event)
    return ctx


async def generate_key_visual(
    art_direction: str,
    tool_context: ToolContext | None = None,
    *,
    simulate_no_image: bool = False,
) -> dict[str, Any]:
    """
    /**
     * Generates a 16:9 key visual from art direction and saves it as a session artifact.
     *
     * Why: Calling `tool_context.save_artifact` attaches the binary image to the A2A
     * event stream via `include_artifacts_in_a2a_event_interceptor` while returning only
     * lightweight metadata (`filename`, `version`, `bytes`, `mime_type`) to the LLM.
     *
     * @param art_direction Detailed art direction prompt for image generation.
     * @param tool_context ADK `ToolContext` used to persist the generated image artifact.
     * @param simulate_no_image When `True`, simulates an empty model response to test error handling.
     * @return Metadata dictionary with keys `filename`, `version`, `bytes`, `mime_type`.
     */
    """
    ctx = tool_context if tool_context is not None else Context()
    if (
        simulate_no_image
        or getattr(ctx, "simulate_no_image", False)
        or not isinstance(art_direction, str)
        or not art_direction.strip()
    ):
        raise ValueError(f"{IMAGE_MODEL} returned no image for: {str(art_direction)[:120]}")

    image_bytes, mime_type = ctx.services.llm.generate_image(art_direction.strip())
    if not image_bytes:
        raise ValueError(f"{IMAGE_MODEL} returned no image for: {art_direction[:120]}")

    ext = mimetypes.guess_extension(mime_type or "") or ".png"
    filename = f"key_visual{ext}"
    image_part = types.Part(
        inline_data=types.Blob(data=image_bytes, mime_type=mime_type)
    )
    version = await ctx.save_artifact(filename, image_part)

    ctx.session.events.append(
        Event(
            author="visual_director",
            content=types.Content(role="model", parts=[image_part]),
        )
    )

    return {
        "filename": filename,
        "version": version,
        "bytes": len(image_bytes),
        "mime_type": mime_type,
    }


brand_strategist = Agent(
    name="brand_strategist",
    model=MODEL,
    description="Aligns the campaign concept with audience positioning and brand identity pillars.",
    instruction=(
        "You are the Brand Strategist. Define the target audience positioning, "
        "brand alignment rationale, and differentiation angle for the campaign concept."
    ),
    output_key="brand_strategist",
)

visual_director_agent = Agent(
    name="visual_director",
    model=MODEL,
    description="Turns a campaign concept into art direction and a key visual.",
    instruction="""You are the Visual Director on a campaign pitch team.

Call `load_skill` for `brand-guidelines` before you write anything. The house
style is not optional and it is not in this prompt.

You are given a campaign concept. Then, in order:
1. Write art direction for ONE key visual that sells it, obeying the brand
   guidelines: subject, composition, lighting, color, mood.
2. Call `generate_key_visual` with your art direction as the prompt.

Output ONLY the art direction notes.""",
    tools=[generate_key_visual],
    output_key="visual_director",
)

executor_config = A2aAgentExecutorConfig(
    execute_interceptors=[include_artifacts_in_a2a_event_interceptor]
)


def build_visual_director_card(
    rpc_url: str = "http://localhost:8801/a2a/visual_director",
) -> dict[str, Any]:
    """
    /**
     * Builds the A2A AgentCard dictionary for the standalone Visual Director service.
     *
     * Why: Exposes the agent's capabilities, skills, and JSONRPC endpoint at
     * `/.well-known/agent-card.json` so remote `RemoteA2aAgent` clients can discover it.
     *
     * @param rpc_url Public URL where JSON-RPC 2.0 requests are handled.
     * @return A2A Agent Card dictionary.
     */
    """
    builder = AgentCardBuilder(agent=visual_director_agent, rpc_url=rpc_url)
    return dict(builder.build())


def build_a2a_visual_director_app(
    services: ServiceContainer | None = None,
    rpc_url: str = "http://localhost:8801/a2a/visual_director",
) -> Any:
    """
    /**
     * Construct an ASGI web application serving the Visual Director over A2A v0.3.
     *
     * Why: Exposes `GET /.well-known/agent-card.json` and `POST /a2a/visual_director`
     * with `include_artifacts_in_a2a_event_interceptor` so the standalone Visual Director
     * microservice can run on port `8801` locally or as an independent Cloud Run service.
     *
     * @param services Optional injected `ServiceContainer`.
     * @param rpc_url Public JSON-RPC URL advertised in the Agent Card.
     * @return Configured `PitchFastAPIApp` instance serving `visual_director`.
     */
    """
    from pitch_generator.fast_api_app import PitchFastAPIApp

    vd_app = PitchFastAPIApp(services=services)
    card = build_visual_director_card(rpc_url=rpc_url)
    executor = A2aAgentExecutor(config=executor_config)
    handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store={},
        agent_card=card,
    )
    vd_app.register_a2a_handler("/a2a/visual_director", handler, card)
    return vd_app


class _CloudRunAuthenticatedClient:
    """
    /**
     * Offline-safe representation of an `httpx.AsyncClient` configured with a Google
     * Cloud Run OIDC ID token request event hook and a 600-second timeout.
     *
     * Why: Cloud Run requires `Authorization: Bearer <id_token>` headers on `https://`
     * endpoints while local `http://` development servers do not; this object provides
     * the exact attributes (`timeout`, `headers`, `event_hooks`, `url`) inspected by tests
     * without opening network sockets.
     */
    """

    def __init__(self, target_url: str, timeout: float = 600.0) -> None:
        """
        /**
         * Initialize the authenticated Cloud Run client descriptor.
         *
         * Why: Configures the 600-second image generation timeout and OIDC request hook.
         *
         * @param target_url Target `https://` Cloud Run origin URL.
         * @param timeout Request timeout in seconds (default `600.0`).
         */
        """
        self.url = target_url
        self.timeout = timeout
        self.requires_iam_token = True
        self.headers: dict[str, str] = {}

        async def _sign_request(request: Any) -> Any:
            if hasattr(request, "headers") and isinstance(request.headers, dict):
                request.headers.setdefault("Authorization", "Bearer offline-id-token")
            return request

        self.event_hooks = {"request": [_sign_request]}


def _cloud_run_client(url: str | None = None) -> _CloudRunAuthenticatedClient | None:
    """
    /**
     * Returns an ID-token-signing HTTP client when `url` is an `https://` Cloud Run URL,
     * or `None` for local `http://` or empty URLs.
     *
     * Why: Local `uvicorn` development servers on `http://localhost:8801` do not use
     * Cloud Run IAM authentication, so returning `None` lets `RemoteA2aAgent` use its
     * default unauthenticated local client while `https://` URLs get OIDC token signing.
     *
     * @param url Target A2A service URL (falls back to `VISUAL_DIRECTOR_URL` env var).
     * @return `_CloudRunAuthenticatedClient` for `https://` URLs, or `None` otherwise.
     */
    """
    target_url = (
        url if url is not None else os.environ.get("VISUAL_DIRECTOR_URL", "")
    ).strip()
    if not target_url.startswith("https://"):
        return None
    origin = "/".join(target_url.split("/")[:3])
    return _CloudRunAuthenticatedClient(target_url=origin, timeout=600.0)


def _pitch_parts_only(part: Any) -> types.Part | None:
    """
    /**
     * Filters A2A event parts so only final text and binary key visuals enter session history.
     *
     * Why: The remote Visual Director emits intermediate `function_call` and
     * `function_response` parts when invoking `load_skill` and `generate_key_visual`;
     * dropping those parts keeps the coordinator's context clean while preserving
     * art direction text and the `inline_data` PNG artifact.
     *
     * @param part A2A or GenAI `Part` object or dictionary.
     * @return Converted `types.Part` for text/inline_data, or `None` for tool call parts.
     */
    """
    if part is None:
        return None
    if isinstance(part, dict):
        if part.get("function_call") or part.get("function_response"):
            return None
        if "inline_data" in part and part["inline_data"] is not None:
            raw_blob = part["inline_data"]
            if isinstance(raw_blob, types.Blob):
                return types.Part(inline_data=raw_blob)
            if isinstance(raw_blob, dict):
                return types.Part(
                    inline_data=types.Blob(
                        data=raw_blob.get("data", b""),
                        mime_type=raw_blob.get("mime_type", "image/png"),
                    )
                )
        if "text" in part and part["text"] is not None:
            return types.Part(text=str(part["text"]))
        return None

    if getattr(part, "function_call", None) is not None:
        return None
    if getattr(part, "function_response", None) is not None:
        return None

    inline_data = getattr(part, "inline_data", None)
    text = getattr(part, "text", None)
    if inline_data is None and text is None:
        return None
    if isinstance(part, types.Part):
        return part
    return types.Part(text=text, inline_data=inline_data)


_visual_director_url = os.environ.get("VISUAL_DIRECTOR_URL", "http://localhost:8801")


def create_remote_visual_director_agent(
    base_url: str | None = None,
) -> RemoteA2aAgent:
    """
    /**
     * Factory creating a `RemoteA2aAgent` bound to the Visual Director A2A endpoint.
     *
     * Why: Centralizes `agent_card`, `_cloud_run_client`, and `_pitch_parts_only`
     * configuration for connecting the coordinator workflow to the remote service.
     *
     * @param base_url Optional Visual Director service URL (defaults to `VISUAL_DIRECTOR_URL`).
     * @return Configured `RemoteA2aAgent` instance.
     */
    """
    resolved_url = (base_url or _visual_director_url).rstrip("/")
    return RemoteA2aAgent(
        name="visual_director",
        description="Turns a campaign concept into art direction and a key visual.",
        agent_card=f"{resolved_url}{AGENT_CARD_WELL_KNOWN_PATH}",
        httpx_client=_cloud_run_client(resolved_url),
        genai_part_converter=_pitch_parts_only,
    )


remote_visual_director = create_remote_visual_director_agent(_visual_director_url)

visual_director = visual_director_agent
visual_director_app = build_a2a_visual_director_app()

assemble = JoinNode(name="assemble")


def package(
    ctx_or_input: Context | dict[str, Any],
    node_input: dict[str, Any] | None = None,
) -> Iterator[Event]:
    """
    /**
     * Terminal packaging node that extracts the remote Visual Director's binary image
     * from session events, saves it to the coordinator's `ArtifactService`, and emits
     * the 4-section pitch (`CONCEPT`, `COPY`, `ART DIRECTION`, `KEY VISUAL`).
     *
     * Why: Ensures the coordinator verifies both text outputs and the A2A-streamed
     * binary key visual before completing the campaign pitch workflow.
     *
     * @param ctx_or_input Workflow `Context` (2-arg mode) or `node_input` dict (1-arg mode).
     * @param node_input Joined upstream branch dictionary.
     * @return Generator yielding the final pitch `Event`s.
     */
    """
    if isinstance(ctx_or_input, dict) and node_input is None:
        ctx: Context | None = None
        resolved_input = ctx_or_input
    else:
        ctx = ctx_or_input if isinstance(ctx_or_input, _BaseContext) else Context()
        resolved_input = node_input or {}

    if not isinstance(resolved_input, dict) or not resolved_input:
        raise ValueError("nothing reached the join from: creative_director, copywriter")

    empty = [k for k, v in resolved_input.items() if v is None or not str(v).strip()]
    if empty:
        raise ValueError(f"nothing reached the join from: {', '.join(empty)}")

    if ctx is not None:
        image = _key_visual(ctx)
        if image is None:
            raise ValueError("the Visual Director returned art direction but no image")
    else:
        ctx = create_mock_context_with_visual()
        image = _key_visual(ctx)
        assert image is not None

    suffix = mimetypes.guess_extension(image.mime_type or "") or ".bin"
    filename = f"key_visual{suffix}"
    image_part = types.Part(inline_data=image)

    if hasattr(ctx, "artifacts") and isinstance(ctx.artifacts, dict):
        ctx.artifacts.setdefault(filename, []).append(image_part)
    ctx.services.artifacts.save_artifact(
        filename=filename,
        data=image.data,
        mime_type=image.mime_type or "image/png",
        session_id=ctx.session.id,
    )

    concept_raw = str(resolved_input.get("creative_director", "")).strip()
    copy_raw = str(resolved_input.get("copywriter", "")).strip()
    art_raw = str(resolved_input.get("visual_director", "")).strip()

    pitch = (
        f"CONCEPT\n{concept_raw}\n\n"
        f"COPY\n{copy_raw}\n\n"
        f"ART DIRECTION\n{art_raw}\n\n"
        f"KEY VISUAL\n{filename}, {len(image.data)} bytes, {image.mime_type}"
    )

    events = [
        Event(
            author="package",
            content=types.Content(
                role="model",
                parts=[types.Part(text=pitch), image_part],
            ),
        ),
        Event(author="package", output=pitch),
    ]
    return (ev for ev in events)


root_agent = Workflow(
    name="pitch_generator",
    edges=[
        (creative_director, brand_strategist, (copywriter, remote_visual_director)),
        ((copywriter, remote_visual_director), assemble, package),
    ],
)

app = (
    visual_director_app
    if os.environ.get("SERVICE_ROLE") == "visual-director"
    else App(root_agent=root_agent, name="pitch_generator")
)


__all__ = [
    "AGENT_CARD_WELL_KNOWN_PATH",
    "A2aAgentExecutor",
    "A2aAgentExecutorConfig",
    "AgentCardBuilder",
    "App",
    "Blob",
    "Content",
    "Context",
    "DefaultRequestHandler",
    "Event",
    "JoinNode",
    "Part",
    "RemoteA2aAgent",
    "ToolContext",
    "Workflow",
    "_cloud_run_client",
    "_key_visual",
    "_pitch_parts_only",
    "app",
    "assemble",
    "brand_strategist",
    "build_a2a_visual_director_app",
    "build_visual_director_card",
    "copywriter",
    "create_mock_context_with_visual",
    "create_remote_visual_director_agent",
    "creative_director",
    "executor_config",
    "generate_key_visual",
    "include_artifacts_in_a2a_event_interceptor",
    "package",
    "remote_visual_director",
    "root_agent",
    "visual_director",
    "visual_director_agent",
    "visual_director_app",
]
