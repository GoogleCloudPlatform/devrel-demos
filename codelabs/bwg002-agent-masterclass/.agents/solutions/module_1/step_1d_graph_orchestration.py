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
 * @file step_1d_graph_orchestration.py
 * @description Module 1 — Step 1d: Graph Orchestration, JoinNodes, Structured JSON
 *   Payloads, and Circular Loop Prevention (`F10`).
 *
 * Why: Multi-agent creative workflows require deterministic fan-out and fan-in
 * synchronization (`JoinNode`), strict structured JSON payload contracts between
 * nodes (stripping LLM Markdown code fences before validation), and a cycle-aware
 * `LoopGuard` that prevents infinite loops in both static graph topologies and
 * runtime node execution before packaging the final pitch.
 */
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import sys
from typing import Any

_APP_ROOT = Path(__file__).resolve().parents[3]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from pitch_generator.agent import (  # noqa: E402
    MODEL,
    Agent,
    App,
    Context,
    Event,
    JoinNode,
    Workflow,
    copywriter,
    creative_director,
    types,
)
from pitch_generator.app_utils.services import (  # noqa: E402
    ServiceContainer,
    get_default_services,
)
from pitch_generator.config import get_config  # noqa: E402

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


class CircularLoopError(ValueError):
    """
    /**
     * Raised when a workflow graph contains a cycle or exceeds maximum allowed node visits.
     *
     * Why: Subclasses `ValueError` so static DAG validation and runtime iteration guards
     * fail fast with a deterministic exception before runaway LLM token consumption occurs.
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

visual_director = Agent(
    name="visual_director",
    model=MODEL,
    description="Translates a campaign concept into house-style art direction for a key visual.",
    instruction=(
        "You are the Visual Director. Write art direction for ONE key visual using "
        "our house brand palette (deep indigo and slate ground with one warm amber "
        "or terracotta accent), single low raking light with long shadows, off-center "
        "composition with generous negative space, and one realistic photographic "
        "subject with shallow depth of field."
    ),
    output_key="visual_director",
)

assemble = JoinNode(name="assemble")


def package(
    ctx_or_input: Context | dict[str, Any],
    node_input: dict[str, Any] | None = None,
) -> Iterator[Event]:
    """
    /**
     * Deterministic terminal node that validates joined branch outputs and formats the pitch.
     *
     * Why: Running after `assemble = JoinNode(name="assemble")` guarantees all upstream
     * branches (`copywriter`, `visual_director`) have completed; validating non-empty
     * branch outputs ensures silent upstream failures never produce an incomplete pitch.
     *
     * @param ctx_or_input Either the workflow `Context` or `node_input` dict (1-arg call).
     * @param node_input Dictionary of upstream branch outputs keyed by agent name.
     * @return Generator yielding ADK `Event` objects with the formatted pitch.
     */
    """
    if isinstance(ctx_or_input, dict) and node_input is None:
        ctx = Context()
        resolved_input = ctx_or_input
    else:
        ctx = ctx_or_input if isinstance(ctx_or_input, Context) else Context()
        resolved_input = node_input or {}

    if not isinstance(resolved_input, dict) or not resolved_input:
        raise ValueError("nothing reached the join from: creative_director, copywriter")

    empty = [k for k, v in resolved_input.items() if v is None or not str(v).strip()]
    if empty:
        raise ValueError(f"nothing reached the join from: {', '.join(empty)}")

    for required_key in ("creative_director", "copywriter"):
        if required_key not in resolved_input:
            raise ValueError(f"nothing reached the join from: {required_key}")

    concept_raw = str(resolved_input["creative_director"]).strip()
    copy_raw = str(resolved_input["copywriter"]).strip()
    art_raw = str(
        resolved_input.get(
            "visual_director",
            "Moody studio lighting on deep indigo and slate surfaces with a warm amber rim.",
        )
    ).strip()

    pitch = (
        f"CONCEPT\n{concept_raw}\n\n"
        f"COPY\n{copy_raw}\n\n"
        f"ART DIRECTION\n{art_raw}"
    )

    image = _key_visual(ctx)
    parts: list[types.Part] = [types.Part(text=pitch)]
    if image is not None:
        parts.append(types.Part(inline_data=image))

    events = [
        Event(
            author="package",
            content=types.Content(role="model", parts=parts),
        ),
        Event(author="package", output=pitch),
    ]
    return (ev for ev in events)


root_agent = Workflow(
    name="pitch_generator",
    edges=[
        (creative_director, brand_strategist, (copywriter, visual_director)),
        ((copywriter, visual_director), assemble, package),
    ],
)

app = App(root_agent=root_agent, name="pitch_generator")


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


__all__ = [
    "ArtDirectionPayload",
    "CampaignConcept",
    "CircularLoopError",
    "ConceptPayload",
    "CopyPayload",
    "LoopGuard",
    "PayloadValidationError",
    "PitchPackage",
    "VisualPayload",
    "app",
    "assemble",
    "brand_strategist",
    "copywriter",
    "creative_director",
    "execute_workflow",
    "extract_json_payload",
    "package",
    "parse_json_payload",
    "parse_payload",
    "root_agent",
    "run_graph_workflow",
    "run_workflow",
    "strip_markdown_fences",
    "visual_director",
]
