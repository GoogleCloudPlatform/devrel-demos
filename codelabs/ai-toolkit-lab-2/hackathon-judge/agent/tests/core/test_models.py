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

# tests/core/test_models.py
from src.core.models.message import AgentRequest, AgentResponse, ScoringCriteria, CategoryScore

def test_agent_request_model():
    req = AgentRequest(
        task_id="tsk_123",
        project_name="Test Project",
        github_url="https://github.com/moficodes/test",
        submission_text="Here is my code",
        judging_rubric="Be nice",
        scoring_criteria=[ScoringCriteria(name="Innovation", description="How new is this?", weight=0.5)]
    )
    assert req.task_id == "tsk_123"
    assert req.scoring_criteria[0].max_score == 10.0
    assert req.scoring_criteria[0].description == "How new is this?"

def test_agent_response_model():
    res = AgentResponse(
        task_id="tsk_123",
        status="success",
        scores=[CategoryScore(name="Innovation", score=8, reasoning="Good")],
        total_score=4.0
    )
    assert res.task_id == "tsk_123"
    assert res.status == "success"
    assert len(res.scores) == 1
