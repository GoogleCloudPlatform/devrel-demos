"""A2A client for the remote Digital Twin Gatekeeper.

Google Cloud access tokens expire after one hour. Instead of setting a fixed
`Authorization` header when the client is created, `GoogleAuthRefresh` checks
the credentials on every request and refreshes them when needed.
"""

from collections.abc import Generator
import os

from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
import google.auth
from google.auth.transport.requests import Request
import httpx

# The gatekeeper project serves A2A at /a2a/app. Locally it runs on port 8001.
LOCAL_GATEKEEPER_URL = "http://localhost:8001/a2a/app"
_CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class GoogleAuthRefresh(httpx.Auth):
    """Adds a fresh Google OAuth2 bearer token to every outgoing request."""

    def __init__(self) -> None:
        self._credentials, _ = google.auth.default(
            scopes=[_CLOUD_PLATFORM_SCOPE]
        )

    def auth_flow(
            self,
            request: httpx.Request,
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """Refreshes expired credentials, then sets the Authorization header."""
        if not self._credentials.valid:
            self._credentials.refresh(Request())
        request.headers["Authorization"] = f"Bearer {self._credentials.token}"
        yield request


def create_remote_gatekeeper_agent() -> RemoteA2aAgent:
    """Creates a sub-agent that calls the Gatekeeper over the A2A protocol.

    The Gatekeeper URL comes from the `GATEKEEPER_A2A_URL` environment variable
    and defaults to the local Gatekeeper server. Requests to `https://` URLs
    (Agent Runtime) are authenticated with `GoogleAuthRefresh`.

    Returns:
        A RemoteA2aAgent that discovers the Gatekeeper from its agent card.
    """
    base_url = os.environ.get("GATEKEEPER_A2A_URL", LOCAL_GATEKEEPER_URL)
    base_url = base_url.rstrip("/")
    auth = GoogleAuthRefresh() if base_url.startswith("https://") else None
    return RemoteA2aAgent(
        name="remote_gatekeeper",
        description=(
            "FIA Digital Twin Gatekeeper. Gives final homologation approval "
            "for a circuit after the Assessor has passed it."
        ),
        agent_card=f"{base_url}{AGENT_CARD_WELL_KNOWN_PATH}",
        httpx_client=httpx.AsyncClient(auth=auth, timeout=120.0),
    )
