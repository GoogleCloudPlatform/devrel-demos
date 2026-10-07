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
 * @file step_4b_hybrid_routing.py
 * @description Module 4 Step 4b — Hybrid Model Routing and Tiered Fallback Chain.
 *
 * Why: Enterprise pitch generation workloads vary widely in latency sensitivity, data
 * privacy requirements, and computational complexity. Running every task on frontier cloud
 * models incurs unnecessary egress and quota consumption. This module provides a 3-tier
 * dynamic router across client browser WebLLM (on-device), local open-weights Gemma (low-latency
 * private edge), and Gemini Enterprise Agent Platform (frontier cloud reasoning) with a
 * deterministic fallback chain ("webllm_browser" -> "local_model" -> "cloud_frontier").
 */
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from pitch_generator.config import (
    PitchConfig,
    get_config,
)

VALID_ROUTING_MODES: tuple[str, ...] = (
    "auto",
    "webllm_browser",
    "local_model",
    "cloud_frontier",
)
FALLBACK_CHAIN: list[str] = ["webllm_browser", "local_model", "cloud_frontier"]
DEFAULT_WEBLLM_MODEL: str = "Llama-3.2-1B-Instruct-q4f16_1-MLC"


@dataclass
class RoutingDecision:
    """
    /**
     * Strongly typed container representing the target execution environment for a task.
     *
     * Why: Provides structured metadata detailing the selected execution target, model
     * identifier, whether fallback was activated, and the architectural rationale. Supports
     * both attribute access and dictionary-style subscripting for seamless interoperability.
     *
     * @param target Selected execution tier ("webllm_browser", "local_model", or "cloud_frontier").
     * @param model_id Concrete model identifier assigned to handle the task.
     * @param requested_mode Original routing mode requested by the caller ("auto" or specific tier).
     * @param fallback_used Whether execution degraded along the fallback chain.
     * @param fallback_applied Identical to fallback_used for interface compatibility.
     * @param fallback_chain Ordered sequence of candidate fallback tiers.
     * @param rationale Architectural reasoning for the dispatch decision.
     * @param webgpu_available Whether client WebGPU hardware acceleration was detected.
     * @param local_gpu_available Whether local Gemma GPU execution environment was available.
     */
    """

    target: str
    model_id: str
    requested_mode: str = "auto"
    fallback_used: bool = False
    fallback_applied: bool = False
    fallback_chain: list[str] = field(default_factory=lambda: list(FALLBACK_CHAIN))
    rationale: str = ""
    webgpu_available: bool = False
    local_gpu_available: bool = False

    def __post_init__(self) -> None:
        """
        /**
         * Synchronize fallback indicator flags upon initialization.
         *
         * Why: Guarantees fallback_used and fallback_applied remain strictly identical.
         */
        """
        if self.fallback_used or self.fallback_applied:
            self.fallback_used = True
            self.fallback_applied = True

    def __getitem__(self, item: str) -> Any:
        """
        /**
         * Support dictionary-style key subscripting.
         *
         * Why: Allows callers to access fields via decision["target"] transparently.
         */
        """
        if hasattr(self, item):
            return getattr(self, item)
        raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        """
        /**
         * Support dictionary-style .get() access.
         *
         * Why: Prevents KeyErrors when consumers treat decision as a standard mapping.
         */
        """
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        """
        /**
         * Support 'in' containment checks.
         *
         * Why: Allows callers to verify field existence via 'target' in decision.
         */
        """
        return hasattr(self, item)

    def keys(self) -> list[str]:
        """
        /**
         * Return list of public attribute names.
         *
         * Why: Satisfies mapping dictionary inspection routines.
         */
        """
        return [
            "target",
            "model_id",
            "requested_mode",
            "fallback_used",
            "fallback_applied",
            "fallback_chain",
            "rationale",
            "webgpu_available",
            "local_gpu_available",
        ]

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Convert decision into a plain dictionary representation.
         *
         * Why: Enables straightforward JSON serialization for REST API responses.
         */
        """
        return {
            "target": self.target,
            "model_id": self.model_id,
            "requested_mode": self.requested_mode,
            "fallback_used": self.fallback_used,
            "fallback_applied": self.fallback_applied,
            "fallback_chain": list(self.fallback_chain),
            "rationale": self.rationale,
            "webgpu_available": self.webgpu_available,
            "local_gpu_available": self.local_gpu_available,
        }


class HybridModelRouter:
    """
    /**
     * Dynamic task complexity analyzer and multi-tier hybrid model router.
     *
     * Why: Evaluates task metadata (complexity, multimodal requirements, privacy sensitivity)
     * against runtime hardware constraints to select the optimal execution environment.
     */
    """

    def __init__(
        self,
        config: PitchConfig | None = None,
        webllm_model_id: str = DEFAULT_WEBLLM_MODEL,
    ) -> None:
        """
        /**
         * Initialize the hybrid model router.
         *
         * Why: Injects runtime configuration and defines default browser model identifiers.
         *
         * @param config Optional PitchConfig container.
         * @param webllm_model_id Client browser WebLLM model identifier.
         */
        """
        self.config = config or get_config()
        self.webllm_model_id = webllm_model_id

    def route_task(
        self,
        task: Mapping[str, Any] | str | None = None,
        **kwargs: Any,
    ) -> RoutingDecision:
        """
        /**
         * Dispatch a task across browser, local, and cloud tiers with automatic fallback.
         *
         * Why: Implements the 3-tier routing strategy and fallback chain:
         * 1. Multimodal tasks strictly require Cloud Frontier (overriding forced edge requests).
         * 2. High-complexity or explicit cloud tasks route directly to Cloud Frontier.
         * 3. Low-complexity tasks target browser WebLLM, falling back to local GPU, then cloud.
         * 4. Medium-complexity or private tasks target local GPU, falling back to cloud.
         *
         * @param task Task metadata dictionary, prompt string, or None.
         * @param kwargs Additional task parameter overrides.
         * @return Structured RoutingDecision instance.
         */
        """
        meta: dict[str, Any] = {}
        if isinstance(task, Mapping):
            meta.update(task)
        elif isinstance(task, str):
            meta["brief"] = task
            meta["prompt"] = task
        meta.update(kwargs)

        raw_mode = (
            meta.get("routing_mode")
            or meta.get("preferred_target")
            or meta.get("target")
            or "auto"
        )
        clean_mode = str(raw_mode).strip().lower()
        if clean_mode not in VALID_ROUTING_MODES:
            raise ValueError(
                f"Unsupported routing_mode {raw_mode!r}. Expected one of {VALID_ROUTING_MODES}."
            )

        task_type = str(meta.get("task_type", "")).strip().lower()
        complexity = str(meta.get("complexity", "medium")).strip().lower()
        privacy_level = str(meta.get("privacy_level", "standard")).strip().lower()

        privacy_sensitive = bool(meta.get("privacy_sensitive", False)) or (
            privacy_level in {"strict", "pii", "high", "sensitive"}
        )
        requires_multimodal = bool(meta.get("requires_multimodal", False)) or (
            task_type in {"generate_key_visual", "image_generation", "multimodal"}
        )
        browser_webgpu = bool(
            meta.get("browser_webgpu_available", meta.get("webgpu_available", False))
        )
        local_gpu = bool(
            meta.get("local_gpu_available", meta.get("local_gpu", False))
        )

        # 1. Multimodal Override Rule: Vision tasks require cloud frontier capabilities
        if requires_multimodal:
            model_id = self.config.image_model
            fallback_needed = clean_mode in {"webllm_browser", "local_model"}
            return RoutingDecision(
                target="cloud_frontier",
                model_id=model_id,
                requested_mode=clean_mode,
                fallback_used=fallback_needed,
                fallback_applied=fallback_needed,
                webgpu_available=browser_webgpu,
                local_gpu_available=local_gpu,
                rationale=(
                    f"Routed to Cloud Frontier ({model_id}) on Gemini Enterprise Agent Platform because "
                    "multimodal visual asset generation requires cloud image model capabilities."
                ),
            )

        # 2. Explicit Cloud Frontier or High Complexity in Auto Mode
        if clean_mode == "cloud_frontier" or (clean_mode == "auto" and complexity == "high"):
            model_id = self.config.flash_model
            return RoutingDecision(
                target="cloud_frontier",
                model_id=model_id,
                requested_mode=clean_mode,
                fallback_used=False,
                fallback_applied=False,
                webgpu_available=browser_webgpu,
                local_gpu_available=local_gpu,
                rationale=(
                    f"Routed to Cloud Frontier ({model_id}) for high-complexity multi-agent "
                    "reasoning and strategic brand synthesis."
                ),
            )

        # 3. Determine Desired Target Tier
        if clean_mode == "webllm_browser":
            desired_target = "webllm_browser"
        elif clean_mode == "local_model":
            desired_target = "local_model"
        else:
            # Auto mode determination
            if complexity == "low":
                desired_target = "webllm_browser"
            elif complexity == "medium" and (local_gpu or privacy_sensitive):
                desired_target = "local_model"
            elif privacy_sensitive:
                desired_target = "webllm_browser"
            else:
                desired_target = "cloud_frontier"

        # 4. Evaluate Hardware Availability and Apply Fallback Chain
        if desired_target == "webllm_browser":
            if browser_webgpu:
                return RoutingDecision(
                    target="webllm_browser",
                    model_id=self.webllm_model_id,
                    requested_mode=clean_mode,
                    fallback_used=False,
                    fallback_applied=False,
                    webgpu_available=True,
                    local_gpu_available=local_gpu,
                    rationale=(
                        "Routed to client-side WebLLM in browser via WebGPU acceleration for "
                        "zero-cost on-device execution."
                    ),
                )
            elif local_gpu:
                return RoutingDecision(
                    target="local_model",
                    model_id=self.config.local_model,
                    requested_mode=clean_mode,
                    fallback_used=True,
                    fallback_applied=True,
                    webgpu_available=False,
                    local_gpu_available=True,
                    rationale=(
                        "Fell back from browser WebLLM to local model (Gemma) because client "
                        "browser WebGPU acceleration is unavailable."
                    ),
                )
            else:
                return RoutingDecision(
                    target="cloud_frontier",
                    model_id=self.config.flash_model,
                    requested_mode=clean_mode,
                    fallback_used=True,
                    fallback_applied=True,
                    webgpu_available=False,
                    local_gpu_available=False,
                    rationale=(
                        "Fell back from browser WebLLM and local model to Cloud Frontier Flash "
                        "because neither WebGPU nor local GPU hardware was detected."
                    ),
                )

        if desired_target == "local_model":
            if local_gpu:
                return RoutingDecision(
                    target="local_model",
                    model_id=self.config.local_model,
                    requested_mode=clean_mode,
                    fallback_used=False,
                    fallback_applied=False,
                    webgpu_available=browser_webgpu,
                    local_gpu_available=True,
                    rationale=(
                        f"Routed to local open-weights model ({self.config.local_model}) on local "
                        "GPU for confidential edge execution."
                    ),
                )
            else:
                return RoutingDecision(
                    target="cloud_frontier",
                    model_id=self.config.flash_model,
                    requested_mode=clean_mode,
                    fallback_used=True,
                    fallback_applied=True,
                    webgpu_available=browser_webgpu,
                    local_gpu_available=False,
                    rationale=(
                        "Fell back from local model to Cloud Frontier Flash because local GPU "
                        "environment is unavailable."
                    ),
                )

        # Default fallback to Cloud Frontier
        return RoutingDecision(
            target="cloud_frontier",
            model_id=self.config.flash_model,
            requested_mode=clean_mode,
            fallback_used=False,
            fallback_applied=False,
            webgpu_available=browser_webgpu,
            local_gpu_available=local_gpu,
            rationale=(
                f"Routed to Cloud Frontier Flash model ({self.config.flash_model}) as the "
                "balanced default for campaign pitch synthesis."
            ),
        )

    select_route = route_task


def route_task(
    task: Mapping[str, Any] | str | None = None,
    **kwargs: Any,
) -> RoutingDecision:
    """
    /**
     * Functional entry point for hybrid model routing.
     *
     * Why: Provides a stateless functional API allowing callers to dispatch tasks
     * without manually instantiating a HybridModelRouter.
     *
     * @param task Task specification dictionary or brief string.
     * @param kwargs Additional routing parameter overrides.
     * @return Structured RoutingDecision instance.
     */
    """
    router = HybridModelRouter()
    return router.route_task(task, **kwargs)


select_route = route_task
