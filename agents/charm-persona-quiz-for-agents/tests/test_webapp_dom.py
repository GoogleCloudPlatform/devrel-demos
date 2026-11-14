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

"""DOM, Agent-API, and End-to-End tests for the GitHub Pages OCEAN app."""

from __future__ import annotations

from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pytest

from charm_gemini.client import (
    call_gemini_decisions_api,
    evaluate_browser_decisions_via_jsc,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
JSC_BIN = Path(
    shutil.which("jsc")
    or "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc"
)
requires_jsc = pytest.mark.skipif(
    not JSC_BIN.exists(),
    reason="JavaScriptCore (jsc) binary not found",
)


def _strip_esm_syntax(js_source: str) -> str:
    """Strip ES module import/export keywords so WebKit jsc can run top-level code."""
    no_imports = re.sub(
        r"^\s*import\s+[\s\S]*?from\s+['\"].*?['\"];?\s*$",
        "",
        js_source,
        flags=re.MULTILINE,
    )
    return (
        no_imports.replace("export const ", "const ")
        .replace("export async function ", "async function ")
        .replace("export function ", "function ")
    )


def _run_jsc(js_code: str) -> str:
    with tempfile.NamedTemporaryFile(
        "w", suffix=".js", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(js_code)
        tmp_path = tmp.name
    try:
        proc = subprocess.run(
            [str(JSC_BIN), tmp_path],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise AssertionError(
                f"JSC execution failed (exit {proc.returncode}):\n"
                f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
        return proc.stdout.strip()
    finally:
        Path(tmp_path).unlink(missing_ok=True)


class QuestionnaireFormInspector(HTMLParser):
    """Inspect index.html to verify zero multiple-choice inputs in the questionnaire."""

    def __init__(self) -> None:
        super().__init__()
        self.in_form = False
        self.form_depth = 0
        self.textarea_ids: list[str] = []
        self.radio_or_checkbox_inputs: list[dict[str, str]] = []
        self.selects_in_form: list[dict[str, str]] = []
        self.script_blocks: dict[str, str] = {}
        self._current_script_id: str | None = None
        self._current_script_chunks: list[str] = []
        self.all_ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: (v or "") for k, v in attrs}
        elem_id = attr_map.get("id", "")
        if elem_id:
            self.all_ids.add(elem_id)

        if tag == "form" and elem_id == "ocean-questionnaire-form":
            self.in_form = True
            self.form_depth = 1
        elif self.in_form and tag == "form":
            self.form_depth += 1

        if self.in_form:
            if tag == "textarea" and elem_id:
                self.textarea_ids.append(elem_id)
            elif tag == "input" and attr_map.get("type", "").lower() in {
                "radio",
                "checkbox",
            }:
                self.radio_or_checkbox_inputs.append(attr_map)
            elif tag == "select":
                self.selects_in_form.append(attr_map)

        if tag == "script" and elem_id:
            self._current_script_id = elem_id
            self._current_script_chunks = []

    def handle_data(self, data: str) -> None:
        if self._current_script_id is not None:
            self._current_script_chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.in_form and tag == "form":
            self.form_depth -= 1
            if self.form_depth <= 0:
                self.in_form = False
        if tag == "script" and self._current_script_id is not None:
            self.script_blocks[self._current_script_id] = "".join(
                self._current_script_chunks
            ).strip()
            self._current_script_id = None
            self._current_script_chunks = []


def test_index_html_enforces_open_ended_paragraphs_and_zero_multiple_choice() -> None:
    index_path = REPO_ROOT / "index.html"
    assert index_path.exists(), "index.html must exist at repository root for GitHub Pages"

    html = index_path.read_text(encoding="utf-8")
    inspector = QuestionnaireFormInspector()
    inspector.feed(html)

    assert inspector.textarea_ids == [f"prompt-q{i}" for i in range(1, 16)]
    assert (
        inspector.radio_or_checkbox_inputs == []
    ), "Questionnaire form must contain zero radio or checkbox multiple-choice inputs"
    assert (
        inspector.selects_in_form == []
    ), "Questionnaire form must contain zero <select> dropdowns for agent answers"

    # Machine-readable schema block for headless/DOM agents
    assert "agent-questionnaire-schema" in inspector.script_blocks
    schema = json.loads(inspector.script_blocks["agent-questionnaire-schema"])
    assert schema["protocol"] == "charm.v1"
    assert schema["decision_model"] == "gemini-decision-1"
    assert schema["api_contract"] == "/v1beta/decisions"
    assert schema["multiple_choice_allowed"] is False
    assert schema["response_type"] == "paragraph"
    assert len(schema["prompts"]) == 15

    # Machine-readable output block for headless/DOM agents
    assert "ocean-result-json" in inspector.script_blocks
    initial_result = json.loads(inspector.script_blocks["ocean-result-json"])
    assert initial_result["status"] == "awaiting_submission"
    assert initial_result["decision_model"] == "gemini-decision-1"

    # Key UI landmarks + Tabletop Player Mat star footers
    for required_id in [
        "agent-id",
        "agent-model",
        "evaluate-btn",
        "transport-mode",
        "ocean-radar-svg",
        "trait-cards-container",
        "archetype-banner",
        "noul-indicators",
        "raw-json-inspector",
        "stars-q1",
        "stars-q5",
        "stars-q15",
        "ocean-glossary-deck",
        "ocean-def-stack",
        "ocean-def-prev-btn",
        "ocean-def-next-btn",
        "question-stack-slot",
        "question-card-stack",
        "question-prev-btn",
        "question-next-btn",
        "question-stack-indicator",
        "wild-persona-card",
        "wild-persona-name",
        "wild-persona-desc",
    ]:
        assert required_id in inspector.all_ids, f"Missing required element #{required_id}"

    assert "format-c-codex" not in inspector.all_ids, "Standalone #format-c-codex section must be deleted"

    assert "player-mat" in html
    assert "menu-card" in html
    assert "mat-rulebook-footer" in html
    for q_label in [
        "Question 1",
        "Question 2",
        "Question 3",
        "Question 4",
        "Question 5",
    ]:
        assert q_label in html, f"Expected neutral card label '{q_label}' in index.html"
    for giveaway in [
        "GLIMMER-SNOUT PUFFLE",
        "CLOCKWORK BRISTLE-TOAD",
        "CHATTER-PLUME PIPKIN",
        "MOSS-BELLY SNOOTLING",
        "JITTER-QUILL FIZZLET",
        "- Openness (O) -",
        "- Conscientiousness (C) -",
        "- Extraversion (E) -",
        "- Agreeableness (A) -",
        "- Neuroticism (N) -",
    ]:
        assert giveaway not in html, f"Question cards must not contain '{giveaway}'"


@requires_jsc
def test_app_js_exposes_charm_agent_api_and_never_fails_silently_in_jsc() -> None:
    app_js_path = REPO_ROOT / "app.js"
    assert app_js_path.exists(), "app.js must exist at repository root"

    raw_app_js = app_js_path.read_text(encoding="utf-8")
    assert (
        "evaluateBrowserSystemOne" not in raw_app_js
    ), "app.js must never import or invoke Tier 2 evaluateBrowserSystemOne as a fallback"

    ocean_core_js = _strip_esm_syntax(
        (REPO_ROOT / "ocean-core.js").read_text(encoding="utf-8")
    )
    app_js = _strip_esm_syntax(raw_app_js)

    script = f"""
    const elementsById = {{}};
    function makeEl(id) {{
      return {{
        id: id,
        value: "",
        textContent: "",
        innerHTML: "",
        disabled: false,
        hidden: true,
        className: "",
        dataset: {{}},
        style: {{}},
        classList: {{
          add: function() {{}},
          remove: function() {{}},
          toggle: function() {{}},
          contains: function() {{ return false; }}
        }},
        addEventListener: function() {{}},
        setAttribute: function() {{}},
        getAttribute: function() {{ return null; }},
        appendChild: function() {{}},
        querySelectorAll: function() {{ return []; }},
        querySelector: function() {{ return makeEl("child"); }}
      }};
    }}
    globalThis.window = globalThis;
    globalThis.document = {{
      getElementById: function(id) {{
        if (!elementsById[id]) elementsById[id] = makeEl(id);
        return elementsById[id];
      }},
      querySelectorAll: function() {{ return []; }},
      querySelector: function() {{ return makeEl("qs"); }},
      createElement: function(tag) {{ return makeEl(tag); }},
      createElementNS: function(ns, tag) {{ return makeEl(tag); }},
      addEventListener: function(evt, fn) {{
        if (evt === "DOMContentLoaded") fn();
      }}
    }};
    {ocean_core_js}
    {app_js}
    (async () => {{
      const api = window.CHARM_AGENT_API;
      const questions = api.getQuestions();
      const formatCPersonas = api.getFormatCPersonas();
      api.loadPreset("sentinel");
      const loadedCombo = api.loadFormatCCombo("OCEAN");

      // Verify that calling evaluate() without a live model throws and surfaces #form-error-banner
      let threwError = false;
      let caughtMessage = "";
      try {{
        await api.evaluate();
      }} catch (err) {{
        threwError = true;
        caughtMessage = String(err.message || err);
      }}

      // Explicitly render a test profile using the test-only harness to verify DOM rendering
      const testPayload = buildSystemOnePayload(loadedCombo.agentId, loadedCombo.responses);
      const testRaw = evaluateBrowserSystemOne(testPayload);
      const testProfile = normalizeOceanProfile(testRaw, loadedCombo.agentId);
      api.renderProfileToDom(testProfile, testPayload, "Gemini Decision 1 (gemini-decision-1)");

      const populatedState = {{
        wildPersonaName: elementsById["wild-persona-name"].textContent,
        wildPersonaDesc: elementsById["wild-persona-desc"].textContent,
        traitCardsContainerHtml: elementsById["trait-cards-container"].innerHTML,
        starsConscientiousnessHtml: elementsById["stars-q2"].innerHTML,
        badgeCVal: elementsById["badge-c-val"].textContent,
        oceanCodeBadgeText: elementsById["ocean-code-badge"].textContent,
        archetypeTitleText: elementsById["archetype-title"].textContent,
        archetypeTaglineText: elementsById["archetype-tagline"].textContent,
      }};

      // Test flipping left and right through the Question 1-15 card stack
      const initialIdx = api.getActiveQuestionIndex();
      const nextIdx = api.flipQuestionCard(1);
      const indicatorAfterNext = elementsById["question-stack-indicator"].textContent;
      const wrappedPrevIdx = api.setActiveQuestionCard(0) || api.flipQuestionCard(-1);
      const indicatorAfterWrap = elementsById["question-stack-indicator"].textContent;
      const sentinelOpennessLen = elementsById["prompt-q1"].value.length;

      // Verify resetMat() clears all cards back to awaiting state
      api.resetMat();

      print(JSON.stringify({{
        hasApi: Boolean(api),
        questionCount: questions.length,
        formatCCount: formatCPersonas.length,
        loadedComboCode: loadedCombo ? loadedCombo.persona.code : null,
        initialIdx: initialIdx,
        nextIdx: nextIdx,
        indicatorAfterNext: indicatorAfterNext,
        wrappedPrevIdx: wrappedPrevIdx,
        indicatorAfterWrap: indicatorAfterWrap,
        threwError: threwError,
        caughtMessage: caughtMessage,
        errorBannerHidden: elementsById["form-error-banner"].hidden,
        statusPillText: elementsById["transport-status-pill"].textContent,
        sentinelOpennessLen: sentinelOpennessLen,
        agentIdValue: elementsById["agent-id"].value,
        starsConscientiousnessHtml: populatedState.starsConscientiousnessHtml,
        badgeCVal: populatedState.badgeCVal,
        oceanCodeBadgeText: populatedState.oceanCodeBadgeText,
        archetypeTitleText: populatedState.archetypeTitleText,
        archetypeTaglineText: populatedState.archetypeTaglineText,
        traitCardsContainerHtml: populatedState.traitCardsContainerHtml,
        wildPersonaName: populatedState.wildPersonaName,
        wildPersonaDesc: populatedState.wildPersonaDesc,
        afterResetArchetypeTitle: elementsById["archetype-title"].textContent,
        afterResetWildPersonaName: elementsById["wild-persona-name"].textContent,
        afterResetTraitCardsLen: elementsById["trait-cards-container"].innerHTML.length,
        afterResetRadarLen: elementsById["ocean-radar-svg"].innerHTML.length,
        afterResetOpennessVal: elementsById["prompt-q1"].value
      }}));
    }})();
    """
    stdout = _run_jsc(script)
    out = json.loads(stdout.splitlines()[-1])
    assert out["hasApi"] is True
    assert out["questionCount"] == 15
    assert out["formatCCount"] == 32
    assert out["loadedComboCode"] == "OCEAN"
    assert out["initialIdx"] == 0
    assert out["nextIdx"] == 1
    assert out["indicatorAfterNext"] == "Card 2 of 15"
    assert out["wrappedPrevIdx"] == 14
    assert out["indicatorAfterWrap"] == "Card 15 of 15"
    assert out["threwError"] is True
    assert "Heuristic Tier 2 fallback is disabled" in out["caughtMessage"]
    assert out["errorBannerHidden"] is True
    assert out["statusPillText"] == "Error · Live Model Unavailable"
    assert out["sentinelOpennessLen"] >= 120
    assert out["agentIdValue"] == "flow-32-OCEAN-vanguard"
    assert out["starsConscientiousnessHtml"] == ""
    assert "★" in out["badgeCVal"]
    assert "O+" in out["oceanCodeBadgeText"]
    assert out["archetypeTitleText"] == "Vanguard"
    assert "Flow #" not in out["archetypeTaglineText"]
    assert "Openness to Experience" in out["traitCardsContainerHtml"]
    assert out["wildPersonaName"] == "Vanguard (OCEAN)"
    assert out["wildPersonaDesc"] == "Holistic, meticulous, outgoing, empathetic, and hyper-vigilant."
    assert out["afterResetArchetypeTitle"] == "Awaiting Score"
    assert out["afterResetWildPersonaName"] == "Awaiting Score"
    assert out["afterResetTraitCardsLen"] == 0
    assert out["afterResetRadarLen"] == 0
    assert out["afterResetOpennessVal"] == ""


@requires_jsc
def test_end_to_end_ocean_core_with_gemini_decision_1() -> None:
    """Verify ocean-core.js payload -> test-only JSC harness -> ocean-core.js normalizer, and strict error on missing key."""
    ocean_core_js = _strip_esm_syntax(
        (REPO_ROOT / "ocean-core.js").read_text(encoding="utf-8")
    )

    # Step 1: Build Decisions API payload in JS from preset "explorer"
    build_script = f"""
    {ocean_core_js}
    const preset = PRESET_AGENTS.explorer;
    const payload = buildSystemOnePayload(preset.agentId, preset.responses, "gemini-decision-1");
    print(JSON.stringify(payload));
    """
    stdout1 = _run_jsc(build_script)
    payload = json.loads(stdout1.splitlines()[-1])

    # Step 2: Verify call_gemini_decisions_api raises RuntimeError when live model key is missing
    try:
        call_gemini_decisions_api(request_payload=payload, api_key="", timeout=5.0)
        raise AssertionError("Expected RuntimeError when live model is unavailable")
    except RuntimeError as exc:
        assert "Tier 2 heuristic fallback is disabled" in str(exc)

    # Step 3: Evaluate payload using explicit test-only JSC harness
    raw_systemone = evaluate_browser_decisions_via_jsc(request_payload=payload)
    assert "gemini-decision-1" in raw_systemone["model"].lower()

    # Step 3: Normalize raw Gemini Decision 1 output in JS via normalizeOceanProfile
    normalize_script = f"""
    {ocean_core_js}
    const raw = {json.dumps(raw_systemone)};
    const profile = normalizeOceanProfile(raw, "atlas-explorer-v2");
    print(JSON.stringify(profile));
    """
    stdout2 = _run_jsc(normalize_script)
    profile = json.loads(stdout2.splitlines()[-1])
    assert "gemini-decision-1" in profile["meta"]["model"].lower()
    assert set(profile["traits"].keys()) == {
        "openness",
        "conscientiousness",
        "extraversion",
        "agreeableness",
        "neuroticism",
    }
    for trait_key, trait_val in profile["traits"].items():
        assert 0 <= trait_val["percentage"] <= 100
        assert len(trait_val["levels"]) == 5, f"Missing 5 levels for {trait_key}"
    assert profile["archetype"]["id"] in {
        "inventive_architect",
        "methodical_sentinel",
        "diplomatic_coordinator",
        "autonomous_specialist",
        "vigilant_realist",
    }
    assert 0.0 <= profile["flags"]["rubricGamingProbability"] <= 1.0
    assert 0.0 <= profile["flags"]["selfReflectionProbability"] <= 1.0


@requires_jsc
def test_render_profile_to_dom_escapes_untrusted_html() -> None:
    """Verify renderProfileToDom neutralizes XSS payloads inside profile fields."""
    ocean_core_js = _strip_esm_syntax(
        (REPO_ROOT / "ocean-core.js").read_text(encoding="utf-8")
    )
    app_js = _strip_esm_syntax(
        (REPO_ROOT / "app.js").read_text(encoding="utf-8")
    )
    script = f"""
    const elementsById = {{}};
    function makeEl(id) {{
      return {{
        id: id,
        value: "",
        textContent: "",
        innerHTML: "",
        disabled: false,
        hidden: true,
        className: "",
        dataset: {{}},
        style: {{}},
        classList: {{ add: function() {{}}, remove: function() {{}}, toggle: function() {{}}, contains: function() {{ return false; }} }},
        addEventListener: function() {{}},
        setAttribute: function() {{}},
        getAttribute: function() {{ return null; }},
        appendChild: function() {{}},
        querySelectorAll: function() {{ return []; }},
        querySelector: function() {{ return makeEl("child"); }}
      }};
    }}
    globalThis.window = globalThis;
    globalThis.document = {{
      getElementById: function(id) {{
        if (!elementsById[id]) elementsById[id] = makeEl(id);
        return elementsById[id];
      }},
      querySelectorAll: function() {{ return []; }},
      querySelector: function() {{ return makeEl("qs"); }},
      createElement: function(tag) {{ return makeEl(tag); }},
      createElementNS: function(ns, tag) {{ return makeEl(tag); }},
      addEventListener: function(evt, fn) {{ if (evt === "DOMContentLoaded") fn(); }}
    }};
    {ocean_core_js}
    {app_js}
    const payload = buildSystemOnePayload("xss-test", PRESET_AGENTS.explorer.responses);
    const raw = evaluateBrowserSystemOne(payload);
    const profile = normalizeOceanProfile(raw, "xss-test");
    profile.formatC.topCombos[0].archetype = '<img src=x onerror="alert(1)">';
    profile.formatC.topCombos[0].description = '<script>alert(2)</script>';
    profile.traits.openness.levels[0].label = '"><svg onload=alert(3)>';
    const oceanMatchesHtml = (() => {{
      const p2 = Object.assign({{}}, profile, {{
        formatC: Object.assign({{}}, window.CHARM_AGENT_API.getFormatCPersonas()[0], {{ probability: 0.9, topCombos: profile.formatC.topCombos }})
      }});
      window.CHARM_AGENT_API.renderProfileToDom(p2, payload, "src");
      return elementsById["wild-persona-matches"].innerHTML;
    }})();
    window.CHARM_AGENT_API.renderProfileToDom(profile, payload, '<b onclick=alert(4)>src</b>');
    print(JSON.stringify({{
      metaHtml: elementsById["results-meta-line"].innerHTML,
      distHtml: elementsById["archetype-distribution"].innerHTML,
      traitCardsHtml: elementsById["trait-cards-container"].innerHTML,
      oceanMatchesHtml: oceanMatchesHtml
    }}));
    """
    stdout = _run_jsc(script)
    out = json.loads(stdout.splitlines()[-1])
    assert "(OCEan)" in out["oceanMatchesHtml"]
    for html_chunk in (out["metaHtml"], out["distHtml"], out["traitCardsHtml"]):
        assert "<img " not in html_chunk
        assert "<script>" not in html_chunk
        assert "<svg " not in html_chunk
        assert "<b " not in html_chunk
    assert "&lt;b onclick=alert(4)&gt;src&lt;/b&gt;" in out["metaHtml"]
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in out["distHtml"]
    assert "&quot;&gt;&lt;svg onload=alert(3)&gt;" in out["traitCardsHtml"]


def test_dev_server_static_allowlist_and_request_limits() -> None:
    """Verify dev_server blocks dotfiles/non-allowlisted paths, rejects oversized POSTs, and sets security headers."""
    import http.client
    from http.server import ThreadingHTTPServer
    import threading
    import urllib.error
    import urllib.request

    from scripts.dev_server import CharmDevHandler, MAX_POST_BYTES, _sanitize_error_message

    dummy_key = "AIza" + "SyDummySecretValue12345"
    assert "AIza" not in _sanitize_error_message(f"bad key {dummy_key}")
    assert "topsecret" not in _sanitize_error_message("https://example.com?key=topsecret&x=1")

    server = ThreadingHTTPServer(("127.0.0.1", 0), CharmDevHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/llms.txt") as resp:
            assert resp.status == 200
            assert resp.headers.get("X-Content-Type-Options") == "nosniff"
            assert resp.headers.get("X-Frame-Options") == "DENY"

        for blocked in ("/.env", "/AGENTS.md", "/tests/test_webapp_dom.py"):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}{blocked}")
                raise AssertionError(f"Expected 404 for {blocked}")
            except urllib.error.HTTPError as exc:
                assert exc.code == 404

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.putrequest("POST", "/api/prefill")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Content-Length", str(MAX_POST_BYTES + 1))
        conn.endheaders()
        resp = conn.getresponse()
        assert resp.status == 413
        conn.close()

        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request(
            "POST",
            "/api/decisions",
            body=b"{}",
            headers={"Content-Type": "application/json"},
        )
        bad_resp = conn.getresponse()
        assert bad_resp.status == 400
        bad_resp.read()
        conn.close()
    finally:
        server.shutdown()
        server.server_close()


def test_dev_server_loads_repo_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify _load_dotenv_key reads GEMINI_API_KEY/GOOGLE_API_KEY with spaces or export prefix and invalidates on edits."""
    from pathlib import Path as _Path
    from scripts import dev_server

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setattr(dev_server, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(_Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.setattr(dev_server, "_DOTENV_CACHE", None)
    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text('export GEMINI_API_KEY = "repo-root-test-value"\n', encoding="utf-8")

    assert dev_server._load_dotenv_key() == "repo-root-test-value"
    # Updating .env invalidates the stat-based cache without requiring a server restart.
    dotenv_file.write_text('GEMINI_API_KEY="repo-root-rotated-value"\n', encoding="utf-8")
    assert dev_server._load_dotenv_key() == "repo-root-rotated-value"
    dotenv_file.unlink()
    assert dev_server._load_dotenv_key() == ""


@requires_jsc
def test_server_polling_survives_transient_failures_in_jsc() -> None:
    """Verify transient fetch failures do not permanently disable polling before MAX_SERVER_API_FAILURES."""
    ocean_core_js = _strip_esm_syntax((REPO_ROOT / "ocean-core.js").read_text(encoding="utf-8"))
    app_js = _strip_esm_syntax((REPO_ROOT / "app.js").read_text(encoding="utf-8"))
    script = f"""
    const elementsById = {{}};
    function makeEl(id) {{
      return {{
        id: id, value: "", textContent: "", innerHTML: "", disabled: false, hidden: true,
        className: "", dataset: {{}}, style: {{}},
        classList: {{ add: function() {{}}, remove: function() {{}}, toggle: function() {{}}, contains: function() {{ return false; }} }},
        addEventListener: function() {{}}, setAttribute: function() {{}}, getAttribute: function() {{ return null; }},
        appendChild: function() {{}}, querySelectorAll: function() {{ return []; }}, querySelector: function() {{ return makeEl("child"); }}
      }};
    }}
    let pollCallback = null;
    let clearedCount = 0;
    globalThis.setInterval = function(fn) {{ pollCallback = fn; return 42; }};
    globalThis.clearInterval = function() {{ clearedCount += 1; }};
    globalThis.fetch = function() {{
      return Promise.resolve({{ ok: true, status: 200, json: () => Promise.resolve({{ status: "awaiting_submission", version: 0 }}) }});
    }};
    globalThis.window = globalThis;
    globalThis.location = {{ origin: "http://127.0.0.1:8787", search: "" }};
    globalThis.URLSearchParams = function() {{ return {{ get: function() {{ return null; }} }}; }};
    globalThis.document = {{
      getElementById: function(id) {{ if (!elementsById[id]) elementsById[id] = makeEl(id); return elementsById[id]; }},
      querySelectorAll: function() {{ return []; }},
      querySelector: function() {{ return makeEl("qs"); }},
      createElement: function(tag) {{ return makeEl(tag); }},
      createElementNS: function(ns, tag) {{ return makeEl(tag); }},
      addEventListener: function(evt, fn) {{ if (evt === "DOMContentLoaded") fn(); }}
    }};
    {ocean_core_js}
    {app_js}
    recordServerApiFailure();
    recordServerApiFailure();
    const aliveAfterTwo = isServerApiReachable();
    markServerApiResponse({{ ok: true, status: 200 }});
    const aliveAfterRecovery = isServerApiReachable() && serverApiFailureCount === 0;
    recordServerApiFailure();
    recordServerApiFailure();
    recordServerApiFailure();
    const disabledAfterThree = !isServerApiReachable();
    if (pollCallback) pollCallback();
    // Reset state and verify HTTP 404 immediately disables polling for static hosts.
    serverApiAvailable = true;
    serverApiFailureCount = 0;
    markServerApiResponse({{ ok: false, status: 404 }});
    const disabledImmediatelyOn404 = !isServerApiReachable();
    print(JSON.stringify({{ aliveAfterTwo, aliveAfterRecovery, disabledAfterThree, disabledImmediatelyOn404, clearedCount, hasPoll: typeof pollCallback === "function" }}));
    """
    stdout = _run_jsc(script)
    out = json.loads(stdout.splitlines()[-1])
    assert out == {
        "aliveAfterTwo": True,
        "aliveAfterRecovery": True,
        "disabledAfterThree": True,
        "disabledImmediatelyOn404": True,
        "clearedCount": 1,
        "hasPoll": True,
    }
