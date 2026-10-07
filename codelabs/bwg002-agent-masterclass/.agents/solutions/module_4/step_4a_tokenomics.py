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
 * @file step_4a_tokenomics.py
 * @description Module 4 Step 4a — Tokenomics, Memory Compression, History Pruning, and Prompt Caching.
 *
 * Why: High-volume enterprise multi-agent applications incur significant cost and latency
 * from unconstrained context accumulation across iterative refinement cycles. This module
 * provides algorithmic memory compression (summarizing older conversation turns), sliding-window
 * history pruning enforcing strict token budgets, deterministic SHA-256 prompt caching with
 * TTL support, and model tier selection across flash, pro, low, high, and local models.
 */
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from pitch_generator.config import (
    DEFAULT_FLASH_MODEL,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_LOCAL_MODEL,
    PitchConfig,
    get_config,
)

VALID_STRATEGY_TIERS: tuple[str, ...] = ("flash", "pro", "low", "high", "local")

MODEL_STRATEGIES: dict[str, dict[str, Any]] = {
    "flash": {
        "tier": "flash",
        "model_id": DEFAULT_FLASH_MODEL,
        "model": DEFAULT_FLASH_MODEL,
        "cost_tier": "low",
        "latency_tier": "ultra_low",
        "thinking_budget": 0,
        "target": "cloud_frontier",
        "temperature": 0.7,
        "rationale": (
            "Fast, cost-effective multimodal reasoning for real-time draft generation "
            "and iterative pitch critique."
        ),
    },
    "pro": {
        "tier": "pro",
        "model_id": DEFAULT_FLASH_MODEL,
        "model": DEFAULT_FLASH_MODEL,
        "cost_tier": "standard",
        "latency_tier": "moderate",
        "thinking_budget": 2048,
        "target": "cloud_frontier",
        "temperature": 0.4,
        "rationale": (
            "Extended thinking budget on Gemini 3.8 Flash for strategic synthesis, brand compliance "
            "evals, and final executive review."
        ),
    },
    "low": {
        "tier": "low",
        "model_id": DEFAULT_FLASH_MODEL,
        "model": DEFAULT_FLASH_MODEL,
        "cost_tier": "lowest",
        "latency_tier": "ultra_low",
        "thinking_budget": 0,
        "target": "cloud_frontier",
        "temperature": 0.6,
        "rationale": (
            "Lightweight tokenomics tier optimized for high-throughput brainstorming and simple "
            "tagline generation."
        ),
    },
    "high": {
        "tier": "high",
        "model_id": DEFAULT_FLASH_MODEL,
        "model": DEFAULT_FLASH_MODEL,
        "cost_tier": "high",
        "latency_tier": "high",
        "thinking_budget": 4096,
        "target": "cloud_frontier",
        "temperature": 0.3,
        "rationale": (
            "Deep reasoning tier with extended thinking budget on Gemini 3.8 Flash for exhaustive "
            "market analysis and multi-persona evaluation."
        ),
    },
    "local": {
        "tier": "local",
        "model_id": DEFAULT_LOCAL_MODEL,
        "model": DEFAULT_LOCAL_MODEL,
        "cost_tier": "zero_cloud",
        "latency_tier": "low",
        "thinking_budget": 0,
        "target": "local_model",
        "temperature": 0.7,
        "rationale": (
            "Private on-premise execution using open-weights Gemma for confidential internal "
            "brand strategy without cloud egress."
        ),
    },
}


class CompressedHistoryList(list):
    """
    /**
     * Specialized list container for compressed and pruned conversation history turns.
     *
     * Why: Subclasses the built-in `list` so test runners, JSON serializers, and downstream
     * agent loops can treat it directly as `list[dict[str, Any]]` (including equality to `[]`
     * when empty), while simultaneously exposing `.turns`, `.history`, `.summary`, and
     * token savings metrics for tokenomics auditing.
     */
    """

    def __init__(
        self,
        iterable: Sequence[dict[str, Any]] | None = None,
        *,
        summary: str = "",
        original_tokens: int = 0,
        optimized_tokens: int = 0,
        tokens_saved: int = 0,
    ) -> None:
        """
        /**
         * Initialize the compressed history list container.
         *
         * Why: Preserves token accounting metadata alongside turn dictionaries.
         *
         * @param iterable Initial list of turn dictionaries.
         * @param summary Synthetic summary text created during compression.
         * @param original_tokens Estimated raw tokens before compression/pruning.
         * @param optimized_tokens Estimated remaining tokens after compression/pruning.
         * @param tokens_saved Total delta in tokens saved.
         */
        """
        super().__init__(iterable or [])
        self._summary = summary
        self._original_tokens = max(0, int(original_tokens))
        self._optimized_tokens = max(0, int(optimized_tokens))
        computed_saved = max(0, self._original_tokens - self._optimized_tokens)
        self._tokens_saved = max(computed_saved, int(tokens_saved))

    @property
    def turns(self) -> list[dict[str, Any]]:
        """
        /**
         * Access turns as a standard list.
         *
         * Why: Satisfies callers that expect a `.turns` attribute on compression results.
         *
         * @return Shallow copy of current turns.
         */
        """
        return list(self)

    @property
    def history(self) -> list[dict[str, Any]]:
        """
        /**
         * Access history as a standard list.
         *
         * Why: Satisfies callers that expect a `.history` attribute on compression results.
         *
         * @return Shallow copy of current turns.
         */
        """
        return list(self)

    @property
    def summary(self) -> str:
        """
        /**
         * Synthetic summary generated from older conversation turns.
         *
         * Why: Gives callers immediate access to the condensed context snippet.
         *
         * @return Condensed context summary string.
         */
        """
        return self._summary

    @property
    def original_tokens(self) -> int:
        """
        /**
         * Raw token count prior to optimization.
         *
         * Why: Enables cost and latency baseline comparison.
         *
         * @return Original token count integer.
         */
        """
        return self._original_tokens

    @property
    def optimized_tokens(self) -> int:
        """
        /**
         * Token count after compression and pruning.
         *
         * Why: Confirms enforcement of context window limits.
         *
         * @return Optimized token count integer.
         */
        """
        return self._optimized_tokens

    @property
    def tokens_saved(self) -> int:
        """
        /**
         * Delta between original and optimized tokens.
         *
         * Why: Quantifies tokenomics efficiency improvements.
         *
         * @return Tokens saved integer.
         */
        """
        return self._tokens_saved

    @property
    def saved_tokens(self) -> int:
        """
        /**
         * Alias for tokens_saved.
         *
         * Why: Ensures interoperability across varying consumer naming conventions.
         *
         * @return Tokens saved integer.
         */
        """
        return self._tokens_saved

    def to_dict(self) -> dict[str, Any]:
        """
        /**
         * Convert history container into a plain dictionary representation.
         *
         * Why: Simplifies JSON serialization for REST API and BigQuery logging.
         *
         * @return Dictionary with turns, summary, and token accounting metrics.
         */
        """
        return {
            "turns": list(self),
            "history": list(self),
            "summary": self._summary,
            "original_tokens": self._original_tokens,
            "optimized_tokens": self._optimized_tokens,
            "tokens_saved": self._tokens_saved,
            "saved_tokens": self._tokens_saved,
        }


def estimate_tokens(text: Any) -> int:
    """
    /**
     * Compute a deterministic token estimate for string content.
     *
     * Why: Aligns with the standard heuristic of ~4 characters per token for English text
     * while guaranteeing positive values for non-empty strings and 0 for empty strings.
     *
     * @param text String or object to estimate.
     * @return Estimated token count integer.
     */
    """
    if text is None:
        return 0
    raw = str(text)
    if not raw.strip():
        return 0
    return max(1, len(raw) // 4)


def compress_memory(
    turns: Sequence[Mapping[str, Any] | str] | None,
    *,
    keep_recent: int = 2,
    max_summary_chars: int = 160,
) -> CompressedHistoryList:
    """
    /**
     * Condense older conversation turns into a succinct system summary entry.
     *
     * Why: Prevents unbounded token growth across multi-turn pitch refinement sessions
     * by replacing lengthy conversational preamble with an aggregated context statement
     * while preserving the most recent turns verbatim.
     *
     * @param turns Sequence of conversation turn dictionaries or strings.
     * @param keep_recent Number of most recent turns to preserve verbatim.
     * @param max_summary_chars Maximum character length for synthesized summary.
     * @return CompressedHistoryList containing condensed history and token metrics.
     */
    """
    if not turns:
        return CompressedHistoryList([])

    normalized: list[dict[str, Any]] = []
    for item in turns:
        if isinstance(item, Mapping):
            normalized.append(
                {
                    "role": str(item.get("role", "user")),
                    "content": str(item.get("content", "")),
                }
            )
        else:
            normalized.append({"role": "user", "content": str(item)})

    orig_tokens = sum(estimate_tokens(t["content"]) for t in normalized)
    num_turns = len(normalized)

    if num_turns <= keep_recent:
        return CompressedHistoryList(
            normalized,
            summary="",
            original_tokens=orig_tokens,
            optimized_tokens=orig_tokens,
            tokens_saved=0,
        )

    split_idx = num_turns - max(1, keep_recent)
    older_turns = normalized[:split_idx]
    recent_turns = normalized[split_idx:]

    older_chars = sum(len(t["content"]) for t in older_turns)
    bullets: list[str] = []
    for idx, t in enumerate(older_turns):
        snippet = t["content"].strip().replace("\n", " ")
        if len(snippet) > 40:
            snippet = snippet[:37] + "..."
        bullets.append(f"T{idx+1}({t['role']}): {snippet}")

    combined_snippets = "; ".join(bullets)
    if len(combined_snippets) > max_summary_chars:
        combined_snippets = combined_snippets[: max_summary_chars - 3] + "..."

    summary_text = f"[Summary of {len(older_turns)} earlier turns: {combined_snippets}]"
    if len(summary_text) >= older_chars and older_chars > 0:
        summary_text = f"[Summary: {len(older_turns)} earlier turns archived]"

    summary_turn = {"role": "system", "content": summary_text, "compressed": True}
    result_turns = [summary_turn, *recent_turns]
    opt_tokens = sum(estimate_tokens(t["content"]) for t in result_turns)
    saved_tokens = max(0, orig_tokens - opt_tokens)

    return CompressedHistoryList(
        result_turns,
        summary=summary_text,
        original_tokens=orig_tokens,
        optimized_tokens=opt_tokens,
        tokens_saved=saved_tokens,
    )


compress_history = compress_memory


def prune_history(
    turns: Sequence[Mapping[str, Any] | str] | None,
    *,
    max_turns: int = 6,
    max_tokens: int = 512,
) -> CompressedHistoryList:
    """
    /**
     * Enforce a hard sliding window and token budget across conversation turns.
     *
     * Why: Guarantees prompt requests sent to Gemini never exceed strict token quotas.
     * Evaluates turns from newest to oldest, deterministically truncating oversized
     * turns when necessary to fit within the budget.
     *
     * @param turns Sequence of conversation turns.
     * @param max_turns Maximum number of turns allowed in the sliding window.
     * @param max_tokens Positive integer representing maximum token budget.
     * @return CompressedHistoryList satisfying both turn and token constraints.
     */
    """
    if max_tokens is None or int(max_tokens) <= 0:
        raise ValueError(f"max_tokens must be greater than 0, got {max_tokens}")
    if max_turns is not None and int(max_turns) <= 0:
        raise ValueError(f"max_turns must be greater than 0, got {max_turns}")

    budget_tokens = int(max_tokens)
    limit_turns = int(max_turns) if max_turns is not None else 6

    if not turns:
        return CompressedHistoryList([])

    normalized: list[dict[str, Any]] = []
    for item in turns:
        if isinstance(item, Mapping):
            normalized.append(
                {
                    "role": str(item.get("role", "user")),
                    "content": str(item.get("content", "")),
                }
            )
        else:
            normalized.append({"role": "user", "content": str(item)})

    orig_tokens = sum(estimate_tokens(t["content"]) for t in normalized)
    window = normalized[-limit_turns:] if len(normalized) > limit_turns else list(normalized)

    remaining_budget = budget_tokens
    kept_reversed: list[dict[str, Any]] = []

    for turn in reversed(window):
        content = turn["content"]
        turn_tok = estimate_tokens(content)

        if turn_tok <= remaining_budget:
            kept_reversed.append(turn)
            remaining_budget -= turn_tok
        elif not kept_reversed:
            max_chars = max(1, budget_tokens * 4)
            truncated_content = (
                (content[: max_chars - 3] + "...") if len(content) > max_chars else content[:max_chars]
            )
            while estimate_tokens(truncated_content) > budget_tokens and len(truncated_content) > 3:
                truncated_content = truncated_content[:-4] + "..."
            kept_turn = dict(turn)
            kept_turn["content"] = truncated_content
            kept_turn["truncated"] = True
            kept_reversed.append(kept_turn)
            remaining_budget = 0
            break
        else:
            break

    result_turns = list(reversed(kept_reversed))
    opt_tokens = sum(estimate_tokens(t["content"]) for t in result_turns)
    saved_tokens = max(0, orig_tokens - opt_tokens)

    return CompressedHistoryList(
        result_turns,
        summary="",
        original_tokens=orig_tokens,
        optimized_tokens=opt_tokens,
        tokens_saved=saved_tokens,
    )


class PromptCacheManager:
    """
    /**
     * In-memory cache manager for system prompts, brand guidelines, and static context.
     *
     * Why: Prevents redundant token generation and latency penalties by caching invariant
     * system instructions and skill guidelines indexed by cryptographic SHA-256 digests.
     */
    """

    def __init__(
        self,
        default_ttl_seconds: float = 300.0,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        """
        /**
         * Initialize the prompt cache manager.
         *
         * Why: Configures default time-to-live and injects time function for deterministic testing.
         *
         * @param default_ttl_seconds Default lifetime for cache entries in seconds.
         * @param time_fn Optional time provider returning current epoch seconds.
         */
        """
        self.default_ttl_seconds = float(default_ttl_seconds)
        self._time_fn = time_fn or time.time
        self._entries: dict[str, dict[str, Any]] = {}

    def compute_cache_key(self, prompt: str, *, namespace: str = "") -> str:
        """
        /**
         * Generate a 64-character SHA-256 hexadecimal cache key.
         *
         * Why: Provides a collision-resistant deterministic key based on prompt content.
         *
         * @param prompt Text content to hash.
         * @param namespace Optional namespace scope.
         * @return 64-character lowercase hex string.
         */
        """
        key_source = f"{namespace}:{prompt}" if namespace else prompt
        return hashlib.sha256(key_source.encode("utf-8")).hexdigest()

    def get_or_create(
        self,
        prompt: str,
        *,
        ttl_seconds: float | None = None,
        namespace: str = "",
    ) -> dict[str, Any]:
        """
        /**
         * Lookup existing cached prompt or register new cache entry.
         *
         * Why: Eliminates duplicate token processing when identical system prompts
         * are submitted repeatedly across agent turns.
         *
         * @param prompt Prompt text to cache.
         * @param ttl_seconds Optional TTL override in seconds.
         * @param namespace Optional namespace qualifier.
         * @return Cache lookup result containing key, cache_hit boolean, and saved tokens.
         */
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string")

        effective_ttl = self.default_ttl_seconds if ttl_seconds is None else float(ttl_seconds)
        cache_key = self.compute_cache_key(prompt, namespace=namespace)
        tokens = estimate_tokens(prompt)
        now = self._time_fn()

        entry = self._entries.get(cache_key)
        is_hit = False

        if entry is not None and effective_ttl > 0 and self.default_ttl_seconds > 0:
            if now < entry["expires_at"]:
                is_hit = True

        if is_hit and entry is not None:
            entry["hits"] += 1
            return {
                "cache_key": cache_key,
                "key": cache_key,
                "cache_hit": True,
                "hit": True,
                "token_count": tokens,
                "saved_tokens": tokens,
                "tokens_saved": tokens,
                "ttl_seconds": effective_ttl,
                "hits": entry["hits"],
            }

        new_entry = {
            "cache_key": cache_key,
            "prompt": prompt,
            "token_count": tokens,
            "created_at": now,
            "expires_at": now + max(0.0, effective_ttl),
            "hits": 0,
        }
        self._entries[cache_key] = new_entry

        return {
            "cache_key": cache_key,
            "key": cache_key,
            "cache_hit": False,
            "hit": False,
            "token_count": tokens,
            "saved_tokens": 0,
            "tokens_saved": 0,
            "ttl_seconds": effective_ttl,
            "hits": 0,
        }

    lookup_or_store = get_or_create
    cache_prompt = get_or_create


def select_model_strategy(tier: str, *, config: PitchConfig | None = None) -> dict[str, Any]:
    """
    /**
     * Map a model strategy tier to its concrete model identifier and parameters.
     *
     * Why: Supports all five syllabus tiers (flash, pro, low, high, local) so applications
     * can dynamically balance reasoning capability against latency and financial cost.
     *
     * @param tier Strategy tier identifier string.
     * @param config Optional runtime PitchConfig container.
     * @return Strategy configuration dictionary with model_id, target, and thinking budget.
     */
    """
    clean_tier = (tier or "").strip().lower()
    if clean_tier not in VALID_STRATEGY_TIERS:
        raise ValueError(
            f"Unsupported strategy tier {tier!r}. Expected one of {VALID_STRATEGY_TIERS}."
        )

    base = dict(MODEL_STRATEGIES[clean_tier])
    cfg = config or get_config()

    if clean_tier in {"flash", "low", "pro", "high"}:
        base["model_id"] = cfg.flash_model
        base["model"] = cfg.flash_model
    elif clean_tier == "local":
        base["model_id"] = cfg.local_model
        base["model"] = cfg.local_model

    return base


resolve_model_strategy = select_model_strategy


class TokenomicsManager:
    """
    /**
     * Holistic tokenomics coordinator combining compression, pruning, and caching.
     *
     * Why: Orchestrates full token optimization lifecycle for pitch generation sessions,
     * ensuring context fits target token limits while tracking saved tokens and latency impact.
     */
    """

    def __init__(
        self,
        *,
        max_turns: int = 4,
        max_tokens: int = 256,
        cache_manager: PromptCacheManager | None = None,
        config: PitchConfig | None = None,
    ) -> None:
        """
        /**
         * Initialize the tokenomics manager.
         *
         * Why: Configures default thresholds and injects cache manager and runtime config.
         *
         * @param max_turns Default maximum turns allowed in context.
         * @param max_tokens Default maximum token budget for the session.
         * @param cache_manager Optional PromptCacheManager instance.
         * @param config Optional PitchConfig instance.
         */
        """
        self.max_turns = int(max_turns)
        self.max_tokens = int(max_tokens)
        self.cache_manager = cache_manager or PromptCacheManager()
        self.config = config or get_config()

    def optimize(
        self,
        turns: Sequence[Mapping[str, Any] | str] | None,
        *,
        static_prompt: str = "",
        strategy_tier: str = "flash",
        max_turns: int | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        /**
         * Optimize conversation history and static prompt for efficient model execution.
         *
         * Why: Compresses older turns, prunes history within token limits, caches static
         * system instructions, and maps the designated model strategy.
         *
         * @param turns Input conversation turns.
         * @param static_prompt Invariant system instructions or brand guidelines.
         * @param strategy_tier Target model strategy tier.
         * @param max_turns Optional turn count override.
         * @param max_tokens Optional token budget override.
         * @return Comprehensive tokenomics report dictionary.
         */
        """
        eff_max_turns = self.max_turns if max_turns is None else int(max_turns)
        eff_max_tokens = self.max_tokens if max_tokens is None else int(max_tokens)

        cache_info = (
            self.cache_manager.get_or_create(static_prompt)
            if static_prompt and static_prompt.strip()
            else {
                "cache_key": hashlib.sha256(b"").hexdigest(),
                "cache_hit": False,
                "token_count": 0,
                "saved_tokens": 0,
            }
        )

        input_turns = turns or []
        raw_history_tokens = 0
        for item in input_turns:
            if isinstance(item, Mapping):
                raw_history_tokens += estimate_tokens(item.get("content", ""))
            else:
                raw_history_tokens += estimate_tokens(str(item))

        prompt_tokens = int(cache_info.get("token_count", 0))
        original_tokens = raw_history_tokens + prompt_tokens

        compressed = compress_memory(
            input_turns,
            keep_recent=max(1, min(2, eff_max_turns - 1)),
        )

        uncached_prompt_tokens = 0 if cache_info.get("cache_hit") else prompt_tokens
        history_budget = max(1, eff_max_tokens - uncached_prompt_tokens)

        pruned = prune_history(
            compressed,
            max_turns=eff_max_turns,
            max_tokens=history_budget,
        )

        opt_history_tokens = sum(estimate_tokens(t.get("content", "")) for t in pruned)
        optimized_tokens = opt_history_tokens + uncached_prompt_tokens
        if optimized_tokens > eff_max_tokens:
            optimized_tokens = eff_max_tokens

        tokens_saved = max(0, original_tokens - optimized_tokens)
        strategy = select_model_strategy(strategy_tier, config=self.config)

        return {
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": tokens_saved,
            "saved_tokens": tokens_saved,
            "cache_hit": bool(cache_info.get("cache_hit", False)),
            "cache_key": str(cache_info.get("cache_key", "")),
            "cache_saved_tokens": int(cache_info.get("saved_tokens", 0)),
            "selected_strategy": strategy,
            "strategy": strategy,
            "turns": list(pruned),
            "history": list(pruned),
        }

    optimize_session = optimize
