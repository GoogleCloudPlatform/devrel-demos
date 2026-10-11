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
 * @file step_3c_hitl_authorizations.py
 * @description Module 3 Step 3c reference solution implementing Human-in-the-Loop
 *   (HITL) authorization gates (`approve_concept` with `rerun_on_resume=False`
 *   and `user_approval` with `rerun_on_resume=True`) and workflow orchestration.
 *
 * Why: Placing an explicit human approval gate after `creative_director` and
 * before parallel fan-out to `copywriter` and `visual_director` prevents wasted
 * downstream LLM tokens and image-generation costs when a human reviewer rejects
 * a draft campaign concept (`docs/outline.md` §5.3).
 */
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib.util
from pathlib import Path
import sys
from typing import Any, AsyncIterator, Callable

_APP_ROOT = Path(__file__).resolve().parents[3]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from pitch_generator.agent import (  # noqa: E402
    Context as _BaseContext,
    Event,
    JoinNode,
    RequestInput,
    Workflow,
    assemble,
    copywriter,
    creative_director,
    node,
    package,
    types,
)
from pitch_generator.app_utils.services import (  # noqa: E402
    ServiceContainer,
    get_default_services,
)

APPROVAL_PROMPT_MESSAGE: str = "Please approve the campaign concept (yes/no)."
AFFIRMATIVE_RESPONSES: frozenset[str] = frozenset({"yes", "y"})


def _load_step_3b_scrubber() -> Any:
    """
    /**
     * Dynamically load Step 3b's `PIIScrubber` to sanitize campaign briefs before
     * persisting HITL session state.
     *
     * Why: Ensures Step 3c works seamlessly whether imported via package path or
     * `importlib.util.spec_from_file_location`.
     */
    """
    step_3b_path = Path(__file__).resolve().parent / "step_3b_pii_scrubbing.py"
    spec = importlib.util.spec_from_file_location(
        "step_3b_pii_scrubbing_internal",
        step_3b_path,
    )
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.PIIScrubber()


class Context(_BaseContext):
    """
    /**
     * Enhanced ADK `Context` supporting `resume_input` injection for HITL resumption.
     *
     * Why: When a paused workflow resumes after `approve_concept`, ADK supplies the
     * human reviewer's response via `resume_input` (or `session.state["approval_response"]`)
     * so `await ctx.run_node(approve_concept)` returns the human's decision without
     * re-emitting the `RequestInput` prompt (`rerun_on_resume=False`).
     */
    """

    def __init__(
        self,
        session_id: str = "default",
        state: dict[str, Any] | None = None,
        services: ServiceContainer | None = None,
        node_runner: Callable[[Any], Any] | None = None,
        *,
        resume_input: Any = None,
    ) -> None:
        """
        /**
         * Initialize the HITL-aware ADK execution context.
         *
         * Why: Stores `resume_input` and binds `self.state` as a convenience alias
         * for `self.session.state` so both `ctx.session.state` and `ctx.state` work.
         *
         * @param session_id Unique identifier for the workflow session.
         * @param state Initial session state dictionary (e.g., `{"creative_director": ...}`).
         * @param services Optional injected `ServiceContainer`.
         * @param node_runner Optional custom runner for `ctx.run_node`.
         * @param resume_input Optional human response supplied when resuming from pause.
         */
        """
        super().__init__(
            session_id=session_id,
            state=state,
            services=services,
            node_runner=node_runner,
        )
        self.resume_input = resume_input
        self.state = self.session.state

    async def run_node(self, target_node: Any) -> Any:
        """
        /**
         * Execute a sub-node or return the cached `resume_input` when resuming a
         * `rerun_on_resume=False` gate node.
         *
         * Why: Enables `user_approval` to `await ctx.run_node(approve_concept)` and
         * receive the human's `"yes"`/`"no"` string upon resumption.
         *
         * @param target_node Target node function (`approve_concept`).
         * @return Human response string or yielded `RequestInput` event.
         */
        """
        if self._node_runner is not None:
            return self._node_runner(target_node)
        if self.resume_input is not None:
            return self.resume_input
        if "approval_response" in self.session.state:
            return self.session.state["approval_response"]
        return await super().run_node(target_node)


@node(rerun_on_resume=False)
async def approve_concept(ctx: Context | None = None) -> AsyncIterator[RequestInput]:
    """
    /**
     * HITL prompt node that pauses the workflow and asks a human to approve the concept.
     *
     * Why: Decorated with `@node(rerun_on_resume=False)` so ADK yields `RequestInput`
     * on the initial pass to pause execution, and on resume returns the human's
     * response directly without re-running the prompt node. Also validates that
     * `creative_director` produced a non-empty concept before prompting the reviewer.
     *
     * @param ctx Active ADK `Context` containing `session.state["creative_director"]`.
     * @return Async iterator yielding `RequestInput`.
     */
    """
    if ctx is not None:
        state_dict = (
            ctx.session.state
            if hasattr(ctx, "session") and hasattr(ctx.session, "state")
            else getattr(ctx, "state", None)
        )
        if isinstance(state_dict, dict):
            concept_draft = state_dict.get("creative_director")
            if not isinstance(concept_draft, str) or not concept_draft.strip():
                raise ValueError(
                    "Cannot request human approval for an empty campaign concept draft."
                )

    yield RequestInput(
        message=APPROVAL_PROMPT_MESSAGE,
        response_schema=str,
    )


def evaluate_user_approval(concept: str, user_response: Any) -> str:
    """
    /**
     * Validate the human reviewer's approval response in fail-closed mode.
     *
     * Why: Security and cost gates must fail closed—only explicit affirmative
     * responses (`"yes"` or `"y"`, case-insensitive) unlock downstream execution,
     * whereas `"no"`, `"n"`, empty strings, whitespace, or ambiguous replies
     * (`"maybe"`, `"later"`) raise `ValueError("User rejected the concept")`.
     *
     * @param concept The upstream campaign concept text to approve.
     * @param user_response Raw human response string or boolean.
     * @return Formatted Markdown string starting with `"## Approved Concept"`.
     */
    """
    if not isinstance(concept, str) or not concept.strip():
        raise ValueError(
            "Cannot request human approval for an empty campaign concept draft."
        )

    if isinstance(user_response, bool):
        is_approved = user_response is True
    elif isinstance(user_response, str):
        normalized = user_response.strip().lower()
        is_approved = normalized in AFFIRMATIVE_RESPONSES
    else:
        is_approved = False

    if not is_approved:
        raise ValueError("User rejected the concept")

    return f"## Approved Concept\n\n{concept.strip()}"


@node(rerun_on_resume=True)
async def user_approval(ctx: Context) -> AsyncIterator[Event]:
    """
    /**
     * HITL validation node that awaits `approve_concept` and enforces the human's decision.
     *
     * Why: Decorated with `@node(rerun_on_resume=True)` so ADK re-enters this node
     * when the human submits their decision, receives the response from
     * `await ctx.run_node(approve_concept)`, emits `## Approved Concept` on `"yes"`,
     * or raises `ValueError("User rejected the concept")` to halt the graph on rejection.
     *
     * @param ctx Active ADK `Context`.
     * @return Async iterator yielding the approved concept `Event`.
     */
    """
    concept_text = ""
    if hasattr(ctx, "session") and hasattr(ctx.session, "state"):
        concept_text = str(ctx.session.state.get("creative_director") or "")
    elif hasattr(ctx, "state") and isinstance(ctx.state, dict):
        concept_text = str(ctx.state.get("creative_director") or "")

    user_response = await ctx.run_node(approve_concept)
    approved_md = evaluate_user_approval(concept_text, user_response)

    yield Event(
        content=types.Content(role="model", parts=[types.Part(text=approved_md)]),
        output=approved_md,
    )


@dataclass
class HITLWorkflowResult:
    """
    /**
     * Structured result returned by `run_hitl_workflow`.
     *
     * Why: Provides both attribute access and dictionary compatibility for
     * inspecting workflow `status` (`"input_required"`, `"completed"`, `"rejected"`),
     * downstream call counts, and generated campaign artifacts.
     */
    """

    session_id: str
    status: str
    concept: str
    approved_banner: str = ""
    copy: str = ""
    art_direction: str = ""
    key_visual_uri: str | None = None
    pitch_text: str = ""
    prompt: str = APPROVAL_PROMPT_MESSAGE
    downstream_calls: int = 0
    copywriter_calls: int = 0
    visual_director_calls: int = 0
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    telemetry: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Convert the HITL workflow result into a plain dictionary.
         *
         * Why: Ensures seamless interoperability with JSON endpoints and `extract_field`.
         *
         * @return Dictionary representation of the workflow result.
         */
        """
        return {
            "session_id": self.session_id,
            "status": self.status,
            "concept": self.concept,
            "approved_banner": self.approved_banner,
            "concept_header": self.approved_banner,
            "copy": self.copy,
            "art_direction": self.art_direction,
            "key_visual_uri": self.key_visual_uri,
            "pitch_text": self.pitch_text,
            "prompt": self.prompt,
            "downstream_calls": self.downstream_calls,
            "copywriter_calls": self.copywriter_calls,
            "visual_director_calls": self.visual_director_calls,
            "artifacts": list(self.artifacts),
            "telemetry": dict(self.telemetry),
        }


def run_hitl_workflow(
    brief: str,
    *,
    approved: bool | str | None = None,
    session_id: str = "default",
    feedback: str = "",
    services: ServiceContainer | None = None,
) -> dict[str, Any]:
    """
    /**
     * Execute the HITL-guarded Pitch Generator workflow for a campaign brief.
     *
     * Why: Orchestrates `creative_director` -> `user_approval` (`approve_concept`) ->
     * parallel `copywriter` + `visual_director` -> `assemble` (`JoinNode`) -> `package`.
     * Strictly guarantees that when `approved` is `None` (paused) or `False` / `"no"`
     * (rejected), zero downstream `copywriter` or `visual_director` calls occur.
     *
     * @param brief Product or campaign brief text.
     * @param approved `None` to pause for input, `True`/`"yes"` to approve, or `False`/`"no"` to reject.
     * @param session_id Unique session identifier for Memory Bank persistence.
     * @param feedback Optional human reviewer notes.
     * @param services Optional injected `ServiceContainer`.
     * @return Dictionary with `status`, `concept`, `copy`, `art_direction`, `key_visual_uri`, and call counts.
     */
    """
    if not isinstance(brief, str) or not brief.strip():
        raise ValueError("Campaign brief must be a non-empty string.")

    active_services = services or get_default_services()
    scrubber = _load_step_3b_scrubber()
    clean_brief = (
        scrubber.scrub_text(brief.strip()).scrubbed
        if scrubber is not None
        else brief.strip()
    )
    clean_feedback = (
        scrubber.scrub_text(feedback.strip()).scrubbed
        if (scrubber is not None and feedback)
        else (feedback or "").strip()
    )

    concept_text = active_services.llm.generate_text(
        clean_brief,
        system_instruction=creative_director.instruction,
        model=active_services.config.flash_model,
    )
    if scrubber is not None:
        concept_text = scrubber.scrub_text(concept_text).scrubbed

    # Case 1: Paused awaiting human input
    if approved is None:
        session_state = {
            "session_id": session_id,
            "brief": clean_brief,
            "status": "input_required",
            "creative_director": concept_text,
            "concept": concept_text,
            "copy": "",
            "art_direction": "",
            "key_visual_uri": None,
            "prompt": APPROVAL_PROMPT_MESSAGE,
            "downstream_calls": 0,
            "copywriter_calls": 0,
            "visual_director_calls": 0,
        }
        active_services.memory_bank.save_session(session_id, session_state)
        return dict(session_state)

    # Determine whether the human response is affirmative
    try:
        resp_token = (
            "yes"
            if approved is True
            else ("no" if approved is False else str(approved))
        )
        approved_banner = evaluate_user_approval(concept_text, resp_token)
    except ValueError as exc:
        # Case 2: Rejected — strictly zero downstream calls!
        telemetry_event = {
            "session_id": session_id,
            "status": "rejected",
            "downstream_calls": 0,
            "reason": str(exc),
        }
        active_services.analytics.record_telemetry(telemetry_event)
        rejected_state = {
            "session_id": session_id,
            "brief": clean_brief,
            "status": "rejected",
            "creative_director": concept_text,
            "concept": concept_text,
            "approved_banner": "",
            "concept_header": "",
            "copy": "",
            "art_direction": "",
            "key_visual_uri": None,
            "pitch_text": "",
            "feedback": clean_feedback,
            "error": str(exc),
            "downstream_calls": 0,
            "copywriter_calls": 0,
            "visual_director_calls": 0,
            "artifacts": [],
            "telemetry": telemetry_event,
        }
        active_services.memory_bank.save_session(session_id, rejected_state)
        return dict(rejected_state)

    # Case 3: Approved — execute downstream copywriter and visual_director branches
    copy_prompt = (
        f"{concept_text}\nReviewer feedback: {clean_feedback}"
        if clean_feedback
        else concept_text
    )
    copy_text = active_services.llm.generate_text(
        copy_prompt,
        system_instruction=copywriter.instruction,
        model=active_services.config.flash_model,
    )
    art_direction = active_services.llm.generate_text(
        concept_text,
        system_instruction=(
            "You are the Visual Director. Translate the approved campaign concept "
            "into brand-compliant art direction with deep indigo/slate grounding, "
            "warm amber/terracotta accent, golden hour raking light, and off-center composition."
        ),
        model=active_services.config.flash_model,
    )
    if scrubber is not None:
        copy_text = scrubber.scrub_text(copy_text).scrubbed
        art_direction = scrubber.scrub_text(art_direction).scrubbed

    image_bytes, mime_type = active_services.llm.generate_image(
        art_direction,
        model=active_services.config.image_model,
    )
    artifact_record = active_services.artifacts.save_artifact(
        filename="key_visual.png",
        data=image_bytes,
        mime_type=mime_type,
        session_id=session_id,
    )
    key_visual_uri = (
        artifact_record.gcs_uri
        or f"memory://{session_id}/{artifact_record.filename}#v{artifact_record.version}"
    )

    packaged_events = list(
        package(
            {
                "creative_director": concept_text,
                "copywriter": copy_text,
                "visual_director": art_direction,
            }
        )
    )
    packaged_body = str(packaged_events[-1].output or "")
    full_pitch_text = f"{approved_banner}\n\n{packaged_body}"

    telemetry_event = {
        "session_id": session_id,
        "status": "completed",
        "downstream_calls": 2,
        "copywriter_calls": 1,
        "visual_director_calls": 1,
        "key_visual_uri": key_visual_uri,
    }
    active_services.analytics.record_telemetry(telemetry_event)

    completed_state = {
        "session_id": session_id,
        "brief": clean_brief,
        "status": "completed",
        "creative_director": concept_text,
        "concept": concept_text,
        "approved_banner": approved_banner,
        "concept_header": approved_banner,
        "copy": copy_text,
        "art_direction": art_direction,
        "key_visual_uri": key_visual_uri,
        "pitch_text": full_pitch_text,
        "feedback": clean_feedback,
        "downstream_calls": 2,
        "copywriter_calls": 1,
        "visual_director_calls": 1,
        "artifacts": [artifact_record.to_metadata_dict()],
        "telemetry": telemetry_event,
    }
    active_services.memory_bank.save_session(session_id, completed_state)
    return dict(completed_state)


execute_hitl_workflow = run_hitl_workflow

hitl_workflow = Workflow(
    name="pitch_generator_hitl",
    edges=[
        ("START", creative_director),
        (creative_director, user_approval),
        (user_approval, copywriter),
        ((user_approval, copywriter), assemble),
        (assemble, package),
    ],
)

__all__ = [
    "AFFIRMATIVE_RESPONSES",
    "APPROVAL_PROMPT_MESSAGE",
    "Context",
    "Event",
    "HITLWorkflowResult",
    "JoinNode",
    "RequestInput",
    "Workflow",
    "approve_concept",
    "evaluate_user_approval",
    "execute_hitl_workflow",
    "hitl_workflow",
    "node",
    "run_hitl_workflow",
    "user_approval",
]
