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
 * @file agent.py
 * @description Multi-agent ADK workflow definition and service-injected execution
 *   engine for the Agentic Pitch Generator.
 *
 * Why: Defines the baseline pre-Module 1 Google ADK agent graph (`creative_director`,
 * `copywriter`, `assemble = JoinNode(name="assemble")`, `package`, `root_agent`, `app`)
 * running on Gemini Enterprise Agent Platform (`gemini-3.8-flash`) while providing
 * lightweight stdlib fallback shims when `google-adk` / `google-genai` wheels are not
 * installed locally. Also exposes `run_pitch_workflow` and `resume_pitch_workflow`
 * wired through `ServiceContainer` so local runs use live Cloud models and offline
 * test suites execute deterministically. As learners add specialist agents
 * (`brand_strategist`, `visual_director`), HITL gates (`approve_concept`, `user_approval`),
 * or hybrid routing in Modules 1–4, the workflow dynamically incorporates them.
 */
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Iterator
import urllib.parse

from pitch_generator.app_utils.services import (
    ServiceContainer,
    get_default_services,
)
from pitch_generator.config import (
    VALID_ROUTING_MODES,
    PitchConfig,
    get_config,
)


class _GenAITypesShim:
    """
    /**
     * Offline-compatible namespace matching `google.genai.types` (`Blob`, `Part`,
     * `Content`, `HttpRetryOptions`).
     *
     * Why: Allows ADK node functions (`package`, `_pitch_parts_only`) to construct
     * `types.Content` and `types.Part` objects identically in Cloud Run and in offline
     * test environments without `google-genai`.
     */
    """

    @dataclass
    class Blob:
        """
        /**
         * Binary data container for inline multimodal parts (`types.Blob`).
         *
         * Why: Holds raw PNG bytes and MIME type when saving or streaming artifacts.
         */
        """

        data: bytes
        mime_type: str = "image/png"

    @dataclass
    class Part:
        """
        /**
         * Single message part (`types.Part`) holding text, inline binary data, or tool calls.
         *
         * Why: Enables `_pitch_parts_only` to filter out internal function call parts while
         * retaining text and generated key visual images.
         */
        """

        text: str | None = None
        inline_data: Any = None
        function_call: Any = None
        function_response: Any = None

        @classmethod
        def from_bytes(cls, data: bytes, mime_type: str = "image/png") -> "_GenAITypesShim.Part":
            """
            /**
             * Construct a binary `Part` from raw bytes and MIME type.
             *
             * Why: Matches `types.Part.from_bytes(data=..., mime_type=...)` in `google.genai`.
             *
             * @param data Binary payload bytes.
             * @param mime_type MIME type string.
             * @return Configured `Part` with `inline_data=Blob(...)`.
             */
            """
            return cls(inline_data=_GenAITypesShim.Blob(data=bytes(data), mime_type=mime_type))

    @dataclass
    class Content:
        """
        /**
         * Multi-part conversation content container (`types.Content`).
         *
         * Why: Wraps a list of `Part` instances with a role (`"model"` or `"user"`).
         */
        """

        role: str = "model"
        parts: list[Any] = field(default_factory=list)

    @dataclass
    class HttpRetryOptions:
        """
        /**
         * HTTP retry configuration (`types.HttpRetryOptions`) for Gemini model clients.
         *
         * Why: Configures automatic retry attempts on transient 429/503 responses.
         */
        """

        attempts: int = 3


types = _GenAITypesShim()


@dataclass
class Gemini:
    """
    /**
     * ADK `Gemini` model wrapper specifying model name, location, and retry options.
     *
     * Why: Binds each specialist `Agent` to the configured Gemini model (`gemini-3.8-flash`)
     * and global/regional Gemini Enterprise Agent Platform endpoint.
     */
    """

    model: str
    client_kwargs: dict[str, Any] = field(default_factory=lambda: {"location": "global"})
    retry_options: Any = field(default_factory=lambda: types.HttpRetryOptions(attempts=3))


@dataclass
class Event:
    """
    /**
     * ADK workflow event emitted by agent or custom Python nodes.
     *
     * Why: Carries either user-visible `content` (`types.Content`) or structured
     * downstream `output` across workflow edges.
     */
    """

    content: Any = None
    output: Any = None
    author: str = "model"


@dataclass
class RequestInput:
    """
    /**
     * ADK Human-in-the-Loop interrupt event (`RequestInput`).
     *
     * Why: Yielding `RequestInput` inside a `@node(rerun_on_resume=False)` function
     * pauses workflow execution and signals `TASK_STATE_INPUT_REQUIRED` to the caller
     * until a human reviewer approves or rejects the pending step (used in Module 3).
     */
    """

    message: str
    response_schema: Any = str


def node(*, rerun_on_resume: bool = False) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    /**
     * Decorator registering a function as an ADK custom graph node (`@node(...)`).
     *
     * Why: Annotates custom workflow nodes with `rerun_on_resume` metadata so the ADK
     * runner knows whether to return cached human input (`rerun_on_resume=False`) or
     * re-execute validation logic (`rerun_on_resume=True`) when resuming a paused session.
     *
     * @param rerun_on_resume Whether the node re-runs from the start upon session resume.
     * @return Decorator function attaching ADK node attributes.
     */
    """

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, "is_adk_node", True)
        setattr(fn, "rerun_on_resume", rerun_on_resume)
        return fn

    return _decorator


class _SessionData:
    """
    /**
     * Internal session container exposed on `Context.session`.
     *
     * Why: Provides `ctx.session.state` (mapping agent `output_key` to outputs) and
     * `ctx.session.events` as expected by workflow nodes.
     */
    """

    def __init__(
        self,
        session_id: str = "default",
        state: dict[str, Any] | None = None,
    ) -> None:
        """
        /**
         * Initialize session state and event history list.
         *
         * @param session_id Unique session identifier.
         * @param state Initial state dictionary.
         */
        """
        self.id = session_id
        self.state: dict[str, Any] = dict(state or {})
        self.events: list[Any] = []


class Context:
    """
    /**
     * ADK execution context (`ctx`) passed to custom workflow nodes and tools.
     *
     * Why: Gives graph nodes and tool functions access to `ctx.session.state`,
     * `await ctx.save_artifact(filename, part)`, and `await ctx.run_node(subnode)`
     * while routing storage calls to the injected `ServiceContainer`.
     */
    """

    def __init__(
        self,
        session_id: str = "default",
        state: dict[str, Any] | None = None,
        services: ServiceContainer | None = None,
        node_runner: Callable[[Any], Any] | None = None,
    ) -> None:
        """
        /**
         * Initialize the ADK execution context.
         *
         * @param session_id Active session identifier.
         * @param state Optional dictionary of initial session state keys.
         * @param services Optional injected `ServiceContainer`.
         * @param node_runner Optional callback to resolve `await ctx.run_node(...)`.
         */
        """
        self.session = _SessionData(session_id=session_id, state=state)
        self.services = services or get_default_services()
        self._node_runner = node_runner

    async def save_artifact(self, filename: str, part: Any) -> int:
        """
        /**
         * Persist a `types.Part` (or raw bytes) to the configured artifact service.
         *
         * Why: Matches ADK's `await ctx.save_artifact("key_visual.png", image_part)`
         * contract and returns the new integer version number.
         *
         * @param filename Artifact filename (e.g., `"key_visual.png"`).
         * @param part `types.Part` with `inline_data`, or raw `bytes`.
         * @return Persisted integer version number.
         */
        """
        if isinstance(part, (bytes, bytearray)):
            raw_bytes = bytes(part)
            mime_type = "image/png"
        elif hasattr(part, "inline_data") and part.inline_data is not None:
            raw_bytes = bytes(part.inline_data.data)
            mime_type = getattr(part.inline_data, "mime_type", "image/png")
        else:
            raise ValueError("save_artifact requires bytes or a Part with inline_data")

        record = self.services.artifacts.save_artifact(
            filename=filename,
            data=raw_bytes,
            mime_type=mime_type,
            session_id=self.session.id,
        )
        return record.version

    async def run_node(self, target_node: Any) -> Any:
        """
        /**
         * Execute a sub-node (such as `approve_concept`) inside `user_approval`.
         *
         * Why: Enables `user_approval` in Module 3 to await `ctx.run_node(approve_concept)`
         * and inspect the human reviewer's `"yes"`/`"no"` decision.
         *
         * @param target_node Node function or object to execute.
         * @return Result returned or yielded by the sub-node.
         */
        """
        if self._node_runner is not None:
            return self._node_runner(target_node)
        if "approval_response" in self.session.state:
            return self.session.state["approval_response"]
        gen = target_node(self)
        if hasattr(gen, "__anext__"):
            return await gen.__anext__()
        if hasattr(gen, "__next__"):
            return next(gen)
        return gen


@dataclass
class Agent:
    """
    /**
     * ADK `Agent` definition representing a specialized LLM role in the workflow.
     *
     * Why: Encapsulates the agent's `name`, `model`, `description`, `instruction`,
     * `output_key`, `tools`, and optional lifecycle hooks (`before_tool_callback`,
     * `before_model_callback`, `after_tool_callback`).
     */
    """

    name: str
    model: Any = None
    description: str = ""
    instruction: str = ""
    output_key: str | None = None
    tools: list[Any] = field(default_factory=list)
    output_schema: Any = None
    before_tool_callback: Callable[..., Any] | None = None
    before_model_callback: Callable[..., Any] | None = None
    after_tool_callback: Callable[..., Any] | None = None


@dataclass
class RemoteA2aAgent:
    """
    /**
     * ADK client proxy (`RemoteA2aAgent`) that delegates a graph node to a remote
     * A2A service (such as the standalone `visual_director` Cloud Run service in Step 1e).
     *
     * Why: Replaces an in-process `Agent` with a network-decoupled A2A specialist
     * discovered via its `/.well-known/agent-card.json` endpoint.
     */
    """

    name: str
    description: str
    agent_card: str
    httpx_client: Any = None
    genai_part_converter: Callable[[Any], Any] | None = None
    output_key: str | None = "visual_director"


@dataclass
class JoinNode:
    """
    /**
     * ADK synchronization barrier (`JoinNode`) that waits for all upstream parallel
     * branches before invoking the downstream packaging node.
     *
     * Why: Ensures `package` only runs after all upstream specialists (`creative_director`
     * and `copywriter` in the starter graph, plus `visual_director` in Module 1) have completed.
     */
    """

    name: str


@dataclass
class Workflow:
    """
    /**
     * ADK directed graph `Workflow` orchestrating specialist agents, join barriers,
     * and optional Human-in-the-Loop approval gates.
     *
     * Why: Declaratively specifies execution edges (`("START", creative_director)`,
     * fan-out tuples, and join transitions) so multi-agent pipelines are inspectable
     * and loop-bounded.
     */
    """

    name: str
    edges: list[Any] = field(default_factory=list)
    max_steps: int = 20


@dataclass
class App:
    """
    /**
     * Top-level ADK `App` binding `root_agent` to the application name.
     *
     * Why: Required by `agents-cli` and `uvicorn` runners to locate the root workflow.
     */
    """

    root_agent: Any
    name: str = "pitch_generator"


class _DualSyncAsyncEventStream:
    """
    /**
     * Iterable wrapper allowing `package(...)` to be consumed with either `for ev in ...`
     * or `async for ev in ...`.
     *
     * Why: Part 1's baseline `package(node_input)` is a synchronous generator (`def`),
     * whereas the enhanced `package(ctx, node_input)` is an async generator (`async def`).
     * Providing a dual iterator ensures both sync and async callers can iterate over
     * `package(...)` seamlessly while eager input validation raises `ValueError`
     * immediately on missing upstream keys.
     */
    """

    def __init__(self, events: list[Event]) -> None:
        """
        /**
         * Store pre-validated `Event` objects for sync or async iteration.
         *
         * @param events List of emitted `Event` instances.
         */
        """
        self._events = list(events)

    def __iter__(self) -> Iterator[Event]:
        return iter(self._events)

    def __aiter__(self) -> AsyncIterator[Event]:
        async def _agen() -> AsyncIterator[Event]:
            for ev in self._events:
                yield ev

        return _agen()


MODEL: str = get_config().flash_model


def _model() -> Gemini:
    """
    /**
     * Construct the default `Gemini` model configuration (`gemini-3.8-flash`) for starter
     * specialist agents.
     *
     * Why: Centralizes `location="global"` and `HttpRetryOptions(attempts=3)` so every
     * specialist agent shares resilient retry settings on Gemini Enterprise Agent Platform.
     *
     * @return Configured `Gemini` model descriptor.
     */
    """
    cfg = get_config()
    return Gemini(
        model=cfg.flash_model,
        client_kwargs={"location": cfg.location},
        retry_options=types.HttpRetryOptions(attempts=3),
    )


_build_model = _model


async def generate_key_visual(
    art_direction: str,
    tool_context: Context | None = None,
    *,
    simulate_no_image: bool = False,
) -> dict[str, Any]:
    """
    /**
     * Generate a 16:9 key visual PNG from art direction notes and save it to session artifacts.
     *
     * Why: Attached to `visual_director` (`tools=[generate_key_visual]`) in Module 1 Step 1a
     * so the Visual Director specialist can synthesize a key visual image via the configured
     * `image_model` (`gemini-nano-banana-2.1`) and store it in the session artifact store.
     *
     * @param art_direction Art direction prompt describing palette, lighting, composition, and subject.
     * @param tool_context Optional ADK `Context` / `ToolContext` for saving the image artifact.
     * @param simulate_no_image If True, simulates an empty image response to test error handling.
     * @return Metadata dictionary with `filename`, `version`, `bytes`, and `mime_type`.
     */
    """
    import mimetypes

    ctx = tool_context if tool_context is not None else Context()
    cfg = ctx.services.config if hasattr(ctx, "services") and ctx.services else get_config()
    if (
        simulate_no_image
        or getattr(ctx, "simulate_no_image", False)
        or not isinstance(art_direction, str)
        or not art_direction.strip()
    ):
        raise ValueError(f"{cfg.image_model} returned no image for: {str(art_direction)[:120]}")

    image_bytes, mime_type = ctx.services.llm.generate_image(
        art_direction.strip(),
        model=cfg.image_model,
    )
    if not image_bytes:
        raise ValueError(f"{cfg.image_model} returned no image for: {art_direction[:120]}")

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


creative_director = Agent(
    name="creative_director",
    model=_model(),
    description="Turns a raw idea into a campaign concept.",
    instruction=(
        "You are the Creative Director. Turn the idea you are given into ONE "
        "punchy campaign concept line with the rationale explanation behind it."
    ),
    output_key="creative_director",
)

copywriter = Agent(
    name="copywriter",
    model=_model(),
    description="Writes social copy for a campaign concept.",
    instruction=(
        "You are the Copywriter. Write ONE short social caption for the "
        "campaign concept you are given. Under 25 words."
    ),
    output_key="copywriter",
)

assemble = JoinNode(name="assemble")


def package(
    ctx_or_input: Any,
    node_input: dict[str, Any] | None = None,
) -> _DualSyncAsyncEventStream:
    """
    /**
     * Format and validate the joined specialist outputs into the final campaign pitch.
     *
     * Why: Acts as the terminal node after `assemble = JoinNode(name="assemble")`.
     * Explicitly checks that every expected upstream branch produced non-empty output
     * (raising `ValueError("nothing reached the join from: ...")` if any branch is
     * missing or empty) so silent branch failures are caught immediately. Supports both
     * `package(node_input)` and `package(ctx, node_input)` signatures.
     *
     * @param ctx_or_input Either a `node_input` dict (1-arg form) or `Context` (2-arg form).
     * @param node_input Dictionary of upstream outputs when `ctx_or_input` is a `Context`.
     * @return Dual sync/async stream yielding `Event(content=...)` and `Event(output=...)`.
     */
    """
    if node_input is None:
        if not isinstance(ctx_or_input, dict):
            raise ValueError("node_input must be a non-empty dictionary")
        actual_input = ctx_or_input
    else:
        if not isinstance(node_input, dict):
            raise ValueError("node_input must be a non-empty dictionary")
        actual_input = node_input

    if not actual_input:
        raise ValueError("nothing reached the join from: creative_director, copywriter")

    required_keys = ["creative_director", "copywriter"]
    missing_or_empty = [
        k for k in required_keys if k not in actual_input or not str(actual_input.get(k) or "").strip()
    ]
    extra_empty = [
        name
        for name, value in actual_input.items()
        if name not in missing_or_empty and not str(value or "").strip()
    ]
    all_empty = missing_or_empty + extra_empty
    if all_empty:
        raise ValueError(f"nothing reached the join from: {', '.join(all_empty)}")

    sections = [
        f"CONCEPT\n{actual_input['creative_director']}",
        f"COPY\n{actual_input['copywriter']}",
    ]
    if "brand_strategist" in actual_input and actual_input["brand_strategist"]:
        sections.append(f"BRAND STRATEGY\n{actual_input['brand_strategist']}")
    if "visual_director" in actual_input and actual_input["visual_director"]:
        sections.append(f"ART DIRECTION\n{actual_input['visual_director']}")

    pitch = "\n\n".join(sections)
    events = [
        Event(content=types.Content(role="model", parts=[types.Part(text=pitch)])),
        Event(output=pitch),
    ]
    return _DualSyncAsyncEventStream(events)


root_agent = Workflow(
    name="pitch_generator",
    edges=[
        ("START", creative_director),
        (creative_director, copywriter),
        ((creative_director, copywriter), assemble),
        (assemble, package),
    ],
)

app = App(root_agent=root_agent, name="pitch_generator")


def select_routing_decision(
    brief: str = "",
    routing_mode: str = "auto",
    *,
    complexity: str = "medium",
    privacy_level: str = "standard",
    requires_multimodal: bool = False,
    browser_webgpu_available: bool = False,
    local_gpu_available: bool = False,
    config: PitchConfig | None = None,
) -> dict[str, Any]:
    """
    /**
     * Resolve the active Cloud model (`gemini-3.8-flash`) for the starter Pitch Generator.
     *
     * Why: In the pre-Module 1 starter state, all campaign pitch tasks execute on
     * Gemini Enterprise Agent Platform using `gemini-3.8-flash` (`cloud_frontier`).
     * Learners expand this into a 3-tier Hybrid Model Router in Module 4 (Step 4b).
     *
     * @param brief Campaign brief or task prompt text.
     * @param routing_mode Requested mode (`"auto"` or `"cloud_frontier"`).
     * @param complexity Unused in starter (used in Module 4).
     * @param privacy_level Unused in starter (used in Module 4).
     * @param requires_multimodal Unused in starter (used in Module 4).
     * @param browser_webgpu_available Unused in starter (used in Module 4).
     * @param local_gpu_available Unused in starter (used in Module 4).
     * @param config Optional `PitchConfig` with model identifiers.
     * @return Routing decision dictionary targeting `cloud_frontier` (`gemini-3.8-flash`).
     */
    """
    del brief, complexity, privacy_level, requires_multimodal, browser_webgpu_available, local_gpu_available
    clean_mode = (routing_mode or "auto").strip().lower()
    if clean_mode not in VALID_ROUTING_MODES:
        raise ValueError(
            f"Unsupported routing_mode {routing_mode!r}. Expected one of {VALID_ROUTING_MODES}."
        )

    cfg = config or get_config()
    return {
        "target": "cloud_frontier",
        "model_id": cfg.flash_model,
        "requested_mode": clean_mode,
        "fallback_applied": False,
        "fallback_chain": ["cloud_frontier"],
        "rationale": (
            f"Routed to Gemini Enterprise Agent Platform ({cfg.flash_model}) "
            "for multi-agent campaign pitch generation."
        ),
    }


def run_pitch_workflow(
    brief: str,
    *,
    session_id: str = "default",
    services: ServiceContainer | None = None,
    approved: bool | None = True,
    routing_mode: str = "auto",
    require_approval: bool = False,
) -> dict[str, Any]:
    """
    /**
     * Execute the Pitch Generator multi-agent workflow using injected cloud services.
     *
     * Why: Coordinates the starter two-agent pipeline (`creative_director` -> `copywriter`
     * -> `assemble` -> `package`) on Gemini Enterprise Agent Platform (`gemini-3.8-flash`),
     * persists session state in `MemoryBankService`, and records telemetry via
     * `BigQueryAnalyticsService`. If the learner has added `brand_strategist`,
     * `visual_director`, or the HITL approval gate (`approve_concept`) in `agent.py`
     * during Modules 1–3, this runner dynamically executes those branches as well.
     *
     * @param brief Non-empty campaign topic brief.
     * @param session_id Session identifier for Memory Bank persistence.
     * @param services Optional injected `ServiceContainer` (defaults to `get_default_services()`).
     * @param approved HITL approval state (`True` to complete, `False` to reject,
     *   `None` to pause at `input_required` when HITL is enabled).
     * @param routing_mode Routing mode (`"auto"` or `"cloud_frontier"`).
     * @param require_approval If True, pauses at the HITL gate (`status="input_required"`).
     * @return Workflow result dictionary with keys `session_id`, `status`, `concept`,
     *   `copy`, `art_direction`, `key_visual_uri`, `routing_decision`, `telemetry`,
     *   `artifacts`, `pitch_text`, and `trace`.
     */
    """
    if not isinstance(brief, str) or not brief.strip():
        raise ValueError("Campaign brief must not be empty")
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session_id must not be empty")

    clean_brief = brief.strip()
    clean_session = session_id.strip()
    active_services = services or get_default_services()

    routing_decision = select_routing_decision(
        brief=clean_brief,
        routing_mode=routing_mode,
        config=active_services.config,
    )
    active_model = routing_decision["model_id"]

    # Step 1: Creative Director generates campaign concept & rationale
    concept = active_services.llm.generate_text(
        clean_brief,
        system_instruction=creative_director.instruction,
        model=active_model,
    )

    # Determine effective approval state (used when learner enables HITL in Module 3)
    effective_approved: bool | None = approved
    if require_approval and approved is True:
        effective_approved = None

    if effective_approved is False:
        telemetry_event = active_services.analytics.record_telemetry(
            {
                "session_id": clean_session,
                "status": "rejected",
                "brief": clean_brief,
                "routing_target": routing_decision["target"],
                "model_id": active_model,
                "nodes_executed": ["creative_director", "approve_concept", "user_approval"],
            }
        )
        rejected_state = {
            "session_id": clean_session,
            "status": "rejected",
            "brief": clean_brief,
            "concept": concept,
            "copy": "",
            "art_direction": "",
            "key_visual_uri": None,
            "routing_decision": routing_decision,
            "telemetry": telemetry_event,
            "artifacts": [],
            "pitch_text": "",
            "trace": ["creative_director", "approve_concept", "user_approval"],
        }
        active_services.memory_bank.save_session(clean_session, rejected_state)
        return rejected_state

    if effective_approved is None:
        telemetry_event = active_services.analytics.record_telemetry(
            {
                "session_id": clean_session,
                "status": "input_required",
                "brief": clean_brief,
                "routing_target": routing_decision["target"],
                "model_id": active_model,
                "nodes_executed": ["creative_director", "approve_concept"],
            }
        )
        paused_state = {
            "session_id": clean_session,
            "status": "input_required",
            "prompt": "Please approve the campaign concept (yes/no).",
            "brief": clean_brief,
            "concept": concept,
            "copy": "",
            "art_direction": "",
            "key_visual_uri": None,
            "routing_decision": routing_decision,
            "telemetry": telemetry_event,
            "artifacts": [],
            "pitch_text": "",
            "trace": ["creative_director", "approve_concept"],
        }
        active_services.memory_bank.save_session(clean_session, paused_state)
        return paused_state

    # Step 2: Copywriter generates <25-word social caption
    copy_text = active_services.llm.generate_text(
        concept,
        system_instruction=copywriter.instruction,
        model=active_model,
    )

    join_inputs: dict[str, Any] = {
        "creative_director": concept,
        "copywriter": copy_text,
    }
    nodes_executed: list[str] = ["creative_director", "copywriter"]
    brand_text = ""
    art_direction = ""
    key_visual_uri: str | None = None
    key_visual_url: str | None = None
    artifacts_meta: list[dict[str, Any]] = []

    # Dynamic expansion: if the learner has defined LoopGuard, strip_markdown_fences,
    # brand_strategist, or visual_director in agent.py (Module 1), execute them automatically.
    module_globals = globals()
    loop_guard_cls = module_globals.get("LoopGuard")
    active_guard = None
    if callable(loop_guard_cls):
        active_guard = loop_guard_cls(max_iterations=10)
        if hasattr(active_guard, "validate_graph") and hasattr(root_agent, "edges"):
            active_guard.validate_graph(root_agent.edges)
        if hasattr(active_guard, "record_step"):
            active_guard.record_step("creative_director")
            active_guard.record_step("copywriter")

    strip_fn = module_globals.get("strip_markdown_fences")
    if callable(strip_fn):
        concept = strip_fn(concept)
        copy_text = strip_fn(copy_text)
        join_inputs["creative_director"] = concept
        join_inputs["copywriter"] = copy_text

    brand_agent = module_globals.get("brand_strategist")
    if brand_agent is not None:
        brand_instruction = getattr(
            brand_agent,
            "instruction",
            "You are the Brand Strategist. Provide audience positioning for the concept.",
        )
        brand_text = active_services.llm.generate_text(
            concept,
            system_instruction=brand_instruction,
            model=active_model,
        )
        if callable(strip_fn):
            brand_text = strip_fn(brand_text)
        join_inputs["brand_strategist"] = brand_text
        nodes_executed.append("brand_strategist")
        if active_guard is not None and hasattr(active_guard, "record_step"):
            active_guard.record_step("brand_strategist")

    remote_vd = module_globals.get("remote_visual_director")
    visual_agent = module_globals.get("visual_director") or remote_vd
    if visual_agent is not None:
        if remote_vd is not None:
            from pitch_generator.app_utils.services import _is_offline_test_mode
            import urllib.request

            if not _is_offline_test_mode(active_services.config.project_id):
                vd_url = active_services.config.visual_director_url.rstrip("/")
                card_url = f"{vd_url}/.well-known/agent-card.json"
                headers: dict[str, str] = {"Accept": "application/json"}
                if card_url.startswith("https://"):
                    try:
                        import google.auth.transport.requests
                        import google.oauth2.id_token

                        auth_req = google.auth.transport.requests.Request()
                        id_tok = google.oauth2.id_token.fetch_id_token(auth_req, vd_url)
                        if id_tok:
                            headers["Authorization"] = f"Bearer {id_tok}"
                    except Exception:
                        pass
                try:
                    req = urllib.request.Request(card_url, headers=headers, method="GET")
                    with urllib.request.urlopen(req, timeout=10.0) as resp:
                        if resp.status >= 400:
                            raise RuntimeError(f"HTTP {resp.status}")
                except Exception as exc:
                    raise RuntimeError(
                        f"[A2A Remote Error] Could not connect to remote Visual Director service at "
                        f"'{vd_url}' ({card_url}): {exc}. Ensure the Visual Director service is running "
                        f"(or verify VISUAL_DIRECTOR_URL in .env)."
                    ) from exc

        visual_instruction = getattr(
            visual_agent,
            "instruction",
            (
                "You are the Visual Director. Produce brand-compliant art direction "
                "using our deep indigo and slate palette with a warm amber or terracotta "
                "accent, single low raking light with long shadows, off-center negative "
                "space, and one realistic photographic subject."
            ),
        )
        art_direction = active_services.llm.generate_text(
            concept,
            system_instruction=visual_instruction,
            model=active_model,
        )
        if callable(strip_fn):
            art_direction = strip_fn(art_direction)
        image_bytes, mime_type = active_services.llm.generate_image(
            art_direction,
            model=active_services.config.image_model,
        )
        artifact_record = active_services.artifacts.save_artifact(
            filename="key_visual.png",
            data=image_bytes,
            mime_type=mime_type,
            session_id=clean_session,
        )
        key_visual_url = (
            f"/api/artifacts/{clean_session}/{artifact_record.filename}"
            f"?v={artifact_record.version}"
        )
        key_visual_uri = (
            artifact_record.gcs_uri
            or f"/api/artifacts/{clean_session}/{artifact_record.filename}"
        )
        artifacts_meta.append(artifact_record.to_metadata_dict())
        join_inputs["visual_director"] = art_direction
        nodes_executed.append("visual_director")
        if active_guard is not None and hasattr(active_guard, "record_step"):
            active_guard.record_step("visual_director")

    # Step 3: Assemble and Package join output validation
    join_events = list(package(join_inputs))
    pitch_text = str(join_events[-1].output or "")
    nodes_executed.extend(["assemble", "package"])
    if active_guard is not None and hasattr(active_guard, "record_step"):
        active_guard.record_step("assemble")
        active_guard.record_step("package")

    telemetry_event = active_services.analytics.record_telemetry(
        {
            "session_id": clean_session,
            "status": "completed",
            "brief": clean_brief,
            "routing_target": routing_decision["target"],
            "model_id": active_model,
            "key_visual_uri": key_visual_uri,
            "nodes_executed": list(nodes_executed),
        }
    )

    completed_result = {
        "session_id": clean_session,
        "status": "completed",
        "brief": clean_brief,
        "concept": concept,
        "copy": copy_text,
        "brand_strategy": brand_text,
        "art_direction": art_direction,
        "key_visual_uri": key_visual_uri,
        "key_visual_url": key_visual_url,
        "routing_decision": routing_decision,
        "telemetry": telemetry_event,
        "artifacts": artifacts_meta,
        "pitch_text": pitch_text,
        "trace": list(nodes_executed),
    }

    active_services.memory_bank.save_session(clean_session, completed_result)
    active_services.memory_bank.store_memory(
        "campaigns",
        clean_session,
        {
            "brief": clean_brief,
            "concept": concept,
            "copy": copy_text,
            "key_visual_uri": key_visual_uri,
        },
    )
    return completed_result


def resume_pitch_workflow(
    session_id: str,
    *,
    approved: bool,
    feedback: str = "",
    services: ServiceContainer | None = None,
) -> dict[str, Any]:
    """
    /**
     * Resume a paused Human-in-the-Loop workflow session stored in `MemoryBankService`.
     *
     * Why: When `POST /api/approve` or an A2A approval message arrives for a paused
     * `session_id` (Module 3), this function loads the saved concept from Memory Bank
     * and either completes the downstream workflow (`approved=True`) or marks the
     * session `"rejected"` (`approved=False`).
     *
     * @param session_id Session identifier of the paused workflow.
     * @param approved Boolean decision from the human reviewer.
     * @param feedback Optional reviewer note or refinement instruction.
     * @param services Optional injected `ServiceContainer`.
     * @return Updated workflow result dictionary (`"completed"` or `"rejected"`).
     */
    """
    if not isinstance(session_id, str) or not session_id.strip():
        raise ValueError("session_id must not be empty")
    clean_session = session_id.strip()
    active_services = services or get_default_services()
    stored = active_services.memory_bank.load_session(clean_session)
    if not stored:
        raise KeyError(f"Unknown session_id: {clean_session}")

    brief = str(stored.get("brief") or "Campaign brief")
    routing_mode = str(
        stored.get("routing_decision", {}).get("requested_mode") or "auto"
    )

    if not approved:
        result = run_pitch_workflow(
            brief,
            session_id=clean_session,
            services=active_services,
            approved=False,
            routing_mode=routing_mode,
        )
        result["reviewer_feedback"] = feedback
        active_services.memory_bank.save_session(clean_session, result)
        return result

    effective_brief = f"{brief} ({feedback.strip()})" if feedback and feedback.strip() else brief
    result = run_pitch_workflow(
        effective_brief,
        session_id=clean_session,
        services=active_services,
        approved=True,
        routing_mode=routing_mode,
        require_approval=False,
    )
    result["reviewer_feedback"] = feedback
    active_services.memory_bank.save_session(clean_session, result)
    return result
