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

import argparse
import logging
import os
from urllib.parse import urlparse
from typing import Tuple

import httpx

logger = logging.getLogger(__name__)

# Define the metadata server URL and the required header
METADATA_URL = "http://metadata.google.internal/computeMetadata/v1"
METADATA_HEADERS = {"Metadata-Flavor": "Google"}

def get_service_endpoint() -> Tuple[str, str, int]:
    """
    Gets host, scheme and port of the public URL of the running service.

    If APP_URL environment variable is configured, it parses that URL,
    and returns the respective endpoint parameters.

    If no APP_URL is set,
    it checks K_SERVICE to determine if running in a Cloud Run environment,
    and if so, it fetches project number, region, and service details
    from the metadata server to retrieve the service's host name,
    assuming the scheme is `https` and the port is `443`.

    Otherwise, it will try to infer these attributes from the environment
    and the command line parameters (--port and --host),
    with `localhost` and `8000` as defaults.

    Returns:
        A tuple with hostname, protocol/scheme and port
        of the service's public URL, e.g. ('example.com', 'https', 443).
)

    Raises:
        RuntimeError: If it fails to retrieve data from the metadata server.
    """

    # First, check if APP_URL environment variable is configured
    app_url = os.getenv("APP_URL", None)
    if app_url:
        parsed_url = urlparse(app_url)
        host = parsed_url.hostname or "localhost"
        port = parsed_url.port or 443
        scheme = parsed_url.scheme or ("https" if port == 443 else "http")
        return host, scheme, port

    # Get the service name from the environment variable set by Cloud Run
    service_name = os.getenv("K_SERVICE", None)
    if not service_name:
        logging.warning(
            "The K_SERVICE environment variable is not set."
            "Getting the endpoint from the command line parameters "
            "and the environment variables instead."
        )
        p = argparse.ArgumentParser()
        p.add_argument(
            '--host',
            required=False,
            default=os.getenv("HOST", "localhost")
        )
        p.add_argument(
            '--port',
            type=int,
            required=False,
            default=int(os.getenv("PORT", 8000))
        )
        args, _ = p.parse_known_args()
        host = args.host
        port = args.port
        scheme = "https" if port == 443 else "http"
        return host, scheme, port

    try:
        with httpx.Client(
            base_url=METADATA_URL,
            headers=METADATA_HEADERS
        ) as client:
            # 1. Get Project Number
            project_number_res = client.get("/project/numeric-project-id")
            project_number_res.raise_for_status()
            project_number = project_number_res.text

            # 2. Get Region
            # The response is in the format 'projects/12345/regions/us-central1'
            region_res = client.get("/instance/region")
            region_res.raise_for_status()
            region = region_res.text.split("/")[-1]

    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to query metadata server: {e}") from e

    host = f"{service_name}-{project_number}.{region}.run.app"
    scheme = "https"
    port = 443
    return host, scheme, port

