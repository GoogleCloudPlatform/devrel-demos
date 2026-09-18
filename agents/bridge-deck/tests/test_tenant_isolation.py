#!/usr/bin/env python3
"""
Test Suite for Track 2: Tenant Context Manager, Storage Abstraction, and Data Isolation.
Verifies that multiple tenants operate in strict isolation with zero cross-tenant contamination.
"""

import os
import sys
import json
import shutil
import tempfile
import io
import fnmatch
import unittest
import unittest.mock
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.tenant import (
    sanitize_tenant_id,
    get_tenant_dir,
    ensure_tenant_initialized,
    TenantRegistry,
    DEFAULT_TENANT_ID
)
import bridge_runner


class TestTenantIsolation(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_bridge_tenants_"))
        self.seed_dir = self.test_dir / "seed"
        self.seed_dir.mkdir(parents=True, exist_ok=True)
        self.seed_agents = self.seed_dir / "agents"
        self.seed_agents.mkdir(parents=True, exist_ok=True)

        schema_src = ROOT_DIR / "agents" / "_schema.json"
        if not schema_src.exists():
            schema_src = ROOT_DIR / "seed" / "agents" / "_schema.json"
        if schema_src.exists():
            shutil.copy(schema_src, self.seed_agents / "_schema.json")

        for fname in ["profiles.json", "projects.json", "engines.json", "models.json", "skill_usage.json"]:
            src_f = ROOT_DIR / "seed" / fname
            dst_f = self.seed_dir / fname
            if src_f.exists():
                shutil.copy2(src_f, dst_f)

        self._old_gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        os.environ["GOOGLE_CLOUD_PROJECT"] = "test-governance-project"

        # Populate starter seed files in mock environment with neutral archetypes
        self.seed_profiles = {
            "profiles": [
                {
                    "id": "lead",
                    "name": "Team Lead",
                    "role": "Project Lead & Coordinator",
                    "engine": "human",
                    "model": "Human Contributor",
                    "access_read": ["./workspace"],
                    "access_write": ["./workspace"],
                    "resume": []
                },
                {
                    "id": "architect",
                    "name": "Architect",
                    "role": "Systems Architect",
                    "engine": "antigravity-queue",
                    "model": "gemini-3.7-flash",
                    "access_read": ["./workspace"],
                    "access_write": ["./workspace"],
                    "resume": []
                },
                {
                    "id": "engineer",
                    "name": "Engineer",
                    "role": "Implementation Engineer",
                    "engine": "google-adk",
                    "model": "gemini-3.7-flash",
                    "access_read": ["./workspace"],
                    "access_write": ["./workspace"],
                    "resume": []
                },
                {
                    "id": "advisor",
                    "name": "Advisor",
                    "role": "Technical Advisor",
                    "engine": "antigravity-queue",
                    "model": "claude-opus-5",
                    "access_read": ["./workspace"],
                    "access_write": [],
                    "resume": []
                }
            ]
        }
        with open(self.seed_dir / "profiles.json", "w", encoding="utf-8") as f:
            json.dump(self.seed_profiles, f, indent=2)

        self.seed_projects = {
            "projects": [
                {
                    "id": "starter_project",
                    "name": "Team Workspace",
                    "directories": ["./workspace"],
                    "members": ["lead", "architect", "engineer", "advisor"],
                    "allow_subagents": True
                }
            ]
        }
        with open(self.seed_dir / "projects.json", "w", encoding="utf-8") as f:
            json.dump(self.seed_projects, f, indent=2)

        self.seed_engines = {
            "engines": [
                {
                    "id": "vertex-ai",
                    "name": "Google Model Garden",
                    "category": "model",
                    "type": "vertex-ai",
                    "provider_types": ["vertex-ai", "vertex-anthropic"],
                    "models": [{"id": "claude-opus-5", "name": "Claude Opus 5"}]
                }
            ]
        }
        with open(self.seed_dir / "engines.json", "w", encoding="utf-8") as f:
            json.dump(self.seed_engines, f, indent=2)

        self.seed_models = {
            "models": [
                {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider_type": "vertex-ai"},
                {"id": "gemini-3.7-flash", "name": "Gemini 3.7 Flash", "provider_type": "google-adk"}
            ]
        }
        with open(self.seed_dir / "models.json", "w", encoding="utf-8") as f:
            json.dump(self.seed_models, f, indent=2)

        advisor_manifest = {
            "id": "advisor",
            "name": "Advisor",
            "role": "Technical Advisor",
            "provider": {"type": "antigravity-queue"},
            "access_read": ["./workspace"],
            "access_write": []
        }
        with open(self.seed_agents / "advisor.agent.json", "w", encoding="utf-8") as f:
            json.dump(advisor_manifest, f, indent=2)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)
        if self._old_gcp_project is not None:
            os.environ["GOOGLE_CLOUD_PROJECT"] = self._old_gcp_project
        else:
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

    def test_repo_seed_templates_are_neutral(self):
        """
        Verifies that:
        1. Operator personal identifiers are 100% eliminated from seed/, core/, providers/, bridge_runner.py, bridge_cli.py, bridge_listener.py, index.html, docs/, README.md, and tests/.
        2. Seed templates (seed/) contain zero specific agent identities (Astra, Vector, Lumen, Nexus, Orion).
        3. Legacy persona references in bridge_runner.py are explicitly inventoried and guarded by a non-growth ratchet.
        """
        self.assertTrue((ROOT_DIR / "seed").exists(), "Repository seed/ directory must exist")
        self.assertTrue((ROOT_DIR / "seed" / "models.json").exists(), "seed/models.json must exist")

        # Construct denylist literals dynamically to prevent self-matching within test code
        OPERATOR_DENYLIST = [
            "".join(["a", "m", "a", "n", "d", "a", " ", "f", "i", "t", "c", "h"]),
            "".join(["/users/", "a", "f", "i", "t", "c", "h"]),
            "".join(["a", "m", "a", "n", "d", "a"]),
            "".join(["f", "i", "t", "c", "h"])
        ]
        SEED_IDENTITY_DENYLIST = ["Astra", "Vector", "Lumen", "Nexus", "Orion"]

        # Dynamically enumerate repository files, deriving exclusions strictly from .gitignore
        gitignore_patterns = [".git"]
        gi_file = ROOT_DIR / ".gitignore"
        if gi_file.exists():
            for line in gi_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    pat = line.rstrip("/")
                    if pat not in gitignore_patterns:
                        gitignore_patterns.append(pat)

        def is_ignored(path: Path) -> bool:
            try:
                rel = path.relative_to(ROOT_DIR)
            except ValueError:
                return False
            for part in rel.parts:
                for pat in gitignore_patterns:
                    if fnmatch.fnmatch(part, pat) or fnmatch.fnmatch(str(rel), pat) or fnmatch.fnmatch(str(rel), pat + "/*"):
                        return True
            return False

        files_to_scan = []
        for root, dirs, files in os.walk(ROOT_DIR):
            root_path = Path(root)
            if is_ignored(root_path):
                dirs[:] = []
                continue
            dirs[:] = [d for d in dirs if not is_ignored(root_path / d)]
            for f in files:
                fp = root_path / f
                if not is_ignored(fp):
                    files_to_scan.append(fp)

        for p in files_to_scan:
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            text_folded = text.casefold()
            # Invariant 1: Operator personal identifiers must never exist anywhere in product code, tests, docs, or seed templates (case-insensitive)
            for lit in OPERATOR_DENYLIST:
                self.assertNotIn(lit.casefold(), text_folded, f"Found prohibited operator literal '{lit}' in {p.relative_to(ROOT_DIR)}")

            # Invariant 2: Seed templates must be completely neutral archetypes
            if p.is_relative_to(ROOT_DIR / "seed"):
                for lit in SEED_IDENTITY_DENYLIST:
                    self.assertNotIn(lit, text, f"Found prohibited agent identity literal '{lit}' in seed template {p.relative_to(ROOT_DIR)}")

        # Invariant 3 (Ratchet): Legacy agent persona references in bridge_runner.py must not grow beyond current inventory
        # Carve-out inventory: Astra (5), Vector (6), Lumen (5), Nexus (2), Orion (2) = 20 total
        runner_text = (ROOT_DIR / "bridge_runner.py").read_text(encoding="utf-8")
        actual_persona_count = sum(runner_text.count(lit) for lit in SEED_IDENTITY_DENYLIST)
        self.assertLessEqual(
            actual_persona_count,
            20,
            f"Legacy agent persona references in bridge_runner.py exceeded ratchet limit (found {actual_persona_count}, max 20)"
        )

    def test_root_contains_no_instance_artifacts(self):
        """
        Verify D67 & D73: The product root contains code and neutral configuration only,
        with zero live instance data artifacts or personal data, and data/tenants/ contains
        no phantom default_workspace or unconfigured seeded shells.
        """
        denylist = [
            ROOT_DIR / "history",
            ROOT_DIR / "pending_queries.json",
            ROOT_DIR / "memory" / "semantic",
            ROOT_DIR / "memory" / "shared",
            ROOT_DIR / "profiles.json",
            ROOT_DIR / "projects.json",
            ROOT_DIR / "models.json",
            ROOT_DIR / "engines.json",
            ROOT_DIR / "skill_usage.json",
            ROOT_DIR / "data" / "tenants" / "default_workspace",
            ROOT_DIR / "data" / "tenants" / "tenant_alpha"
        ]
        for path in denylist:
            self.assertFalse(
                path.exists(),
                f"Root instance artifact '{path.relative_to(ROOT_DIR)}' must not exist in product root"
            )

        # Invariant 4: data/tenants/ must contain only authorized local deployment tenant(s)
        tenants_dir = ROOT_DIR / "data" / "tenants"
        if tenants_dir.exists():
            allowed_tenants = {DEFAULT_TENANT_ID, sanitize_tenant_id(DEFAULT_TENANT_ID)}
            for entry in tenants_dir.iterdir():
                if entry.is_dir():
                    self.assertIn(
                        entry.name,
                        allowed_tenants,
                        f"Unexpected tenant directory '{entry.name}' in product tree"
                    )

        # Invariant 5: Verify .gitignore ignores local instance artifacts and secrets
        gitignore = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")
        for ignored in ["server.log", "data/", "data/tenants/", ".env", "deploy.env", "logs/"]:
            self.assertIn(ignored, gitignore, f".gitignore must contain '{ignored}'")

    def test_git_tracked_files_respect_gitignore(self):
        """
        Verify that no tracked file in git matches any pattern in .gitignore
        (ensures private directories like data/, logs/, deploy.env, .env are never tracked in git).
        """
        import subprocess
        gi_file = ROOT_DIR / ".gitignore"
        self.assertTrue(gi_file.exists(), ".gitignore must exist")
        gi_patterns = [line.strip().rstrip("/") for line in gi_file.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]

        try:
            res = subprocess.run(["git", "ls-files"], cwd=str(ROOT_DIR), capture_output=True, text=True, check=True)
            tracked_files = res.stdout.splitlines()
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            self.skipTest(f"git unavailable: {e}")

        for f in tracked_files:
            p = Path(f)
            for pat in gi_patterns:
                for part in p.parts:
                    self.assertFalse(
                        fnmatch.fnmatch(part, pat) or fnmatch.fnmatch(f, pat) or fnmatch.fnmatch(f, pat + "/*"),
                        f"Tracked git file '{f}' violates .gitignore pattern '{pat}'"
                    )

    def test_sanitize_tenant_id_slugification(self):
        self.assertEqual(sanitize_tenant_id("Acme Corp!"), "acme_corp")
        self.assertEqual(sanitize_tenant_id("../../etc/passwd"), "etcpasswd")
        self.assertEqual(sanitize_tenant_id("org---123__alpha"), "org_123_alpha")
        self.assertEqual(sanitize_tenant_id(None), DEFAULT_TENANT_ID)
        self.assertEqual(sanitize_tenant_id(""), DEFAULT_TENANT_ID)
        self.assertEqual(sanitize_tenant_id("default"), DEFAULT_TENANT_ID)

    def test_auto_initialization_from_seed(self):
        t_dir = ensure_tenant_initialized("alpha_corp", base_dir=self.test_dir)
        self.assertTrue(t_dir.exists())
        self.assertTrue((t_dir / "profiles.json").exists())
        self.assertTrue((t_dir / "projects.json").exists())
        self.assertTrue((t_dir / "engines.json").exists())
        self.assertTrue((t_dir / "models.json").exists())
        self.assertTrue((t_dir / "agents" / "advisor.agent.json").exists())

        with open(t_dir / "profiles.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        profile_ids = [p["id"] for p in data["profiles"]]
        self.assertIn("lead", profile_ids)
        self.assertIn("advisor", profile_ids)

    def test_cross_tenant_data_mutation_isolation(self):
        """
        Verify that mutations in Tenant Alpha (profiles, projects, chat history,
        agent manifests, and 3-tier memory) never leak or cross-contaminate Tenant Beta.
        """
        alpha_dir = ensure_tenant_initialized("tenant_alpha", base_dir=self.test_dir)
        beta_dir = ensure_tenant_initialized("tenant_beta", base_dir=self.test_dir)

        # 1. Mutate Alpha Profiles (Add 'cipher' agent to Alpha only)
        cipher_payload = {
            "id": "cipher",
            "name": "Cipher",
            "role": "Security Specialist",
            "engine": "antigravity-queue",
            "model": "gemini-3.7-flash",
            "access_read": ["./workspace"]
        }
        bridge_runner.save_persona(cipher_payload, bridge_dir=alpha_dir)

        beta_profiles = bridge_runner.load_profiles(bridge_dir=beta_dir)
        beta_ids = [p["id"] for p in beta_profiles["profiles"]]
        self.assertNotIn("cipher", beta_ids)

        # 2. Mutate Alpha Projects (Add 'quantum_core' project to Alpha only)
        alpha_projects, a_gen = bridge_runner.load_projects(bridge_dir=alpha_dir, return_gen=True)
        alpha_projects["projects"].append({
            "id": "quantum_core",
            "name": "Quantum Core Probing",
            "directories": ["./workspaces/quantum"],
            "members": ["cipher"]
        })
        bridge_runner.save_projects(alpha_projects, bridge_dir=alpha_dir, expected_generation=a_gen)

        beta_projects = bridge_runner.load_projects(bridge_dir=beta_dir)
        beta_proj_ids = [p["id"] for p in beta_projects["projects"]]
        self.assertNotIn("quantum_core", beta_proj_ids)

        # 3. Append Transaction to Alpha Chat History
        sample_tx = {
            "id": "tx_alpha_001",
            "timestamp": "2026-08-30T00:00:00Z",
            "mode": "claude_direct",
            "prompt_text": "Secret Alpha Research Query",
            "claude_response": "Confidential Alpha Research Response"
        }
        bridge_runner.append_transaction("starter_project", sample_tx, bridge_dir=alpha_dir)

        alpha_hist = bridge_runner.load_history("starter_project", bridge_dir=alpha_dir)
        beta_hist = bridge_runner.load_history("starter_project", bridge_dir=beta_dir)
        self.assertEqual(len(alpha_hist.get("transactions", [])), 1)
        self.assertEqual(len(beta_hist.get("transactions", [])), 0)

        # 4. Verify Registry and Router Caching per Tenant
        registry = TenantRegistry(base_dir=self.test_dir)
        alpha_router = registry.get_router("tenant_alpha")
        beta_router = registry.get_router("tenant_beta")

        self.assertNotEqual(alpha_router, beta_router)
        self.assertIn("cipher", alpha_router.manifests)
        self.assertNotIn("cipher", beta_router.manifests)

        # 5. Verify 3-Tier Memory Store Isolation
        alpha_mem = registry.get_memory_store("tenant_alpha")
        beta_mem = registry.get_memory_store("tenant_beta")

        alpha_mem.append_semantic_fact("advisor", "Alpha confidential insight")
        alpha_facts = alpha_mem.get_semantic_facts("advisor")
        beta_facts = beta_mem.get_semantic_facts("advisor")

        self.assertEqual(len(alpha_facts), 1)
        self.assertEqual(alpha_facts[0]["fact"], "Alpha confidential insight")
        self.assertEqual(len(beta_facts), 0)

    def test_a2a_dispatcher_isolation_across_tenants(self):
        """
        Verify D69: A2ADispatcher is cached per-tenant and parses mentions strictly
        against that tenant's router manifests.
        """
        alpha_dir = ensure_tenant_initialized("tenant_alpha", base_dir=self.test_dir)
        beta_dir = ensure_tenant_initialized("tenant_beta", base_dir=self.test_dir)

        registry = TenantRegistry(base_dir=self.test_dir)
        alpha_disp = registry.get_dispatcher("tenant_alpha")
        beta_disp = registry.get_dispatcher("tenant_beta")

        self.assertNotEqual(alpha_disp, beta_disp)
        self.assertEqual(alpha_disp.bridge_dir, alpha_dir)
        self.assertEqual(beta_disp.bridge_dir, beta_dir)

        # Add custom agent to Alpha manifests only
        alpha_manifest = {
            "id": "alpha_agent",
            "name": "Alpha Agent",
            "role": "Alpha Specialist",
            "provider": {"type": "antigravity-queue"}
        }
        bridge_runner.write_manifest(alpha_manifest, agents_dir=(alpha_dir / "agents"), router=alpha_disp.agent_router)
        alpha_disp.agent_router.reload_registry(force=True)

        # Alpha dispatcher parses @alpha_agent as valid target
        alpha_targets = alpha_disp.parse_mentions("Hey @alpha_agent, please review!")
        self.assertIn("alpha_agent", alpha_targets)

        # Beta dispatcher does NOT recognize @alpha_agent
        beta_targets = beta_disp.parse_mentions("Hey @alpha_agent, please review!")
        self.assertNotIn("alpha_agent", beta_targets)

        alpha_disp.stop()
        beta_disp.stop()

    def test_adk_sync_writes_exclusively_to_tenant_dir(self):
        """
        Verify D70: sync_adk_agents_to_registry writes agent manifests exclusively
        into the specified tenant directory and never touches the product root.
        """
        scratch_dir = ensure_tenant_initialized("tenant_scratch", base_dir=self.test_dir)
        agents_to_sync = [
            {
                "id": "scratch_adk_bot",
                "name": "Scratch ADK Bot",
                "role": "ADK Specialist",
                "skills": ["ADK Automation"]
            }
        ]

        registry = TenantRegistry(base_dir=self.test_dir)
        scratch_router = registry.get_router("tenant_scratch")

        synced = bridge_runner.sync_adk_agents_to_registry(
            agents_to_sync,
            router=scratch_router,
            bridge_dir=scratch_dir
        )
        self.assertEqual(len(synced), 1)

        # Assert manifest exists in tenant directory
        tenant_mf = scratch_dir / "agents" / "scratch_adk_bot.agent.json"
        self.assertTrue(tenant_mf.exists())

        # Assert manifest does NOT exist in root agents directory
        root_agent_file = ROOT_DIR / "agents" / "scratch_adk_bot.agent.json"
        self.assertFalse(root_agent_file.exists(), "Root agents/ must never receive synced tenant manifests")

    def test_load_models_tenant_isolation(self):
        """
        Verify D71: load_models and save_models operate per-tenant when bridge_dir is passed.
        """
        alpha_dir = ensure_tenant_initialized("tenant_alpha", base_dir=self.test_dir)
        beta_dir = ensure_tenant_initialized("tenant_beta", base_dir=self.test_dir)

        custom_alpha_models = {
            "models": [
                {"id": "alpha_custom_llm", "name": "Alpha Custom LLM", "provider_type": "vertex-ai"}
            ]
        }
        bridge_runner.save_models(custom_alpha_models, bridge_dir=alpha_dir)

        alpha_loaded = bridge_runner.load_models(bridge_dir=alpha_dir)
        beta_loaded = bridge_runner.load_models(bridge_dir=beta_dir)

        alpha_model_ids = [m["id"] for m in alpha_loaded.get("models", [])]
        beta_model_ids = [m["id"] for m in beta_loaded.get("models", [])]

        self.assertIn("alpha_custom_llm", alpha_model_ids)
        self.assertNotIn("alpha_custom_llm", beta_model_ids)

    def test_save_engines_writes_exclusively_to_tenant_dir(self):
        """
        Verify D62: save_engines writes exclusively to tenant directory and updates models.json there.
        """
        delta_dir = ensure_tenant_initialized("tenant_delta", base_dir=self.test_dir)
        
        engines_payload = {
            "engines": [
                {
                    "id": "delta-core",
                    "name": "Delta Core",
                    "category": "model",
                    "type": "vertex-ai",
                    "provider_types": ["vertex-delta"],
                    "models": [
                        {"id": "delta-model-1", "name": "Delta Model 1"}
                    ]
                }
            ]
        }
        
        res = bridge_runner.save_engines(engines_payload, bridge_dir=delta_dir)
        self.assertTrue(res)
        
        # Assert files exist in tenant directory
        self.assertTrue((delta_dir / "engines.json").exists())
        self.assertTrue((delta_dir / "models.json").exists())
        
        # Assert models synchronized in tenant models.json
        loaded_models = bridge_runner.load_models(bridge_dir=delta_dir)
        m_ids = [m["id"] for m in loaded_models.get("models", [])]
        self.assertIn("delta-model-1", m_ids)
        
        # Assert root directory remains untouched
        self.assertFalse((ROOT_DIR / "engines.json").exists())
        self.assertFalse((ROOT_DIR / "models.json").exists())

    def test_reactions_and_history_isolation(self):
        """
        Verify D66: History loading, saving, reactions, and deletions operate strictly within tenant directory.
        """
        omega_dir = ensure_tenant_initialized("tenant_omega", base_dir=self.test_dir)
        
        hist_payload = {
            "transactions": [
                {
                    "id": "tx_omega_1",
                    "timestamp": "2026-08-31T15:00:00-0700",
                    "sender": "Omega Lead",
                    "prompt_text": "Hello from Omega",
                    "claude_response": "Response for Omega"
                }
            ]
        }
        
        # Save history into tenant_omega
        bridge_runner.save_history(hist_payload, project_id="proj_omega", bridge_dir=omega_dir, expected_generation=bridge_runner.UNCONDITIONAL)
        
        # Assert written into tenant history directory
        self.assertTrue((omega_dir / "history" / "history_proj_omega.json").exists())
        
        # Load history using bridge_dir
        loaded = bridge_runner.load_history("proj_omega", bridge_dir=omega_dir)
        self.assertEqual(len(loaded.get("transactions", [])), 1)
        self.assertEqual(loaded["transactions"][0]["id"], "tx_omega_1")
        
        # Assert root directory remains completely free of history artifacts
        self.assertFalse((ROOT_DIR / "history").exists(), "Root history/ must never be created")
        self.assertFalse((ROOT_DIR / "history_proj_omega.json").exists())

    def test_http_handlers_reactions_and_deletion_tenant_isolation(self):
        """
        Verify D70: HTTP handlers for /api/reactions and /api/delete-message
        execute through the request boundary and isolate mutations to the target tenant.
        """
        import io
        
        class DummyBridgeRequestHandler(bridge_runner.BridgeRequestHandler):
            def __init__(self, path, payload, headers=None):
                self.path = path
                self.headers = headers or {}
                body = json.dumps(payload).encode("utf-8")
                self.headers["Content-Length"] = str(len(body))
                self.rfile = io.BytesIO(body)
                self.wfile = io.BytesIO()
                self.status_code = None
                self.response_headers = {}
                self.server = unittest.mock.MagicMock()
                self.server.server_address = ("127.0.0.1", 8080)
                self.client_address = ("127.0.0.1", 12345)

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.response_headers[keyword] = value

            def end_headers(self):
                pass

            def send_error_json(self, message, code=500):
                self.status_code = code
                self.wfile.write(json.dumps({"error": message}).encode("utf-8"))

        t_id = "tenant_http_test"
        t_dir = ensure_tenant_initialized(t_id, base_dir=self.test_dir)
        
        # Seed initial history transaction in tenant directory
        initial_history = {
            "transactions": [
                {
                    "id": "tx_http_1",
                    "timestamp": "2026-08-31T15:00:00-0700",
                    "sender": "HTTP User",
                    "prompt_text": "Hello HTTP Tenant",
                    "claude_response": "Hello back!"
                }
            ]
        }
        bridge_runner.save_history(initial_history, project_id="test_project", bridge_dir=t_dir, expected_generation=bridge_runner.UNCONDITIONAL)
        
        # 1. Exercise POST /api/reactions through HTTP Handler boundary
        react_payload = {
            "project_id": "test_project",
            "tx_id": "tx_http_1",
            "emoji": "🚀",
            "user_id": "tester_1",
            "target_sub": "claude"
        }
        headers = {"X-Bridge-Tenant-ID": t_id}
        
        with unittest.mock.patch("bridge_runner.BRIDGE_DIR", self.test_dir):
            handler = DummyBridgeRequestHandler("/api/reactions", react_payload, headers=headers)
            handler.do_POST()
            
            self.assertEqual(handler.status_code, 200)
            
            # Assert reaction saved in tenant history
            t_hist = bridge_runner.load_history("test_project", bridge_dir=t_dir)
            t_tx = t_hist["transactions"][0]
            self.assertIn("🚀", t_tx.get("reactions", {}).get("claude", {}))
            self.assertIn("tester_1", t_tx["reactions"]["claude"]["🚀"])
            
            # Assert root history never created
            self.assertFalse((ROOT_DIR / "history").exists(), "Root history/ must never be created by HTTP handler")
            
            # 2. Exercise POST /api/delete-message through HTTP Handler boundary
            delete_payload = {
                "project_id": "test_project",
                "tx_id": "tx_http_1",
                "target_sub": "claude"
            }
            del_handler = DummyBridgeRequestHandler("/api/delete-message", delete_payload, headers=headers)
            del_handler.do_POST()
            
            self.assertEqual(del_handler.status_code, 200)
            
            # Assert claude_response was cleared in tenant history
            t_hist_after_del = bridge_runner.load_history("test_project", bridge_dir=t_dir)
            self.assertIsNone(t_hist_after_del["transactions"][0].get("claude_response"))
            
            # Assert root history still does not exist
            self.assertFalse((ROOT_DIR / "history").exists())

    def test_http_handlers_engines_and_models_tenant_isolation(self):
        """
        Verify D70: HTTP handlers for /api/engines and /api/models execute
        through the request boundary and write exclusively to the tenant workspace.
        """
        import io

        class DummyBridgeRequestHandler(bridge_runner.BridgeRequestHandler):
            def __init__(self, path, payload, headers=None):
                self.path = path
                self.headers = headers or {}
                body = json.dumps(payload).encode("utf-8")
                self.headers["Content-Length"] = str(len(body))
                self.rfile = io.BytesIO(body)
                self.wfile = io.BytesIO()
                self.status_code = None
                self.response_headers = {}
                self.server = unittest.mock.MagicMock()
                self.server.server_address = ("127.0.0.1", 8080)
                self.client_address = ("127.0.0.1", 12345)

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.response_headers[keyword] = value

            def end_headers(self):
                pass

            def send_error_json(self, message, code=500):
                self.status_code = code
                self.wfile.write(json.dumps({"error": message}).encode("utf-8"))

        t_id = "tenant_eng_test"
        t_dir = ensure_tenant_initialized(t_id, base_dir=self.test_dir)
        headers = {"X-Bridge-Tenant-ID": t_id}

        with unittest.mock.patch("bridge_runner.BRIDGE_DIR", self.test_dir):
            # 1. POST /api/engines (Upsert Engine)
            engine_payload = {
                "id": "custom-engine-x",
                "name": "Custom Engine X",
                "category": "model",
                "type": "custom-engine-x",
                "provider_types": ["custom-x"],
                "models": [
                    {"id": "model-x-1", "name": "Model X1"}
                ]
            }
            eng_handler = DummyBridgeRequestHandler("/api/engines", engine_payload, headers=headers)
            eng_handler.do_POST()

            self.assertEqual(eng_handler.status_code, 200)
            self.assertTrue((t_dir / "engines.json").exists())
            self.assertTrue((t_dir / "models.json").exists())

            # 2. POST /api/models (Upsert Model)
            model_payload = {
                "id": "model-standalone-y",
                "name": "Standalone Model Y",
                "provider_type": "vertex-ai"
            }
            mod_handler = DummyBridgeRequestHandler("/api/models", model_payload, headers=headers)
            mod_handler.do_POST()

            self.assertEqual(mod_handler.status_code, 200)

            # Assert models loaded from tenant directory contain the updates
            t_models = bridge_runner.load_models(bridge_dir=t_dir)
            mod_ids = [m["id"] for m in t_models.get("models", [])]
            self.assertIn("model-x-1", mod_ids)
            self.assertIn("model-standalone-y", mod_ids)

            # Assert root directory remains untouched
            self.assertFalse((ROOT_DIR / "engines.json").exists())
            self.assertFalse((ROOT_DIR / "models.json").exists())

    def test_skill_analytics_tenant_isolation(self):
        """
        Verify that /api/skill-analytics reads and writes strictly to the tenant
        workspace directory and never leaks or writes skill_usage.json to root.
        """
        import io

        class DummyBridgeRequestHandler(bridge_runner.BridgeRequestHandler):
            def __init__(self, path, payload=None, headers=None):
                self.path = path
                self.headers = headers or {}
                body = json.dumps(payload).encode("utf-8") if payload is not None else b""
                self.headers["Content-Length"] = str(len(body))
                self.rfile = io.BytesIO(body)
                self.wfile = io.BytesIO()
                self.status_code = None
                self.response_headers = {}
                self.server = unittest.mock.MagicMock()
                self.server.server_address = ("127.0.0.1", 8080)
                self.client_address = ("127.0.0.1", 12345)

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.response_headers[keyword] = value

            def end_headers(self):
                pass

        t_id = "tenant_skills_test"
        t_dir = ensure_tenant_initialized(t_id, base_dir=self.test_dir)
        headers = {"X-Bridge-Tenant-ID": t_id}

        with unittest.mock.patch("bridge_runner.BRIDGE_DIR", self.test_dir), \
             unittest.mock.patch("bridge_runner.tenant_manager", TenantRegistry(base_dir=self.test_dir)), \
             unittest.mock.patch("core.tenant.ROOT_DIR", self.test_dir):
            # 1. GET /api/skill-analytics
            get_handler = DummyBridgeRequestHandler("/api/skill-analytics", None, headers=headers)
            get_handler.do_GET()
            self.assertEqual(get_handler.status_code, 200)

            # 2. POST /api/skill-analytics
            payload = {
                "skill_id": "test-skill-1",
                "agent_id": "architect"
            }
            post_handler = DummyBridgeRequestHandler("/api/skill-analytics", payload, headers=headers)
            post_handler.do_POST()
            self.assertEqual(post_handler.status_code, 200)

            # Assert tenant skill_usage.json was created / updated
            t_skills = bridge_runner.load_skill_usage(bridge_dir=t_dir)
            skill_ids = [s["id"] for s in t_skills.get("skills", [])]
            self.assertIn("test-skill-1", skill_ids)

            # Assert root skill_usage.json does not exist
            self.assertFalse((ROOT_DIR / "skill_usage.json").exists())

    def test_delete_project_tenant_isolation(self):
        """
        Verify that POST /api/delete-project deletes workspace records strictly
        from the tenant's projects.json and history files, guarding default pinned projects.
        """
        import io

        class DummyBridgeRequestHandler(bridge_runner.BridgeRequestHandler):
            def __init__(self, path, payload=None, headers=None):
                self.path = path
                self.headers = headers or {}
                body = json.dumps(payload).encode("utf-8") if payload is not None else b""
                self.headers["Content-Length"] = str(len(body))
                self.rfile = io.BytesIO(body)
                self.wfile = io.BytesIO()
                self.status_code = None
                self.response_headers = {}
                self.server = unittest.mock.MagicMock()
                self.server.server_address = ("127.0.0.1", 8080)
                self.client_address = ("127.0.0.1", 12345)

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.response_headers[keyword] = value

            def end_headers(self):
                pass

            def send_error_json(self, message, code=500):
                self.status_code = code
                self.wfile.write(json.dumps({"error": message}).encode("utf-8"))

        t_id = "tenant_del_proj_test"
        t_dir = ensure_tenant_initialized(t_id, base_dir=self.test_dir)
        headers = {"X-Bridge-Tenant-ID": t_id}

        with unittest.mock.patch("bridge_runner.BRIDGE_DIR", self.test_dir), \
             unittest.mock.patch("bridge_runner.tenant_manager", TenantRegistry(base_dir=self.test_dir)), \
             unittest.mock.patch("core.tenant.ROOT_DIR", self.test_dir):

            # 1. Create a custom project
            create_payload = {
                "id": "proj_temp_delete_test",
                "name": "Temporary Workspace",
                "icon": "🧪",
                "description": "To be deleted",
                "pinned": False,
                "directories": ["./workspace/temp"],
                "members": ["lead"]
            }
            create_handler = DummyBridgeRequestHandler("/api/projects", create_payload, headers=headers)
            create_handler.do_POST()
            self.assertEqual(create_handler.status_code, 200)

            # Create a history entry for it
            bridge_runner.append_transaction("proj_temp_delete_test", {"id": "tx_del_1", "prompt_text": "hello"}, bridge_dir=t_dir)
            self.assertTrue(bridge_runner.get_history_file("proj_temp_delete_test", bridge_dir=t_dir).exists())
            legacy_file = t_dir / "history_proj_temp_delete_test.json"
            legacy_file.write_text('{"transactions": []}', encoding="utf-8")
            self.assertTrue(legacy_file.exists())

            # 2. Attempt to delete default pinned project -> should fail with 400
            del_pinned_handler = DummyBridgeRequestHandler("/api/delete-project", {"project_id": "lantern"}, headers=headers)
            del_pinned_handler.do_POST()
            self.assertEqual(del_pinned_handler.status_code, 400)

            # 3. Delete custom project -> should succeed with 200
            del_handler = DummyBridgeRequestHandler("/api/delete-project", {"project_id": "proj_temp_delete_test"}, headers=headers)
            del_handler.do_POST()
            self.assertEqual(del_handler.status_code, 200)

            # Assert project is removed from tenant projects.json
            t_projects = bridge_runner.load_projects(bridge_dir=t_dir)
            p_ids = [p["id"] for p in t_projects.get("projects", [])]
            self.assertNotIn("proj_temp_delete_test", p_ids)

            # Assert history file and legacy history file were cleaned up
            self.assertFalse(bridge_runner.get_history_file("proj_temp_delete_test", bridge_dir=t_dir).exists())
            self.assertFalse(legacy_file.exists())

            # Assert root projects.json does not exist
            self.assertFalse((ROOT_DIR / "projects.json").exists())

    def test_check_auth_dual_channel(self):
        """Verify _check_auth enforcement: constant-time comparison via hmac, headers, cookies, query params."""
        class AuthDummyHandler(bridge_runner.BridgeRequestHandler):
            def __init__(self, path, headers=None, server_host="0.0.0.0"):
                self.path = path
                self.headers = headers or {}
                self.rfile = io.BytesIO(b"")
                self.wfile = io.BytesIO()
                self.status_code = None
                self.response_headers = {}
                self.server = unittest.mock.MagicMock()
                self.server.server_address = (server_host, 8080)
                self.client_address = ("192.168.1.100", 12345)

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                self.response_headers[keyword] = value

            def end_headers(self):
                pass

        test_token = "secret-token-test-12345"
        with unittest.mock.patch.dict(os.environ, {"BRIDGE_AUTH_TOKEN": test_token}):
            # 1. No token provided -> 401 Unauthorized
            h_no_token = AuthDummyHandler("/api/profiles")
            self.assertFalse(h_no_token._check_auth())
            self.assertEqual(h_no_token.status_code, 401)

            # 2. Invalid token provided -> 401 Unauthorized
            h_bad_token = AuthDummyHandler("/api/profiles", headers={"X-Bridge-Auth": "wrong-token"})
            self.assertFalse(h_bad_token._check_auth())
            self.assertEqual(h_bad_token.status_code, 401)

            # 3. Valid X-Bridge-Auth header -> 200 OK (returns True)
            h_valid_header = AuthDummyHandler("/api/profiles", headers={"X-Bridge-Auth": test_token})
            self.assertTrue(h_valid_header._check_auth())

            # 4. Valid bridge_auth cookie -> returns True
            h_valid_cookie = AuthDummyHandler("/api/profiles", headers={"Cookie": f"foo=bar; bridge_auth={test_token}; baz=qux"})
            self.assertTrue(h_valid_cookie._check_auth())

            # 5. Valid Authorization: Bearer -> returns True
            h_valid_bearer = AuthDummyHandler("/api/profiles", headers={"Authorization": f"Bearer {test_token}"})
            self.assertTrue(h_valid_bearer._check_auth())

            # 6. Valid query parameter ?token= on root -> returns True
            h_valid_query = AuthDummyHandler(f"/?token={test_token}")
            self.assertTrue(h_valid_query._check_auth())

            # 7. Query parameter ?token= on non-root API endpoint -> disallowed for security, returns 401
            h_invalid_query_path = AuthDummyHandler(f"/api/profiles?token={test_token}")
            self.assertFalse(h_invalid_query_path._check_auth())
            self.assertEqual(h_invalid_query_path.status_code, 401)

        # 8. Loopback without BRIDGE_AUTH_TOKEN -> allowed without auth
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            h_loopback = AuthDummyHandler("/api/profiles", server_host="127.0.0.1")
            self.assertTrue(h_loopback._check_auth())

    def test_exclusion_lists_contain_data_dir(self):
        """Verify Lumen P3: .gitignore, .dockerignore, and .gcloudignore all exclude data/."""
        for fname in [".gitignore", ".dockerignore", ".gcloudignore"]:
            p = ROOT_DIR / fname
            self.assertTrue(p.exists(), f"Expected exclusion file {fname} to exist")
            lines = [line.strip() for line in p.read_text(encoding="utf-8").splitlines()]
            self.assertIn("data/", lines, f"Expected 'data/' to be explicitly excluded in {fname}")

    def test_bridge_data_dir_env_override(self):
        """Verify D1: BRIDGE_DATA_DIR environment variable decouples tenant data from ROOT_DIR."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            custom_data = Path(tmp_dir) / "custom_data"
            custom_data.mkdir()
            with unittest.mock.patch.dict(os.environ, {"BRIDGE_DATA_DIR": str(custom_data)}):
                from core.tenant import get_data_root, get_tenant_dir, LocalStorageAdapter
                self.assertEqual(get_data_root(), custom_data)
                t_dir = get_tenant_dir("tenant_test")
                self.assertEqual(t_dir, custom_data / "tenants" / "tenant_test")
                
                # Test LocalStorageAdapter resolution
                adapter = LocalStorageAdapter()
                resolved = adapter._resolve_path("tenant_test", "profiles.json")
                self.assertEqual(resolved, custom_data / "tenants" / "tenant_test" / "profiles.json")

    def test_explicit_base_dir_precedence_over_env(self):
        """Verify N2: Explicit base_dir argument takes precedence over BRIDGE_DATA_DIR env var."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            explicit_dir = Path(tmp_dir) / "explicit_dir"
            with unittest.mock.patch.dict(os.environ, {"BRIDGE_DATA_DIR": "/tmp/envroot"}):
                from core.tenant import get_data_root
                self.assertEqual(get_data_root(explicit_dir), explicit_dir / "data")


if __name__ == "__main__":
    unittest.main()
