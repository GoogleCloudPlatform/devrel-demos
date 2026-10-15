import asyncio
import os
import time
from typing import Any
from urllib.parse import urlparse

from google.adk.agents.llm_agent import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.integrations.agent_registry import AgentRegistry
from google.adk.tools import ToolContext, BaseTool, BaseToolset
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.auth import exceptions
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]  # required: fail fast
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
DISCOVERY_STATE_KEY = (
    "app:zoo_mcp_servers"  # "app:" prefix scopes state across application run
)
DISCOVERY_TTL_SECONDS = 24 * 60 * 60  # Retention period: rediscovery every 24 hours


class _GoogleAuthHeaders:
    """Provides Authorization headers with implicit token refresh."""

    def __init__(self):
        self._request = Request()
        self._id_token = True
        self._credentials = None
        self._bound = False

    def bind(self, endpoint_url: str) -> None:
        parsed = urlparse(endpoint_url)
        audience = f"{parsed.scheme}://{parsed.netloc}"
        try:
            self._credentials = id_token.fetch_id_token_credentials(
                audience, request=self._request_adapter
            )
        except exceptions.DefaultCredentialsError:
            self._credentials, _ = google.auth.default()
            self._id_token = False
            if not isinstance(self._credentials, credentials.Credentials):
                raise
        self._bound = True

    def __call__(self, unused_context: ReadonlyContext | None = None) -> dict[str, str]:
        if not self._bound:
            raise RuntimeError("MCP endpoint not bound; run discovery first.")
        if self._credentials is None:  # not a Cloud Run endpoint: add no headers
            return {}
        if not self._credentials.valid or (self._id_token and not self._credentials.id_token):
            self._credentials.refresh(self._request_adapter)
        token = self._credentials.id_token if self._user_id_token else self._credentials.token
        return {"Authorization": f"Bearer {token}"}


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


registry = AgentRegistry(
    project_id=PROJECT_ID,
    location=LOCATION,
)


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
            "message": f"No MCP servers found in Agent Registry at {LOCATION} matching '{query}'.",
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

    def _build_toolset(self, server_name: str) -> McpToolset:
        """Creates a toolset for one server with its own ID-token provider (blocking I/O)."""
        header_provider = _GoogleAuthHeaders()
        server_registry = AgentRegistry(
            project_id=self._registry.project_id,
            location=self._registry.location,
            header_provider=header_provider,
        )
        toolset = server_registry.get_mcp_toolset(server_name)
        header_provider.bind(toolset.connection_params.url)
        toolset.connection_params.timeout = 30.0
        return toolset

    async def _tools_of(self, server_name: str, ctx: ReadonlyContext) -> list[BaseTool]:
        """Resolves an MCP server to an McpToolset (cached) and returns its tools."""
        try:
            if server_name not in self._toolsets:
                # get_mcp_toolset performs blocking I/O; run in a worker thread
                self._toolsets[server_name] = await asyncio.to_thread(
                    self._build_toolset, server_name
                )
            return await self._toolsets[server_name].get_tools_with_prefix(ctx)
        except Exception as e:
            # Fault isolation: an unreachable server will not bring down the entire agent
            print(f"Skipping MCP server {server_name}: {e}")
            return []

    async def get_tools(
        self, readonly_context: ReadonlyContext | None = None
    ) -> list[BaseTool]:
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
    model="gemini-3.8-flash",
    name="zoo_agent",
    description="The friendly assistant for handling a user's requests about zoo animals.",
    instruction=zoo_guide_instruction,
    tools=[
        discover_zoo_mcp_servers,
        RegistryDiscoveredToolset(registry),
    ],
)
