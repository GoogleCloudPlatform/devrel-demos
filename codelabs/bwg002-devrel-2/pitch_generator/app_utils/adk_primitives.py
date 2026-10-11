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
 * @file adk_primitives.py
 * @description ADK workflow primitives, structured handoff payload contracts,
 *   and `LoopGuard` DAG validation for the Agentic Pitch Generator.
 *
 * Why: Isolating the underlying ADK runtime shims (`Agent`, `RemoteA2aAgent`,
 * `JoinNode`, `Workflow`, `App`, `Context`, `Event`, `RequestInput`, `node`),
 * structured payload dataclasses (`ConceptPayload`, `CopyPayload`,
 * `ArtDirectionPayload`, `PitchPackage`), and `LoopGuard` cycle detection into
 * a dedicated support module keeps `pitch_generator/agent.py` concise and
 * focused on the specialist agent definitions, workflow graph, and lab guideposts.
 */
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
import json
import re
from typing import Any, AsyncIterator, Callable, Iterator

from pitch_generator.app_utils.services import (
    ServiceContainer,
    get_default_services,
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
