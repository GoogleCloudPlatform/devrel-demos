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
import ssl
from unittest.mock import MagicMock, patch
import pytest

from src.adapters.outbound.sandbox_utils import (
    DEFAULT_ROUTER_URL,
    DEFAULT_TUNNEL_URL,
    SubstrateActorClient,
    get_sandbox_client,
)


def test_default_router_url_points_at_atenet_router():
    assert DEFAULT_ROUTER_URL == "https://atenet-router.ate-system.svc:443"
    assert DEFAULT_TUNNEL_URL == "http://localhost:8080"


def test_router_is_default_method():
    with patch.dict(os.environ, {}, clear=True):
        client = get_sandbox_client()
    assert isinstance(client, SubstrateActorClient)
    assert client.connection_method == "router"
    assert client.api_url == DEFAULT_ROUTER_URL


def test_router_method_explicit():
    with patch.dict(os.environ, {"SANDBOX_CONNECTION_METHOD": "router"}, clear=True):
        client = get_sandbox_client()
    assert isinstance(client, SubstrateActorClient)
    assert client.connection_method == "router"
    assert client.api_url == DEFAULT_ROUTER_URL


def test_router_method_url_override():
    with patch.dict(
        os.environ,
        {
            "SANDBOX_CONNECTION_METHOD": "router",
            "SANDBOX_ROUTER_URL": "https://atenet-router.ate-system.svc:443",
        },
        clear=True,
    ):
        client = get_sandbox_client()
    assert isinstance(client, SubstrateActorClient)
    assert client.connection_method == "router"
    assert client.api_url == "https://atenet-router.ate-system.svc:443"


def test_method_is_case_insensitive():
    with patch.dict(os.environ, {"SANDBOX_CONNECTION_METHOD": "ROUTER"}, clear=True):
        client = get_sandbox_client()
    assert isinstance(client, SubstrateActorClient)
    assert client.connection_method == "router"


def test_tunnel_method():
    with patch.dict(os.environ, {"SANDBOX_CONNECTION_METHOD": "tunnel"}, clear=True):
        client = get_sandbox_client()
    assert isinstance(client, SubstrateActorClient)
    assert client.connection_method == "tunnel"
    assert client.api_url == DEFAULT_TUNNEL_URL
    assert client.build_ssl_context() is None


@pytest.mark.parametrize(
    "method",
    ["gateway", "router_dns", "in_cluster_dns", "in_cluster_ip", "bogus"],
)
def test_unknown_or_removed_methods_raise(method):
    with patch.dict(os.environ, {"SANDBOX_CONNECTION_METHOD": method}, clear=True):
        with pytest.raises(
            ValueError, match=f"Unknown SANDBOX_CONNECTION_METHOD: {method}"
        ):
            get_sandbox_client()


def test_build_ssl_context_loads_mtls_bundles_when_present(tmp_path):
    cert_file = tmp_path / "credential-bundle.pem"
    trust_file = tmp_path / "trust-bundle.pem"
    cert_file.write_text("-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----\n")
    trust_file.write_text("-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----\n")

    client = SubstrateActorClient(
        router_url=DEFAULT_ROUTER_URL,
        connection_method="router",
        client_cert_file=str(cert_file),
        trust_bundle_file=str(trust_file),
    )

    fake_ctx = MagicMock(spec=ssl.SSLContext)
    with patch("ssl.create_default_context", return_value=fake_ctx) as mock_create_ctx:
        ctx = client.build_ssl_context()

    assert ctx is fake_ctx
    mock_create_ctx.assert_called_once_with(
        ssl.Purpose.SERVER_AUTH, cafile=str(trust_file)
    )
    fake_ctx.load_cert_chain.assert_called_once_with(certfile=str(cert_file))


def test_create_sandbox_provisions_actor_egress_policy_waits_for_health_and_terminates():
    import json
    import re
    import subprocess
    import httpx

    cli_calls: list[tuple[list[str], str | None]] = []

    def fake_runner(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        cli_calls.append((args, input_text))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    health_attempts = 0
    seen_headers: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal health_attempts
        seen_headers.append(request.headers)
        if request.url.path == "/health":
            health_attempts += 1
            if health_attempts == 1:
                return httpx.Response(503, json={"status": "waking"})
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404)

    http_client = httpx.Client(
        base_url="https://atenet-router.ate-system.svc.cluster.local:443",
        transport=httpx.MockTransport(handler),
    )

    client = SubstrateActorClient(
        router_url="https://atenet-router.ate-system.svc.cluster.local:443",
        connection_method="router",
        token_file="/run/router-client/ate-api-token",
        api_endpoint="ate-api.ate-system.svc:443",
        http_client=http_client,
        command_runner=fake_runner,
        poll_interval=0.001,
    )

    actor = client.create_sandbox(template="judge-sandbox", namespace="hackathon-judge")

    assert re.fullmatch(r"judge-[0-9a-f]{8}", actor.actor_id)
    assert actor.name == actor.actor_id
    assert len(cli_calls) == 2

    create_actor_cmd, create_actor_stdin = cli_calls[0]
    assert create_actor_cmd == [
        "kubectl-ate",
        "create",
        "actor",
        actor.actor_id,
        "--template",
        "judge-sandbox",
        "-a",
        "hackathon-judge",
        "--token-file",
        "/run/router-client/ate-api-token",
        "--endpoint",
        "ate-api.ate-system.svc:443",
    ]
    assert create_actor_stdin is None

    create_egress_cmd, create_egress_stdin = cli_calls[1]
    assert create_egress_cmd == [
        "kubectl-ate",
        "create",
        "egress-policy",
        actor.actor_id,
        "-a",
        "hackathon-judge",
        "-f",
        "-",
        "--token-file",
        "/run/router-client/ate-api-token",
        "--endpoint",
        "ate-api.ate-system.svc:443",
    ]
    assert create_egress_stdin is not None
    policy_doc = json.loads(create_egress_stdin)
    assert policy_doc == {
        "rules": [
            {
                "http": {
                    "hostnames": [
                        "agent.hackathon-judge.svc.cluster.local",
                        "agent.hackathon-judge.svc",
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

    assert health_attempts == 2
    for hdrs in seen_headers:
        assert hdrs["X-Ate-Target-Atespace"] == "hackathon-judge"
        assert hdrs["X-Ate-Target-Namespace"] == "hackathon-judge"
        assert hdrs["X-Ate-Target-Actor"] == actor.actor_id
        assert hdrs["X-Ate-Target-Name"] == actor.actor_id
        assert hdrs["X-Ate-Target-Port"] == "80"
        assert hdrs["ate-target-actor"] == f"hackathon-judge/{actor.actor_id}"

    # Verify terminate() deletes egress-policy and actor and suppresses cleanup errors
    def failing_delete_runner(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        cli_calls.append((args, input_text))
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="not found")

    client.command_runner = failing_delete_runner
    actor.terminate()

    assert len(cli_calls) == 4
    assert cli_calls[2][0][:6] == [
        "kubectl-ate",
        "delete",
        "egress-policy",
        actor.actor_id,
        "-a",
        "hackathon-judge",
    ]
    assert cli_calls[3][0][:6] == [
        "kubectl-ate",
        "delete",
        "actor",
        actor.actor_id,
        "-a",
        "hackathon-judge",
    ]


def test_actor_commands_run_polls_async_execution_and_files_write_read():
    import json
    import subprocess
    import httpx

    def fake_runner(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    status_polls = 0
    uploaded_files: dict[str, str] = {}
    recorded_requests: list[tuple[str, str, dict[str, str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal status_polls
        recorded_requests.append(
            (request.method, request.url.path, dict(request.headers))
        )
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.method == "POST" and request.url.path == "/execute/start":
            body = json.loads(request.content.decode("utf-8"))
            assert body["command"] == "git clone 'https://github.com/example/repo' repo"
            assert body["timeout"] == 300
            return httpx.Response(200, json={"job_id": "job-123", "status": "running"})
        if request.method == "GET" and request.url.path == "/execute/status/job-123":
            status_polls += 1
            if status_polls < 3:
                return httpx.Response(
                    200,
                    json={
                        "job_id": "job-123",
                        "status": "running",
                        "stdout": "",
                        "stderr": "",
                        "exit_code": None,
                    },
                )
            return httpx.Response(
                200,
                json={
                    "job_id": "job-123",
                    "status": "completed",
                    "stdout": "cloned ok\n",
                    "stderr": "",
                    "exit_code": 0,
                },
            )
        if request.method == "POST" and request.url.path == "/upload":
            path_param = request.url.params.get("path")
            assert path_param is not None
            raw_body = request.content.decode("utf-8", errors="replace")
            if "# Criteria" in raw_body:
                uploaded_files[path_param] = "# Criteria"
            return httpx.Response(200, json={"message": "uploaded"})
        if request.method == "GET" and request.url.path == "/download/evaluation.json":
            return httpx.Response(200, text='{"total_score": 9.5}')
        return httpx.Response(404)

    http_client = httpx.Client(
        base_url="https://atenet-router.ate-system.svc.cluster.local:443",
        transport=httpx.MockTransport(handler),
    )

    client = SubstrateActorClient(
        router_url="https://atenet-router.ate-system.svc.cluster.local:443",
        connection_method="router",
        http_client=http_client,
        command_runner=fake_runner,
        poll_interval=0.001,
    )

    actor = client.create_sandbox(
        template="judge-sandbox",
        namespace="hackathon-judge",
        actor_id="judge-deadbeef",
    )

    cmd_res = actor.commands.run(
        "git clone 'https://github.com/example/repo' repo", timeout=300
    )
    assert cmd_res.exit_code == 0
    assert cmd_res.stdout == "cloned ok\n"
    assert cmd_res.stderr == ""
    assert status_polls == 3

    actor.files.write("criteria.md", "# Criteria")
    assert uploaded_files.get("criteria.md") == "# Criteria"

    eval_json = actor.files.read("evaluation.json")
    assert eval_json == '{"total_score": 9.5}'

    for _, _, hdrs in recorded_requests:
        assert hdrs["x-ate-target-atespace"] == "hackathon-judge"
        assert hdrs["x-ate-target-namespace"] == "hackathon-judge"
        assert hdrs["x-ate-target-actor"] == "judge-deadbeef"
        assert hdrs["x-ate-target-name"] == "judge-deadbeef"
        assert hdrs["x-ate-target-port"] == "80"
        assert hdrs["ate-target-actor"] == "hackathon-judge/judge-deadbeef"


def test_actor_commands_run_raises_timeout_when_job_exceeds_deadline():
    import subprocess
    import httpx

    def fake_runner(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        if request.url.path == "/execute/start":
            return httpx.Response(200, json={"job_id": "job-slow", "status": "running"})
        if request.url.path == "/execute/status/job-slow":
            return httpx.Response(
                200,
                json={
                    "job_id": "job-slow",
                    "status": "running",
                    "stdout": "",
                    "stderr": "",
                    "exit_code": None,
                },
            )
        return httpx.Response(404)

    http_client = httpx.Client(
        base_url="https://atenet-router.ate-system.svc.cluster.local:443",
        transport=httpx.MockTransport(handler),
    )
    client = SubstrateActorClient(
        router_url="https://atenet-router.ate-system.svc.cluster.local:443",
        http_client=http_client,
        command_runner=fake_runner,
        poll_interval=0.005,
    )
    actor = client.create_sandbox(actor_id="judge-timeout1")

    with pytest.raises(TimeoutError, match="Command timed out"):
        actor.commands.run("sleep 999", timeout=0.02)


def test_end_to_end_substrate_actor_client_against_real_agent_sandbox_app(
    tmp_path, monkeypatch
):
    """End-to-end integration test driving SubstrateActorClient against the real agent-sandbox FastAPI app."""
    import importlib.util
    import json
    from pathlib import Path
    import subprocess
    from fastapi.testclient import TestClient
    import httpx

    monkeypatch.setenv("SANDBOX_DIR", str(tmp_path))
    sandbox_main_path = (
        Path(__file__).resolve().parents[3] / "agent-sandbox" / "app" / "main.py"
    )
    spec = importlib.util.spec_from_file_location(
        "agent_sandbox_main_e2e", sandbox_main_path
    )
    assert spec is not None and spec.loader is not None
    sandbox_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sandbox_mod)

    test_client = TestClient(sandbox_mod.app)

    recorded_headers: list[dict[str, str]] = []

    def asgi_bridge_handler(request: httpx.Request) -> httpx.Response:
        recorded_headers.append(dict(request.headers))
        resp = test_client.request(
            method=request.method,
            url=str(request.url.raw_path.decode("ascii")),
            headers=dict(request.headers),
            content=request.content,
        )
        return httpx.Response(
            status_code=resp.status_code,
            headers=dict(resp.headers),
            content=resp.content,
        )

    http_client = httpx.Client(
        base_url="https://atenet-router.ate-system.svc.cluster.local:443",
        transport=httpx.MockTransport(asgi_bridge_handler),
    )

    cli_calls: list[tuple[list[str], str | None]] = []

    def fake_kubectl_ate(
        args: list[str], input_text: str | None = None
    ) -> subprocess.CompletedProcess:
        cli_calls.append((args, input_text))
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="ok", stderr=""
        )

    client = SubstrateActorClient(
        router_url="https://atenet-router.ate-system.svc.cluster.local:443",
        http_client=http_client,
        command_runner=fake_kubectl_ate,
        poll_interval=0.01,
    )

    actor = client.create_sandbox(
        template="judge-sandbox",
        namespace="hackathon-judge",
    )
    try:
        actor.files.write("criteria.md", "# Rubric\n- Quality (10)")
        actor.files.write("prompt.md", "Evaluate repo/")
        assert (tmp_path / "criteria.md").read_text(encoding="utf-8") == "# Rubric\n- Quality (10)"

        # Run a real command through POST /execute/start + GET /execute/status/{job_id}
        py_cmd = (
            "env MODEL_PROXY_BASE_URL=http://agent.hackathon-judge.svc.cluster.local:8000/vertex-proxy "
            'python3 -c \'import json, os, pathlib; '
            'pathlib.Path("evaluation.json").write_text(json.dumps({"proxy": os.environ["MODEL_PROXY_BASE_URL"], "total_score": 9.8})); '
            'print("judge done")\''
        )
        result = actor.commands.run(py_cmd, timeout=30)
        assert result.exit_code == 0
        assert "judge done" in result.stdout

        downloaded = json.loads(actor.files.read("evaluation.json"))
        assert downloaded == {
            "proxy": "http://agent.hackathon-judge.svc.cluster.local:8000/vertex-proxy",
            "total_score": 9.8,
        }
    finally:
        actor.terminate()

    assert [c[0][:3] for c in cli_calls] == [
        ["kubectl-ate", "create", "actor"],
        ["kubectl-ate", "create", "egress-policy"],
        ["kubectl-ate", "delete", "egress-policy"],
        ["kubectl-ate", "delete", "actor"],
    ]
    assert len(recorded_headers) >= 5
    for hdrs in recorded_headers:
        assert hdrs["x-ate-target-actor"] == actor.actor_id
        assert hdrs["x-ate-target-atespace"] == "hackathon-judge"
        assert hdrs["x-ate-target-port"] == "80"


def test_agent_packaging_removes_k8s_agent_sandbox_and_installs_kubectl_ate():
    from pathlib import Path

    agent_dir = Path(__file__).resolve().parents[2]
    pyproject_text = (agent_dir / "pyproject.toml").read_text(encoding="utf-8")
    dockerfile_text = (agent_dir / "Dockerfile").read_text(encoding="utf-8")

    assert "k8s-agent-sandbox" not in pyproject_text
    assert "kubectl-ate" in dockerfile_text
    assert "v1.0.0/kubectl-ate-linux-amd64" in dockerfile_text
    assert "kubectl" in dockerfile_text


def test_create_sandbox_cleans_up_actor_if_egress_policy_creation_fails():
    import subprocess

    cli_calls: list[list[str]] = []

    def runner(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
        cli_calls.append(args)
        if args[:3] == ["kubectl-ate", "create", "egress-policy"]:
            return subprocess.CompletedProcess(
                args=args, returncode=1, stdout="", stderr="policy rejected"
            )
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="ok", stderr=""
        )

    client = SubstrateActorClient(command_runner=runner, poll_interval=0.001)

    with pytest.raises(RuntimeError, match="Failed to create EgressPolicy"):
        client.create_sandbox(
            template="judge-sandbox",
            namespace="hackathon-judge",
            actor_id="judge-badpol01",
        )

    assert [c[:4] for c in cli_calls] == [
        ["kubectl-ate", "create", "actor", "judge-badpol01"],
        ["kubectl-ate", "create", "egress-policy", "judge-badpol01"],
        ["kubectl-ate", "delete", "egress-policy", "judge-badpol01"],
        ["kubectl-ate", "delete", "actor", "judge-badpol01"],
    ]




