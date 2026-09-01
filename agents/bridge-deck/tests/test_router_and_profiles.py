#!/usr/bin/env python3
"""
Unit test suite verifying:
- Router manifest validation, normalization, and secure defaults
- Location precedence chain (model > engine > heuristic)
- Model alias resolution (MODEL_ALIASES & DEFAULT_MODEL)
- Eager validation in VertexCustomEndpointProvider
- Write-time manifest validation and dual-store atomicity in /api/profiles
"""

import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.router import AgentRouter, DEFAULT_MODEL, MODEL_ALIASES, resolve_model_location
from providers.vertex_custom_endpoint import VertexCustomEndpointProvider
import bridge_runner


class TestRouterAndProfiles(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.bridge_dir = Path(__file__).resolve().parent.parent
        self.agents_dir = self.test_dir / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy schema to test directory
        schema_src = self.bridge_dir / "agents" / "_schema.json"
        if schema_src.exists():
            shutil.copy(schema_src, self.agents_dir / "_schema.json")

        self.router = AgentRouter(bridge_dir=self.test_dir)
        self._old_gcp_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        os.environ["GOOGLE_CLOUD_PROJECT"] = "test-governance-project"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        if self._old_gcp_project is not None:
            os.environ["GOOGLE_CLOUD_PROJECT"] = self._old_gcp_project
        else:
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)

    def test_validate_and_normalize_manifest_secure_defaults(self):
        """Verify that manifest normalization sets secure defaults and passes schema validation."""
        raw_manifest = {
            "id": "agent_test",
            "name": "Test Agent",
            "role": "Quality Specialist",
            "harness": "none",
            "provider": {
                "type": "vertex-ai",
                "model": "gemini-3.7-flash",
                "location": "global"
            }
        }
        mf_path = self.agents_dir / "agent_test.agent.json"
        norm = self.router._validate_and_normalize_manifest(raw_manifest, mf_path)
        
        self.assertEqual(norm["id"], "agent_test")
        self.assertEqual(norm["access_read"], [])
        self.assertEqual(norm["access_write"], [])
        self.assertEqual(norm["tools_enabled"], [])
        self.assertEqual(norm["harness"], "none")

    def test_validate_manifest_fails_on_invalid_harness(self):
        """Verify that schema validation rejects invalid harness enum."""
        raw_manifest = {
            "id": "bad_harness_bot",
            "name": "Bad Harness Bot",
            "role": "Tester",
            "harness": "invalid-harness-enum",
            "provider": {
                "type": "vertex-ai",
                "model": "gemini-3.7-flash",
                "location": "global"
            }
        }
        mf_path = self.agents_dir / "bad_harness_bot.agent.json"
        with self.assertRaises(ValueError) as ctx:
            self.router._validate_and_normalize_manifest(raw_manifest, mf_path)
        self.assertIn("invalid value 'invalid-harness-enum'", str(ctx.exception).lower())

    def test_model_alias_resolution(self):
        """Verify that MODEL_ALIASES canonicalizes model names."""
        self.assertEqual(MODEL_ALIASES.get("nexus"), DEFAULT_MODEL)
        self.assertEqual(MODEL_ALIASES.get("google adk"), DEFAULT_MODEL)
        self.assertEqual(MODEL_ALIASES.get("gemini 3.7"), DEFAULT_MODEL)
        self.assertEqual(MODEL_ALIASES.get("gemini 2.5"), "gemini-2.5-flash")
        self.assertEqual(MODEL_ALIASES.get("gemma 4"), "gemma-4-26b-a4b-it")

    def test_resolve_model_location_heuristics(self):
        """Verify fallback region heuristic resolves expected regions."""
        self.assertEqual(resolve_model_location("gemini-3.7-flash"), "global")
        self.assertEqual(resolve_model_location("claude-opus-5"), "global")
        self.assertEqual(resolve_model_location("gemini-2.5-flash"), "us-central1")
        self.assertEqual(resolve_model_location("gemma-4-26b-a4b-it"), "us-central1")

    def test_vertex_custom_endpoint_path_parsing_and_eager_validation(self):
        """Verify that VertexCustomEndpointProvider parses resource path and validates project eagerly."""
        full_path = "projects/my-proj-123/locations/us-central1/endpoints/ep-456"
        provider = VertexCustomEndpointProvider(
            provider_id="custom",
            config={"endpoint_id": full_path}
        )
        self.assertEqual(provider.project_id, "my-proj-123")
        self.assertEqual(provider.location, "us-central1")
        self.assertEqual(provider.endpoint_id, "ep-456")

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                VertexCustomEndpointProvider(
                    provider_id="custom",
                    config={"endpoint_id": "ep-standalone"}
                )

    def test_vertex_custom_endpoint_warmup_retry(self):
        """Verify that VertexCustomEndpointProvider retries on scale-up/warmup errors before succeeding."""
        full_path = "projects/my-proj-123/locations/us-central1/endpoints/ep-456"
        provider = VertexCustomEndpointProvider(
            provider_id="custom",
            config={"endpoint_id": full_path}
        )
        
        mock_client = MagicMock()
        mock_pred = MagicMock()
        mock_pred.predictions = ["Output:\nHello from warmed up Gemma model!<end_of_turn>"]
        
        # Simulate: first 2 attempts fail with 503 warmup, 3rd succeeds
        call_count = 0
        def mock_predict(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("503 Endpoint is currently scaling up from zero nodes and not yet ready for inference.")
            return mock_pred

        mock_client.predict.side_effect = mock_predict
        provider._endpoint_client = mock_client

        with patch("time.sleep", return_value=None):
            res = provider.invoke(prompt="Hello Rhen!")
            self.assertTrue(res["success"])
            self.assertEqual(res["response"], "Hello from warmed up Gemma model!")
            self.assertEqual(call_count, 3)

    def test_save_persona_validation_before_write_and_atomicity(self):
        """Verify that save_persona performs validation-before-write, atomicity, and revocation."""
        mock_profiles_file = self.test_dir / "profiles.json"
        mock_agents_dir = self.agents_dir
        
        # Initial state: profiles.json has an existing persona
        with open(mock_profiles_file, "w", encoding="utf-8") as pf:
            json.dump({"profiles": [{"id": "existing_bot", "name": "Existing Bot"}]}, pf)

        # 1. Bad payload with invalid harness enum MUST raise ValueError
        bad_payload = {
            "id": "bad_harness_bot",
            "name": "Bad Bot",
            "role": "Tester",
            "harness": "invalid-harness-enum",
            "engine": "vertex-ai",
            "model": "gemini-3.7-flash"
        }
        with self.assertRaises(ValueError):
            bridge_runner.save_persona(
                bad_payload,
                profiles_file=mock_profiles_file,
                agents_dir=mock_agents_dir,
                router=self.router
            )

        # Assert bad payload was NEVER written to profiles.json or agents/
        with open(mock_profiles_file, "r", encoding="utf-8") as pf:
            data = json.load(pf)
        self.assertEqual(len(data["profiles"]), 1)
        self.assertEqual(data["profiles"][0]["id"], "existing_bot")
        self.assertFalse((mock_agents_dir / "bad_harness_bot.agent.json").exists())

        # 2. Good payload with explicit access_write: [] (revocation)
        good_payload = {
            "id": "good_bot",
            "name": "Good Bot",
            "role": "Engineer",
            "harness": "voyager",
            "engine": "vertex-ai",
            "model": "gemini-3.7-flash",
            "access_read": ["/path/read"],
            "access_write": []
        }
        res = bridge_runner.save_persona(
            good_payload,
            profiles_file=mock_profiles_file,
            agents_dir=mock_agents_dir,
            router=self.router
        )
        self.assertEqual(res["id"], "good_bot")

        # Assert good payload WAS written to both profiles.json and agents/
        with open(mock_profiles_file, "r", encoding="utf-8") as pf:
            data = json.load(pf)
        self.assertEqual(len(data["profiles"]), 2)
        self.assertEqual(data["profiles"][1]["id"], "good_bot")
        
        mf_path = mock_agents_dir / "good_bot.agent.json"
        self.assertTrue(mf_path.exists())
        with open(mf_path, "r", encoding="utf-8") as mf:
            m_data = json.load(mf)
        self.assertEqual(m_data["id"], "good_bot")
        self.assertEqual(m_data["harness"], "voyager")
        self.assertEqual(m_data["access_write"], [])
        self.assertEqual(m_data["provider"]["model"], "gemini-3.7-flash")

    def test_save_persona_vertex_custom_endpoint_validation(self):
        """Verify D38: saving a custom endpoint persona without endpoint_id fails before writing to disk."""
        mock_profiles_file = self.test_dir / "profiles.json"
        mock_agents_dir = self.agents_dir
        
        with open(mock_profiles_file, "w", encoding="utf-8") as pf:
            json.dump({"profiles": []}, pf)

        # 1. Custom endpoint WITHOUT endpoint_id MUST fail
        bad_custom_payload = {
            "id": "missing_ep_bot",
            "name": "Missing Endpoint Bot",
            "role": "Model Garden Specialist",
            "engine": "vertex-custom",
            "model": "mg-endpoint-llama"
        }
        with self.assertRaises(ValueError):
            bridge_runner.save_persona(
                bad_custom_payload,
                profiles_file=mock_profiles_file,
                agents_dir=mock_agents_dir,
                router=self.router
            )

        # Assert no disk writes
        with open(mock_profiles_file, "r", encoding="utf-8") as pf:
            data = json.load(pf)
        self.assertEqual(data["profiles"], [])
        self.assertFalse((mock_agents_dir / "missing_ep_bot.agent.json").exists())

        # 2. Custom endpoint WITH endpoint_id succeeds
        good_custom_payload = {
            "id": "valid_ep_bot",
            "name": "Valid Endpoint Bot",
            "role": "Model Garden Specialist",
            "engine": "vertex-custom",
            "model": "mg-endpoint-llama",
            "endpoint_id": "projects/test-proj/locations/us-central1/endpoints/12345"
        }
        res = bridge_runner.save_persona(
            good_custom_payload,
            profiles_file=mock_profiles_file,
            agents_dir=mock_agents_dir,
            router=self.router
        )
        self.assertEqual(res["id"], "valid_ep_bot")
        self.assertIn("valid_ep_bot", self.router.manifests)
        self.assertEqual(
            self.router.providers["valid_ep_bot"].__class__.__name__,
            "VertexCustomEndpointProvider"
        )

    def test_save_persona_persists_project_id_from_env_or_payload(self):
        """Verify D39: save_persona resolves and persists provider.project_id into manifest."""
        mock_profiles_file = self.test_dir / "profiles.json"
        mock_agents_dir = self.agents_dir
        
        with open(mock_profiles_file, "w", encoding="utf-8") as pf:
            json.dump({"profiles": []}, pf)

        # 1. Project resolved from environment
        payload = {
            "id": "env_bot",
            "name": "Env Bot",
            "role": "Engineer",
            "engine": "vertex-ai",
            "model": "gemini-3.7-flash"
        }
        res = bridge_runner.save_persona(
            payload,
            profiles_file=mock_profiles_file,
            agents_dir=mock_agents_dir,
            router=self.router
        )
        self.assertEqual(res["id"], "env_bot")
        
        mf_path = mock_agents_dir / "env_bot.agent.json"
        self.assertTrue(mf_path.exists())
        with open(mf_path, "r", encoding="utf-8") as mf:
            m_data = json.load(mf)
        self.assertEqual(m_data["provider"]["project_id"], "test-governance-project")

        # 2. Project explicitly provided in payload overrides env
        custom_payload = {
            "id": "custom_proj_bot",
            "name": "Custom Proj Bot",
            "role": "Engineer",
            "engine": "vertex-ai",
            "model": "gemini-3.7-flash",
            "project_id": "custom-override-project"
        }
        res2 = bridge_runner.save_persona(
            custom_payload,
            profiles_file=mock_profiles_file,
            agents_dir=mock_agents_dir,
            router=self.router
        )
        self.assertEqual(res2["id"], "custom_proj_bot")
        
        mf_path2 = mock_agents_dir / "custom_proj_bot.agent.json"
        with open(mf_path2, "r", encoding="utf-8") as mf:
            m_data2 = json.load(mf)
        self.assertEqual(m_data2["provider"]["project_id"], "custom-override-project")

    def test_save_persona_missing_project_id_raises_when_env_unset(self):
        """Verify D39: save_persona raises ValueError when project_id cannot be resolved."""
        mock_profiles_file = self.test_dir / "profiles.json"
        mock_agents_dir = self.agents_dir
        
        with open(mock_profiles_file, "w", encoding="utf-8") as pf:
            json.dump({"profiles": []}, pf)

        payload = {
            "id": "no_env_bot",
            "name": "No Env Bot",
            "role": "Engineer",
            "engine": "vertex-ai",
            "model": "gemini-3.7-flash"
        }
        
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as cm:
                bridge_runner.save_persona(
                    payload,
                    profiles_file=mock_profiles_file,
                    agents_dir=mock_agents_dir,
                    router=self.router
                )
            self.assertIn("requires a Google Cloud project ID", str(cm.exception))

        # Assert no disk writes
        with open(mock_profiles_file, "r", encoding="utf-8") as pf:
            data = json.load(pf)
        self.assertEqual(data["profiles"], [])
        self.assertFalse((mock_agents_dir / "no_env_bot.agent.json").exists())

    def test_save_persona_non_gcp_engines_succeed_when_env_unset(self):
        """Verify D42: non-GCP engines (human, ollama-local, antigravity-queue, google-adk) succeed when GOOGLE_CLOUD_PROJECT is unset."""
        mock_profiles_file = self.test_dir / "profiles.json"
        mock_agents_dir = self.agents_dir
        
        non_gcp_payloads = [
            {
                "id": "test_human",
                "name": "Human Tester",
                "role": "Collaborator",
                "engine": "human"
            },
            {
                "id": "test_ollama",
                "name": "Ollama Local",
                "role": "Local Specialist",
                "engine": "ollama-local",
                "model": "qwen2.5-coder:7b"
            },
            {
                "id": "test_ag_queue",
                "name": "Queue Bot",
                "role": "Worker",
                "engine": "antigravity-queue",
                "model": "gemini-3.7-flash"
            },
            {
                "id": "test_adk",
                "name": "ADK Agent",
                "role": "Specialist",
                "engine": "google-adk",
                "model": "gemini-3.7-flash"
            }
        ]

        with patch.dict(os.environ, {}, clear=True):
            for payload in non_gcp_payloads:
                p_id = payload["id"]
                res = bridge_runner.save_persona(
                    payload,
                    profiles_file=mock_profiles_file,
                    agents_dir=mock_agents_dir,
                    router=self.router
                )
                self.assertEqual(res["id"], p_id)
                self.assertIn(p_id, self.router.manifests)
                
                # Check manifest on disk
                mf_file = mock_agents_dir / f"{p_id}.agent.json"
                self.assertTrue(mf_file.exists())
                with open(mf_file, "r", encoding="utf-8") as f:
                    mf = json.load(f)
                
                # Verify that no spurious GCP project was injected
                self.assertNotIn("project_id", mf.get("provider", {}))

    def test_sync_adk_agents_defaults_empty_access_read_and_validates(self):
        """Verify D46: sync_adk_agents_to_registry assigns empty access_read and validates schema atomically."""
        agents_to_sync = [
            {
                "id": "synced_specialist",
                "name": "Synced Specialist",
                "role": "ADK Agent",
                "skills": ["ADK Tool Use"]
            }
        ]
        
        synced = bridge_runner.sync_adk_agents_to_registry(agents_to_sync, agents_dir=self.agents_dir, router=self.router)
        self.assertEqual(len(synced), 1)
        self.assertEqual(synced[0]["id"], "synced_specialist")
        self.assertEqual(synced[0]["access_read"], [])
        self.assertEqual(synced[0]["access_write"], [])
        
        mf_path = self.agents_dir / "synced_specialist.agent.json"
        self.assertTrue(mf_path.exists())
        with open(mf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["access_read"], [])
        self.assertEqual(data["access_write"], [])
        
        # Cleanup
        if mf_path.exists():
            mf_path.unlink()
        bridge_runner.tenant_manager.get_router().reload_registry(force=True)

    def test_ollama_local_provider_resolution_and_offline_handling(self):
        """Verify D45 & D47: save_persona with ollama-local engine emits type: ollama-local and router instantiates OllamaLocalProvider."""
        from providers.ollama_local import OllamaLocalProvider
        mock_profiles_file = self.test_dir / "profiles.json"
        mock_agents_dir = self.agents_dir
        
        with open(mock_profiles_file, "w", encoding="utf-8") as pf:
            json.dump({"profiles": []}, pf)

        payload = {
            "id": "ollama_bot",
            "name": "Ollama Bot",
            "role": "Local Specialist",
            "engine": "ollama-local",
            "model": "llama-3.3-70b"
        }

        res = bridge_runner.save_persona(
            payload,
            profiles_file=mock_profiles_file,
            agents_dir=mock_agents_dir,
            router=self.router
        )
        self.assertEqual(res["id"], "ollama_bot")

        # Verify on-disk manifest was written with type "ollama-local"
        mf_path = mock_agents_dir / "ollama_bot.agent.json"
        self.assertTrue(mf_path.exists())
        with open(mf_path, "r", encoding="utf-8") as mf:
            m_data = json.load(mf)
        self.assertEqual(m_data["provider"]["type"], "ollama-local")
        self.assertEqual(m_data["provider"]["model"], "llama3.3:70b")
        
        # Verify router instantiated OllamaLocalProvider
        provider = self.router.providers.get("ollama_bot")
        self.assertIsInstance(provider, OllamaLocalProvider)
        self.assertEqual(provider.model_name, "llama3.3:70b")
        self.assertIn(provider.base_url, ["http://127.0.0.1:11434", "http://localhost:11434"])
        
        # Test offline invoke handling
        res_inv = provider.invoke(prompt="Hello from test suite")
        self.assertIn("success", res_inv)
        if not res_inv["success"]:
            self.assertIn("Ollama daemon unreachable", res_inv["error"])

    def test_save_persona_custom_endpoint_requires_endpoint_id(self):
        """Verify D38: saving a custom endpoint persona without an endpoint_id raises ValueError and writes nothing."""
        mock_profiles_file = self.test_dir / "profiles.json"
        mock_agents_dir = self.agents_dir
        
        with open(mock_profiles_file, "w", encoding="utf-8") as pf:
            json.dump({"profiles": []}, pf)

        payload = {
            "id": "missing_ep_bot",
            "name": "Missing EP Bot",
            "role": "Engineer",
            "engine": "vertex-custom",
            "model": "mg-endpoint-gemma-4-12b",
            "project_id": "test-project"
        }
        
        with self.assertRaises(ValueError) as cm:
            bridge_runner.save_persona(
                payload,
                profiles_file=mock_profiles_file,
                agents_dir=mock_agents_dir,
                router=self.router
            )
        self.assertIn("requires an 'endpoint_id'", str(cm.exception))

        # Assert no disk writes
        with open(mock_profiles_file, "r", encoding="utf-8") as pf:
            data = json.load(pf)
        self.assertEqual(data["profiles"], [])
        self.assertFalse((mock_agents_dir / "missing_ep_bot.agent.json").exists())

    def test_save_persona_custom_endpoint_with_endpoint_id_succeeds(self):
        """Verify D38: saving a custom endpoint persona with endpoint_id succeeds and persists properly."""
        mock_profiles_file = self.test_dir / "profiles.json"
        mock_agents_dir = self.agents_dir
        
        with open(mock_profiles_file, "w", encoding="utf-8") as pf:
            json.dump({"profiles": []}, pf)

        payload = {
            "id": "valid_ep_bot",
            "name": "Valid EP Bot",
            "role": "Engineer",
            "engine": "vertex-custom",
            "model": "gemma-4-12b",
            "endpoint_id": "projects/12345/locations/us-central1/endpoints/67890",
            "project_id": "test-project"
        }
        
        res = bridge_runner.save_persona(
            payload,
            profiles_file=mock_profiles_file,
            agents_dir=mock_agents_dir,
            router=self.router
        )
        self.assertEqual(res["id"], "valid_ep_bot")
        
        mf_path = mock_agents_dir / "valid_ep_bot.agent.json"
        self.assertTrue(mf_path.exists())
        with open(mf_path, "r", encoding="utf-8") as mf:
            m_data = json.load(mf)
        self.assertEqual(m_data["provider"]["endpoint_id"], "projects/12345/locations/us-central1/endpoints/67890")

    def test_sync_project_membership_never_mutates_access_write_or_read(self):
        """Verify D49: sync_project_membership updates resumes but NEVER derives access_write or base access_read."""
        mock_profiles_data = {
            "profiles": [
                {
                    "id": "member_a",
                    "name": "Member A",
                    "access_read": ["/initial/read/path"],
                    "access_write": [],
                    "resume": []
                },
                {
                    "id": "member_b",
                    "name": "Member B",
                    "access_read": [],
                    "access_write": ["/authored/write/path"],
                    "resume": []
                }
            ]
        }

        project_payload = {
            "id": "test_proj_123",
            "name": "New Project",
            "members": ["member_a", "member_b"],
            "directories": ["/unauthorized/project/path"]
        }

        updated_data, changed = bridge_runner.sync_project_membership(project_payload, mock_profiles_data)
        self.assertTrue(changed)

        prof_a = next(p for p in updated_data["profiles"] if p["id"] == "member_a")
        prof_b = next(p for p in updated_data["profiles"] if p["id"] == "member_b")

        # access_write must NOT have /unauthorized/project/path added
        self.assertEqual(prof_a["access_write"], [])
        self.assertEqual(prof_b["access_write"], ["/authored/write/path"])

        # base access_read must NOT have /unauthorized/project/path added
        self.assertEqual(prof_a["access_read"], ["/initial/read/path"])
        self.assertEqual(prof_b["access_read"], [])

        # Resumes must be populated
        self.assertEqual(len(prof_a["resume"]), 1)
        self.assertEqual(prof_a["resume"][0]["project_id"], "test_proj_123")

    def test_write_manifest_validates_and_commits_atomically(self):
        """Verify D9 / D50: write_manifest normalizes IDs, validates schema, and writes atomically without leaving temporary files."""
        mock_agents_dir = self.test_dir / "agents_test"
        mock_agents_dir.mkdir(parents=True, exist_ok=True)

        # 1. Test ID normalization (e.g. "Atomic Bot" -> "atomic-bot")
        valid_manifest = {
            "id": "Atomic Bot",
            "name": "Atomic Bot",
            "role": "Specialist",
            "access_read": [],
            "access_write": [],
            "provider": {
                "type": "human",
                "model": "human"
            }
        }

        res = bridge_runner.write_manifest(valid_manifest, agents_dir=mock_agents_dir, router=self.router)
        self.assertEqual(res["id"], "atomic-bot")
        target_file = mock_agents_dir / "atomic-bot.agent.json"
        self.assertTrue(target_file.exists())

        # 2. Negative test: schema validation failure raises ValueError and leaves zero residual files
        invalid_manifest = {
            "id": "bad_type_bot",
            "name": "Bad Type Bot",
            "role": "Specialist",
            "provider": {
                "type": "nonexistent_unregistered_type",
                "model": "test-model"
            }
        }

        with self.assertRaises(ValueError):
            bridge_runner.write_manifest(invalid_manifest, agents_dir=mock_agents_dir, router=self.router)

        bad_target_file = mock_agents_dir / "bad_type_bot.agent.json"
        self.assertFalse(bad_target_file.exists())
        bad_tmp_file = mock_agents_dir / "bad_type_bot.agent.json.tmp"
        self.assertFalse(bad_tmp_file.exists())

    def test_clean_speaker_name_dynamic_discovery_and_slug_normalization(self):
        """Verify D54 / D61: clean_speaker_name dynamically discovers manifest names from injected bridge_dir and strips slugs."""
        from core.history import clean_speaker_name, format_history_block

        mock_tenant_dir = self.test_dir / "tenant_mock"
        mock_agents_dir = mock_tenant_dir / "agents"
        mock_agents_dir.mkdir(parents=True, exist_ok=True)

        # Create a custom agent manifest in tenant directory
        tenant_agent = {
            "id": "quantum-lead",
            "name": "Quantum Lead",
            "role": "Lead Theorist",
            "provider": {"type": "human", "model": "human"}
        }
        with open(mock_agents_dir / "quantum-lead.agent.json", "w", encoding="utf-8") as f:
            json.dump(tenant_agent, f)

        # Verify slug stripping & dynamic prefix matching
        self.assertEqual(clean_speaker_name("Quantum Lead (Claude Opus 5)", bridge_dir=mock_tenant_dir), "Quantum Lead")
        self.assertEqual(clean_speaker_name("Quantum Lead (you)", bridge_dir=mock_tenant_dir), "Quantum Lead")

        # Verify format_history_block with self-marking
        messages = [
            {"role": "user", "speaker": "Team Lead", "content": "Hello Quantum Lead!"},
            {"role": "assistant", "speaker": "Quantum Lead", "content": "Greetings! I am ready to review."},
            {"role": "user", "speaker": "Team Lead", "content": "What is the next task?"}
        ]
        block = format_history_block(messages, self_name="Quantum Lead", bridge_dir=mock_tenant_dir)
        self.assertIn("[Team Lead]: Hello Quantum Lead!", block)
        self.assertIn("[Quantum Lead (you)]: Greetings! I am ready to review.", block)


if __name__ == "__main__":
    unittest.main()
