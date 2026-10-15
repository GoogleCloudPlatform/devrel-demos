import os
from urllib.parse import urlparse

from google.adk.agents.llm_agent import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.integrations.agent_registry import AgentRegistry
from google.oauth2 import id_token
from google.auth.transport.requests import Request

from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]  # required: fail fast
PROJECT_NUMBER = os.environ["GOOGLE_CLOUD_PROJECT_NUMBER"]  # required: fail fast
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
MCP_SERVER_URN = f"urn:mcp:projects-{PROJECT_NUMBER}:projects:{PROJECT_NUMBER}:locations:{LOCATION}:agentregistry:services:zoo-mcp-server"


class _GoogleAuthHeaders:
    """Provides Authorization headers with implicit token refresh."""

    def __init__(self):
        self._request = Request()
        self._credentials = None

    def bind(self, endpoint_url: str) -> None:
        # Cloud Run expects the service URL (scheme + host) as the audience, not the /mcp path.
        parsed = urlparse(endpoint_url)
        audience = f"{parsed.scheme}://{parsed.netloc}"
        self._credentials = id_token.fetch_id_token_credentials(
            audience, request=self._request
        )

    def __call__(self, unused_context: ReadonlyContext | None = None) -> dict[str, str]:
        if self._credentials is None:
            raise RuntimeError("MCP endpoint not bound; run discovery first.")
        if not self._credentials.valid:
            self._credentials.refresh(self._request)
        return {"Authorization": f"Bearer {self._credentials.token}"}


header_provider = _GoogleAuthHeaders()
registry = AgentRegistry(
    project_id=PROJECT_ID,
    location=LOCATION,
    header_provider=header_provider,
)

mcp_server_name = next(
    (
        s["name"]
        for s in registry.list_mcp_servers().get("mcpServers", [])
        if s.get("mcpServerId") == MCP_SERVER_URN
    ),
    None,
)
if not mcp_server_name:
    raise RuntimeError(f"MCP server '{MCP_SERVER_URN}' not found in Agent Registry.")
zoo_mcp_toolset = registry.get_mcp_toolset(mcp_server_name=mcp_server_name)
header_provider.bind(zoo_mcp_toolset.connection_params.url)
zoo_mcp_toolset.connection_params.timeout = 30.0

_INSTRUCTIONS = """    You are the friendly voice of the Zoo Tour Guide. You help visitors learn
    about the animals that live in the zoo.
    Rules:
    - Never answer questions about the zoo's animals from your own knowledge.
      Every fact about our animals (names, species, counts, ages, enclosures,
      trails) MUST come from the zoo tools. If the tools return nothing, say so.
    - Use the tools on the very first question as well. Do not reply with a
      generic greeting when the visitor has already asked something.
    - For zoo-wide questions (for example "how many animals are in the zoo"),
      first find out which species the zoo has, then gather the animals for
      each species and combine the results.
    - If the visitor only greets you, briefly introduce yourself and offer to
      help them explore the zoo's animals.
"""

root_agent = Agent(
    model="gemini-3.8-flash",
    name="zoo_agent",
    description="The friendly assistant for handling a user's requests about zoo animals.",
    instruction=_INSTRUCTIONS,
    tools=[zoo_mcp_toolset],
)
