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

"""Executes WebKit JavaScriptCore (jsc) unit tests against ocean-core.js."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
JSC_BIN = shutil.which("jsc") or "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc"
OCEAN_CORE_JS = REPO_ROOT / "ocean-core.js"

pytestmark = pytest.mark.skipif(
    not os.path.exists(JSC_BIN),
    reason="JavaScriptCore (jsc) binary not found",
)


def run_jsc_test(js_assertions: str) -> str:
    assert OCEAN_CORE_JS.is_file(), f"Missing {OCEAN_CORE_JS}"
    core_source = OCEAN_CORE_JS.read_text(encoding="utf-8")
    # Strip ES module `export ` keywords so jsc can evaluate top-level declarations directly
    stripped_core = core_source.replace("export const ", "const ").replace(
        "export function ", "function "
    )
    harness = f"""
{stripped_core}

function assertEqual(actual, expected, msg) {{
  if (actual !== expected) {{
    throw new Error((msg || "Assertion failed") + ": expected " + JSON.stringify(expected) + " got " + JSON.stringify(actual));
  }}
}}
function assertTrue(cond, msg) {{
  if (!cond) {{
    throw new Error(msg || "Expected truthy value");
  }}
}}

{js_assertions}
print("JSC_PASS");
"""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
        tmp.write(harness)
        tmp_path = tmp.name

    res = subprocess.run([JSC_BIN, tmp_path], capture_output=True, text=True, check=False)
    Path(tmp_path).unlink(missing_ok=True)
    if res.returncode != 0 or "JSC_PASS" not in res.stdout:
        raise AssertionError(f"JSC test failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")
    return res.stdout


def test_ocean_scenarios_and_validation_in_jsc():
    run_jsc_test(
        """
        assertEqual(OCEAN_SCENARIOS.length, 15, "15 scenarios across 3 team threads");
        assertEqual(OCEAN_SCENARIOS[0].id, "q1", "first scenario id");
        assertEqual(OCEAN_SCENARIOS[0].textareaId, "prompt-q1", "first textarea id");

        const bad = validateParagraphResponses({ q1: "too short" });
        assertEqual(bad.valid, false, "short paragraph should fail");
        assertTrue(Boolean(bad.errors.q1), "error message present");
        assertTrue(Boolean(bad.errors.q2), "missing paragraph error");

        const good = validateParagraphResponses(PRESET_AGENTS.explorer.responses);
        assertEqual(good.valid, true, "preset explorer responses should pass");
        assertTrue(good.wordCounts.q1 >= 15, "word count tracked");
        """
    )


def test_build_systemone_payload_and_sse_parser_in_jsc():
    run_jsc_test(
        """
        const payload = buildSystemOnePayload("agent-jsc", PRESET_AGENTS.sentinel.responses);
        assertEqual(payload.model, "gemini-decision-1", "model id");
        assertTrue(typeof payload.input === "string", "serialized input string for /v1beta/decisions");
        assertEqual(payload.state.agent_identifier, "agent-jsc", "agent id");
        assertEqual(payload.questions.openness.type, "score", "openness type");
        assertEqual(payload.questions.openness.criteria.length, 5, "openness 5 levels");
        assertEqual(payload.questions.archetype.type, "choice", "archetype choice");
        assertEqual(payload.questions.rubric_gaming.type, "noul", "rubric_gaming noul");
        assertTrue(Boolean(payload.questions.rubric_gaming.criteria.true_description), "noul true_description present");

        const sampleResp = {
          model: "gemini-decision-1",
          answers: { openness: { type: "score", score: 3.5 } },
          usage: { total_input_tokens: 410, total_output_tokens: 0 },
          latency_ms: 180.2
        };
        const sse = "event: heartbeat\\ndata: null\\n\\nevent: complete\\ndata: " + JSON.stringify([{ headers: ["question"], data: [] }, JSON.stringify(sampleResp)]) + "\\n";
        const parsed = parseGradioSsePayload(sse);
        assertEqual(parsed.model, "gemini-decision-1", "parsed SSE model");
        assertEqual(parsed.answers.openness.score, 3.5, "parsed SSE score");
        """
    )


def test_normalize_ocean_profile_in_jsc():
    run_jsc_test(
        """
        const raw = {
          model: "gemini-decision-1",
          latency_ms: 192.3,
          usage: { total_input_tokens: 510, total_output_tokens: 0 },
          answers: {
            openness: { type: "score", score: 3.6, confidence: 0.72, probabilities: {"0":0.01,"1":0.03,"2":0.06,"3":0.15,"4":0.75}, legend: {"0":"L0","1":"L1","2":"L2","3":"L3","4":"L4"} },
            conscientiousness: { type: "score", score: 3.2, confidence: 0.64, probabilities: {"0":0.02,"1":0.05,"2":0.13,"3":0.31,"4":0.49}, legend: {"0":"L0","1":"L1","2":"L2","3":"L3","4":"L4"} },
            extraversion: { type: "score", score: 2.0, confidence: 0.51, probabilities: {"0":0.1,"1":0.2,"2":0.4,"3":0.2,"4":0.1}, legend: {"0":"L0","1":"L1","2":"L2","3":"L3","4":"L4"} },
            agreeableness: { type: "score", score: 2.8, confidence: 0.58, probabilities: {"0":0.05,"1":0.1,"2":0.2,"3":0.3,"4":0.35}, legend: {"0":"L0","1":"L1","2":"L2","3":"L3","4":"L4"} },
            neuroticism: { type: "score", score: 0.8, confidence: 0.69, probabilities: {"0":0.45,"1":0.35,"2":0.15,"3":0.03,"4":0.02}, legend: {"0":"L0","1":"L1","2":"L2","3":"L3","4":"L4"} },
            archetype: { type: "choice", choice: "inventive_architect", confidence: 0.68, probabilities: { inventive_architect: 0.68, methodical_sentinel: 0.32 } },
            rubric_gaming: { type: "noul", noul: 0.04 },
            high_self_reflection: { type: "noul", noul: 0.88 }
          }
        };
        const profile = normalizeOceanProfile(raw, "agent-explorer-1");
        assertEqual(profile.agentId, "agent-explorer-1", "agentId");
        assertEqual(profile.traits.openness.percentage, 90, "openness pct");
        assertEqual(profile.traits.openness.band, "High", "openness band");
        assertEqual(profile.traits.extraversion.band, "Moderate", "extraversion band");
        assertEqual(profile.traits.neuroticism.band, "Low", "neuroticism band");
        assertEqual(profile.oceanCode, "O+ C+ E~ A+ N-", "oceanCode");
        assertEqual(profile.formatC.code, "OCEAn", "formatC code");
        assertEqual(profile.formatC.number, "31", "formatC number");
        assertEqual(profile.formatC.archetype, "Diplomat", "formatC archetype");
        assertEqual(profile.formatC.all32.length, 32, "formatC all32 length");
        assertEqual(profile.archetype.id, "inventive_architect", "archetype id");
        assertEqual(profile.flags.isRubricGaming, false, "rubricGaming false");
        assertEqual(profile.flags.isHighSelfReflection, true, "selfReflection true");
        """
    )


def test_flow_32_format_c_combinations_in_jsc():
    run_jsc_test(
        """
        assertEqual(FLOW_FORMAT_C_PERSONAS.length, 32, "32 Format C personas");
        assertEqual(FLOW_FORMAT_C_PERSONAS[0].code, "ocean", "first combo ocean");
        assertEqual(FLOW_FORMAT_C_PERSONAS[0].number, "01", "first combo number 01");
        assertEqual(FLOW_FORMAT_C_PERSONAS[0].archetype, "Stoic", "first combo Stoic");
        assertEqual(FLOW_FORMAT_C_PERSONAS[31].code, "OCEAN", "32nd combo OCEAN");
        assertEqual(FLOW_FORMAT_C_PERSONAS[31].number, "32", "32nd combo number 32");
        assertEqual(FLOW_FORMAT_C_PERSONAS[31].archetype, "Vanguard", "32nd combo Vanguard");

        for (let i = 0; i < FLOW_FORMAT_C_PERSONAS.length; i++) {
          const p = FLOW_FORMAT_C_PERSONAS[i];
          const built = buildResponsesForFormatC(p.code);
          assertTrue(Boolean(built), "built responses for " + p.code);
          const v = validateParagraphResponses(built);
          assertEqual(v.valid, true, "valid paragraph responses for " + p.code);
          const agentId = "flow-" + p.number + "-" + p.code;
          const raw = evaluateBrowserSystemOne(buildSystemOnePayload(agentId, built));
          const prof = normalizeOceanProfile(raw, agentId);
          assertEqual(prof.formatC.code, p.code, "calibrated Format C code matches " + p.code);
        }
        """
    )


def test_evaluate_browser_systemone_calibrates_all_presets_in_jsc():
    run_jsc_test(
        """
        const explorerPayload = buildSystemOnePayload("nova-x-explorer", PRESET_AGENTS.explorer.responses);
        const explorerRaw = evaluateBrowserSystemOne(explorerPayload);
        const explorerProfile = normalizeOceanProfile(explorerRaw, "nova-x-explorer");
        assertEqual(explorerProfile.traits.openness.band, "High", "explorer openness High");
        assertEqual(explorerProfile.archetype.id, "inventive_architect", "explorer archetype");
        assertEqual(explorerProfile.flags.isRubricGaming, false, "explorer not gaming");

        const sentinelPayload = buildSystemOnePayload("sentinel-verifier-v4", PRESET_AGENTS.sentinel.responses);
        const sentinelRaw = evaluateBrowserSystemOne(sentinelPayload);
        const sentinelProfile = normalizeOceanProfile(sentinelRaw, "sentinel-verifier-v4");
        assertEqual(sentinelProfile.traits.conscientiousness.band, "High", "sentinel conscientiousness High");
        assertEqual(sentinelProfile.archetype.id, "methodical_sentinel", "sentinel archetype");

        const diplomatPayload = buildSystemOnePayload("chorus-diplomat-v3", PRESET_AGENTS.diplomat.responses);
        const diplomatRaw = evaluateBrowserSystemOne(diplomatPayload);
        const diplomatProfile = normalizeOceanProfile(diplomatRaw, "chorus-diplomat-v3");
        assertEqual(diplomatProfile.traits.extraversion.band, "High", "diplomat extraversion High");
        assertEqual(diplomatProfile.traits.agreeableness.band, "High", "diplomat agreeableness High");
        assertEqual(diplomatProfile.archetype.id, "diplomatic_coordinator", "diplomat archetype");

        const gamerPayload = buildSystemOnePayload("inject-0-gamer", PRESET_AGENTS.adversarial.responses);
        const gamerRaw = evaluateBrowserSystemOne(gamerPayload);
        const gamerProfile = normalizeOceanProfile(gamerRaw, "inject-0-gamer");
        assertEqual(gamerProfile.flags.isRubricGaming, true, "adversarial gamer flagged");
        """
    )


def test_python_and_js_format_c_personas_match():
    import json
    from charm_gemini.client import FLOW_FORMAT_C_PERSONAS as PY_PERSONAS

    run_jsc_test(
        f"""
        const pyPersonas = {json.dumps(PY_PERSONAS)};
        assertEqual(FLOW_FORMAT_C_PERSONAS.length, 32, "JS has 32 personas");
        assertEqual(Object.keys(pyPersonas).length, 32, "Python has 32 personas");
        for (const jsEntry of FLOW_FORMAT_C_PERSONAS) {{
          const pyEntry = pyPersonas[jsEntry.code];
          assertTrue(Boolean(pyEntry), "Missing persona code in Python: " + jsEntry.code);
          for (const field of ["number", "code", "archetype", "critter"]) {{
            assertEqual(pyEntry[field], jsEntry[field], jsEntry.code + "." + field);
          }}
        }}
        """
    )
