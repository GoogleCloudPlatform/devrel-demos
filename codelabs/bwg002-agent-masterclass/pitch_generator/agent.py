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
 * Why: Defines the Google ADK specialist agent team (`creative_director`,
 * `brand_strategist`, `copywriter`, `visual_director`), structured payload contracts,
 * `LoopGuard` DAG validation, `assemble = JoinNode(name="assemble")`, `package`,
 * `root_agent`, and `app` running on Gemini Enterprise Agent Platform (`gemini-3.8-flash`)
 * while providing lightweight stdlib fallback shims when `google-adk` / `google-genai`
 * wheels are not installed locally. Also exposes `run_pitch_workflow` and
 * `resume_pitch_workflow` wired through `ServiceContainer` so local runs use live
 * Cloud models and offline test suites execute deterministically.
 */
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any, AsyncIterator, Callable, Iterator

from pitch_generator.app_utils.services import (
    ServiceContainer,
    get_default_services,
)
from pitch_generator.config import (
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
     * A2A service (such as the standalone `visual_director` Cloud Run service in Step 1c).
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
     * Why: Ensures `package` only runs after all upstream specialists (`creative_director`,
     * `brand_strategist`, `copywriter`, and `visual_director`) have completed.
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
IMAGE_MODEL: str = get_config().image_model

_MARKDOWN_FENCE_RE = re.compile(
    r"^\s*```(?:json|JSON)?\s*\n?(.*?)\n?\s*```\s*$",
    re.DOTALL,
)


def _key_visual(ctx: Context | None) -> types.Blob | None:
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


class PayloadValidationError(ValueError):
    """
    /**
     * Raised when an inter-agent JSON handoff payload is malformed or missing required keys.
     *
     * Why: Subclasses `ValueError` so callers and E2E tests catching `ValueError` or
     * `PayloadValidationError` can uniformly handle schema violations across graph edges.
     */
    """


class CircularLoopError(ValueError, RuntimeError):
    """
    /**
     * Raised when a workflow graph contains a cycle or exceeds maximum allowed node visits.
     *
     * Why: Subclasses both `ValueError` and `RuntimeError` so static DAG validation and
     * runtime iteration guards fail fast with a deterministic exception before runaway
     * LLM token consumption occurs.
     */
    """


def strip_markdown_fences(raw_text: str) -> str:
    """
    /**
     * Strips optional Markdown code fences (```json ... ```) from an LLM response string.
     *
     * Why: LLMs frequently wrap JSON output in Markdown code blocks even when instructed
     * to return raw JSON; stripping fences before `json.loads` prevents false parser failures.
     *
     * @param raw_text Raw string output from an agent node.
     * @return Clean inner JSON string with leading/trailing whitespace removed.
     */
    """
    if not isinstance(raw_text, str):
        raise PayloadValidationError("Expected string payload for markdown fence stripping.")
    cleaned = raw_text.strip()
    match = _MARKDOWN_FENCE_RE.match(cleaned)
    if match:
        return match.group(1).strip()
    return cleaned


_extract_json_Candidate = strip_markdown_fences


@dataclass
class ConceptPayload:
    """
    /**
     * Structured handoff payload produced by the `creative_director` node.
     *
     * Why: Enforces a non-empty `concept_line` and `rationale` before downstream fan-out
     * branches (`copywriter`, `visual_director`) consume the campaign concept.
     *
     * @param concept_line Core campaign concept headline.
     * @param rationale Strategic rationale explaining why the concept fits the brief.
     */
    """

    concept_line: str
    rationale: str = "Grounded in practical commuter utility and understated design."

    def __post_init__(self) -> None:
        """
        /**
         * Validate that both `concept_line` and `rationale` are non-empty strings.
         *
         * Why: Rejects blank or whitespace-only concept handoffs at construction time.
         */
        """
        if not isinstance(self.concept_line, str) or not self.concept_line.strip():
            raise PayloadValidationError("ConceptPayload.concept_line must be a non-empty string.")
        if not isinstance(self.rationale, str) or not self.rationale.strip():
            raise PayloadValidationError("ConceptPayload.rationale must be a non-empty string.")
        self.concept_line = self.concept_line.strip()
        self.rationale = self.rationale.strip()

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize the concept payload into a plain dictionary.
         *
         * Why: Facilitates JSON serialization and field inspection across graph edges.
         *
         * @return Dictionary with `concept_line` and `rationale`.
         */
        """
        return asdict(self)

    def to_json(self) -> str:
        """
        /**
         * Serialize the concept payload into a JSON string.
         *
         * Why: Enables structured text transport between ADK nodes.
         *
         * @return JSON string representation.
         */
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_text(cls, raw_text: str) -> ConceptPayload:
        """
        /**
         * Parse a `ConceptPayload` from raw or Markdown-fenced JSON text.
         *
         * Why: Allows downstream nodes to deserialize LLM responses directly.
         *
         * @param raw_text Raw or fenced JSON text.
         * @return Validated `ConceptPayload` instance.
         */
        """
        return parse_json_payload(raw_text, cls)


CampaignConcept = ConceptPayload


@dataclass
class CopyPayload:
    """
    /**
     * Structured handoff payload produced by the `copywriter` node.
     *
     * Why: Guarantees that social copy reaching the `assemble` JoinNode is non-empty
     * and adheres to the 25-word maximum brand voice constraint.
     *
     * @param caption Social media caption text (auto-trimmed to <= 25 words).
     * @param channel Target marketing channel identifier.
     * @param word_count Computed word count of `caption`.
     */
    """

    caption: str
    channel: str = "social"
    word_count: int = 0

    def __post_init__(self) -> None:
        """
        /**
         * Validate `caption` is non-empty and enforce the 25-word limit.
         *
         * Why: Prevents over-long social captions from violating copywriter constraints.
         */
        """
        if not isinstance(self.caption, str) or not self.caption.strip():
            raise PayloadValidationError("CopyPayload.caption must be a non-empty string.")
        self.caption = self.caption.strip()
        words = self.caption.split()
        if len(words) > 25:
            self.caption = " ".join(words[:25])
            words = self.caption.split()
        self.word_count = len(words)

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize the copy payload into a plain dictionary.
         *
         * Why: Supports structured logging and test assertions.
         *
         * @return Dictionary with `caption`, `channel`, and `word_count`.
         */
        """
        return asdict(self)

    def to_json(self) -> str:
        """
        /**
         * Serialize the copy payload into a JSON string.
         *
         * Why: Supports structured JSON handoffs in the workflow graph.
         *
         * @return JSON string representation.
         */
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_text(cls, raw_text: str) -> CopyPayload:
        """
        /**
         * Parse a `CopyPayload` from raw or Markdown-fenced JSON text.
         *
         * Why: Strips code fences and validates required fields before instantiation.
         *
         * @param raw_text Raw or fenced JSON string.
         * @return Validated `CopyPayload` instance.
         */
        """
        return parse_json_payload(raw_text, cls)


@dataclass
class ArtDirectionPayload:
    """
    /**
     * Structured handoff payload produced by the `visual_director` node.
     *
     * Why: Captures structured art direction notes (`art_direction`, `palette`, `lighting`)
     * so the `package` node can assemble a complete multi-disciplinary pitch deck.
     *
     * @param art_direction Detailed visual art direction description.
     * @param palette House brand palette summary.
     * @param lighting House brand lighting setup summary.
     */
    """

    art_direction: str
    palette: str = "deep indigo and slate with warm amber accent"
    lighting: str = "single low raking light on textured surface"

    def __post_init__(self) -> None:
        """
        /**
         * Validate that `art_direction` is a non-empty string.
         *
         * Why: Ensures empty visual prompts never reach the image generator or join node.
         */
        """
        if not isinstance(self.art_direction, str) or not self.art_direction.strip():
            raise PayloadValidationError(
                "ArtDirectionPayload.art_direction must be a non-empty string."
            )
        self.art_direction = self.art_direction.strip()

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize the art direction payload into a dictionary.
         *
         * Why: Enables structured inspection of visual direction fields.
         *
         * @return Dictionary with `art_direction`, `palette`, and `lighting`.
         */
        """
        return asdict(self)

    def to_json(self) -> str:
        """
        /**
         * Serialize the art direction payload into a JSON string.
         *
         * Why: Supports JSON transport across graph nodes.
         *
         * @return JSON string representation.
         */
        """
        return json.dumps(self.to_dict())

    @classmethod
    def from_text(cls, raw_text: str) -> ArtDirectionPayload:
        """
        /**
         * Parse an `ArtDirectionPayload` from raw or Markdown-fenced JSON text.
         *
         * Why: Strips Markdown fences and validates fields before returning the payload.
         *
         * @param raw_text Raw or fenced JSON text.
         * @return Validated `ArtDirectionPayload` instance.
         */
        """
        return parse_json_payload(raw_text, cls)


VisualPayload = ArtDirectionPayload


@dataclass
class PitchPackage:
    """
    /**
     * Final aggregated campaign pitch output produced after the `assemble` JoinNode.
     *
     * Why: Combines validated `ConceptPayload`, `CopyPayload`, and `ArtDirectionPayload`
     * artifacts with the execution trace and formatted pitch text.
     *
     * @param concept Validated `ConceptPayload`.
     * @param copy Validated `CopyPayload`.
     * @param art_direction Validated `ArtDirectionPayload`.
     * @param brand_strategy Brand positioning notes.
     * @param pitch_text Formatted multi-section pitch string.
     * @param trace Ordered list of visited graph node names.
     */
    """

    concept: ConceptPayload
    copy: CopyPayload
    art_direction: ArtDirectionPayload
    brand_strategy: str = ""
    pitch_text: str = ""
    trace: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """
        /**
         * Populate `pitch_text` automatically if not explicitly provided.
         *
         * Why: Guarantees `PitchPackage.pitch_text` always contains `CONCEPT`, `COPY`,
         * and `ART DIRECTION` sections.
         */
        """
        if not self.pitch_text:
            concept_str = f"{self.concept.concept_line}\n{self.concept.rationale}"
            self.pitch_text = (
                f"CONCEPT\n{concept_str}\n\n"
                f"COPY\n{self.copy.caption}\n\n"
                f"ART DIRECTION\n{self.art_direction.art_direction}"
            )

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Serialize the pitch package into a nested dictionary.
         *
         * Why: Supports JSON responses and `extract_field` inspection in E2E tests.
         *
         * @return Dictionary representation of the complete pitch package.
         */
        """
        return {
            "concept": self.concept.to_dict(),
            "copy": self.copy.to_dict(),
            "art_direction": self.art_direction.to_dict(),
            "brand_strategy": self.brand_strategy,
            "pitch_text": self.pitch_text,
            "trace": list(self.trace),
        }

    def to_json(self) -> str:
        """
        /**
         * Serialize the pitch package into a JSON string.
         *
         * Why: Enables structured persistence and wire transport.
         *
         * @return JSON string representation.
         */
        """
        return json.dumps(self.to_dict())


def parse_json_payload(raw_text: str, schema_cls: type[Any] | None = None) -> Any:
    """
    /**
     * Parses a JSON object from raw or Markdown-fenced text and validates against a schema.
     *
     * Why: Ensures that malformed JSON, non-object JSON, or empty `{}` objects lacking
     * required handoff fields fail immediately with `PayloadValidationError` (`ValueError`).
     *
     * @param raw_text Raw or Markdown-fenced JSON string.
     * @param schema_cls Optional dataclass type (`ConceptPayload`, `CopyPayload`, etc.).
     * @return Instantiated `schema_cls` object or validated non-empty dictionary.
     */
    """
    cleaned = strip_markdown_fences(raw_text)
    if not cleaned:
        raise PayloadValidationError("Cannot parse empty JSON payload string.")
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise PayloadValidationError(f"Malformed JSON payload: {exc}") from exc

    if not isinstance(data, dict) or not data:
        raise PayloadValidationError("JSON payload must be a non-empty JSON object.")

    if schema_cls is not None:
        try:
            return schema_cls(**data)
        except TypeError as exc:
            raise PayloadValidationError(
                f"JSON payload missing or invalid fields for {schema_cls.__name__}: {exc}"
            ) from exc

    if "concept_line" in data:
        return ConceptPayload(**data)
    if "caption" in data:
        return CopyPayload(**data)
    if "art_direction" in data:
        return ArtDirectionPayload(**data)
    return data


parse_payload = parse_json_payload
extract_json_payload = parse_json_payload


def _node_name(node: Any) -> str:
    """
    /**
     * Extract a string node identifier from an Agent, JoinNode, function, or string.
     *
     * Why: Normalizes heterogeneous ADK node references into string names for `LoopGuard`.
     *
     * @param node Node object or string identifier.
     * @return Resolved node name string.
     */
    """
    if isinstance(node, str):
        return node
    return getattr(node, "name", None) or getattr(node, "__name__", None) or str(node)


def _normalize_directed_edges(edges: Sequence[Any]) -> list[tuple[str, str]]:
    """
    /**
     * Normalizes ADK Workflow edge tuples (chains, fan-outs, fan-ins) into `(u, v)` pairs.
     *
     * Why: ADK `Workflow(edges=[...])` supports multi-element chains `(a, b, c)` as well
     * as parallel fan-out `(a, (b, c))` and fan-in `((a, b), c)` tuples; normalizing to
     * flat `(src, dst)` pairs enables standard DFS cycle detection.
     *
     * @param edges Sequence of workflow edge definitions.
     * @return List of normalized `(source, target)` string pairs.
     */
    """
    directed: list[tuple[str, str]] = []
    for edge in edges:
        if not isinstance(edge, (tuple, list)) or len(edge) < 2:
            continue
        for idx in range(len(edge) - 1):
            left = edge[idx]
            right = edge[idx + 1]
            left_items = list(left) if isinstance(left, (tuple, list)) else [left]
            right_items = list(right) if isinstance(right, (tuple, list)) else [right]
            for u in left_items:
                for v in right_items:
                    directed.append((_node_name(u), _node_name(v)))
    return directed


class LoopGuard:
    """
    /**
     * Static DAG validator and runtime node-visit guard for ADK `Workflow` graphs.
     *
     * Why: Prevents accidental cyclic edges (self-loops, 2-node cycles, 3-node cycles)
     * and enforces a hard `max_iterations` ceiling during graph execution.
     */
    """

    def __init__(self, max_iterations: int = 10, *, allow_revisit: bool = False) -> None:
        """
        /**
         * Initialize the loop guard with an iteration budget and revisit policy.
         *
         * Why: Fails immediately if `max_iterations <= 0` so misconfigured guards are caught early.
         *
         * @param max_iterations Maximum number of runtime node executions allowed (`>= 1`).
         * @param allow_revisit Whether a node may be visited more than once within `max_iterations`.
         */
        """
        if max_iterations <= 0:
            raise CircularLoopError(
                f"LoopGuard max_iterations must be >= 1, got {max_iterations}."
            )
        self.max_iterations = max_iterations
        self.allow_revisit = allow_revisit
        self.visited_nodes: list[str] = []
        self.execution_counts: dict[str, int] = {}
        self.step_count: int = 0

    def validate_graph(self, edges: Sequence[Any]) -> bool:
        """
        /**
         * Validates that the directed graph defined by `edges` is a strict DAG (no cycles).
         *
         * Why: Detects self-loops (`A -> A`), 2-node cycles (`A -> B -> A`), and multi-hop
         * cycles (`A -> B -> C -> A`) using 3-color DFS before any LLM calls are made.
         *
         * @param edges Sequence of workflow edge tuples.
         * @return `True` if the graph is acyclic.
         */
        """
        directed = _normalize_directed_edges(edges)
        adj: dict[str, list[str]] = {}
        nodes: set[str] = set()
        for u, v in directed:
            if u == v:
                raise CircularLoopError(f"Circular self-loop detected on node '{u}'.")
            adj.setdefault(u, []).append(v)
            nodes.add(u)
            nodes.add(v)

        white, gray, black = 0, 1, 2
        color: dict[str, int] = {n: white for n in nodes}
        path: list[str] = []

        def _dfs(node: str) -> None:
            color[node] = gray
            path.append(node)
            for neighbor in adj.get(node, ()):
                if color.get(neighbor, white) == gray:
                    cycle_start = path.index(neighbor)
                    cycle_str = " -> ".join([*path[cycle_start:], neighbor])
                    raise CircularLoopError(
                        f"Circular loop detected in workflow graph: {cycle_str}"
                    )
                if color.get(neighbor, white) == white:
                    _dfs(neighbor)
            path.pop()
            color[node] = black

        for n in list(nodes):
            if color[n] == white:
                _dfs(n)
        return True

    def record_step(self, node_name: str | Any) -> int:
        """
        /**
         * Records a runtime visit to `node_name` and enforces iteration and revisit bounds.
         *
         * Why: Stops runaway graph execution if a node is revisited in a DAG or if the total
         * number of executed steps exceeds `self.max_iterations`.
         *
         * @param node_name Name or object of the workflow node being entered.
         * @return Updated total step count.
         */
        """
        name = _node_name(node_name)
        if not name.strip():
            raise ValueError("Node name cannot be empty.")
        if self.max_iterations <= 0 or self.step_count + 1 > self.max_iterations:
            raise CircularLoopError(
                f"Circular loop guard exceeded max_iterations={self.max_iterations} at node '{name}'."
            )
        if not self.allow_revisit and self.execution_counts.get(name, 0) >= 1:
            raise CircularLoopError(
                f"Circular loop detected: node '{name}' visited multiple times."
            )
        self.step_count += 1
        self.visited_nodes.append(name)
        self.execution_counts[name] = self.execution_counts.get(name, 0) + 1
        return self.step_count

    check_step = record_step
    step = record_step
    enter_node = record_step
    visit = record_step

    def reset(self) -> None:
        """
        /**
         * Resets tracked runtime node visits and step counter.
         *
         * Why: Allows a `LoopGuard` instance to be reused across independent workflow runs.
         */
        """
        self.visited_nodes.clear()
        self.execution_counts.clear()
        self.step_count = 0


def _model(config: PitchConfig | None = None) -> Gemini:
    """
    /**
     * Construct the default `Gemini` model configuration (`gemini-3.8-flash`) for
     * specialist agents.
     *
     * Why: Centralizes `location="global"` and `HttpRetryOptions(attempts=3)` so every
     * specialist agent shares resilient retry settings on Gemini Enterprise Agent Platform.
     *
     * @param config Optional `PitchConfig` override.
     * @return Configured `Gemini` model descriptor.
     */
    """
    cfg = config or get_config()
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
     * Why: Attached to `visual_director` (`tools=[generate_key_visual]`) so the Visual
     * Director specialist can synthesize a key visual image via the configured
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


def build_specialist_team(config: PitchConfig | None = None) -> dict[str, Agent]:
    """
    /**
     * Instantiate the four domain specialist agents for the Pitch Generator team.
     *
     * Why: Provides a deterministic factory that binds each specialist role
     * (`creative_director`, `copywriter`, `brand_strategist`, `visual_director`) to
     * a focused single-responsibility instruction and a unique `output_key` so
     * downstream graph nodes can read each specialist's output without collision.
     *
     * @param config Optional `PitchConfig` used to resolve model settings.
     * @return Dictionary mapping role name to its configured `Agent` instance.
     */
    """
    model = _model(config)
    return {
        "creative_director": Agent(
            name="creative_director",
            model=model,
            description="Turns a raw campaign topic into a punchy concept line and strategic rationale.",
            instruction=(
                "You are the Creative Director. Turn the campaign idea you are given into "
                "ONE punchy campaign concept line accompanied by a clear rationale explanation."
            ),
            output_key="creative_director",
        ),
        "copywriter": Agent(
            name="copywriter",
            model=model,
            description="Writes a concise, high-impact social media caption under 25 words.",
            instruction=(
                "You are the Copywriter. Write ONE short social caption for the campaign "
                "concept you are given. Strictly under 25 words with an energetic call to action."
            ),
            output_key="copywriter",
        ),
        "brand_strategist": Agent(
            name="brand_strategist",
            model=model,
            description="Defines campaign positioning, target audience, and brand tone for the campaign concept.",
            instruction=(
                "You are the Brand Strategist. Define the campaign positioning, "
                "target audience, and brand tone for the campaign concept."
            ),
            output_key="brand_strategist",
        ),
        "visual_director": Agent(
            name="visual_director",
            model=model,
            description="Translates the campaign concept into art direction and key visuals.",
            instruction=(
                "You are the Visual Director. Translate the campaign concept into "
                "art direction and key visuals using our house brand palette (deep indigo "
                "and slate ground with one warm amber or terracotta accent), single low "
                "raking light with long shadows, off-center composition with generous "
                "negative space, and one realistic photographic subject with shallow depth of field."
            ),
            tools=[generate_key_visual],
            output_key="visual_director",
        ),
    }


create_specialist_agents = build_specialist_team
get_specialist_agents = build_specialist_team

SPECIALIST_AGENTS: dict[str, Agent] = build_specialist_team()

creative_director: Agent = SPECIALIST_AGENTS["creative_director"]
copywriter: Agent = SPECIALIST_AGENTS["copywriter"]
brand_strategist: Agent = SPECIALIST_AGENTS["brand_strategist"]
visual_director: Agent = SPECIALIST_AGENTS["visual_director"]


def get_specialist_agent(role: str) -> Agent:
    """
    /**
     * Look up a single specialist `Agent` by role identifier.
     *
     * Why: Fails fast with a descriptive `KeyError` when an invalid or unknown
     * specialist role is requested instead of silently returning `None`.
     *
     * @param role Specialist role name (e.g., `"creative_director"`, `"copywriter"`).
     * @return Matching `Agent` instance.
     */
    """
    if not isinstance(role, str) or not role.strip():
        raise ValueError("Specialist role name must be a non-empty string")
    clean_role = role.strip()
    if clean_role == "market_researcher":
        return SPECIALIST_AGENTS["brand_strategist"]
    if clean_role not in SPECIALIST_AGENTS:
        raise KeyError(
            f"Unknown specialist role {role!r}. Expected one of {tuple(SPECIALIST_AGENTS.keys())}."
        )
    return SPECIALIST_AGENTS[clean_role]


def run_specialist_team(
    brief: str,
    *,
    services: ServiceContainer | None = None,
    config: PitchConfig | None = None,
) -> dict[str, str]:
    """
    /**
     * Execute all four specialist agents sequentially/in-parallel against a campaign brief.
     *
     * Why: Allows learners and automated tests to verify that all four specialist roles
     * (`creative_director`, `copywriter`, `brand_strategist`, `visual_director`) generate
     * domain-appropriate outputs offline via dependency-injected `ServiceContainer`.
     *
     * @param brief Non-empty campaign topic brief.
     * @param services Optional injected `ServiceContainer` for offline LLM execution.
     * @param config Optional `PitchConfig` override.
     * @return Dictionary mapping each specialist's `output_key` to its generated text.
     */
    """
    if not isinstance(brief, str) or not brief.strip():
        raise ValueError("Campaign brief must be a non-empty string")

    clean_brief = brief.strip()
    active_services = services or get_default_services(config)
    team = build_specialist_team(active_services.config)
    model_id = active_services.config.flash_model

    concept_out = active_services.llm.generate_text(
        clean_brief,
        system_instruction=team["creative_director"].instruction,
        model=model_id,
    )
    copy_out = active_services.llm.generate_text(
        concept_out,
        system_instruction=team["copywriter"].instruction,
        model=model_id,
    )
    copy_words = copy_out.split()
    if len(copy_words) > 25:
        copy_out = " ".join(copy_words[:24])

    strategy_out = active_services.llm.generate_text(
        concept_out,
        system_instruction=team["brand_strategist"].instruction,
        model=model_id,
    )
    visual_out = active_services.llm.generate_text(
        concept_out,
        system_instruction=team["visual_director"].instruction,
        model=model_id,
    )

    return {
        "creative_director": concept_out,
        "copywriter": copy_out,
        "brand_strategist": strategy_out,
        "visual_director": visual_out,
    }


execute_specialists = run_specialist_team
run_specialists = run_specialist_team

# [Guidepost — Step 1a: Brand Guidelines Skill]
# Here is where we load the house style skill from `pitch_generator/skills/brand-guidelines` using
# `brand_guidelines_skill = load_skill_from_dir(...)`, attach `[SkillToolset([brand_guidelines_skill]), generate_key_visual]`
# to `visual_director`'s `tools`, and instruct `visual_director` to call `load_skill` for `brand-guidelines`,
# write art direction, call `generate_key_visual`, and output ONLY the art direction notes as plain text.

# [Guidepost — Step 1b: Skill Evaluation Harness]
# Here is where we add `FORBIDDEN_BRAND_PATTERNS`, `SkillEvalResult`,
# `evaluate_brand_skill(art_direction: str, loaded_skills: list[str] | None = None) -> SkillEvalResult`,
# and `run_eval_suite(services: ServiceContainer | None = None) -> dict[str, Any]`
# to verify that `visual_director` activates `brand-guidelines` and avoids forbidden styles.

# [Guidepost — Step 1c: Remote A2A Visual Director Service]
# Here is where we expose `visual_director` over the A2A protocol and connect the coordinator to it:
#   - `build_visual_director_card(rpc_url: str = "http://localhost:8801/a2a/visual_director") -> dict[str, Any]`
#   - `build_a2a_visual_director_app(services: ServiceContainer | None = None, rpc_url: str = ...) -> Any`
#     configured with `A2aAgentExecutorConfig(execute_interceptors=[include_artifacts_in_a2a_event_interceptor])`
#   - `_cloud_run_client(base_url: str)` (600s timeout + OIDC token for `https://`) and `_pitch_parts_only(part: Any)`
#   - `remote_visual_director = RemoteA2aAgent(name="visual_director", agent_card=..., httpx_client=..., genai_part_converter=_pitch_parts_only)`

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
     * `package(node_input)` and `package(ctx, node_input)` signatures, strips Markdown
     * code fences from branch values, and attaches `_key_visual(ctx)` when present.
     *
     * @param ctx_or_input Either a `node_input` dict (1-arg form) or `Context` (2-arg form).
     * @param node_input Dictionary of upstream outputs when `ctx_or_input` is a `Context`.
     * @return Dual sync/async stream yielding `Event(content=...)` and `Event(output=...)`.
     */
    """
    if node_input is None:
        if not isinstance(ctx_or_input, dict):
            raise ValueError("node_input must be a non-empty dictionary")
        ctx: Context | None = None
        actual_input = ctx_or_input
    else:
        if not isinstance(node_input, dict):
            raise ValueError("node_input must be a non-empty dictionary")
        ctx = ctx_or_input if isinstance(ctx_or_input, Context) else None
        actual_input = node_input

    if not actual_input:
        raise ValueError("nothing reached the join from: creative_director, copywriter")

    required_keys = ["creative_director", "copywriter"]
    missing_or_empty = [
        k
        for k in required_keys
        if k not in actual_input or not str(actual_input.get(k) or "").strip()
    ]
    extra_empty = [
        name
        for name, value in actual_input.items()
        if name not in missing_or_empty and not str(value or "").strip()
    ]
    all_empty = missing_or_empty + extra_empty
    if all_empty:
        raise ValueError(f"nothing reached the join from: {', '.join(all_empty)}")

    concept_val = strip_markdown_fences(str(actual_input["creative_director"])).strip()
    copy_val = strip_markdown_fences(str(actual_input["copywriter"])).strip()
    sections = [
        f"CONCEPT\n{concept_val}",
        f"COPY\n{copy_val}",
    ]
    if "brand_strategist" in actual_input and actual_input["brand_strategist"]:
        brand_val = strip_markdown_fences(str(actual_input["brand_strategist"])).strip()
        sections.append(f"BRAND STRATEGY\n{brand_val}")
    if "visual_director" in actual_input and actual_input["visual_director"]:
        art_val = strip_markdown_fences(str(actual_input["visual_director"])).strip()
        sections.append(f"ART DIRECTION\n{art_val}")

    pitch = "\n\n".join(sections)
    parts: list[Any] = [types.Part(text=pitch)]
    image = _key_visual(ctx)
    if image is not None:
        parts.append(types.Part(inline_data=image))

    events = [
        Event(author="package", content=types.Content(role="model", parts=parts)),
        Event(author="package", output=pitch),
    ]
    return _DualSyncAsyncEventStream(events)


loop_guard = LoopGuard(max_iterations=10)

# [Guidepost — Steps 3a & 3c: PreToolUse Hooks & HITL Approval Gate]
# - In Step 3a, add `HookDecision`, `ToolAuthorizationError`, `PreToolUseHook`, and
#   `validate_tool_call(tool_name, tool_args, loaded_skills)` to require `load_skill("brand-guidelines")`
#   before `generate_key_visual` can run.
# - In Step 3c, add `approve_concept` (RequestInput / `@node(rerun_on_resume=False)`),
#   `user_approval` (`@node(rerun_on_resume=True)` raising `ValueError("User rejected the concept")`
#   when rejected), `evaluate_user_approval`, and `run_hitl_workflow` to pause after `creative_director`.
#   Defining `approve_concept` or `user_approval` here also automatically enables the web UI's
#   Human-in-the-Loop approval controls (`#hitl-approval-card` via `/api/pitch` and `/api/approve`).
root_agent = Workflow(
    name="pitch_generator",
    edges=[
        (creative_director, brand_strategist, (copywriter, visual_director)),
        ((copywriter, visual_director), assemble, package),
    ],
)
loop_guard.validate_graph(root_agent.edges)

app = App(root_agent=root_agent, name="pitch_generator")


# [Guidepost — Step 4a: Tokenomics & Context Optimization]
# - In Step 4a, add `CompressedHistoryList`, `PromptCacheManager`, `TokenomicsManager`,
#   `compress_memory(turns)`, `prune_history(turns, max_tokens)`, and `select_model_strategy(task)`.


def run_graph_workflow(
    brief: str,
    *,
    services: ServiceContainer | None = None,
    max_iterations: int = 10,
) -> PitchPackage:
    """
    /**
     * Validates the workflow DAG with `LoopGuard` and executes the fan-out/fan-in pitch graph.
     *
     * Why: Provides a deterministic, offline-safe execution helper that validates the
     * graph topology, tracks every node visit in `LoopGuard`, parses structured payloads,
     * and returns a complete `PitchPackage`.
     *
     * @param brief Campaign product brief string.
     * @param services Optional `ServiceContainer` for offline LLM/artifact services.
     * @param max_iterations Maximum allowed node visits in `LoopGuard`.
     * @return Populated `PitchPackage` instance.
     */
    """
    if not isinstance(brief, str) or not brief.strip():
        raise ValueError("Campaign brief must be a non-empty string.")

    guard = LoopGuard(max_iterations=max_iterations)
    guard.validate_graph(root_agent.edges)

    svc = services or get_default_services()
    ctx = Context(services=svc)
    clean_brief = brief.strip()
    model_id = svc.config.flash_model

    guard.record_step("creative_director")
    concept_raw = svc.llm.generate_text(
        clean_brief,
        system_instruction=creative_director.instruction,
        model=model_id,
    )
    concept_lines = [ln.strip() for ln in concept_raw.splitlines() if ln.strip()]
    concept = ConceptPayload(
        concept_line=concept_lines[0] if concept_lines else f"Engineered for everyday motion: {clean_brief}.",
        rationale=(
            concept_lines[1]
            if len(concept_lines) > 1
            else "Grounded in practical commuter utility and understated design."
        ),
    )

    guard.record_step("brand_strategist")
    strategy_notes = svc.llm.generate_text(
        concept.concept_line,
        system_instruction=brand_strategist.instruction,
        model=model_id,
    )

    guard.record_step("copywriter")
    copy_text = svc.llm.generate_text(
        concept.concept_line,
        system_instruction=copywriter.instruction,
        model=model_id,
    )
    copy_payload = CopyPayload(caption=copy_text)

    guard.record_step("visual_director")
    art_text = svc.llm.generate_text(
        concept.concept_line,
        system_instruction=visual_director.instruction,
        model=model_id,
    )
    art_payload = ArtDirectionPayload(art_direction=art_text)

    guard.record_step("assemble")
    joined_inputs = {
        "creative_director": f"{concept.concept_line}\n{concept.rationale}",
        "brand_strategist": strategy_notes,
        "copywriter": copy_payload.caption,
        "visual_director": art_payload.art_direction,
    }

    guard.record_step("package")
    packaged_events = list(package(ctx, joined_inputs))
    final_text = ""
    for ev in packaged_events:
        if ev.output:
            final_text = str(ev.output)

    return PitchPackage(
        concept=concept,
        copy=copy_payload,
        art_direction=art_payload,
        brand_strategy=strategy_notes,
        pitch_text=final_text,
        trace=list(guard.visited_nodes),
    )


execute_workflow = run_graph_workflow
run_workflow = run_graph_workflow


def run_pitch_workflow(
    brief: str,
    *,
    session_id: str = "default",
    services: ServiceContainer | None = None,
    approved: bool | None = True,
    require_approval: bool = False,
) -> dict[str, Any]:
    """
    /**
     * Execute the Pitch Generator multi-agent workflow using injected cloud services.
     *
     * Why: Coordinates the 4-specialist pipeline (`creative_director` -> `brand_strategist`
     * -> (`copywriter`, `visual_director`) -> `assemble` -> `package`) on Gemini Enterprise
     * Agent Platform (`gemini-3.8-flash`), persists session state in `MemoryBankService`,
     * and records telemetry via `BigQueryAnalyticsService`. When the learner adds the HITL
     * approval gate (`approve_concept` / `user_approval`) in Module 3, this runner dynamically
     * pauses and resumes at the concept review gate.
     *
     * @param brief Non-empty campaign topic brief.
     * @param session_id Session identifier for Memory Bank persistence.
     * @param services Optional injected `ServiceContainer` (defaults to `get_default_services()`).
     * @param approved HITL approval state (`True` to complete, `False` to reject,
     *   `None` to pause at `input_required` when HITL is enabled).
     * @param require_approval If True, pauses at the HITL gate (`status="input_required"`).
     * @return Workflow result dictionary with keys `session_id`, `status`, `concept`,
     *   `copy`, `brand_strategy`, `art_direction`, `key_visual_uri`, `telemetry`,
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
    module_globals = globals()
    strip_fn = module_globals.get("strip_markdown_fences")
    active_model = active_services.config.flash_model

    # Step 1: Creative Director generates campaign concept & rationale
    concept = active_services.llm.generate_text(
        clean_brief,
        system_instruction=creative_director.instruction,
        model=active_model,
    )
    if callable(strip_fn):
        concept = strip_fn(concept)

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
            "brand_strategy": "",
            "art_direction": "",
            "key_visual_uri": None,
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
            "brand_strategy": "",
            "art_direction": "",
            "key_visual_uri": None,
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

    hitl_defined = (
        module_globals.get("approve_concept") is not None
        or module_globals.get("user_approval") is not None
    )
    join_inputs: dict[str, Any] = {
        "creative_director": concept,
        "copywriter": copy_text,
    }
    nodes_executed: list[str] = (
        ["creative_director", "approve_concept", "user_approval", "copywriter"]
        if hitl_defined
        else ["creative_director", "copywriter"]
    )
    brand_text = ""
    art_direction = ""
    key_visual_uri: str | None = None
    key_visual_url: str | None = None
    artifacts_meta: list[dict[str, Any]] = []

    loop_guard_cls = module_globals.get("LoopGuard")
    active_guard = None
    if callable(loop_guard_cls):
        active_guard = loop_guard_cls(max_iterations=10)
        if hasattr(active_guard, "validate_graph") and hasattr(root_agent, "edges"):
            active_guard.validate_graph(root_agent.edges)
        if hasattr(active_guard, "record_step"):
            active_guard.record_step("creative_director")
            active_guard.record_step("copywriter")

    if callable(strip_fn):
        copy_text = strip_fn(copy_text)
        join_inputs["creative_director"] = concept
        join_inputs["copywriter"] = copy_text

    brand_agent = module_globals.get("brand_strategist")
    if brand_agent is None:
        brand_agent = next(
            (
                v
                for v in module_globals.values()
                if isinstance(v, Agent) and getattr(v, "name", "") == "brand_strategist"
            ),
            None,
        )
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
    if remote_vd is None:
        remote_vd = next(
            (v for v in module_globals.values() if isinstance(v, RemoteA2aAgent)),
            None,
        )
    visual_agent = (
        module_globals.get("visual_director")
        or next(
            (
                v
                for v in module_globals.values()
                if isinstance(v, Agent) and getattr(v, "name", "") == "visual_director"
            ),
            None,
        )
        or remote_vd
    )
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

        visual_instruction = str(
            getattr(
                visual_agent,
                "instruction",
                (
                    "You are the Visual Director. Produce brand-compliant art direction "
                    "using our deep indigo and slate palette with a warm amber or terracotta "
                    "accent, single low raking light with long shadows, off-center negative "
                    "space, and one realistic photographic subject."
                ),
            )
            or ""
        )
        skill_md_path = Path(__file__).resolve().parent / "skills" / "brand-guidelines" / "SKILL.md"
        if skill_md_path.is_file():
            try:
                skill_text = skill_md_path.read_text(encoding="utf-8").strip()
                if skill_text and skill_text not in visual_instruction:
                    visual_instruction = f"{visual_instruction}\n\n[Loaded Skill: brand-guidelines]\n{skill_text}"
            except OSError:
                pass
        effective_visual_instruction = (
            f"{visual_instruction}\n\n"
            "Return ONLY the written art direction notes as plain text "
            "(do not emit tool call syntax; generate_key_visual will be invoked automatically with your text output)."
        )
        art_direction = active_services.llm.generate_text(
            concept,
            system_instruction=effective_visual_instruction,
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

    if not approved:
        result = run_pitch_workflow(
            brief,
            session_id=clean_session,
            services=active_services,
            approved=False,
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
        require_approval=False,
    )
    result["reviewer_feedback"] = feedback
    active_services.memory_bank.save_session(clean_session, result)
    return result
