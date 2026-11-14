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

import pytest
import pydantic

from app.judge_schema import CriterionScore, Evaluation


def _valid():
    return {
        "scores": [{"name": "Innovation", "score": 8, "reasoning": "See app/main.py:42."}],
        "total_score": 8,
        "overall_comments": "Solid.",
        "confidence_score": 0.9,
    }


def test_valid_payload_round_trips():
    ev = Evaluation.model_validate(_valid())
    assert ev.scores[0] == CriterionScore(name="Innovation", score=8.0, reasoning="See app/main.py:42.")
    assert ev.total_score == 8.0
    dumped = ev.model_dump()
    assert set(dumped) == {"scores", "total_score", "overall_comments", "confidence_score"}
    assert set(dumped["scores"][0]) == {"name", "score", "reasoning"}


def test_missing_field_rejected():
    payload = _valid()
    del payload["overall_comments"]
    with pytest.raises(pydantic.ValidationError):
        Evaluation.model_validate(payload)


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_confidence_out_of_range_rejected(confidence):
    payload = _valid()
    payload["confidence_score"] = confidence
    with pytest.raises(pydantic.ValidationError):
        Evaluation.model_validate(payload)
