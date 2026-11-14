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

"""Agent Substrate v1.0.0 client for ephemeral Judge Actor lifecycles."""

from collections.abc import Callable
from dataclasses import dataclass
import json
import logging
import os
import ssl
import subprocess
import time
from typing import Any
import urllib.parse
import uuid

import httpx

logger = logging.getLogger(__name__)

DEFAULT_ROUTER_URL = "https://atenet-router.ate-system.svc:443"
DEFAULT_TUNNEL_URL = "http://localhost:8080"
DEFAULT_SANDBOX_TEMPLATE = "judge-sandbox"
DEFAULT_SANDBOX_NAMESPACE = "hackathon-judge"
DEFAULT_ACTOR_PORT = "80"

DEFAULT_CLIENT_CERT_PATHS = (
    "/run/router-client/credential-bundle.pem",
    "/var/run/ate/identity/credential-bundle.pem",
)
DEFAULT_TRUST_BUNDLE_PATHS = (
    "/run/router-client/trust-bundle.pem",
    "/var/run/ate/trust/trust-bundle.pem",
)
DEFAULT_API_TOKEN_PATHS = (
    "/run/router-client/ate-api-token",
    "/var/run/ate/token/ate-api-token",
)


@dataclass
class CommandResult:
    """Result of executing a shell command inside a Judge Actor."""

    stdout: str
    stderr: str
    exit_code: int


def _first_existing_path(
    env_keys: tuple[str, ...], default_paths: tuple[str, ...]
) -> str | None:
    for key in env_keys:
        val = os.getenv(key)
        if val:
            return val
    for path in default_paths:
        if os.path.isfile(path):
            return path
    return None


def _default_command_runner(
    args: list[str], input_text: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def build_egress_policy_document(namespace: str) -> dict:
    """Build the per-actor EgressPolicy allowing internal Model Proxy and external HTTPS."""
    return {
        "rules": [
            {
                "http": {
                    "hostnames": [
                        f"agent.{namespace}.svc.cluster.local",
                        f"agent.{namespace}.svc",
                        "agent",
                    ],
                    "ports": {"numbers": [8000, 8082]},
                }
            },
            {
                "https": {
                    "hostnames": ["*"],
                    "ports": {"numbers": [443]},
                }
            },
        ]
    }


def build_target_headers(namespace: str, actor_id: str) -> dict[str, str]:
    """Build atenet-router target headers for routing requests to a Judge Actor."""
    return {
        "X-Ate-Target-Atespace": namespace,
        "X-Ate-Target-Namespace": namespace,
        "X-Ate-Target-Actor": actor_id,
        "X-Ate-Target-Name": actor_id,
        "X-Ate-Target-Port": DEFAULT_ACTOR_PORT,
        "ate-target-actor": f"{namespace}/{actor_id}",
    }


class _ActorCommands:
    """Asynchronous command execution client over atenet-router."""

    def __init__(self, actor: "SubstrateActor") -> None:
        self._actor = actor

    def run(self, command: str, timeout: float = 600.0) -> CommandResult:
        """Start a command via POST /execute/start and poll GET /execute/status/{job_id}."""
        start_resp = self._actor.request(
            "POST",
            "/execute/start",
            json={"command": command, "timeout": timeout},
        )
        if start_resp.status_code >= 400:
            raise RuntimeError(
                f"Failed to start command on {self._actor.actor_id} "
                f"(HTTP {start_resp.status_code}): {start_resp.text}"
            )
        job_id = start_resp.json()["job_id"]

        deadline = time.monotonic() + timeout
        while True:
            status_resp = self._actor.request(
                "GET",
                f"/execute/status/{job_id}",
            )
            if status_resp.status_code >= 400:
                raise RuntimeError(
                    f"Failed to poll job {job_id} on {self._actor.actor_id} "
                    f"(HTTP {status_resp.status_code}): {status_resp.text}"
                )
            payload = status_resp.json()
            status = payload.get("status")
            if status in ("completed", "failed"):
                exit_code = payload.get("exit_code")
                if exit_code is None:
                    exit_code = 0 if status == "completed" else 1
                return CommandResult(
                    stdout=payload.get("stdout") or "",
                    stderr=payload.get("stderr") or "",
                    exit_code=int(exit_code),
                )
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Command timed out after {timeout}s on {self._actor.actor_id}: {command}"
                )
            time.sleep(self._actor.poll_interval)


class _ActorFiles:
    """File upload and download client over atenet-router."""

    def __init__(self, actor: "SubstrateActor") -> None:
        self._actor = actor

    def write(self, path: str, content: str | bytes) -> None:
        """Upload a file into the Judge Actor working directory via POST /upload."""
        raw_bytes = (
            content.encode("utf-8") if isinstance(content, str) else content
        )
        filename = os.path.basename(path) or path
        resp = self._actor.request(
            "POST",
            "/upload",
            params={"path": path},
            files={"file": (filename, raw_bytes, "text/plain")},
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Failed to upload '{path}' to {self._actor.actor_id} "
                f"(HTTP {resp.status_code}): {resp.text}"
            )

    def read(self, path: str) -> str:
        """Download a file from the Judge Actor working directory via GET /download/{path}."""
        clean_path = urllib.parse.quote(path.lstrip("/"), safe="/")
        resp = self._actor.request(
            "GET",
            f"/download/{clean_path}",
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"Failed to download '{path}' from {self._actor.actor_id} "
                f"(HTTP {resp.status_code}): {resp.text}"
            )
        return resp.text


class SubstrateActor:
    """Handle to an active Judge Actor in Agent Substrate."""

    def __init__(
        self,
        actor_id: str,
        namespace: str,
        template: str,
        client: "SubstrateActorClient",
    ) -> None:
        self.actor_id = actor_id
        self.namespace = namespace
        self.template = template
        self._client = client
        self.commands = _ActorCommands(self)
        self.files = _ActorFiles(self)

    @property
    def name(self) -> str:
        return self.actor_id

    @property
    def headers(self) -> dict[str, str]:
        return build_target_headers(self.namespace, self.actor_id)

    @property
    def poll_interval(self) -> float:
        return self._client.poll_interval

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Send an actor-scoped HTTP request over atenet-router."""
        merged_headers = dict(self.headers)
        extra_headers = kwargs.pop("headers", None)
        if extra_headers:
            merged_headers.update(extra_headers)
        return self._client.request(
            method,
            path,
            headers=merged_headers,
            **kwargs,
        )

    def terminate(self) -> None:
        """Delete the per-actor EgressPolicy and the Judge Actor via kubectl-ate."""
        self._client.delete_actor_and_policy(
            actor_id=self.actor_id,
            namespace=self.namespace,
        )


SubstrateSandbox = SubstrateActor


class SubstrateActorClient:
    """Client for creating, driving, and deleting ephemeral Judge Actors."""

    def __init__(
        self,
        router_url: str = DEFAULT_ROUTER_URL,
        connection_method: str = "router",
        client_cert_file: str | None = None,
        trust_bundle_file: str | None = None,
        token_file: str | None = None,
        api_endpoint: str | None = None,
        http_client: httpx.Client | None = None,
        command_runner: Callable[[list[str], str | None], subprocess.CompletedProcess]
        | None = None,
        poll_interval: float = 2.0,
        readiness_timeout: float = 60.0,
    ) -> None:
        self.router_url = router_url.rstrip("/")
        self.connection_method = connection_method
        self.client_cert_file = client_cert_file or _first_existing_path(
            ("SUBSTRATE_CLIENT_CERT_FILE", "SUBSTRATE_TLS_CERT_FILE"),
            DEFAULT_CLIENT_CERT_PATHS,
        )
        self.trust_bundle_file = trust_bundle_file or _first_existing_path(
            ("SUBSTRATE_TRUST_BUNDLE_FILE",),
            DEFAULT_TRUST_BUNDLE_PATHS,
        )
        self.token_file = token_file or _first_existing_path(
            ("SUBSTRATE_API_TOKEN_FILE",),
            DEFAULT_API_TOKEN_PATHS,
        )
        self.api_endpoint = api_endpoint or os.getenv("SUBSTRATE_API_ENDPOINT")
        self.http_client = http_client
        self.command_runner = command_runner or _default_command_runner
        self.poll_interval = poll_interval
        self.readiness_timeout = readiness_timeout

    @property
    def api_url(self) -> str:
        return self.router_url

    def build_ssl_context(self) -> ssl.SSLContext | None:
        """Build an mTLS SSLContext for atenet-router when cert bundles are present."""
        if self.connection_method != "router":
            return None
        if (
            self.client_cert_file
            and self.trust_bundle_file
            and os.path.isfile(self.client_cert_file)
            and os.path.isfile(self.trust_bundle_file)
        ):
            ctx = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH,
                cafile=self.trust_bundle_file,
            )
            ctx.load_cert_chain(certfile=self.client_cert_file)
            return ctx
        return None

    def _get_http_client(self) -> tuple[httpx.Client, bool]:
        if self.http_client is not None:
            return self.http_client, False
        ssl_ctx = self.build_ssl_context()
        verify: ssl.SSLContext | bool = ssl_ctx if ssl_ctx is not None else True
        return (
            httpx.Client(
                base_url=self.router_url,
                verify=verify,
                timeout=httpx.Timeout(30.0, connect=10.0),
            ),
            True,
        )

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Send an HTTP request over the configured router/tunnel client."""
        client, should_close = self._get_http_client()
        try:
            return client.request(method, path, **kwargs)
        finally:
            if should_close:
                client.close()

    def _cli_global_flags(self) -> list[str]:
        flags: list[str] = []
        if self.token_file:
            flags.extend(["--token-file", self.token_file])
        if self.api_endpoint:
            flags.extend(["--endpoint", self.api_endpoint])
        return flags

    def _run_cli(
        self, args: list[str], input_text: str | None = None
    ) -> subprocess.CompletedProcess:
        full_args = ["kubectl-ate", *args, *self._cli_global_flags()]
        return self.command_runner(full_args, input_text)

    def delete_actor_and_policy(self, actor_id: str, namespace: str) -> None:
        for kind in ("egress-policy", "actor"):
            try:
                proc = self._run_cli(["delete", kind, actor_id, "-a", namespace])
                if proc.returncode != 0:
                    logger.warning(
                        "kubectl-ate delete %s %s returned %d: %s",
                        kind,
                        actor_id,
                        proc.returncode,
                        (proc.stderr or "").strip(),
                    )
            except Exception as exc:
                logger.warning(
                    "Ignoring error deleting %s %s: %s", kind, actor_id, exc
                )

    _delete_actor_and_policy = delete_actor_and_policy

    def _wait_for_health(self, actor: SubstrateActor) -> None:
        deadline = time.monotonic() + self.readiness_timeout
        last_error = "no response"
        while True:
            try:
                resp = actor.request("GET", "/health")
                if resp.status_code == 200:
                    return
                last_error = f"HTTP {resp.status_code}"
            except httpx.HTTPError as exc:
                last_error = str(exc)

            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Timed out waiting for Judge Actor {actor.actor_id} readiness ({last_error})"
                )
            time.sleep(self.poll_interval)

    def create_sandbox(
        self,
        template: str | None = None,
        namespace: str = DEFAULT_SANDBOX_NAMESPACE,
        *,
        warmpool: str | None = None,
        actor_id: str | None = None,
    ) -> SubstrateActor:
        """Create an ephemeral Judge Actor from the Golden Snapshot, attach its EgressPolicy, and wait for /health."""
        resolved_template = template or warmpool or DEFAULT_SANDBOX_TEMPLATE
        resolved_actor_id = actor_id or f"judge-{uuid.uuid4().hex[:8]}"

        actor_proc = self._run_cli(
            [
                "create",
                "actor",
                resolved_actor_id,
                "--template",
                resolved_template,
                "-a",
                namespace,
            ]
        )
        if actor_proc.returncode != 0:
            stderr = (actor_proc.stderr or "").strip()
            raise RuntimeError(
                f"Failed to create Judge Actor {resolved_actor_id}: {stderr}"
            )

        policy_json = json.dumps(build_egress_policy_document(namespace))
        policy_proc = self._run_cli(
            [
                "create",
                "egress-policy",
                resolved_actor_id,
                "-a",
                namespace,
                "-f",
                "-",
            ],
            input_text=policy_json,
        )
        if policy_proc.returncode != 0:
            stderr = (policy_proc.stderr or "").strip()
            self._delete_actor_and_policy(resolved_actor_id, namespace)
            raise RuntimeError(
                f"Failed to create EgressPolicy for {resolved_actor_id}: {stderr}"
            )

        actor = SubstrateActor(
            actor_id=resolved_actor_id,
            namespace=namespace,
            template=resolved_template,
            client=self,
        )
        try:
            self._wait_for_health(actor)
        except Exception:
            actor.terminate()
            raise
        return actor


SubstrateSandboxClient = SubstrateActorClient
