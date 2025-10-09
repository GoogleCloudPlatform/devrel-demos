# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
from urllib.parse import urlparse

import httpx

from google.adk.agents.remote_a2a_agent import DEFAULT_TIMEOUT

from google.auth.credentials import TokenState
from google.auth.transport.requests import AuthorizedSession, Request
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2.id_token import fetch_id_token_credentials


def create_authenticated_client(
        remote_service_url: str,
        timeout: float = DEFAULT_TIMEOUT
    ) -> httpx.AsyncClient:
    """Creates an httpx.AsyncClient with Google identity token authentication.
    Identity tokens are obtained:
      - If running in Cloud, from Compute Metadata server
      - If running locally, from gcloud CLI

    Args:
        remote_service_url (str): URL of the service to authenticate requests to.
        timeout (float, optional): Request timeout. Defaults to DEFAULT_TIMEOUT.

    Returns:
        httpx.AsyncClient: httpx Client with Google identity token authentication.
    """

    class _IdentityTokenAuth(httpx.Auth):
        requires_request_body = False

        def __init__(self, remote_service_url: str):
            parsed_url = urlparse(remote_service_url)
            self.root_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            self.outside_cloud = False # at first, assume we run in Cloud
            self.session = None

        def auth_flow(self, request):
            if not self.outside_cloud:
                try:
                    if not self.session:
                        credentials = fetch_id_token_credentials(
                            audience=self.root_url,
                        )
                        credentials.refresh(Request())
                        self.session = AuthorizedSession(
                            credentials
                        )
                    if self.session.credentials.token_state != TokenState.FRESH:
                            self.session.credentials.refresh(
                                Request()
                            )
                    id_token = self.session.credentials.token
                except DefaultCredentialsError:
                    self.outside_cloud = True
            if self.outside_cloud:
                # Local run, fetching authenticated user's identity token
                # from gcloud CLI
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

    return httpx.AsyncClient(
        auth=_IdentityTokenAuth(remote_service_url),
        timeout=timeout,
    )