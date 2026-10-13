import os
import httpx

from google.adk.agents.llm_agent import Agent
from google.adk.integrations.agent_registry import AgentRegistry
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
import google.auth
from google.auth.transport.requests import Request

from dotenv import load_dotenv
load_dotenv()

PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]             # required: fail fast
PROJECT_NUMBER = os.environ["GOOGLE_CLOUD_PROJECT_NUMBER"]  # required: fail fast
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-west1")
MCP_SERVER_URN = f"urn:mcp:projects-{PROJECT_NUMBER}:projects:{PROJECT_NUMBER}:locations:{REGISTRY}:run:services:zoo-mcp-server"

class _GoogleAuthHeaders():
    "Provides Authorization headers with thread-safe, implicit token refresh."
    def __init__(self, quota_project_id: str | None = None):
        self._credentials, default_project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self._quota_project_id = quota_project_id or getattr(
            self._credentials, "quota_project_id", default_project
        )
        self._request = Request()

    def __call__(self, unused_context: ReadonlyContext | None = None) -> dict[str, str]:
        # Enforce implicit refresh whenever the token expires or is invalid
        if not self._credentials.valid:
            self._credentials.refresh(self._request)
        headers = {"Authorization": f"Bearer {self._credentials.token}"}
        if self._quota_project_id:
            headers["x-goog-user-project"] = self._quota_project_id
        return headers


    """
    Auth header provider with support for automatic token refresh.
    """
    def __init__(self):
        # Obtain Google credentials (e.g., Application Default Credentials)
        self._credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        self.request_adapter = Request()

    def __call__(self, unused_context: ReadonlyContext) -> dict[str, str]:
        # Refresh the credentials if they are expired or not yet loaded
        if not self._credentials.valid:
            self._credentials.refresh(self.request_adapter)
        return {
            "Authorization": f"Bearer {self._credentials.token}",
        }

registry = AgentRegistry(
    project_id=PROJECT_ID,
    location=REGION,
    header_provider=_GoogleAuthHeaders(),
)
mcp_server_name = None
mcp_servers_response = registry.list_mcp_servers()
for server in mcp_servers_response.get("mcpServers", []):
    if server.get("mcpServerId") == MCP_SERVER_URN:
        mcp_server_name = server.get("name")
        break

zoo_mcp_toolset = registry.get_mcp_toolset(
   mcp_server_name=mcp_server_name,
)

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
