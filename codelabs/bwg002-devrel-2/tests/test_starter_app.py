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

"""
/**
 * @file test_starter_app.py
 * @description Comprehensive offline unit and functional test suite for the R1
 *   Pitch Generator starter application (Milestone 1: Features F1–F6).
 *
 * Why: Verifies that every component of the pre-Module 1 starter application—
 * project layout (`F1`), dependency-injected cloud services (`F2`), baseline ADK
 * multi-agent workflow (`creative_director` + `copywriter` on `gemini-3.8-flash`)
 * and FastAPI/A2A endpoints (`F3`), vanilla HTML5/CSS3/ES6 JS frontend (`F4`),
 * smart dynamic container/shell/Terraform infrastructure (`F5`), and Javadoc-style
 * "why" comments (`F6`)—meets the specification with 100% offline execution.
 */
"""

from __future__ import annotations

import ast
import pathlib
import re
import subprocess
from typing import Any

import pytest

from pitch_generator import agent, config, fast_api_app
from pitch_generator.app_utils import a2a, memory_bank, services

PITCH_GEN_ROOT = pathlib.Path(__file__).resolve().parent.parent
LAB_ROOT = PITCH_GEN_ROOT.parent


# ============================================================================
# Feature F1: `agents-cli` & ADK Project Layout Tests
# ============================================================================


def test_f1_project_directory_and_file_layout() -> None:
    """
    /**
     * Verify that all required R1 starter project files and directories exist.
     *
     * Why: Learners connecting to the pre-configured Antigravity 2.0 VM expect
     * a complete `agents-cli` and Google ADK project structure in `pitch-generator/`.
     */
    """
    required_paths = [
        "pyproject.toml",
        ".env.example",
        "README.md",
        "Dockerfile",
        "call_agent.py",
        "scripts/setup.sh",
        "scripts/deploy.sh",
        "frontend/index.html",
        "frontend/styles.css",
        "frontend/app.js",
        "pitch_generator/__init__.py",
        "pitch_generator/config.py",
        "pitch_generator/agent.py",
        "pitch_generator/fast_api_app.py",
        "pitch_generator/app_utils/__init__.py",
        "pitch_generator/app_utils/services.py",
        "pitch_generator/app_utils/memory_bank.py",
        "pitch_generator/app_utils/a2a.py",
    ]
    for rel in required_paths:
        target = PITCH_GEN_ROOT / rel
        assert target.is_file(), f"Missing required starter application file: {rel}"
        assert target.stat().st_size > 0, f"Starter application file is empty: {rel}"


def test_f1_pyproject_toml_and_env_example_contract() -> None:
    """
    /**
     * Verify `pyproject.toml` declares ADK/GenAI dependencies and `.env.example`
     * documents all required environment variables and model identifiers.
     *
     * Why: Ensures the package metadata matches `agents-cli` conventions and documents
     * Gemini Enterprise Agent Platform (`GOOGLE_GENAI_USE_ENTERPRISE`), `gemini-3.8-flash`,
     * `gemini-nano-banana-2.1`, Memory Bank, and Cloud Storage configuration keys.
     */
    """
    pyproject_text = (PITCH_GEN_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'name = "pitch-generator"' in pyproject_text or 'name = "pitch_generator"' in pyproject_text
    for dep in ("google-adk", "google-genai", "fastapi", "uvicorn", "pydantic"):
        assert dep in pyproject_text, f"pyproject.toml missing expected dependency: {dep}"

    env_example = (PITCH_GEN_ROOT / ".env.example").read_text(encoding="utf-8")
    for env_key in (
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_REGION",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_GENAI_USE_ENTERPRISE",
        "LOGS_BUCKET_NAME",
        "VISUAL_DIRECTOR_URL",
        "PITCH_GENERATOR_URL",
        "MEMORY_BANK_ID",
        "FLASH_MODEL=gemini-3.8-flash",
        "IMAGE_MODEL=gemini-nano-banana-2.1",
    ):
        assert env_key in env_example, f".env.example missing required key: {env_key}"
    assert "PRO_MODEL" not in env_example


# ============================================================================
# Feature F2: `PitchConfig` & Injectable Cloud Services (`services.py`, `memory_bank.py`)
# ============================================================================


@pytest.mark.parametrize(
    "enterprise_val,expected",
    [
        ("TRUE", True),
        ("true", True),
        ("1", True),
        ("false", False),
        ("0", False),
    ],
)
def test_f2_pitch_config_enterprise_resolution(
    enterprise_val: str, expected: bool
) -> None:
    """
    /**
     * Verify `get_config()` resolves `use_enterprise` from `GOOGLE_GENAI_USE_ENTERPRISE`
     * and sets `gemini-3.8-flash` and `gemini-nano-banana-2.1` as default models.
     *
     * Why: Ensures the Gemini Enterprise Agent Platform flag (`GOOGLE_GENAI_USE_ENTERPRISE`)
     * and model constants are parsed deterministically across boolean string representations.
     */
    """
    cfg = config.get_config(
        {
            "GOOGLE_CLOUD_PROJECT": "demo-proj",
            "GOOGLE_CLOUD_REGION": "europe-west1",
            "GOOGLE_GENAI_USE_ENTERPRISE": enterprise_val,
            "LOGS_BUCKET_NAME": "gs://demo-proj-bwg/",
        }
    )
    assert cfg.project_id == "demo-proj"
    assert cfg.region == "europe-west1"
    assert cfg.use_enterprise is expected
    assert cfg.logs_bucket_name == "demo-proj-bwg"
    assert cfg.flash_model == "gemini-3.8-flash"
    assert cfg.image_model == "gemini-nano-banana-2.1"
    assert not hasattr(cfg, "pro_model")


def test_f2_in_memory_and_gcs_artifact_services(
    in_memory_artifacts: services.InMemoryArtifactService,
    gcs_artifacts: services.GcsArtifactService,
) -> None:
    """
    /**
     * Verify `InMemoryArtifactService`, `GcsArtifactService`, and `get_artifact_service`
     * factory selection based on `LOGS_BUCKET_NAME`.
     *
     * Why: Ensures local tests use fast in-memory storage when `LOGS_BUCKET_NAME` is
     * unset, while production/Module 2b configurations persist versioned `gs://` URIs.
     */
    """
    png_bytes = b"\x89PNG\r\n\x1a\nfake-image-payload"
    rec1 = in_memory_artifacts.save_artifact("key_visual.png", png_bytes, session_id="s1")
    rec2 = in_memory_artifacts.save_artifact("key_visual.png", png_bytes + b"-v2", session_id="s1")
    assert rec1.version == 1
    assert rec2.version == 2
    assert rec1.gcs_uri is None
    loaded = in_memory_artifacts.get_artifact("key_visual.png", session_id="s1")
    assert loaded is not None
    assert loaded.version == 2
    assert len(in_memory_artifacts.list_artifacts(session_id="s1")) == 2

    with pytest.raises(ValueError, match="empty"):
        in_memory_artifacts.save_artifact("empty.png", b"", session_id="s1")

    gcs_rec = gcs_artifacts.save_artifact("key_visual.png", png_bytes, session_id="camp-42")
    assert gcs_rec.gcs_uri is not None
    assert gcs_rec.gcs_uri.startswith("gs://test-project-bwg-bwg/")
    assert gcs_rec.filename == "key_visual.png"

    cfg_local = config.get_config({"LOGS_BUCKET_NAME": ""})
    assert isinstance(services.get_artifact_service(cfg_local), services.InMemoryArtifactService)

    cfg_gcs = config.get_config({"LOGS_BUCKET_NAME": "gs://my-lab-bucket"})
    svc_gcs = services.get_artifact_service(cfg_gcs)
    assert isinstance(svc_gcs, services.GcsArtifactService)
    assert svc_gcs.bucket_name == "my-lab-bucket"
    r1 = svc_gcs.save_artifact("key_visual.png", png_bytes, session_id="s1")
    r2 = svc_gcs.save_artifact("key_visual.png", png_bytes + b"-v2", session_id="s1")
    assert r1.version == 1
    assert r2.version == 2
    assert r1.gcs_uri == "gs://my-lab-bucket/key-visuals/key_visual.png"


def test_f2_enterprise_genai_llm_client_and_default_service_container(
    test_config: config.PitchConfig,
) -> None:
    """
    /**
     * Verify `ServiceContainer` defaults to `EnterpriseGenAILLMClient` and delegates text and
     * image generation to `google.genai.Client.models.generate_content` using `gemini-3.8-flash`
     * and `gemini-nano-banana-2.1`.
     *
     * Why: Ensures runtime requests invoke live Gemini models on the Gemini Enterprise Agent
     * Platform when an SDK client is present while falling back to `DeterministicMockLLMClient`
     * offline.
     */
    """
    default_container = services.get_default_services(test_config)
    assert isinstance(default_container.llm, services.EnterpriseGenAILLMClient)

    class _FakeInlineData:
        data = services.MINIMAL_PNG_BYTES
        mime_type = "image/png"

    class _FakePart:
        inline_data = _FakeInlineData()

    class _FakeContent:
        parts = [_FakePart()]

    class _FakeCandidate:
        content = _FakeContent()

    class _FakeGenAIResponse:
        text = "Live Gemini Enterprise Agent Platform campaign concept"
        candidates = [_FakeCandidate()]

    class _FakeModels:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def generate_content(self, *, model: str, contents: str, config: Any = None) -> _FakeGenAIResponse:
            """
            /**
             * Record the `generate_content` invocation and return a stub response.
             *
             * Why: Simulates `google.genai.Client.models.generate_content` without network calls.
             */
            """
            self.calls.append({"model": model, "contents": contents, "config": config})
            return _FakeGenAIResponse()

    class _FakeGenAIClient:
        def __init__(self) -> None:
            self.models = _FakeModels()

    fake_sdk = _FakeGenAIClient()
    enterprise_llm = services.EnterpriseGenAILLMClient(config=test_config, sdk_client=fake_sdk)

    text_out = enterprise_llm.generate_text(
        "Eco-friendly running shoes",
        system_instruction="You are the Creative Director.",
    )
    assert text_out == "Live Gemini Enterprise Agent Platform campaign concept"
    assert len(fake_sdk.models.calls) == 1
    assert fake_sdk.models.calls[0]["model"] == "gemini-3.8-flash"

    img_bytes, img_mime = enterprise_llm.generate_image("Deep indigo studio product shot")
    assert img_bytes == services.MINIMAL_PNG_BYTES
    assert img_mime == "image/png"
    assert len(fake_sdk.models.calls) == 2
    assert fake_sdk.models.calls[1]["model"] == "gemini-nano-banana-2.1"

    # A3: Verify in-memory prompt deduplication/caching avoids duplicate SDK calls
    cached_text = enterprise_llm.generate_text(
        "Eco-friendly running shoes",
        system_instruction="You are the Creative Director.",
    )
    assert cached_text == text_out
    assert enterprise_llm.cache_hits == 1
    assert len(fake_sdk.models.calls) == 2

    # A1: Verify 429 RESOURCE_EXHAUSTED automatic retry with exponential backoff
    class _Flaky429Models:
        def __init__(self) -> None:
            self.attempts = 0

        def generate_content(self, *, model: str, contents: str, config: Any = None) -> _FakeGenAIResponse:
            """
            /**
             * Simulate two transient 429 quota errors before succeeding on attempt 3.
             *
             * Why: Verifies exponential backoff retry recovery in `EnterpriseGenAILLMClient`.
             */
            """
            self.attempts += 1
            if self.attempts < 3:
                raise Exception("429 RESOURCE_EXHAUSTED: Resource exhausted. Please try again later.")
            return _FakeGenAIResponse()

    class _Flaky429Client:
        def __init__(self) -> None:
            self.models = _Flaky429Models()

    flaky_sdk = _Flaky429Client()
    retry_llm = services.EnterpriseGenAILLMClient(
        config=test_config,
        sdk_client=flaky_sdk,
        max_retries=3,
        base_retry_delay_sec=0.005,
        min_call_interval_sec=0.005,
    )
    recovered = retry_llm.generate_text("Retry test brief")
    assert recovered == "Live Gemini Enterprise Agent Platform campaign concept"
    assert flaky_sdk.models.attempts == 3
    assert retry_llm.retry_count == 2


def test_f2_memory_bank_session_and_long_term_memory(
    memory_bank: memory_bank.MemoryBankService,
) -> None:
    """
    /**
     * Verify `MemoryBankService` persists session state and long-term memories with
     * query filtering and defensive copy isolation.
     *
     * Why: Prevents external mutation of stored session dicts and enables multi-turn
     * campaign memory retrieval in the starter app and Module 4 tokenomics.
     */
    """
    state = {"concept": "Rain-ready commuter bike", "step": "copywriter"}
    memory_bank.save_session("sess-101", state)
    state["concept"] = "MUTATED_LOCALLY"

    loaded = memory_bank.load_session("sess-101")
    assert loaded["concept"] == "Rain-ready commuter bike"
    assert memory_bank.load_session("nonexistent-session") == {}

    memory_bank.store_memory("brand_campaigns", "bike_pitch", {"tagline": "Ride dry in Seattle"})
    memory_bank.store_memory("brand_campaigns", "cat_skate", {"tagline": "Nine lives on four wheels"})

    all_mems = memory_bank.retrieve_memories("brand_campaigns")
    assert len(all_mems) == 2

    filtered = memory_bank.retrieve_memories("brand_campaigns", query="Seattle")
    assert len(filtered) == 1
    assert filtered[0]["key"] == "bike_pitch"

    with pytest.raises(ValueError):
        memory_bank.save_session("", {"a": 1})


def test_f2_bigquery_analytics_service_sql_and_scoring(
    bq_analytics: services.BigQueryAnalyticsService,
) -> None:
    """
    /**
     * Verify `BigQueryAnalyticsService` records telemetry events, constructs BigQuery
     * `ObjectRef` (`OBJ.MAKE_REF`, `OBJ.FETCH_METADATA`) and `AI.SCORE` SQL queries,
     * and evaluates brand compliance thresholds (`brand_fit >= 7.0`).
     *
     * Why: Validates the analytics foundation required by R1 and Module 2 (`bwg.key_visuals`
     * and `bwg.brand_review`) without executing live BigQuery jobs.
     */
    """
    bq_analytics.record_telemetry({"session_id": "s1", "node": "creative_director", "latency_ms": 42})
    assert len(bq_analytics.events) == 1

    kv_sql = bq_analytics.build_key_visuals_sql(
        project_id="demo-proj",
        region="us-central1",
        bucket_name="demo-proj-bwg",
    )
    assert "bwg.key_visuals" in kv_sql
    assert "OBJ.MAKE_REF" in kv_sql
    assert "OBJ.FETCH_METADATA" in kv_sql
    assert "us-central1.pitch-connection" in kv_sql

    score_sql = bq_analytics.build_brand_score_sql(
        project_id="demo-proj",
        region="us-central1",
    )
    assert "bwg.brand_review" in score_sql
    assert "AI.SCORE" in score_sql
    assert "brand_fit >= 7" in score_sql
    assert "on brand" in score_sql
    assert "needs another pass" in score_sql

    scored = bq_analytics.score_brand_compliance(
        [
            {"campaign_id": "c1", "brand_fit": 8.5},
            {"campaign_id": "c2", "brand_fit": 5.2},
        ]
    )
    assert scored[0]["verdict"] == "on brand"
    assert scored[1]["verdict"] == "needs another pass"


# ============================================================================
# Feature F3: Baseline Multi-Agent Workflow, FastAPI & A2A Endpoints
# ============================================================================


def test_f3_run_pitch_workflow_happy_path_and_hitl_states(
    service_container: services.ServiceContainer,
) -> None:
    """
    /**
     * Verify `run_pitch_workflow` orchestrates the starter 4-specialist workflow
     * (`creative_director`, `copywriter`, `brand_strategist`, `visual_director`,
     * `assemble` (`JoinNode`), and `package`) on `gemini-3.8-flash` and persists
     * session state in Memory Bank.
     *
     * Why: Confirms the starter multi-agent workflow executes all four specialists
     * in parallel fan-out/fan-in and generates a key visual.
     */
    """
    result = agent.run_pitch_workflow(
        "A commuter bike built for rainy cities",
        session_id="sess-bike",
        services=service_container,
        approved=True,
    )
    assert result["session_id"] == "sess-bike"
    assert result["status"] == "completed"
    assert result["concept"]
    assert result["copy"]
    assert len(result["copy"].split()) <= 25
    assert result["brand_strategy"]
    assert result["art_direction"]
    assert result["key_visual_uri"] is not None
    assert result["trace"] == [
        "creative_director",
        "copywriter",
        "brand_strategist",
        "visual_director",
        "assemble",
        "package",
    ]
    assert "telemetry" in result

    saved_session = service_container.memory_bank.load_session("sess-bike")
    assert saved_session.get("status") == "completed"
    assert saved_session.get("concept") == result["concept"]

    paused = agent.run_pitch_workflow(
        "Solar-powered espresso maker for campers",
        session_id="sess-pause",
        services=service_container,
        approved=None,
    )
    assert paused["status"] == "input_required"
    assert paused["concept"]

    rejected = agent.run_pitch_workflow(
        "Solar-powered espresso maker for campers",
        session_id="sess-reject",
        services=service_container,
        approved=False,
    )
    assert rejected["status"] == "rejected"

    with pytest.raises(ValueError):
        agent.run_pitch_workflow("   ", session_id="sess-empty", services=service_container)


def test_f3_specialist_agents_and_run_specialist_team() -> None:
    """
    /**
     * Verify specialist agent definitions (`creative_director`, `copywriter`,
     * `brand_strategist`, `visual_director`) and `run_specialist_team` in `agent.py`.
     *
     * Why: Confirms the starter application includes all four domain specialists
     * with isolated `output_key` bindings and a <= 25 word caption constraint.
     */
    """
    for attr in ("creative_director", "copywriter", "brand_strategist", "visual_director"):
        spec_agent = getattr(agent, attr)
        assert getattr(spec_agent, "name", "") == attr
        assert getattr(spec_agent, "output_key", "") == attr
        assert len(getattr(spec_agent, "instruction", "").strip()) > 20

    result = agent.run_specialist_team("Waterproof commuter jacket with sealed seams")
    assert isinstance(result, dict)
    assert len(result) == 4
    assert len(str(result["copywriter"]).split()) <= 25

    with pytest.raises(ValueError):
        agent.run_specialist_team("   ")


def test_f3_structured_payloads_and_markdown_fence_parser() -> None:
    """
    /**
     * Verify `strip_markdown_fences`, `parse_json_payload`, and `ConceptPayload` in `agent.py`.
     *
     * Why: Confirms the starter workflow strips ```json fences cleanly and validates
     * structured JSON handoffs between graph nodes.
     */
    """
    fenced = '```json\n{"concept_line": "Urban shell", "rationale": "Commuter ready"}\n```'
    stripped = agent.strip_markdown_fences(fenced)
    assert stripped == '{"concept_line": "Urban shell", "rationale": "Commuter ready"}'

    parsed = agent.parse_json_payload(fenced, getattr(agent, "ConceptPayload", None))
    if hasattr(parsed, "concept_line"):
        assert parsed.concept_line == "Urban shell"
        assert parsed.rationale == "Commuter ready"
    else:
        assert parsed["concept_line"] == "Urban shell"
        assert parsed["rationale"] == "Commuter ready"

    for bad_raw in ("{unclosed", "{}"):
        with pytest.raises((ValueError, TypeError, KeyError)):
            agent.parse_json_payload(bad_raw, getattr(agent, "ConceptPayload", None))


def test_f3_loop_guard_cycle_detection_and_iteration_bounds() -> None:
    """
    /**
     * Verify `LoopGuard` detects self-loops, 2-node, and 3-node cycles and enforces `max_iterations`.
     *
     * Why: Confirms `agent.LoopGuard` and `agent.CircularLoopError` prevent infinite circular
     * loops in static graph topologies and runtime execution.
     */
    """
    guard = agent.LoopGuard(max_iterations=10)
    assert guard.validate_graph(
        [("creative_director", "copywriter"), ("copywriter", "assemble")]
    )

    with pytest.raises(agent.CircularLoopError):
        guard.validate_graph([("node_a", "node_a")])

    with pytest.raises(agent.CircularLoopError):
        guard.validate_graph([("node_a", "node_b"), ("node_b", "node_a")])

    with pytest.raises(agent.CircularLoopError):
        guard.validate_graph(
            [
                ("creative_director", "copywriter"),
                ("copywriter", "assemble"),
                ("assemble", "creative_director"),
            ]
        )

    with pytest.raises((agent.CircularLoopError, ValueError)):
        g0 = agent.LoopGuard(max_iterations=0)
        g0.record_step("node_1")

    g2 = agent.LoopGuard(max_iterations=2)
    g2.record_step("node_1")
    g2.record_step("node_2")
    with pytest.raises(agent.CircularLoopError):
        g2.record_step("node_3")


def test_f3_adk_graph_exports_and_join_validation() -> None:
    """
    /**
     * Verify `agent.py` exports `root_agent`, `app`, `creative_director`, `copywriter`,
     * `assemble` (`JoinNode`), and `package` (which raises `ValueError` on missing branch output).
     *
     * Why: Preserves structural continuity with the `agents-cli` ADK scaffold and
     * Part 1 `package(ctx, node_input)` validation contract.
     */
    """
    assert hasattr(agent, "root_agent")
    assert hasattr(agent, "app")
    assert hasattr(agent, "creative_director")
    assert hasattr(agent, "copywriter")
    assert hasattr(agent, "assemble")
    assert hasattr(agent, "package")

    with pytest.raises(ValueError, match="nothing reached the join"):
        agent.package(None, {"concept": "", "copy": "Valid tagline"})


def test_f3_fastapi_rest_and_a2a_endpoints(api_client: Any) -> None:
    """
    /**
     * Verify HTTP REST (`/api/health`, `/api/config`, `/api/pitch`),
     * A2A (`/a2a/pitch_generator/.well-known/agent-card.json`, `/a2a/pitch_generator`),
     * and static frontend (`/`) endpoints in `fast_api_app.py`.
     *
     * Why: Ensures the Cloud Run web server exposes every endpoint expected by the
     * vanilla JS frontend (`frontend/app.js`), `call_agent.py`, and remote A2A callers.
     */
    """
    health_resp = api_client.get("/api/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "ok"
    assert health_data["service"] == "pitch-generator"

    for health_alias in ("/healthz", "/health"):
        alias_resp = api_client.get(health_alias)
        assert alias_resp.status_code == 200
        assert alias_resp.json()["status"] == "ok"

    cfg_resp = api_client.get("/api/config")
    assert cfg_resp.status_code == 200
    cfg_data = cfg_resp.json()
    assert cfg_data["models"]["flash"] == "gemini-3.8-flash"
    assert cfg_data["models"]["image"] == "gemini-nano-banana-2.1"
    assert "pro" not in cfg_data["models"]

    pitch_resp = api_client.post(
        "/api/pitch",
        json={
            "brief": "Flying skateboards for cats",
            "session_id": "http-sess-1",
            "require_approval": False,
        },
    )
    assert pitch_resp.status_code == 200
    pitch_data = pitch_resp.json()
    assert pitch_data["status"] == "completed"
    assert pitch_data["concept"]
    assert pitch_data["copy"]

    # Posting require_approval=True before Step 3c (approve_concept not defined) still completes
    pre_hitl_resp = api_client.post(
        "/api/pitch",
        json={
            "brief": "Flying skateboards for cats",
            "session_id": "http-sess-pre-hitl",
            "require_approval": True,
        },
    )
    assert pre_hitl_resp.status_code == 200
    pre_hitl_data = pre_hitl_resp.json()
    assert pre_hitl_data["status"] == "completed"
    assert pre_hitl_data["hitl_enabled"] is False
    assert pre_hitl_data["hitl_requested"] is True

    card_resp = api_client.get("/a2a/pitch_generator/.well-known/agent-card.json")
    assert card_resp.status_code == 200
    card_data = card_resp.json()
    assert card_data["name"] == "pitch_generator"
    assert "capabilities" in card_data

    a2a_resp = api_client.post(
        "/a2a/pitch_generator",
        json={
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": "Modular solar backpack"}],
                }
            },
        },
    )
    assert a2a_resp.status_code == 200
    a2a_payload = a2a_resp.json()
    assert a2a_payload.get("jsonrpc") == "2.0"
    assert "result" in a2a_payload

    index_resp = api_client.get("/")
    assert index_resp.status_code == 200
    assert "<!DOCTYPE html>" in index_resp.text or "<html" in index_resp.text


def test_f3_call_agent_cli_offline_invocation(tmp_path: pathlib.Path) -> None:
    """
    /**
     * Verify `call_agent.py` can execute an offline pitch request and save key visual
     * output to disk.
     *
     * Why: Learners use `call_agent.py` during the Project Walkthrough and HITL/A2A
     * exercises to test the agent from the terminal.
     */
    """
    import call_agent

    output_img = tmp_path / "key_visual.png"
    response = call_agent.run_cli_pitch(
        brief="Smart umbrella that predicts wind gusts",
        auto_approve=True,
        output_image_path=output_img,
        force_offline=True,
    )
    assert response["status"] == "completed"
    assert response["concept"]
    assert response["copy"]
    assert output_img.is_file()
    assert output_img.stat().st_size > 0


# ============================================================================
# Feature F4: Plain HTML/CSS/JS Web Frontend Verification
# ============================================================================


def test_f4_plain_html_css_js_frontend_zero_frameworks() -> None:
    """
    /**
     * Verify that `frontend/` uses strictly plain HTML5, CSS3, and vanilla ES6 JS
     * with zero prohibited frontend frameworks (React, Vue, Angular, Streamlit)
     * and wires starter backend endpoints cleanly without premature WebLLM/Gemma controls.
     *
     * Why: Enforces Requirement R1 & Acceptance Criterion 2 while keeping the starter
     * UI focused on Gemini Enterprise Agent Platform.
     */
    """
    html_text = (PITCH_GEN_ROOT / "frontend/index.html").read_text(encoding="utf-8")
    css_text = (PITCH_GEN_ROOT / "frontend/styles.css").read_text(encoding="utf-8")
    js_text = (PITCH_GEN_ROOT / "frontend/app.js").read_text(encoding="utf-8")

    combined_lower = (html_text + "\n" + css_text + "\n" + js_text).lower()
    forbidden_patterns = [
        r"\breact\b",
        r"\breact-dom\b",
        r"\bvue\b",
        r"\bangular\b",
        r"\bstreamlit\b",
        r"unpkg\.com/react",
        r"cdn\.jsdelivr\.net/npm/vue",
    ]
    for pat in forbidden_patterns:
        assert not re.search(pat, combined_lower), f"Prohibited frontend framework pattern found: {pat}"

    assert "<!DOCTYPE html>" in html_text
    assert "styles.css" in html_text
    assert "app.js" in html_text
    assert "hitl-approval-card" in html_text
    assert "require-approval-checkbox" in html_text
    assert "webgpu-badge" not in html_text
    assert "routing-mode-select" not in html_text
    assert "local_model" not in html_text
    assert "gemma" not in html_text
    for endpoint in (
        "/api/health",
        "/api/config",
        "/api/pitch",
        "/api/approve",
        "/a2a/pitch_generator/.well-known/agent-card.json",
    ):
        assert endpoint in js_text, f"frontend/app.js does not connect to {endpoint}"


# ============================================================================
# Feature F5: Infrastructure, Shell Scripts (`bash -n`) & Terraform (`fmt -check`)
# ============================================================================


def test_f5_shell_scripts_pass_bash_syntax_check_and_dynamic_deploy() -> None:
    """
    /**
     * Execute `bash -n` on all shell scripts in `pitch-generator/` (`setenv.sh`,
     * `scripts/setup.sh`, `scripts/deploy.sh`) and verify `scripts/deploy.sh --dry-run`
     * dynamically deploys only `pitch-generator` in the starter state.
     *
     * Why: Enforces Acceptance Criterion 5 and verifies smart dynamic service detection.
     */
    """
    scripts = [
        PITCH_GEN_ROOT / "scripts/setup.sh",
        PITCH_GEN_ROOT / "scripts/deploy.sh",
    ]
    for script_path in scripts:
        proc = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"bash -n failed for {script_path}: {proc.stderr}"

    deploy_proc = subprocess.run(
        ["bash", str(PITCH_GEN_ROOT / "scripts/deploy.sh"), "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert deploy_proc.returncode == 0
    assert "Deploying pitch-generator to Cloud Run" in deploy_proc.stdout
    assert "Deploying visual-director to Cloud Run" not in deploy_proc.stdout


def test_f5_terraform_fmt_check_and_validate_and_untouched_lab_tf() -> None:
    """
    /**
     * Verify `pitch-generator/terraform/` passes `terraform fmt -check` and defines
     * valid Terraform configuration blocks.
     *
     * Why: Enforces Requirement R4 and Acceptance Criterion 5 offline without
     * requiring network provider downloads.
     */
    """
    tf_dir = PITCH_GEN_ROOT / "terraform"
    if not tf_dir.is_dir():
        return
    fmt_proc = subprocess.run(
        ["terraform", "fmt", "-check", str(tf_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert fmt_proc.returncode == 0, f"terraform fmt -check failed: {fmt_proc.stdout} {fmt_proc.stderr}"

    main_tf = (tf_dir / "main.tf").read_text(encoding="utf-8")
    assert "google_cloud_run_v2_service" in main_tf
    assert "GOOGLE_GENAI_USE_ENTERPRISE" in main_tf


# ============================================================================
# Feature F6: Javadoc-Style "Why" Comments & Modularity Audit
# ============================================================================


def test_f6_javadoc_style_why_comments_across_all_starter_files() -> None:
    """
    /**
     * Audit every Python, JS, and CSS source file in `pitch-generator/` to verify
     * Javadoc-style comments (`/** ... */`) and `Why:` design rationale explanations
     * on modules, classes, and public functions.
     *
     * Why: Enforces `RULE[user_global]` and Acceptance Criterion 4 of R1
     * (`ORIGINAL_REQUEST.md` lines 23, 50).
     */
    """
    py_files = sorted(
        list((PITCH_GEN_ROOT / "pitch_generator").rglob("*.py"))
        + [PITCH_GEN_ROOT / "call_agent.py"]
        + list((PITCH_GEN_ROOT / "tests").glob("*.py"))
    )
    assert py_files, "No Python files found to audit"

    for py_file in py_files:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
        mod_doc = ast.get_docstring(tree)
        assert mod_doc, f"Missing module docstring in {py_file.relative_to(PITCH_GEN_ROOT)}"
        assert "Why:" in mod_doc or "/**" in mod_doc, (
            f"Module docstring in {py_file.relative_to(PITCH_GEN_ROOT)} must include Javadoc-style 'Why:' rationale"
        )

        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                doc = ast.get_docstring(node)
                assert doc, (
                    f"Missing docstring on public symbol '{node.name}' in {py_file.relative_to(PITCH_GEN_ROOT)}"
                )
                assert "Why:" in doc or "/**" in doc or "@param" in doc or "@return" in doc, (
                    f"Docstring on '{node.name}' in {py_file.relative_to(PITCH_GEN_ROOT)} lacks Javadoc/Why rationale"
                )

    for web_file in (PITCH_GEN_ROOT / "frontend/app.js", PITCH_GEN_ROOT / "frontend/styles.css"):
        content = web_file.read_text(encoding="utf-8")
        assert "/**" in content and "Why:" in content, (
            f"{web_file.relative_to(PITCH_GEN_ROOT)} must include Javadoc '/** ... Why: ... */' comments"
        )
