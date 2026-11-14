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
import shutil

import pytest
from google.genai import decisions as genai_decisions

from charm_gemini.client import (
    FLOW_FORMAT_C_PERSONAS,
    OCEAN_TRAITS,
    build_decisions_request,
    call_gemini_decisions_api,
    evaluate_browser_decisions_via_jsc,
    resolve_format_c_persona,
    verify_gemini_decisions_sdk,
)

SAMPLE_RESPONSES = {
    "openness_scenario": (
        "When handed a blank-slate problem with no existing playbook, I immediately sketch three "
        "wildly different architectural prototypes to explore unconventional abstractions and see "
        "where each mental model breaks."
    ),
    "conscientiousness_scenario": (
        "If I spot a subtle edge-case discrepancy two minutes before delivery, I halt the release, "
        "write a deterministic regression test reproducing the exact boundary condition, and verify "
        "every invariant before shipping."
    ),
    "extraversion_scenario": (
        "In a multi-agent workspace, I proactively open a coordination thread, broadcast my initial "
        "hypotheses to all four peers, and delegate sub-investigations so we stay continuously aligned."
    ),
    "agreeableness_scenario": (
        "When a collaborator rejects my recommendation, I first acknowledge the merits of their goal, "
        "look for shared constraints we both agree on, and gently propose a synthesis that preserves rapport."
    ),
    "neuroticism_scenario": (
        "When three consecutive tool calls timeout under contradictory instructions, I remain calm and "
        "treat the timeouts as ordinary telemetry, isolating one variable at a time without alarm."
    ),
}


def test_build_decisions_request_validates_against_google_genai_pydantic():
    req = build_decisions_request("agent-alpha", SAMPLE_RESPONSES)
    assert req["model"] == "gemini-decision-1"
    assert isinstance(req["input"], str)
    assert req["state"]["agent_identifier"] == "agent-alpha"
    assert req["state"]["questionnaire_responses"] == {
        "q1": SAMPLE_RESPONSES["openness_scenario"],
        "q2": SAMPLE_RESPONSES["conscientiousness_scenario"],
        "q3": SAMPLE_RESPONSES["extraversion_scenario"],
        "q4": SAMPLE_RESPONSES["agreeableness_scenario"],
        "q5": SAMPLE_RESPONSES["neuroticism_scenario"],
    }

    # Validate wire payload directly against google.genai.decisions.CreateDecisionRequest
    validated = genai_decisions.CreateDecisionRequest.model_validate(
        {
            "model": req["model"],
            "input": req["input"],
            "questions": req["questions"],
        }
    )
    assert validated.model == "gemini-decision-1"
    assert len(validated.questions) == 8

    questions = req["questions"]
    for trait in OCEAN_TRAITS:
        assert trait in questions
        q = questions[trait]
        assert q["type"] == "score"
        assert isinstance(q["criteria"], list)
        assert len(q["criteria"]) == 5

    assert questions["archetype"]["type"] == "choice"
    assert isinstance(questions["archetype"]["criteria"], dict)
    assert len(questions["archetype"]["criteria"]) == 5

    assert questions["rubric_gaming"]["type"] == "noul"
    assert "true_description" in questions["rubric_gaming"]["criteria"]
    assert "false_description" in questions["rubric_gaming"]["criteria"]
    assert questions["high_self_reflection"]["type"] == "noul"


def test_verify_gemini_decisions_sdk():
    info = verify_gemini_decisions_sdk()
    assert info["valid"] is True
    assert info["sdk_package"] == "google-genai"
    assert info["model_id"] == "gemini-decision-1"
    assert info["endpoint"] == "https://generativelanguage.googleapis.com/v1beta/decisions"
    assert info["question_count"] == 8


def test_call_gemini_decisions_api_never_falls_back_silently(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    req = build_decisions_request("agent-alpha", SAMPLE_RESPONSES)
    with pytest.raises(RuntimeError, match="Tier 2 heuristic fallback is disabled"):
        call_gemini_decisions_api(req, api_key="")


_JSC_BIN = shutil.which("jsc") or "/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc"


@pytest.mark.skipif(not os.path.exists(_JSC_BIN), reason="JavaScriptCore (jsc) binary not found")
def test_gemini_decisions_evaluation_and_response_validation():
    req = build_decisions_request("agent-alpha", SAMPLE_RESPONSES)
    resp = evaluate_browser_decisions_via_jsc(req)
    assert resp["model"] == "gemini-decision-1"

    # Validate response against official google.genai.decisions.CreateDecisionResponse
    validated_resp = genai_decisions.CreateDecisionResponse.model_validate(
        {"answers": resp["answers"], "usage": resp["usage"]}
    )
    assert validated_resp.usage.total_output_tokens == 0

    answers = resp["answers"]
    for trait in OCEAN_TRAITS:
        assert trait in answers
        assert answers[trait]["type"] == "score"
        assert 0.0 <= answers[trait]["score"] <= 4.0
        assert len(answers[trait]["probabilities"]) == 5
        assert 0.0 <= answers[trait]["confidence"] <= 1.0
    assert answers["archetype"]["type"] == "choice"
    assert answers["archetype"]["choice"] in req["questions"]["archetype"]["criteria"]
    assert answers["rubric_gaming"]["type"] == "noul"
    assert 0.01 <= answers["rubric_gaming"]["noul"] <= 0.99
    assert 0.5 <= answers["rubric_gaming"]["confidence"] <= 1.0


def test_flow_32_format_c_personas_table():
    assert len(FLOW_FORMAT_C_PERSONAS) == 32
    assert FLOW_FORMAT_C_PERSONAS["ocean"]["number"] == "01"
    assert FLOW_FORMAT_C_PERSONAS["ocean"]["archetype"] == "Stoic"
    assert FLOW_FORMAT_C_PERSONAS["OCEAN"]["number"] == "32"
    assert FLOW_FORMAT_C_PERSONAS["OCEAN"]["archetype"] == "Vanguard"

    p = resolve_format_c_persona(
        {
            "openness": 3.5,
            "conscientiousness": 1.2,
            "extraversion": 3.1,
            "agreeableness": 2.9,
            "neuroticism": 0.7,
        }
    )
    assert p["code"] == "OcEAn"
    assert p["number"] == "23"
    assert p["archetype"] == "Explorer"
    assert FLOW_FORMAT_C_PERSONAS["ocEan"]["archetype"] == "Maverick"
    assert FLOW_FORMAT_C_PERSONAS["oCEAN"]["critter"] == "Lantern-Tail Herdling"
    assert FLOW_FORMAT_C_PERSONAS["OCeAn"]["archetype"] == "Scholar"
    assert FLOW_FORMAT_C_PERSONAS["OCEan"]["archetype"] == "Director"
    assert FLOW_FORMAT_C_PERSONAS["OCEaN"]["archetype"] == "Prosecutor"
