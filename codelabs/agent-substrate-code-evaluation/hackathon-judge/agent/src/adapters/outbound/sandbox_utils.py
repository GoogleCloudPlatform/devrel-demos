# Copyright 2026 Google LLC
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

import os

from .substrate_client import (
    DEFAULT_ROUTER_URL,
    DEFAULT_SANDBOX_NAMESPACE,
    DEFAULT_SANDBOX_TEMPLATE,
    DEFAULT_TUNNEL_URL,
    CommandResult,
    SubstrateActor,
    SubstrateActorClient,
    SubstrateSandbox,
    SubstrateSandboxClient,
)


def get_sandbox_client() -> SubstrateActorClient:
    """Builds a SubstrateActorClient for the configured connection method.

    SANDBOX_CONNECTION_METHOD:
      - "router" (default): in-cluster via atenet-router with PodCertificate mTLS.
        Override the URL with SANDBOX_ROUTER_URL.
      - "tunnel": local development via HTTP port-forward or bridge.
    """
    method = os.getenv("SANDBOX_CONNECTION_METHOD", "router").lower()

    if method == "router":
        router_url = os.getenv("SANDBOX_ROUTER_URL", DEFAULT_ROUTER_URL)
    elif method == "tunnel":
        router_url = os.getenv("SANDBOX_ROUTER_URL", DEFAULT_TUNNEL_URL)
    else:
        raise ValueError(f"Unknown SANDBOX_CONNECTION_METHOD: {method}")

    return SubstrateActorClient(
        router_url=router_url,
        connection_method=method,
    )


__all__ = [
    "CommandResult",
    "DEFAULT_ROUTER_URL",
    "DEFAULT_SANDBOX_NAMESPACE",
    "DEFAULT_SANDBOX_TEMPLATE",
    "DEFAULT_TUNNEL_URL",
    "SubstrateActor",
    "SubstrateActorClient",
    "SubstrateSandbox",
    "SubstrateSandboxClient",
    "get_sandbox_client",
]
