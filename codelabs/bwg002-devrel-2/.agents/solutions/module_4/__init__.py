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
 * @file __init__.py
 * @description Package initializer for Module 4 ("Optimize for scale") reference solutions.
 *
 * Why: Exposes step metadata and core interfaces for Module 4 Step 4a
 * (Tokenomics memory compression, sliding-window history pruning, SHA-256 prompt caching,
 * and 5-tier model strategy) so learners, verification tools, and multi-agent coordination
 * pipelines can access scale optimization capabilities cleanly.
 */
"""

from __future__ import annotations

from .step_4a_tokenomics import (
    MODEL_STRATEGIES,
    VALID_STRATEGY_TIERS,
    CompressedHistoryList,
    PromptCacheManager,
    TokenomicsManager,
    compress_history,
    compress_memory,
    estimate_tokens,
    prune_history,
    resolve_model_strategy,
    select_model_strategy,
)

MODULE_ID: int = 4
MODULE_TITLE: str = "Optimize for scale"
MODULE_4_STEPS: tuple[str, ...] = ("4a",)

__all__ = [
    "MODULE_ID",
    "MODULE_TITLE",
    "MODULE_4_STEPS",
    "VALID_STRATEGY_TIERS",
    "MODEL_STRATEGIES",
    "CompressedHistoryList",
    "PromptCacheManager",
    "TokenomicsManager",
    "estimate_tokens",
    "compress_memory",
    "compress_history",
    "prune_history",
    "select_model_strategy",
    "resolve_model_strategy",
]
