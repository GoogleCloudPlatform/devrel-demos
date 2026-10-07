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
 * @file test_module_4.py
 * @description Comprehensive offline unit and functional test suite for Module 4 (Steps 4a–4b, F18–F19).
 *
 * Why: Validates that Module 4 tokenomics (memory compression, sliding window history pruning,
 * SHA-256 prompt caching, and 5-tier model strategy) and hybrid model routing (3-tier dispatch
 * across browser WebLLM, local Gemma, and Cloud Frontier, with deterministic fallback and
 * vanilla ES6 JavaScript WebGPU integration) execute deterministically and 100% offline.
 */
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
from typing import Any
import pytest

APP_ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS_M4 = APP_ROOT / ".agents" / "solutions" / "module_4"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))


def _load_step(filename: str) -> Any:
    """
    /**
     * Dynamically loads a Module 4 solution module from `.agents/solutions/module_4/`.
     *
     * Why: Isolates step namespaces while testing solution files in `.agents/solutions/module_4/`.
     *
     * @param filename Filename inside `.agents/solutions/module_4/`.
     * @return Loaded Python module object.
     */
    """
    target = SOLUTIONS_M4 / filename
    assert target.is_file(), f"Missing solution file: {target}"
    module_name = f"_test_m4_{target.stem}"
    spec = importlib.util.spec_from_file_location(module_name, target)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# ===========================================================================
# Step 4a — Tokenomics, Memory Compression, Pruning, Caching (F18)
# ===========================================================================


def test_step_4a_estimate_tokens() -> None:
    """
    /**
     * Verifies deterministic token estimation using max(1, len(text) // 4).
     *
     * Why: Confirms positive token counts for non-empty text and 0 for empty/None inputs.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    estimate_tokens = step_4a.estimate_tokens

    assert estimate_tokens(None) == 0
    assert estimate_tokens("") == 0
    assert estimate_tokens("   ") == 0
    assert estimate_tokens("a") == 1
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcdefgh") == 2
    assert estimate_tokens("1234567890123456") == 4


def test_step_4a_compress_memory_summarizes_older_turns() -> None:
    """
    /**
     * Verifies compress_memory summarizes older conversation turns into a system summary.
     *
     * Why: Reduces context window token consumption on multi-turn pitch refinement sessions.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    compress_fn = step_4a.compress_memory

    turns = [
        {
            "role": "user" if i % 2 == 0 else "model",
            "content": f"Turn {i}: Detailed discussion on commuter rain bike frame geometry and night visibility.",
        }
        for i in range(10)
    ]
    orig_chars = sum(len(t["content"]) for t in turns)
    compressed = compress_fn(turns)

    assert isinstance(compressed, list)
    assert hasattr(compressed, "turns")
    assert hasattr(compressed, "history")
    assert hasattr(compressed, "summary")
    assert len(compressed) == 3  # 1 system summary + 2 recent turns
    assert compressed[0]["role"] == "system"
    assert compressed[0]["compressed"] is True

    comp_chars = sum(len(t["content"]) for t in compressed)
    assert comp_chars < orig_chars
    assert compressed.tokens_saved > 0
    assert compressed.original_tokens > compressed.optimized_tokens


def test_step_4a_compress_and_prune_empty_and_single_turn() -> None:
    """
    /**
     * Verifies compress_memory and prune_history handle empty and single-turn histories gracefully.
     *
     * Why: First-turn sessions have 0 or 1 turn of history and must not raise IndexErrors.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    comp_fn = step_4a.compress_memory
    prune_fn = step_4a.prune_history

    empty_comp = comp_fn([])
    assert empty_comp == []
    assert empty_comp.turns == []

    empty_pruned = prune_fn([], max_tokens=100)
    assert empty_pruned == []
    assert empty_pruned.turns == []

    single = [{"role": "user", "content": "Hello"}]
    single_comp = comp_fn(single)
    assert len(single_comp) == 1
    assert single_comp[0]["content"] == "Hello"

    single_pruned = prune_fn(single, max_tokens=100)
    assert len(single_pruned) == 1
    assert single_pruned[0]["content"] == "Hello"


def test_step_4a_prune_history_enforces_sliding_window_and_budget() -> None:
    """
    /**
     * Verifies prune_history enforces max_turns and max_tokens sliding window limits.
     *
     * Why: Guarantees a hard upper bound on conversation history tokens sent to the model.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    prune_fn = step_4a.prune_history
    est_fn = step_4a.estimate_tokens

    turns = [
        {
            "role": "user",
            "content": f"Turn {i} with about twenty words of campaign context for testing sliding window pruning limits.",
        }
        for i in range(15)
    ]
    pruned = prune_fn(turns, max_turns=4, max_tokens=200)
    assert len(pruned) <= 5
    total_tokens = sum(est_fn(t["content"]) for t in pruned)
    assert total_tokens <= 200


def test_step_4a_prune_history_rejects_invalid_budgets() -> None:
    """
    /**
     * Verifies prune_history raises ValueError when max_tokens or max_turns is non-positive.
     *
     * Why: Token budgets must be positive integers.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    prune_fn = step_4a.prune_history
    turns = [{"role": "user", "content": "Test turn"}]

    with pytest.raises(ValueError):
        prune_fn(turns, max_tokens=0)
    with pytest.raises(ValueError):
        prune_fn(turns, max_tokens=-50)
    with pytest.raises(ValueError):
        prune_fn(turns, max_turns=0, max_tokens=100)


def test_step_4a_single_oversized_turn_truncated() -> None:
    """
    /**
     * Verifies a single 10,000-character turn exceeding budget is deterministically truncated.
     *
     * Why: Enforces hard token budget ceiling even when a single user message is enormous.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    prune_fn = step_4a.prune_history
    est_fn = step_4a.estimate_tokens

    huge = [{"role": "user", "content": "B" * 10000}]
    pruned = prune_fn(huge, max_tokens=50)

    assert len(pruned) == 1
    assert pruned[0].get("truncated") is True
    total_tokens = sum(est_fn(t["content"]) for t in pruned)
    assert total_tokens <= 50


def test_step_4a_prompt_cache_manager_lifecycle() -> None:
    """
    /**
     * Verifies PromptCacheManager computes 64-hex SHA-256 keys, handles miss/hit, and invalidates on change.
     *
     * Why: Caches invariant system prompts and brand guidelines across multi-turn sessions.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    cache = step_4a.PromptCacheManager()

    static_text = "System Instruction: Follow house brand guidelines (deep indigo, slate, amber accent)."
    res1 = cache.get_or_create(static_text)
    res2 = cache.get_or_create(static_text)

    key1 = res1["cache_key"]
    key2 = res2["cache_key"]
    assert len(key1) == 64
    assert key1 == key2
    assert res1["cache_hit"] is False
    assert res2["cache_hit"] is True
    assert res2["saved_tokens"] > 0

    mutated_text = "System Instruction: Follow house brand guidelines (deep indigo, slate, golden accent)."
    res3 = cache.get_or_create(mutated_text)
    assert res3["cache_key"] != key1
    assert res3["cache_hit"] is False

    with pytest.raises(ValueError):
        cache.get_or_create("")


def test_step_4a_prompt_cache_ttl_expiration() -> None:
    """
    /**
     * Verifies PromptCacheManager expires entries when TTL is 0.
     *
     * Why: Prevents serving stale cached instructions after configuration updates.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    cache = step_4a.PromptCacheManager(default_ttl_seconds=0)

    text = "Temporary instruction"
    res1 = cache.get_or_create(text, ttl_seconds=0)
    res2 = cache.get_or_create(text, ttl_seconds=0)
    assert res1["cache_hit"] is False
    assert res2["cache_hit"] is False


def test_step_4a_model_strategy_tiers() -> None:
    """
    /**
     * Verifies model strategy selection supports all five syllabus tiers (flash, pro, low, high, local).
     *
     * Why: Confirms coverage of docs/outline.md §6.1.3 and rejection of unsupported tier names.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    select_strat = step_4a.select_model_strategy

    for tier in ("flash", "pro", "low", "high", "local"):
        strategy = select_strat(tier)
        assert strategy["tier"] == tier
        assert bool(strategy["model_id"])
        assert "target" in strategy
        assert "cost_tier" in strategy
        assert "thinking_budget" in strategy

    with pytest.raises(ValueError):
        select_strat("ultra-quantum-xl")


def test_step_4a_tokenomics_manager_optimize() -> None:
    """
    /**
     * Verifies TokenomicsManager.optimize orchestrates compression, pruning, and caching.
     *
     * Why: Quantifies end-to-end token and cost savings for campaign pitch sessions.
     */
    """
    step_4a = _load_step("step_4a_tokenomics.py")
    mgr = step_4a.TokenomicsManager(max_turns=4, max_tokens=300)

    turns = [
        {
            "role": "user" if i % 2 == 0 else "model",
            "content": f"Turn {i}: Extended discussion on commuter cycling campaign narrative and audience segmentation.",
        }
        for i in range(12)
    ]
    static_prompt = "Brand Rules: deep indigo, slate, amber, generous negative space."

    opt1 = mgr.optimize(turns, static_prompt=static_prompt, max_turns=4, max_tokens=300)
    opt2 = mgr.optimize(turns, static_prompt=static_prompt, max_turns=4, max_tokens=300)

    assert opt1["optimized_tokens"] < opt1["original_tokens"]
    assert opt1["optimized_tokens"] <= 300
    assert opt1["tokens_saved"] > 0
    assert opt1["cache_hit"] is False
    assert opt2["cache_hit"] is True
    assert len(opt2["cache_key"]) == 64
    assert opt1["selected_strategy"]["tier"] == "flash"
    assert len(opt1["turns"]) <= 4


# ===========================================================================
# Step 4b — Hybrid Model Routing and Fallback Chain (F19)
# ===========================================================================


def test_step_4b_route_lightweight_privacy_task() -> None:
    """
    /**
     * Verifies low-complexity, privacy-sensitive tasks route to webllm_browser when WebGPU is available.
     *
     * Why: Keeps private user drafts on-device in browser with zero cloud token cost.
     */
    """
    step_4b = _load_step("step_4b_hybrid_routing.py")
    route_fn = step_4b.route_task

    decision = route_fn(
        {
            "task_type": "draft_copy",
            "complexity": "low",
            "privacy_sensitive": True,
            "requires_multimodal": False,
            "browser_webgpu_available": True,
            "local_gpu_available": True,
        }
    )

    assert decision.target == "webllm_browser"
    assert decision["target"] == "webllm_browser"
    assert decision.fallback_used is False
    assert decision.fallback_applied is False
    assert bool(decision.rationale)


def test_step_4b_route_medium_task_to_local_gemma() -> None:
    """
    /**
     * Verifies medium-complexity text tasks route to local_model when local GPU is available.
     *
     * Why: Validates local edge execution for confidential synthesis without cloud egress.
     */
    """
    step_4b = _load_step("step_4b_hybrid_routing.py")
    route_fn = step_4b.route_task

    decision = route_fn(
        {
            "task_type": "concept_refinement",
            "complexity": "medium",
            "requires_multimodal": False,
            "browser_webgpu_available": False,
            "local_gpu_available": True,
        }
    )

    assert decision.target == "local_model"
    assert decision.fallback_used is False
    assert bool(decision.rationale)


def test_step_4b_route_multimodal_to_cloud_frontier() -> None:
    """
    /**
     * Verifies multimodal or high-complexity tasks route to cloud_frontier.
     *
     * Why: Key visual image generation requires Gemini Enterprise Agent Platform vision capabilities.
     */
    """
    step_4b = _load_step("step_4b_hybrid_routing.py")
    route_fn = step_4b.route_task

    decision = route_fn(
        {
            "task_type": "generate_key_visual",
            "complexity": "high",
            "requires_multimodal": True,
            "browser_webgpu_available": True,
            "local_gpu_available": True,
        }
    )

    assert decision.target == "cloud_frontier"
    assert bool(decision.rationale)


def test_step_4b_single_fallback_webllm_to_local() -> None:
    """
    /**
     * Verifies fallback from webllm_browser to local_model when WebGPU is unavailable.
     *
     * Why: Exercises first hop of the fallback chain when client browser lacks WebGPU.
     */
    """
    step_4b = _load_step("step_4b_hybrid_routing.py")
    route_fn = step_4b.route_task

    decision = route_fn(
        {
            "task_type": "draft_copy",
            "complexity": "low",
            "privacy_sensitive": True,
            "browser_webgpu_available": False,
            "local_gpu_available": True,
        }
    )

    assert decision.target == "local_model"
    assert decision.fallback_used is True
    assert decision.fallback_applied is True


def test_step_4b_double_fallback_to_cloud_frontier() -> None:
    """
    /**
     * Verifies double fallback webllm_browser -> local_model -> cloud_frontier when both GPUs are missing.
     *
     * Why: Guarantees task execution succeeds on Cloud Frontier even when edge hardware is absent.
     */
    """
    step_4b = _load_step("step_4b_hybrid_routing.py")
    route_fn = step_4b.route_task

    decision = route_fn(
        {
            "task_type": "draft_copy",
            "complexity": "low",
            "privacy_sensitive": True,
            "browser_webgpu_available": False,
            "local_gpu_available": False,
        }
    )

    assert decision.target == "cloud_frontier"
    assert decision.fallback_used is True
    assert decision.fallback_applied is True


def test_step_4b_multimodal_overrides_forced_targets() -> None:
    """
    /**
     * Verifies requires_multimodal=True forces cloud_frontier even when webllm or local is requested.
     *
     * Why: Browser WebLLM and local text models cannot generate image assets.
     */
    """
    step_4b = _load_step("step_4b_hybrid_routing.py")
    route_fn = step_4b.route_task

    for pref in ("webllm_browser", "local_model"):
        decision = route_fn(
            {
                "task_type": "generate_key_visual",
                "requires_multimodal": True,
                "routing_mode": pref,
                "preferred_target": pref,
                "browser_webgpu_available": True,
                "local_gpu_available": True,
            }
        )
        assert decision.target == "cloud_frontier"


def test_step_4b_rejects_unknown_routing_mode() -> None:
    """
    /**
     * Verifies unknown routing_mode raises ValueError.
     *
     * Why: Fails fast on invalid configuration strings to prevent silent misrouting.
     */
    """
    step_4b = _load_step("step_4b_hybrid_routing.py")
    route_fn = step_4b.route_task

    with pytest.raises(ValueError):
        route_fn({"routing_mode": "invalid_mode_xyz"})


def test_step_4b_handles_empty_metadata_safely() -> None:
    """
    /**
     * Verifies empty metadata routes safely to cloud_frontier default.
     *
     * Why: Ensures zero-argument routing calls work predictably out of the box.
     */
    """
    step_4b = _load_step("step_4b_hybrid_routing.py")
    route_fn = step_4b.route_task

    decision = route_fn({})
    assert decision.target == "cloud_frontier"
    assert decision.model_id == "gemini-3.8-flash"


# ===========================================================================
# Step 4b — Vanilla ES6 JavaScript Router (webllm_router.js) & API
# ===========================================================================


def test_webllm_router_js_content_and_compliance() -> None:
    """
    /**
     * Verifies webllm_router.js contains Javadoc comments, WebGPU checks, and zero UI frameworks.
     *
     * Why: Enforces vanilla ES6 client compliance with zero framework dependencies.
     */
    """
    js_path = SOLUTIONS_M4 / "webllm_router.js"
    assert js_path.is_file(), f"Missing {js_path}"
    content = js_path.read_text(encoding="utf-8")

    assert "/**" in content
    assert "navigator.gpu" in content
    assert "webllm_browser" in content
    assert "local_model" in content
    assert "cloud_frontier" in content

    lower_js = content.lower()
    for forbidden in ("from 'react'", 'from "react"', "from 'vue'", "angular", "streamlit"):
        assert forbidden not in lower_js


def test_module_4_javadoc_why_comments_in_python_files() -> None:
    """
    /**
     * Verifies every Python file in module_4 contains Javadoc-style "Why:" comments.
     *
     * Why: Satisfies repository-wide Javadoc rationale compliance check.
     */
    """
    py_files = list(SOLUTIONS_M4.glob("*.py"))
    assert len(py_files) >= 3  # __init__.py, step_4a_tokenomics.py, step_4b_hybrid_routing.py

    for fpath in py_files:
        tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
        doc = (ast.get_docstring(tree) or "").lower()
        assert "why" in doc, f"Missing 'why' rationale in module docstring of {fpath.name}"
