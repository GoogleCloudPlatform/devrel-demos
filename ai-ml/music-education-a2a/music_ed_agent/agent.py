import os
import subprocess
from urllib.parse import urlparse

import httpx

from a2a.types import AgentCard

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, DEFAULT_TIMEOUT

from google.auth import compute_engine
from google.auth.credentials import TokenState
import google.auth.transport.requests

from music_ed_agent.tools import (
    adk_youtube_search_tool,
    adk_wikipedia_tool,
)

def create_authenticated_client(
        remote_cloud_run_url: str,
        timeout: float = DEFAULT_TIMEOUT
    ) -> httpx.AsyncClient:
    class IdentityTokenAuth(httpx.Auth):
        requires_request_body = False

        def __init__(self, remote_cloud_run_url: str):
            parsed_url = urlparse(remote_cloud_run_url)
            root_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            root_url = remote_cloud_run_url
            self.root_url = root_url
            self.session = None


        def auth_flow(self, request):
            if "K_SERVICE" in os.environ:
                # We are in Cloud Run, use a service identity token.
                # Start from getting a cached session, one per remote URL.
                if not self.session:
                    cr_request = google.auth.transport.requests.Request()
                    credentials = compute_engine.IDTokenCredentials(
                        request=request,
                        target_audience=self.root_url,
                        use_metadata_identity_endpoint=True
                    )
                    credentials.refresh(cr_request)
                    self.session = google.auth.transport.requests.AuthorizedSession(
                        credentials
                    )
                if self.session.credentials.token_state != TokenState.FRESH:
                    self.session.credentials.refresh(
                        google.auth.transport.requests.Request()
                    )
                id_token = self.session.credentials.token
            else:
                # Local run, fetching authenticated user's identity token.
                id_token = subprocess.check_output(
                    [
                        "gcloud",
                        "auth",
                        "print-identity-token",
                        "-q"
                    ]
                ).decode().strip()
            request.headers["Authorization"] = f"Bearer {id_token}"
            yield request

    client = httpx.AsyncClient(
        auth=IdentityTokenAuth(remote_cloud_run_url),
        timeout=timeout,
    )

    return client


# Get env var - location of Remote A2A agent
remote_agent_card = os.getenv("REMOTE_AGENT_CARD")
if not remote_agent_card:
    raise RuntimeError("REMOTE_AGENT_CARD environment variable must be set.")

# Create an authenticated HTTP client for A2A client.
httpx_client = create_authenticated_client(remote_agent_card)

# Remote agent (historical context)
historical_context_agent = RemoteA2aAgent(
    name="historical_context_agent",
    description="Agent that researches the historical context of a classical music composition, and its composer.",
    agent_card=remote_agent_card,
    httpx_client=httpx_client
)

# Root agent info
agent_instruction = """

You are a music education agent that helps students learn about classical compositions.

As input, the user will provide the name of a composition, along with the composer. Your task is to educate the student about the composition. Suggested workflow:
1. Use the model to verify that the composition is a valid classical piece. If not, request that the user provides another piece.
2. Use the Youtube Search Tool to find the first YouTube search result URL for that classical piece. eg. it might return ['/watch?v=jOofzffyDSA'].
3. Call the Gemini model with the name of the composition and the audio. Ask Gemini to analyze the classical piece based on what it knows and the audio, providing the student with key info about the following. (Use plenty of emojis and text formatting to make this more readable.)
    - The piece's form and structure (is there a key theme or melody?)
    - Instrumentation, including which musical familes are involved (is there a brass section?)
    - Key
    - Tempo
    - Mood
    - Technical elements (eg. harmonic progressions)
4. Search Wikipedia for the composition to get definitive information about things like tempo.
5. Provide the full youtube link for the student to listen to as they learn about the piece. Ask the user if they want more information on the classical piece.

Then stop and ask the user if they want to hear about the historical context of the composition. If they say yes, invoke the historical_context_agent to get more info.

TOOLS:
- adk_youtube_search_tool - langchain tool that lets you search youtube for videos, can limit to 1 result tool.run("mozart violin concerto no 3,1").
- adk_wikipedia_tool - langchain tool to search wikipedia articles. (string search query)

SUB AGENTS:
- historical_context_agent - Searches the web for historical context about the composer, influences, and time period.
"""


root_agent = Agent(
    model="gemini-2.5-pro",
    name="music_ed_agent",
    instruction=agent_instruction,
    tools=[adk_youtube_search_tool, adk_wikipedia_tool],
    sub_agents=[historical_context_agent],
)
