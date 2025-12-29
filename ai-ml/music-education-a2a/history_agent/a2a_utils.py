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


import json

from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
    PREV_AGENT_CARD_WELL_KNOWN_PATH
)

from starlette.applications import Starlette
from starlette.datastructures import URL
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint
)
from starlette.requests import Request
from starlette.responses import Response


async def a2a_card_dispatch(
        request: Request,
        call_next: RequestResponseEndpoint
) -> Response:
    """Handles requests for A2A Agent Cards by making sure
       the agent URL's protocol, and netloc are the same as in the card's
       request.

    Args:
        request (Request): HTTP Request.
        call_next (RequestResponseEndpoint): original handler to call.

    Returns:
        Response: HTTP Response
    """
    response = await call_next(request)
    if (
        response.status_code == 200
        and (
            request.url.path.endswith(AGENT_CARD_WELL_KNOWN_PATH)
            or request.url.path.endswith(PREV_AGENT_CARD_WELL_KNOWN_PATH)
            or request.url.path.endswith(EXTENDED_AGENT_CARD_PATH)
        )
    ):
        body = b""
        if hasattr(response, "body_iterator"):
            async for chunk in response.body_iterator: # type: ignore
                if isinstance(chunk, str):
                    chunk = chunk.encode(response.charset)
                body += chunk
        else:
            body = response.body
        if isinstance(body, memoryview):
            body = body.tobytes()
        body = body.decode(response.charset)
        card = json.loads(body)
        agent_url = URL(card["url"])

        headers = request.headers
        host = headers.get("x-forwarded-host", request.url.hostname)
        scheme = headers.get(
            "x-forwarded-proto",
            request.url.scheme or "http"
        ).lower()
        port = headers.get("x-forwarded-port", request.url.port)
        if port:
            if (
                scheme == "http" and port == "80"
            ) or (
                scheme == "https" and port == "443"
            ):
                port = None

        agent_url = agent_url.replace(
            scheme=scheme,
            hostname=host,
            port=port,
        )
        card["url"] = str(agent_url)
        response_headers = response.headers
        del response_headers["content-length"] # Content length will be recalculated
        response = Response(
            json.dumps(card).encode(response.charset),
            media_type="application/json",
            headers=response_headers,
        )
    return response


def add_a2a_card_handler(app: Starlette):
    """Adds A2A middleware handler to a Starlette app.

    Args:
        app (Starlette): Starlette app.
    """
    app.add_middleware(BaseHTTPMiddleware, dispatch=a2a_card_dispatch)