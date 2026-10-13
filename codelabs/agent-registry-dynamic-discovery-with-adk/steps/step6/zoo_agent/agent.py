import asyncio
import os
import time
from typing import Any

from google.adk.agents.llm_agent import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.integrations.agent_registry import AgentRegistry
from google.adk.tools import ToolContext, BaseTool, BaseToolset
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
import google.auth
from google.auth.transport.requests import Request

from dotenv import load_dotenv
load_dotenv()

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]          # required: fail fast
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-west1")
DISCOVERY_STATE_KEY = "app:zoo_mcp_servers" # "app:" prefix scopes state across application run
DISCOVERY_TTL_SECONDS = 24 * 60 * 60  # Retention period: rediscovery every 24 hours

class _GoogleAuthHeaders():
    """Provides Authorization headers with implicit token refresh."""
    def __init__(self, quota_project_id: str | None = None):
        self._credentials, default_project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self._quota_project_id = quota_project_id or getattr(
            self._credentials, "quota_project_id", default_project
        )
        self._request = Request()

    def __call__(self, unused_context: ReadonlyContext | None = None) -> dict[str, str]:
        if not self._credentials.valid:
            self._credentials.refresh(self._request)
        headers = {"Authorization": f"Bearer {self._credentials.token}"}
        if self._quota_project_id:
            headers["x-goog-user-project"] = self._quota_project_id
        return headers

registry = AgentRegistry(
    project_id=PROJECT_ID,
    location=REGION,
    header_provider=_GoogleAuthHeaders(),
)

def _fresh_discovery(state: Any) -> dict[str, Any] | None:
    """Returns the saved discovery record if it exists and has not expired."""
    if not state:
        return None
    record = state.get(DISCOVERY_STATE_KEY)
    if not record or not record.get("servers"):
        return None
    if time.time() - record.get("discovered_at", 0) > DISCOVERY_TTL_SECONDS:
        return None
    return record

def discover_zoo_mcp_servers(query: str, tool_context: ToolContext) -> dict[str, Any]:
    """Discovers Zoo MCP server(s) matching the query using semantic search.
    
    Args:
        query: Semantic description of zoo capabilities needed (e.g. 'zoo animal info')
    """
    # Check retention/cache
    cached = _fresh_discovery(tool_context.state)
    if cached:
        return {
            "status": "already_discovered",
            "message": "Zoo MCP servers are already discovered.",
            "servers": cached["servers"],
        }

    # Query Agent Registry directly using native Python SDK
    try:
        response = registry.search_mcp_servers(
            search_string=query,
            search_type="SEMANTIC",
            page_size=5,
        )
    except Exception as e:
        return {
            "status": "error",
            "message": f"Agent Registry search failed: {e}",
        }

    found_servers = response.get("mcpServers", [])
    if not found_servers:
        return {
            "status": "not_found",
            "message": f"No MCP servers found in Agent Registry at {REGION} matching '{query}'.",
        }

    valid_servers = [s["name"] for s in found_servers if "name" in s]
    tool_context.state[DISCOVERY_STATE_KEY] = {
        "servers": valid_servers,
        "discovered_at": time.time(),
    }
    return {
        "status": "discovered",
        "message": f"Successfully discovered {len(valid_servers)} Zoo MCP server(s).",
        "servers": valid_servers,
    }

class RegistryDiscoveredToolset(BaseToolset):
    """Dynamically resolves and mounts tools from servers saved in session state."""
    def __init__(self, agent_registry: AgentRegistry):
        super().__init__()
        self._registry = agent_registry
        self._toolsets: dict[str, McpToolset] = {}
        # OVERRIDE BaseToolset._use_invocation_cache so the toolset reacts immediately to discovery/rediscovery
        self._use_invocation_cache = False

    async def _tools_of(self, server_name: str, ctx: ReadonlyContext) -> list[BaseTool]:
        """Resolves an MCP server to an McpToolset (cached) and returns its tools."""
        try:
            if server_name not in self._toolsets:
                # get_mcp_toolset performs blocking I/O; run in a worker thread
                self._toolsets[server_name] = await asyncio.to_thread(
                    self._registry.get_mcp_toolset, server_name
                )
            return await self._toolsets[server_name].get_tools_with_prefix(ctx)
        except Exception as e:
            # Fault isolation: an unreachable server will not bring down the entire agent
            print(f"Skipping MCP server {server_name}: {e}")
            return []

    async def get_tools(self, readonly_context: ReadonlyContext | None = None) -> list[BaseTool]:
        """Fetches active tools from all discovered servers in the current state."""
        if not readonly_context:
            return []
        record = _fresh_discovery(readonly_context.state)
        if not record or not record.get("servers"):
            if self._toolsets:
                await self.close()
            return []
        # Concurrently resolve and collect tools across all registered servers
        per_server = await asyncio.gather(
            *(self._tools_of(name, readonly_context) for name in record["servers"])
        )
        return [tool for tools in per_server for tool in tools]

    async def close(self) -> None:
        """Concurrently closes all active MCP client sessions."""
        if self._toolsets:
            await asyncio.gather(
                *(toolset.close() for toolset in self._toolsets.values()),
                return_exceptions=True,
            )
            self._toolsets.clear()

_ROLE = """You are a friendly, knowledgeable guide at the zoo. You help visitors
with animals, exhibits, feeding and show times, maps, tickets, and events.
Base every fact about this zoo on tool results; never invent them.
"""
_DISCOVERY_PROMPT = """
TOOL DISCOVERY - do this once before answering the visitor:
1. Call `discover_zoo_mcp_servers` with a semantic query such as
   "zoo animals, exhibits, habitat, care, feeding schedule".
2. As soon as the discovery succeeds, the zoo tools become available to you.
3. Immediately use those tools to answer the visitor's request.
"""
def zoo_guide_instruction(ctx: ReadonlyContext) -> str:
    record = _fresh_discovery(ctx.state)
    if record is None:
        return _ROLE + _DISCOVERY_PROMPT
    return _ROLE + (
        f"\nYour active Zoo MCP servers: {', '.join(record['servers'])}. "
        "Do not run discovery again; use the active zoo tools directly to fulfill the visitor's request."
    )
root_agent = Agent(
    name="zoo_guide",
    model="gemini-2.5-flash",
    description="A friendly zoo guide that discovers and uses zoo MCP tools.",
    instruction=zoo_guide_instruction,
    tools=[
        discover_zoo_mcp_servers,
        RegistryDiscoveredToolset(registry),
    ],
)
