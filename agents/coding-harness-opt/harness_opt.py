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
Harness Optimization Reference Implementations (Python 3.11+)

This module provides reference implementations for four
core architectural patterns to improve coding agent harness efficiency and reduce token costs. 

1. CacheInvariantPromptBuilder: Immutable prefix isolation and reverse compaction.
2. ASTAwareFileReader: AST skeletal extraction stripping function bodies.
3. DynamicMCPRegistry: On-demand lazy tool discovery and response projection.
4. GovernedTierRouter: Multi-tier routing with 4 deterministic escalation triggers.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence


# =====================================================================
# 1. Cache-Invariant Prompt Builder
# =====================================================================

@dataclass(frozen=True)
class Message:
    role: str
    content: str
    is_tool_call: bool = False
    is_tool_response: bool = False


class CacheInvariantPromptBuilder:
    """
    Constructs multi-turn conversational payloads while guaranteeing server-side
    KV-cache prefix stability.

    Separates the prompt into:
    1. Static Prefix: System instructions, repo conventions, immutable tools.
    2. Dynamic Tail: Append-only user prompts, assistant turns, and tool outputs.

    Provides reverse compaction to prune older tool outputs without altering
    the prefix hash.
    """

    def __init__(self, system_instructions: str, repo_manifest: str) -> None:
        # The immutable prefix is pinned and never modified during execution.
        self._prefix_content: str = (
            f"<system_instructions>\n{system_instructions.strip()}\n</system_instructions>\n"
            f"<repository_manifest>\n{repo_manifest.strip()}\n</repository_manifest>"
        )
        self._turns: List[Message] = []

    @property
    def prefix(self) -> str:
        return self._prefix_content

    def append_turn(self, role: str, content: str, is_tool_response: bool = False) -> None:
        """Appends a new interaction to the dynamic tail."""
        self._turns.append(
            Message(role=role, content=content, is_tool_response=is_tool_response)
        )

    def reverse_compact(self, keep_last_n_tool_outputs: int = 2) -> None:
        """
        Prunes intermediate tool logs from older turns in the tail.
        Replaces bloated raw execution outputs with concise structural summaries
        while preserving the conversation graph and prefix integrity.
        """
        tool_response_indices = [
            i for i, msg in enumerate(self._turns) if msg.is_tool_response
        ]

        if len(tool_response_indices) <= keep_last_n_tool_outputs:
            return

        # Prune older tool outputs, leaving only the most recent N
        indices_to_prune = tool_response_indices[:-keep_last_n_tool_outputs]
        for idx in indices_to_prune:
            original = self._turns[idx]
            first_line = original.content.strip().split("\n")[0]
            compacted_content = f"[Output pruned: {first_line[:80]}... (status: completed)]"
            self._turns[idx] = Message(
                role=original.role,
                content=compacted_content,
                is_tool_response=True,
            )

    def build_payload(self) -> Dict[str, Any]:
        """
        Builds the final payload structure compatible with Gemini Context Caching
        and Anthropic Prompt Caching standards.
        """
        return {
            "cached_prefix": self._prefix_content,
            "turns": [
                {"role": m.role, "content": m.content}
                for m in self._turns
            ],
            "turn_count": len(self._turns),
        }


# =====================================================================
# 2. AST-Aware File Reader
# =====================================================================

class ASTAwareFileReader:
    """
    Extracts structural skeletons from source files by stripping implementation
    bodies while preserving module docstrings, class declarations, function
    signatures, and type annotations.
    """

    @staticmethod
    def extract_skeleton(source_code: str) -> str:
        """
        Parses Python source code and returns a compressed skeletal outline.
        Reduces observation tokens by 60%-75% compared to raw file ingestion.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            # Fall back to raw source if file contains unparseable syntax
            return source_code

        class BodyPruner(ast.NodeTransformer):
            def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
                return self._prune_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
                return self._prune_function(node)

            def _prune_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
                docstring = ast.get_docstring(node)
                new_body: List[ast.stmt] = []

                if docstring:
                    # Keep concise docstring summary (first line only)
                    first_line = docstring.strip().split("\n")[0]
                    new_body.append(ast.Expr(value=ast.Constant(value=first_line)))

                # Replace internal implementation with Ellipsis (...)
                new_body.append(ast.Expr(value=ast.Constant(value=Ellipsis)))
                node.body = new_body
                return node

        pruned_tree = BodyPruner().visit(tree)
        ast.fix_missing_locations(pruned_tree)
        return ast.unparse(pruned_tree)

    @staticmethod
    def read_line_range(source_code: str, start_line: int, end_line: int) -> str:
        """Reads an exact slice of lines when surgical modification is required."""
        lines = source_code.splitlines()
        sliced = lines[max(0, start_line - 1):end_line]
        return "\n".join(sliced)


# =====================================================================
# 3. Dynamic MCP Tool Registry
# =====================================================================

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    handler: Callable[..., Any]
    category: str = "general"


class DynamicMCPRegistry:
    """
    Implements dynamic tool discovery for Model Context Protocol (MCP) ecosystems.
    Replaces static 30k-60k token schema dumps with an on-demand 3-step workflow:
    1. search_tools: Returns matching tool names and 1-line descriptions.
    2. describe_tools: Returns the full JSONSchema for selected tools only.
    3. execute_tool: Executes the tool and applies response field projections.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDefinition] = {}

    def register_tool(
        self,
        name: str,
        description: str,
        parameters_schema: Dict[str, Any],
        handler: Callable[..., Any],
        category: str = "general",
    ) -> None:
        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            handler=handler,
            category=category,
        )

    def search_tools(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """
        Lightweight metadata search over available tool registry.
        Injects minimal tokens (~100-300 tokens) on Turn 0.
        """
        query_terms = set(query.lower().split())
        scored: List[tuple[int, ToolDefinition]] = []

        for tool in self._tools.values():
            text = f"{tool.name} {tool.description} {tool.category}".lower()
            score = sum(1 for term in query_terms if term in text)
            if score > 0 or not query_terms:
                scored.append((score, tool))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = scored[:top_k] if scored else [(0, t) for t in list(self._tools.values())[:top_k]]

        return [
            {"name": tool.name, "description": tool.description}
            for _, tool in selected
        ]

    def describe_tools(self, tool_names: Sequence[str]) -> List[Dict[str, Any]]:
        """Returns the full JSONSchema parameters only for requested tools."""
        return [
            {
                "name": name,
                "description": self._tools[name].description,
                "parameters": self._tools[name].parameters_schema,
            }
            for name in tool_names
            if name in self._tools
        ]

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        fields_projection: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a tool and filters the response payload to strip nulls,
        nested metadata, and unrequested fields before returning to LLM context.
        """
        if tool_name not in self._tools:
            return {"error": f"Tool '{tool_name}' not found."}

        raw_result = self._tools[tool_name].handler(**arguments)

        if not isinstance(raw_result, dict):
            return {"result": raw_result}

        # Response Projection: Retain only requested fields and omit None values
        if fields_projection:
            projected = {
                k: v for k, v in raw_result.items()
                if k in fields_projection and v is not None
            }
            return projected

        # Default: Strip None values to reduce token footprint
        return {k: v for k, v in raw_result.items() if v is not None}


# =====================================================================
# 4. Governed Tier Router (Escalation & Budget Governance)
# =====================================================================

class ModelTier(str, Enum):
    WORKHORSE = "workhorse"  # e.g., Gemini 3.8 Flash, Claude Haiku 4.5
    FRONTIER = "frontier"    # e.g., Gemini 3.1 Pro, Claude Sonnet/Opus


@dataclass
class RouteDecision:
    tier: ModelTier
    reason: str
    escalation_count: int
    spend_downshifted: bool = False


class GovernedTierRouter:
    """
    Executes Workhorse-first Escalation Routing for autonomous coding trajectories.
    Routes execution turns to the Workhorse tier by default and escalates to Frontier
    only when deterministic triggers are met.

    Triggers:
    1. Turn is an initial planning or decomposition step.
    2. Pre-commit test/linter gate failed >= 2 consecutive times on the same target.
    3. AST-detected public signature mutation in diff.
    4. Workhorse output failed schema validation.

    Mitigations:
    - Sticky Escalation Lock: Prevents cascade thrashing.
    - Escalation Budget Cap: Hard limit on expensive tier invocations per run.
    - Spend Downshifting: Progressively disables frontier tier as budget caps approach.
    """

    def __init__(
        self,
        max_escalations: int = 8,
        spend_budget_limit: float = 5.00,
        current_spend: float = 0.00,
    ) -> None:
        self.max_escalations = max_escalations
        self.spend_budget_limit = spend_budget_limit
        self.current_spend = current_spend

        self.escalation_count: int = 0
        self.consecutive_gate_failures: Dict[str, int] = {}
        self.sticky_tier: Optional[ModelTier] = None

    def record_spend(self, amount: float) -> None:
        """Tracks cumulative spend across turns."""
        self.current_spend += amount

    def record_gate_result(self, file_path: str, passed: bool) -> None:
        """Tracks consecutive pre-commit test/gate failures per target file."""
        if passed:
            self.consecutive_gate_failures[file_path] = 0
            # Release sticky lock once target passes verification
            self.sticky_tier = None
        else:
            self.consecutive_gate_failures[file_path] = (
                self.consecutive_gate_failures.get(file_path, 0) + 1
            )

    @staticmethod
    def detects_public_signature_mutation(before_code: str, after_code: str) -> bool:
        """
        Determines if a code change mutates public class/function signatures
        using AST diffing rather than unstructured text regexes.
        """
        def get_signatures(source: str) -> set[str]:
            try:
                tree = ast.parse(source)
            except SyntaxError:
                return set()

            sigs = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_"):
                        arg_names = [a.arg for a in node.args.args]
                        sigs.add(f"def {node.name}({', '.join(arg_names)})")
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith("_"):
                        sigs.add(f"class {node.name}")
            return sigs

        return get_signatures(before_code) != get_signatures(after_code)

    def route_turn(
        self,
        is_planning_phase: bool = False,
        active_file: Optional[str] = None,
        schema_validation_failed: bool = False,
        before_code: Optional[str] = None,
        after_code: Optional[str] = None,
    ) -> RouteDecision:
        """
        Evaluates turn context and returns routing destination with audit reason.
        """
        # 1. Check Spend Budget Threshold (Progressive Downshifting)
        spend_downshifted = self.current_spend >= (self.spend_budget_limit * 0.85)

        # 2. If budget limit exceeded or max escalations reached, force Workhorse
        if self.escalation_count >= self.max_escalations or spend_downshifted:
            reason = (
                "Spend threshold reached (>85% budget)"
                if spend_downshifted
                else f"Escalation cap reached ({self.max_escalations})"
            )
            return RouteDecision(
                tier=ModelTier.WORKHORSE,
                reason=f"Forced Workhorse: {reason}",
                escalation_count=self.escalation_count,
                spend_downshifted=spend_downshifted,
            )

        # 3. Check Sticky Lock (Prevent Cascade Thrashing)
        if self.sticky_tier == ModelTier.FRONTIER:
            return RouteDecision(
                tier=ModelTier.FRONTIER,
                reason="Sticky escalation lock active (resolving ongoing failure)",
                escalation_count=self.escalation_count,
            )

        # 4. Trigger 1: Planning / Task Decomposition Phase
        if is_planning_phase:
            self._escalate()
            return RouteDecision(
                tier=ModelTier.FRONTIER,
                reason="Trigger 1: Initial task planning/decomposition",
                escalation_count=self.escalation_count,
            )

        # 5. Trigger 2: Consecutive Gate Failures (>= 2 on same file)
        if active_file and self.consecutive_gate_failures.get(active_file, 0) >= 2:
            self._escalate()
            self.sticky_tier = ModelTier.FRONTIER  # Lock until resolved
            return RouteDecision(
                tier=ModelTier.FRONTIER,
                reason=f"Trigger 2: Gate failed {self.consecutive_gate_failures[active_file]} times on {active_file}",
                escalation_count=self.escalation_count,
            )

        # 6. Trigger 3: AST-detected Public Signature Mutation
        if before_code and after_code and self.detects_public_signature_mutation(before_code, after_code):
            self._escalate()
            return RouteDecision(
                tier=ModelTier.FRONTIER,
                reason="Trigger 3: AST detected public signature mutation",
                escalation_count=self.escalation_count,
            )

        # 7. Trigger 4: Schema Validation Failure
        if schema_validation_failed:
            self._escalate()
            return RouteDecision(
                tier=ModelTier.FRONTIER,
                reason="Trigger 4: Workhorse output failed schema validation",
                escalation_count=self.escalation_count,
            )

        # Default: Route to Workhorse Tier
        return RouteDecision(
            tier=ModelTier.WORKHORSE,
            reason="Default execution turn (mechanical edits / test execution)",
            escalation_count=self.escalation_count,
        )

    def _escalate(self) -> None:
        self.escalation_count += 1