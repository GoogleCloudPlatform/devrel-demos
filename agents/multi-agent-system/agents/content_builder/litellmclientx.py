import os
from typing import Any, Optional, Union
from google.adk.models.lite_llm import LiteLLMClient
import google.auth
import google.auth.transport.requests
from google.oauth2 import id_token
from litellm import CustomStreamWrapper, ModelResponse


def get_auth_token() -> Optional[str]:
    """Obtains a Google ID token for the given audience (Cloud Run service URL)."""
    audience = os.getenv("OLLAMA_API_BASE", "")
    try:
        creds, _ = google.auth.default()
        # if user credentials are used
        if hasattr(creds, "id_token") and creds.id_token:
            return creds.id_token
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        if hasattr(creds, "id_token") and creds.id_token:
            return creds.id_token
        # if service account credentials are used
        fetched_id_token = id_token.fetch_id_token(auth_req, audience)
        return fetched_id_token
    except Exception as e:
        print(f"Error obtaining ID token for {audience}: {e}")
        return None


class AuthLiteLLMClient(LiteLLMClient):
    """
    Overrides the LiteLLMClient to inject a custom httpx.AsyncClient.
    """

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

    async def acompletion(
        self, model, messages, tools, **kwargs
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        """
        Updating headers to inject bearer token.
        """

        token: str = get_auth_token()
        if "extra_headers" not in kwargs or kwargs["extra_headers"] is None:
            kwargs["extra_headers"] = {}
        kwargs["extra_headers"]["Authorization"] = f"Bearer {token}"

        # Ensure we call the parent class acompletion to preserve ADK internal logic
        return await super().acompletion(
            model=model, messages=messages, tools=tools, **kwargs
        )
