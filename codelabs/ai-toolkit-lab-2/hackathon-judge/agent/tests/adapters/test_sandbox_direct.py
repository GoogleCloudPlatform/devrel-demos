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
from unittest.mock import patch, MagicMock

from src.core.models.message import AgentRequest, ScoringCriteria
from src.adapters.outbound.sandbox_direct import SandboxDirectAdapter

@pytest.fixture
def sample_request():
    return AgentRequest(
        task_id="task-123",
        project_name="Test Project",
        github_url="https://github.com/user/repo",
        submission_text="This is a test submission.",
        judging_rubric="Test Rubric",
        scoring_criteria=[
            ScoringCriteria(name="Innovation", description="How innovative?", weight=1.0, max_score=10.0),
            ScoringCriteria(name="Execution", description="How well executed?", weight=2.0, max_score=10.0)
        ]
    )

@pytest.mark.asyncio
async def test_sandbox_direct_adapter_success(sample_request):
    adapter = SandboxDirectAdapter()
    
    # Mock the synchronous sandbox evaluation
    mock_result_json = """
    {
      "scores": [
        {"name": "Innovation", "score": 8.5, "reasoning": "Good idea."},
        {"name": "Execution", "score": 7.0, "reasoning": "Okay execution."}
      ],
      "total_score": 15.5,
      "overall_comments": "A solid project overall.",
      "confidence_score": 0.9
    }
    """
    
    with patch('src.adapters.outbound.sandbox_direct.evaluate_repository', return_value=mock_result_json) as mock_eval:
        response = await adapter.process_message(sample_request)
        
        # Verify the mock was called correctly
        mock_eval.assert_called_once()
        args, _ = mock_eval.call_args
        assert args[0] == "https://github.com/user/repo"
        assert "How innovative?" in args[1]
        
        # Verify the response
        assert response.status == "success"
        assert response.total_score == 15.5
        assert len(response.scores) == 2
        
        # Check that weights and max scores are populated
        innovation_score = next(s for s in response.scores if s.name == "Innovation")
        assert innovation_score.weight == 1.0
        assert innovation_score.max_score == 10.0

@pytest.mark.asyncio
async def test_sandbox_direct_adapter_sandbox_error(sample_request):
    adapter = SandboxDirectAdapter()
    
    # Mock a failure returned by the sandbox itself
    mock_result_json = """
    {"error": "Sandbox evaluation failed: Could not clone repo"}
    """
    
    with patch('src.adapters.outbound.sandbox_direct.evaluate_repository', return_value=mock_result_json):
        response = await adapter.process_message(sample_request)
        
        assert response.status == "error"
        assert "Sandbox evaluation failed" in response.error_message

@pytest.mark.asyncio
async def test_sandbox_direct_adapter_invalid_json(sample_request):
    adapter = SandboxDirectAdapter()
    
    # Mock invalid JSON
    mock_result_json = "This is not json"
    
    with patch('src.adapters.outbound.sandbox_direct.evaluate_repository', return_value=mock_result_json):
        response = await adapter.process_message(sample_request)
        
        assert response.status == "error"
        assert "Failed to parse sandbox output" in response.error_message
