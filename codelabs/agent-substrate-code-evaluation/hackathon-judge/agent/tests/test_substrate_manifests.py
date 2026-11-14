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

from pathlib import Path
import subprocess
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
K8S_DIR = REPO_ROOT / "k8s"


def _load_yaml_docs(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    return [doc for doc in yaml.safe_load_all(content) if doc is not None]


def test_deprecated_agent_sandbox_manifests_are_removed():
    deprecated_files = [
        "sandbox-claim-template.yaml",
        "sandbox-networkpolicy.yaml",
        "sandbox_router.yaml",
        "sandbox-warmpool.yaml",
        "sandbox.yaml",
        "sandbox-template.yaml",
        "sandbox-router.yaml",
    ]
    for filename in deprecated_files:
        assert not (K8S_DIR / filename).exists(), f"Deprecated manifest {filename} should be removed"


def test_namespace_manifest_enables_ate_api_access():
    docs = _load_yaml_docs(K8S_DIR / "namespace.yaml")
    assert len(docs) == 1
    ns = docs[0]
    assert ns["kind"] == "Namespace"
    assert ns["metadata"]["name"] == "hackathon-judge"
    assert ns["metadata"].get("labels", {}).get("ate.dev/api-access") == "true"


def test_service_account_manifest_excludes_sandbox_sa_for_zero_credential_actors():
    docs = _load_yaml_docs(K8S_DIR / "service-account.yaml")
    names = [doc["metadata"]["name"] for doc in docs if doc.get("kind") == "ServiceAccount"]
    assert names == ["hackathon-judge-sa"]
    assert "hackathon-judge-sandbox-sa" not in names


def test_rbac_manifest_grants_substrate_and_core_permissions_to_orchestrator_sa():
    docs = _load_yaml_docs(K8S_DIR / "rbac.yaml")
    roles = [d for d in docs if d.get("kind") == "Role"]
    bindings = [d for d in docs if d.get("kind") == "RoleBinding"]
    assert len(roles) >= 1
    assert len(bindings) >= 1

    role = roles[0]
    rules = role.get("rules", [])
    ate_resources: set[str] = set()
    core_resources: set[str] = set()
    for rule in rules:
        api_groups = rule.get("apiGroups", [])
        if "ate.dev" in api_groups:
            ate_resources.update(rule.get("resources", []))
        if "" in api_groups:
            core_resources.update(rule.get("resources", []))

    assert {"actors", "actortemplates", "workerpools", "egresspolicies"}.issubset(ate_resources)
    assert {"pods", "pods/exec", "services"}.issubset(core_resources)

    binding = bindings[0]
    subjects = binding.get("subjects", [])
    assert any(
        s.get("kind") == "ServiceAccount"
        and s.get("name") == "hackathon-judge-sa"
        and s.get("namespace") == "hackathon-judge"
        for s in subjects
    )


def test_configmap_configures_substrate_template_and_router_connection():
    docs = _load_yaml_docs(K8S_DIR / "configmap.yaml")
    assert len(docs) == 1
    data = docs[0].get("data", {})
    assert data.get("SANDBOX_TEMPLATE") == "judge-sandbox"
    assert data.get("SANDBOX_WARMPOOL") == "judge-sandbox"
    assert data.get("SANDBOX_NAMESPACE") == "hackathon-judge"
    assert data.get("SANDBOX_CONNECTION_METHOD") == "router"


def _parse_memory_mib(val: str | int) -> float:
    if isinstance(val, int):
        return val / (1024 * 1024)
    s = str(val).strip()
    if s.endswith("Gi"):
        return float(s[:-2]) * 1024
    if s.endswith("Mi"):
        return float(s[:-2])
    return float(s) / (1024 * 1024)


def test_substrate_manifest_workerpool_and_actor_template_headroom_and_fields():
    docs = _load_yaml_docs(K8S_DIR / "substrate.yaml")
    assert len(docs) == 1
    wp = docs[0]
    assert wp["kind"] == "WorkerPool"
    assert wp["apiVersion"] == "ate.dev/v1"
    assert wp["metadata"]["name"] == "judge-workerpool"
    assert wp["metadata"]["namespace"] == "hackathon-judge"

    spec = wp["spec"]
    assert spec["replicas"] == 3
    assert {"name": "gvisor"} in spec["sandboxClasses"]
    assert spec["template"]["labels"]["workload"] == "hackathon-judge"

    limits = spec["template"]["resources"]["limits"]
    requests = spec["template"]["resources"]["requests"]
    assert limits["cpu"] == "2000m"
    assert requests["cpu"] == "1000m"
    wp_limit_mib = _parse_memory_mib(limits["memory"])
    wp_req_mib = _parse_memory_mib(requests["memory"])
    assert wp_limit_mib >= 4096 + 64
    assert wp_req_mib >= 4096 + 64

    # Verify k8s/actortemplate.yaml is the single source of truth for ActorTemplate
    at_standalone = _load_yaml_docs(K8S_DIR / "actortemplate.yaml")
    assert len(at_standalone) == 1
    tmpl = at_standalone[0]

    assert tmpl["metadata"]["name"] == "judge-sandbox"
    assert tmpl["metadata"]["atespace"] == "hackathon-judge"
    assert tmpl["workerSelector"]["matchLabels"]["workload"] == "hackathon-judge"
    assert tmpl["resources"]["limits"]["cpuMillicores"] == 2000
    assert tmpl["resources"]["limits"]["memoryBytes"] == 4294967296
    assert (
        wp_limit_mib - _parse_memory_mib(tmpl["resources"]["limits"]["memoryBytes"])
        >= 64
    )
    assert tmpl["snapshotConfig"]["preferredFidelity"] == "SNAPSHOT_FIDELITY_MEMORY"

    # Verify trust bundles (egress-mitm.ate.dev and system-roots.ate.dev)
    trust_names: set[str] = set(tmpl.get("trustBundles", []))
    for vol in tmpl.get("volumes", []):
        for ds in vol.get("systemInfo", {}).get("dataSources", []):
            trust_names.update(ds.get("trustBundle", {}).get("names", []))
    assert {"egress-mitm.ate.dev", "system-roots.ate.dev"}.issubset(trust_names)

    container = tmpl["containers"][0]
    assert container["image"] == "${AGENT_SANDBOX_IMAGE}"
    env_map = {e["name"]: e["value"] for e in container.get("env", [])}
    assert "GOOGLE_CLOUD_PROJECT" in env_map
    assert env_map.get("GOOGLE_CLOUD_LOCATION") == "global"
    assert env_map.get("SANDBOX_DIR") == "/home/sandbox/app"
    assert (
        env_map.get("MODEL_PROXY_BASE_URL")
        == "http://agent.hackathon-judge.svc.cluster.local:8000/vertex-proxy"
    )
    assert env_map.get("JUDGE_MODEL") == ""
    assert env_map.get("SSL_CERT_FILE") == "/run/ate/trust-bundle.pem"

    probe = container["wakeupProbe"]["httpGet"]
    assert probe["path"] == "/health"
    assert probe["port"] == 80
    assert "NET_BIND_SERVICE" in container["securityContext"]["capabilities"]["add"]


def test_access_policy_manifest_grants_editor_role_to_orchestrator_sa():
    docs = _load_yaml_docs(K8S_DIR / "access-policy.yaml")
    assert len(docs) == 1
    policy = docs[0]
    assert policy["metadata"]["name"] == "default"
    bindings = policy["bindings"]
    assert any(
        b.get("role") == "editor"
        and "user:system:serviceaccount:hackathon-judge:hackathon-judge-sa"
        in b.get("members", [])
        for b in bindings
    )


def test_agent_manifest_exposes_model_proxy_service_and_mounts_router_client_mtls():
    docs = _load_yaml_docs(K8S_DIR / "agent.yaml")
    services = [d for d in docs if d.get("kind") == "Service"]
    deployments = [d for d in docs if d.get("kind") == "Deployment"]
    assert len(services) == 1
    assert len(deployments) == 1

    svc = services[0]
    assert svc["metadata"]["name"] == "agent"
    assert svc["metadata"]["namespace"] == "hackathon-judge"
    assert svc["spec"]["selector"] == {"app": "agent"}
    ports = {p["port"]: p["targetPort"] for p in svc["spec"]["ports"]}
    assert ports.get(8000) == 8000
    assert ports.get(8082) == 8000

    deploy = deployments[0]
    pod_spec = deploy["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]
    env_names = {e["name"] for e in container.get("env", [])}
    assert "SANDBOX_TEMPLATE" in env_names

    mounts = {m["name"]: m["mountPath"] for m in container.get("volumeMounts", [])}
    assert mounts.get("router-client") == "/run/router-client"

    volumes = {v["name"]: v for v in pod_spec.get("volumes", [])}
    assert "router-client" in volumes
    sources = volumes["router-client"]["projected"]["sources"]

    sa_tokens = [s["serviceAccountToken"] for s in sources if "serviceAccountToken" in s]
    assert any(
        t.get("audience") == "api.ate-system.svc" and t.get("path") == "ate-api-token"
        for t in sa_tokens
    )

    trust_bundles = [s["clusterTrustBundle"] for s in sources if "clusterTrustBundle" in s]
    assert any(
        tb.get("signerName") == "servicedns.podcert.ate.dev/identity"
        and tb.get("labelSelector", {}).get("matchLabels", {}).get("podcert.ate.dev/canarying")
        == "live"
        and tb.get("path") == "trust-bundle.pem"
        for tb in trust_bundles
    )

    pod_certs = [s["podCertificate"] for s in sources if "podCertificate" in s]
    assert any(
        pc.get("signerName") == "podidentity.podcert.ate.dev/identity"
        and pc.get("keyType") == "ECDSAP256"
        and pc.get("credentialBundlePath") == "credential-bundle.pem"
        for pc in pod_certs
    )


def test_agent_sandbox_dockerfile_sets_home_env():
    dockerfile = (REPO_ROOT / "agent-sandbox" / "Dockerfile").read_text(encoding="utf-8")
    assert "ENV HOME=/home/sandbox" in dockerfile


def test_shell_scripts_pass_bash_syntax_check():
    for script_name in ("deploy.sh", "deploy-all.sh", "destroy.sh", "setup-env.sh"):
        script_path = REPO_ROOT / script_name
        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{script_name} failed bash -n: {result.stderr}"


def test_deploy_scripts_provision_gke_standard_gvisor_and_substrate_v1():
    for script_name in ("deploy.sh", "deploy-all.sh"):
        content = (REPO_ROOT / script_name).read_text(encoding="utf-8")
        # GKE Standard 1.37 cluster in RAPID channel with nested virtualization and Gateway API
        assert 'clusters create "$CLUSTER_NAME"' in content
        assert "--release-channel=rapid" in content
        assert "--machine-type=c3-standard-4" in content
        assert "--enable-nested-virtualization" in content
        assert "--gateway-api=standard" in content
        assert '--workload-pool="${GOOGLE_CLOUD_PROJECT}.svc.id.goog"' in content
        assert "clusters create-auto" not in content

        # Agent Substrate v1.0.0 installation & SPIFFE allowlist
        assert 'SUBSTRATE_VERSION="v1.0.0"' in content
        assert "kubectl-ate" in content
        assert "spiffe://cluster.local/ns/hackathon-judge/sa/hackathon-judge-sa" in content
        assert "ate-snapshot-transfer" in content

        # Zero-credential Judge Actors (no sandbox SA IAM binding) and no legacy agent-sandbox
        assert "hackathon-judge-sandbox-sa" not in content
        assert "kubernetes-sigs/agent-sandbox" not in content
        assert "sandbox_router.yaml" not in content
        assert "sandbox-networkpolicy.yaml" not in content
        assert "sandbox-claim-template.yaml" not in content
        assert "sandbox-warmpool.yaml" not in content

        # Applies Substrate manifests and waits for Golden Snapshot
        assert "k8s/substrate.yaml" in content
        assert "awk '/^---$/{exit}'" not in content
        assert "create atespace" in content
        assert "AGENT_SANDBOX_DIGEST" in content
        assert "AGENT_SANDBOX_IMAGE" in content
        assert "k8s/access-policy.yaml" in content
        assert "k8s/actortemplate.yaml" in content
        assert "goldenTag" in content
        assert 'if [ -z "$GOLDEN_TAG" ]; then' in content


def test_destroy_script_cleans_up_substrate_resources():
    content = (REPO_ROOT / "destroy.sh").read_text(encoding="utf-8")
    assert "-ate-snapshots" in content
    assert "ate-snapshot-transfer" in content
    assert "-stabby" not in content
    assert "GKE Autopilot" not in content
    assert "agent-sandbox" not in content


def test_documentation_describes_agent_substrate_and_excludes_legacy_sandbox_crds():
    doc_rels = ["README.md", "k8s/README.md"]
    if (REPO_ROOT / "index.lab.md").exists():
        doc_rels.append("index.lab.md")
    for doc_rel in doc_rels:
        content = (REPO_ROOT / doc_rel).read_text(encoding="utf-8")
        assert "Agent Substrate" in content, f"{doc_rel} must describe Agent Substrate"
        assert "WorkerPool" in content, f"{doc_rel} must describe WorkerPool"
        assert "ActorTemplate" in content, f"{doc_rel} must describe ActorTemplate"
        assert "Golden Snapshot" in content, f"{doc_rel} must describe Golden Snapshot"
        assert "Judge Actor" in content, f"{doc_rel} must describe Judge Actor"
        assert "EgressPolicy" in content or "Egress Policy" in content, f"{doc_rel} must describe EgressPolicy"
        assert "atenet-router" in content, f"{doc_rel} must describe atenet-router"
        assert "Model Proxy" in content, f"{doc_rel} must describe Model Proxy"

    forbidden_legacy_terms = (
        "kubernetes-sigs/agent-sandbox",
        "SandboxWarmPool",
        "SandboxClaim",
        "sandbox-claim-template.yaml",
        "sandbox-warmpool.yaml",
        "sandbox_router.yaml",
        "sandbox-networkpolicy.yaml",
        "hackathon-judge-sandbox-sa",
    )
    all_doc_rels = [
        *doc_rels,
        "agent/README.md",
        "agent-sandbox/README.md",
    ]
    for doc_rel in all_doc_rels:
        content = (REPO_ROOT / doc_rel).read_text(encoding="utf-8")
        for term in forbidden_legacy_terms:
            assert term not in content, f"{doc_rel} still contains deprecated term {term!r}"

    sandbox_readme = (REPO_ROOT / "agent-sandbox" / "README.md").read_text(encoding="utf-8")
    assert "/execute/start" in sandbox_readme
    assert "/execute/status/" in sandbox_readme
    assert "/health" in sandbox_readme


def test_no_retired_branding_or_hardcoded_personal_identifiers_in_docs_and_manifests():
    target_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "k8s" / "README.md",
        REPO_ROOT / "agent" / "README.md",
        REPO_ROOT / "agent-sandbox" / "README.md",
        REPO_ROOT / "deploy.sh",
        REPO_ROOT / "deploy-all.sh",
        REPO_ROOT / "destroy.sh",
        REPO_ROOT / "setup-env.sh",
        REPO_ROOT / ".env.example",
        *sorted(K8S_DIR.glob("*.yaml")),
    ]
    if (REPO_ROOT / "index.lab.md").exists():
        target_files.append(REPO_ROOT / "index.lab.md")
    for path in target_files:
        content = path.read_text(encoding="utf-8")
        lower = content.lower()
        assert "vertex ai" not in lower, f"{path.relative_to(REPO_ROOT)} contains retired branding 'Vertex AI'"
        assert "mofilabs" not in lower, f"{path.relative_to(REPO_ROOT)} contains personal project identifier 'mofilabs'"
        assert "ate-cluster" not in lower, f"{path.relative_to(REPO_ROOT)} contains personal cluster identifier 'ate-cluster'"



