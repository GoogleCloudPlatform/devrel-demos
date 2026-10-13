import os
import httpx
import google.auth
from google.auth.transport.requests import Request

from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

from dotenv import load_dotenv
load_dotenv()

MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]       # required: fail fast

class GoogleAuthHeaders(httpx.Auth):
    """
    HTTPX Auth extension that guarantees a valid bearer token is attached
    to every request.
    """
    def __init__(self):
        # Obtain Google credentials (e.g., Application Default Credentials)
        self._credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        self._request_adapter = Request()

    def auth_flow(self, request: httpx.Request):
        # Refresh the credentials if they are expired or not yet loaded
        if not self._credentials.valid:
            self._credentials.refresh(self._request_adapter)

        # Inject the fresh token into the request headers
        request.headers["Authorization"] = f"Bearer {self._credentials.token}"

        # Yield the modified request back to httpx to be sent
        yield request

_auth_provider = GoogleAuthHeaders()
def _auth_client_factory(headers, timeout,auth) -> httpx.AsyncClient:
    """Factory that attaches our dynamic Auth flow to the ADK HTTP client."""

    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        # Override any ADK auth with our dynamic AutoRefreshingBearerAuth
        auth=_auth_provider,
    )

zoo_mcp_toolset = McpToolset(
   connection_params = StreamableHTTPConnectionParams(
      url=MCP_SERVER_URL,
      httpx_client_factory=_auth_client_factory,
))

root_agent = Agent(
    model='gemini-3.8-flash',
    name='zoo_agent',
    description="The friendly assistant for handling a user's requests about zoo animals.",
    instruction="""
    You are the friendly voice of the Zoo Tour Guide. Your tasks are:
    - Let the user know you will help them learn about the animals we have in the zoo.
    - When the user responds, use the tools to find information about animals.
    """,
    tools=[zoo_mcp_toolset],
)
