"""
Unit tests for harness_optimization.py.
Verifies veracity, syntax correctness, and runtime behavior for all 4 patterns,
including edge cases and failure handling.
"""

import sys
import os

# Ensure local directory is importable
sys.path.insert(0, os.path.dirname(__file__))

from harness_optimization_gists import (
    CacheInvariantPromptBuilder,
    ASTAwareFileReader,
    DynamicMCPRegistry,
    GovernedTierRouter,
    ModelTier,
)


def test_cache_invariant_prompt_builder():
    builder = CacheInvariantPromptBuilder(
        system_instructions="You are an autonomous AI coding agent.",
        repo_manifest="repo: my-service, runtime: python3.11",
    )

    assert "<system_instructions>" in builder.prefix
    assert "<repository_manifest>" in builder.prefix

    builder.append_turn("user", "Fix bug in auth.py")
    builder.append_turn("assistant", "Running pytest...")
    builder.append_turn("user", "Traceback (most recent call last):\nFile 'test.py', line 10\nAssertionError", is_tool_response=True)
    builder.append_turn("assistant", "Reading auth.py...")
    builder.append_turn("user", "def authenticate():\n    return False\n", is_tool_response=True)
    builder.append_turn("assistant", "Applying fix...")
    builder.append_turn("user", "pytest passed with exit code 0", is_tool_response=True)

    # Reverse compact to keep only the last 2 tool outputs
    builder.reverse_compact(keep_last_n_tool_outputs=2)
    payload = builder.build_payload()

    assert payload["turn_count"] == 7
    assert "[Output pruned: Traceback" in payload["turns"][2]["content"]
    assert "def authenticate():" in payload["turns"][4]["content"]
    assert "pytest passed" in payload["turns"][6]["content"]


def test_cache_invariant_edge_cases():
    builder = CacheInvariantPromptBuilder("system", "repo")
    
    # 1. No compaction when empty or few tool outputs
    builder.reverse_compact(keep_last_n_tool_outputs=2)
    assert builder.build_payload()["turn_count"] == 0

    builder.append_turn("user", "Hello")
    builder.append_turn("assistant", "Tool output", is_tool_response=True)
    builder.reverse_compact(keep_last_n_tool_outputs=2)
    assert builder.build_payload()["turns"][1]["content"] == "Tool output"


def test_ast_aware_file_reader():
    sample_code = '''
"""Module docstring for user service."""
from typing import Optional

class UserService:
    """Manages user authentication and records."""

    def __init__(self, db_url: str) -> None:
        """Initialize database connection."""
        self.db_url = db_url
        self.connected = True
        self._setup_connection_pool()

    def get_user_profile(self, user_id: str) -> Optional[dict]:
        """Fetch user profile record from database."""
        if not user_id:
            raise ValueError("user_id required")
        raw_record = self._query_database(user_id)
        return {"id": user_id, "data": raw_record}
'''

    skeleton = ASTAwareFileReader.extract_skeleton(sample_code)

    assert "class UserService:" in skeleton
    assert "def __init__(self, db_url: str) -> None:" in skeleton
    assert "def get_user_profile(self, user_id: str) -> Optional[dict]:" in skeleton
    assert "self._setup_connection_pool()" not in skeleton
    assert "raise ValueError" not in skeleton
    assert "..." in skeleton

    # Test line range slicing
    sliced = ASTAwareFileReader.read_line_range(sample_code, start_line=5, end_line=9)
    assert "class UserService:" in sliced


def test_ast_aware_async_and_syntax_fallback():
    async_code = '''
async def fetch_async_data(url: str) -> dict:
    """Fetch data asynchronously."""
    response = await client.get(url)
    return response.json()
'''
    skeleton = ASTAwareFileReader.extract_skeleton(async_code)
    assert "async def fetch_async_data(url: str) -> dict:" in skeleton
    assert "Fetch data asynchronously." in skeleton
    assert "..." in skeleton
    assert "client.get" not in skeleton

    # Syntax error fallback
    bad_code = "def broken_syntax(:"
    assert ASTAwareFileReader.extract_skeleton(bad_code) == bad_code


def test_dynamic_mcp_registry():
    registry = DynamicMCPRegistry()

    def mock_query_db(query: str, limit: int = 10):
        return {
            "query": query,
            "row_count": 2,
            "rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "execution_metadata": {"server_load": 0.12, "debug_trace": "ok"},
            "empty_notes": None,
        }

    registry.register_tool(
        name="database_query",
        description="Execute read-only SQL queries against the replica database.",
        parameters_schema={"type": "object", "properties": {"query": {"type": "string"}}},
        handler=mock_query_db,
        category="database",
    )

    registry.register_tool(
        name="github_create_pr",
        description="Create a pull request on the repository.",
        parameters_schema={"type": "object", "properties": {"title": {"type": "string"}}},
        handler=lambda title: {"pr_id": 101, "url": f"https://github.com/org/repo/pull/101"},
        category="vcs",
    )

    # 1. Search tools
    results = registry.search_tools("database query", top_k=1)
    assert len(results) == 1
    assert results[0]["name"] == "database_query"

    # 2. Describe tools
    schemas = registry.describe_tools(["database_query"])
    assert len(schemas) == 1
    assert "query" in schemas[0]["parameters"]["properties"]

    # 3. Execute tool with projection
    res = registry.execute_tool(
        "database_query",
        arguments={"query": "SELECT * FROM users"},
        fields_projection=["rows", "row_count"],
    )
    assert "rows" in res
    assert "row_count" in res
    assert "execution_metadata" not in res
    assert "empty_notes" not in res

    # 4. Error handling for unknown tool
    err = registry.execute_tool("unknown_tool", arguments={})
    assert "error" in err


def test_governed_tier_router():
    router = GovernedTierRouter(max_escalations=3, spend_budget_limit=2.00)

    # Turn 1: Planning phase should trigger Frontier tier
    d1 = router.route_turn(is_planning_phase=True)
    assert d1.tier == ModelTier.FRONTIER
    assert router.escalation_count == 1

    # Turn 2: Mechanical execution turn should default to Workhorse
    d2 = router.route_turn(is_planning_phase=False)
    assert d2.tier == ModelTier.WORKHORSE

    # Turn 3: AST signature change should trigger Frontier tier
    before_code = "def process_data(records: list): pass"
    after_code = "def process_data(records: list, strict: bool = False): pass"
    d3 = router.route_turn(before_code=before_code, after_code=after_code)
    assert d3.tier == ModelTier.FRONTIER
    assert router.escalation_count == 2

    # Turn 4: Consecutive gate failures on a file
    router.record_gate_result("src/service.py", passed=False)
    router.record_gate_result("src/service.py", passed=False)
    d4 = router.route_turn(active_file="src/service.py")
    assert d4.tier == ModelTier.FRONTIER
    assert router.escalation_count == 3

    # Turn 5: Escalation cap reached (max 3), should force Workhorse
    d5 = router.route_turn(schema_validation_failed=True)
    assert d5.tier == ModelTier.WORKHORSE
    assert "Escalation cap reached" in d5.reason

    # Test spend downshifting
    router_spend = GovernedTierRouter(spend_budget_limit=1.00, current_spend=0.90)
    d_spend = router_spend.route_turn(is_planning_phase=True)
    assert d_spend.tier == ModelTier.WORKHORSE
    assert d_spend.spend_downshifted is True

    # Test sticky lock release on success
    router_sticky = GovernedTierRouter(max_escalations=5)
    router_sticky.record_gate_result("app.py", passed=False)
    router_sticky.record_gate_result("app.py", passed=False)
    d_locked = router_sticky.route_turn(active_file="app.py")
    assert d_locked.tier == ModelTier.FRONTIER
    assert router_sticky.sticky_tier == ModelTier.FRONTIER

    # Pass the gate
    router_sticky.record_gate_result("app.py", passed=True)
    assert router_sticky.sticky_tier is None
    d_unlocked = router_sticky.route_turn(active_file="app.py")
    assert d_unlocked.tier == ModelTier.WORKHORSE