import os

from google.adk.agents.llm_agent import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.environ["MCP_SERVER_URL"].rstrip("/")  # required: fail fast


class _GoogleAuthHeaders:
    """Provides Authorization headers with implicit token refresh."""

    def __init__(self, audience: str):
        self._request_adapter = Request()
        self._id_token = False
        try:
            self._credentials = id_token.fetch_id_token_credentials(
                audience, request=self._request_adapter
            )
        except google.auth.exceptions.DefaultCredentialsError:
            self._credentials, _ = google.auth.default()
            self._id_token = True
            if not isinstance(self._credentials, credentials.Credentials):
                raise

    def __call__(self, unused_context: ReadonlyContext | None = None) -> dict[str, str]:
        if not self._credentials.valid or (self._id_token and not self._credentials.id_token):
            self._credentials.refresh(self._request_adapter)
        token = self._credentials.id_token if self._id_token else self._credentials.token
        return {"Authorization": f"Bearer {token}"}


zoo_mcp_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=f"{MCP_SERVER_URL}/mcp",
        timeout=30.0,  # leave room for Cloud Run cold starts
    ),
    header_provider=_GoogleAuthHeaders(MCP_SERVER_URL),
)

_INSTRUCTIONS = """You are the friendly voice of the Zoo Tour Guide. You help visitors learn
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
