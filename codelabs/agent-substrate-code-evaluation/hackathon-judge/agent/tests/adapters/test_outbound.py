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

# tests/adapters/test_outbound.py
import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from src.core.models.message import AgentRequest, AgentResponse, ScoringCriteria
from src.adapters.outbound.adk_agent import ADKAgentAdapter
from src.adapters.outbound.pubsub_publisher import MockPubSubPublisherAdapter, PubSubPublisherAdapter

@pytest.mark.asyncio
@patch('src.adapters.outbound.adk_agent.Runner')
async def test_adk_agent_adapter(mock_runner_cls):
    # Setup mock runner to avoid real API calls
    mock_runner_instance = MagicMock()
    mock_runner_cls.return_value = mock_runner_instance
    
    # Mock run_async to just yield an empty event stream (or nothing)
    async def mock_run_async(*args, **kwargs):
        # We need to simulate setting the state in the session since the agent would do that
        session_service = kwargs.get('session_service')
        # In the actual code, session is retrieved from the agent's session_service.
        # But we can just monkeypatch the session_service of the ADKAgentAdapter inside the test.
        yield
        
    mock_runner_instance.run_async = mock_run_async

    agent = ADKAgentAdapter()
    
    # Monkeypatch the session service to return a mocked session
    original_get_session = agent.session_service.get_session
    async def fake_get_session(*args, **kwargs):
        session = await original_get_session(*args, **kwargs)
        from src.core.models.evaluation import EvaluationOutput, EvaluationScore
        session.state["evaluation_result"] = EvaluationOutput(
            scores=[EvaluationScore(name="Innovation", score=8.5, reasoning="Very innovative")],
            total_score=8.5,
            overall_comments="Great project",
            confidence_score=0.9
        )
        return session

    agent.session_service.get_session = fake_get_session

    req = AgentRequest(
        task_id="tsk_1",
        project_name="Test Project",
        github_url="https://github.com/test/test",
        submission_text="Here is my code",
        judging_rubric="Be nice",
        scoring_criteria=[ScoringCriteria(name="Innovation", description="test", weight=0.5)]
    )
    res = await agent.process_message(req)
    
    assert res.task_id == "tsk_1"
    assert res.status == "success"
    assert res.total_score == 8.5
    assert len(res.scores) == 1
    assert res.scores[0].name == "Innovation"

def test_evaluate_repository_tool_registration():
    adapter = ADKAgentAdapter()
    from src.adapters.outbound.shared_sandbox import evaluate_repository
    assert evaluate_repository in adapter.agent.tools

@pytest.mark.asyncio
@patch('src.adapters.outbound.shared_sandbox.get_sandbox_client')
async def test_evaluate_repository_execution(mock_get_sandbox_client):
    # Setup mock client
    mock_client = MagicMock()
    mock_get_sandbox_client.return_value = mock_client
    
    mock_sandbox = MagicMock()
    mock_sandbox.name = "judge-12345678"
    
    # Mocking successful commands and file reads (sync)
    mock_client.create_sandbox = MagicMock(return_value=mock_sandbox)
    mock_sandbox.commands.run = MagicMock(return_value=MagicMock(exit_code=0))
    mock_sandbox.files.write = MagicMock(return_value=None)
    mock_sandbox.files.read = MagicMock(return_value='{"total_score": 10}')
    mock_sandbox.terminate = MagicMock(return_value=None)

    with patch.dict(
        'os.environ',
        {'SANDBOX_TEMPLATE': 'judge-sandbox', 'SANDBOX_NAMESPACE': 'test-ns'},
        clear=True,
    ):
        from src.adapters.outbound.shared_sandbox import evaluate_repository
        result = evaluate_repository("https://github.com/test/repo", "# Criteria")

    assert "total_score" in result
    mock_client.create_sandbox.assert_called_once_with(template="judge-sandbox", namespace="test-ns")
    mock_sandbox.commands.run.assert_any_call("git clone https://github.com/test/repo repo")
    from src.adapters.outbound.shared_sandbox import SANDBOX_PROMPT
    mock_sandbox.files.write.assert_any_call("criteria.md", "# Criteria")
    mock_sandbox.files.write.assert_any_call("prompt.md", SANDBOX_PROMPT)
    mock_sandbox.commands.run.assert_any_call(
        "env MODEL_PROXY_BASE_URL=http://agent.test-ns.svc.cluster.local:8000/vertex-proxy uv run python -m app.judge",
        timeout=600,
    )
    mock_sandbox.files.read.assert_called_once_with("evaluation.json")
    mock_sandbox.terminate.assert_called_once()


@patch('src.adapters.outbound.shared_sandbox.get_sandbox_client')
def test_evaluate_repository_defaults_and_warmpool_fallback(mock_get_sandbox_client):
    mock_client = MagicMock()
    mock_get_sandbox_client.return_value = mock_client
    mock_sandbox = MagicMock()
    mock_client.create_sandbox = MagicMock(return_value=mock_sandbox)
    mock_sandbox.commands.run = MagicMock(return_value=MagicMock(exit_code=0))
    mock_sandbox.files.read = MagicMock(return_value='{"total_score": 10}')

    from src.adapters.outbound.shared_sandbox import evaluate_repository

    # Defaults to template="judge-sandbox" and namespace="hackathon-judge"
    with patch.dict('os.environ', {}, clear=True):
        evaluate_repository("https://github.com/test/repo", "# Criteria")

    mock_client.create_sandbox.assert_called_with(
        template="judge-sandbox", namespace="hackathon-judge"
    )
    mock_sandbox.commands.run.assert_any_call(
        "env MODEL_PROXY_BASE_URL=http://agent.hackathon-judge.svc.cluster.local:8000/vertex-proxy uv run python -m app.judge",
        timeout=600,
    )

    # Falls back to SANDBOX_WARMPOOL and honors custom MODEL_PROXY_BASE_URL
    mock_client.create_sandbox.reset_mock()
    with patch.dict(
        'os.environ',
        {
            'SANDBOX_WARMPOOL': 'legacy-pool',
            'SANDBOX_NAMESPACE': 'custom-ns',
            'MODEL_PROXY_BASE_URL': 'http://agent.custom-ns.svc.cluster.local:8082/vertex-proxy',
        },
        clear=True,
    ):
        evaluate_repository("https://github.com/test/repo", "# Criteria")

    mock_client.create_sandbox.assert_called_once_with(
        template="legacy-pool", namespace="custom-ns"
    )
    mock_sandbox.commands.run.assert_any_call(
        "env MODEL_PROXY_BASE_URL=http://agent.custom-ns.svc.cluster.local:8082/vertex-proxy uv run python -m app.judge",
        timeout=600,
    )

@pytest.mark.asyncio
async def test_mock_publisher():
    pub = MockPubSubPublisherAdapter()
    res = AgentResponse(task_id="tsk_1", status="success")
    await pub.publish(res)
    assert len(pub.published_messages) == 1

@pytest.mark.asyncio
@patch('src.adapters.outbound.pubsub_publisher.pubsub_v1.PublisherClient')
async def test_real_publisher_no_attribute_errors(mock_publisher_client_cls):
    # Setup mock publisher
    mock_publisher_instance = MagicMock()
    mock_publisher_client_cls.return_value = mock_publisher_instance
    mock_future = MagicMock()
    mock_future.result.return_value = "msg_123"
    mock_publisher_instance.publish.return_value = mock_future
    mock_publisher_instance.topic_path.return_value = "projects/test/topics/test"

    pub = PubSubPublisherAdapter(project_id="test-project", topic_id="test-topic")
    
    # Create response model
    res = AgentResponse(
        task_id="tsk_123",
        status="success",
        overall_comments="Tested properly."
    )
    
    # This should run without throwing any exceptions like AttributeError
    await pub.publish(res)
    
    # Verify the mock was called correctly
    mock_publisher_instance.publish.assert_called_once()
    args, kwargs = mock_publisher_instance.publish.call_args
    assert args[0] == "projects/test/topics/test"
    assert b"tsk_123" in kwargs['data']


@patch('src.adapters.outbound.shared_sandbox.get_sandbox_client')
def test_evaluate_repository_judge_failure_returns_error(mock_get_sandbox_client):
    mock_client = MagicMock()
    mock_get_sandbox_client.return_value = mock_client
    mock_sandbox = MagicMock()
    mock_client.create_sandbox = MagicMock(return_value=mock_sandbox)

    def run(command, timeout=60):
        if command.startswith("git clone"):
            return MagicMock(exit_code=0, stdout="", stderr="")
        return MagicMock(exit_code=3, stdout="", stderr="noise\njudge: timed out after 540s\n")

    mock_sandbox.commands.run = MagicMock(side_effect=run)

    with patch.dict('os.environ', {'SANDBOX_WARMPOOL': 'test-pool', 'SANDBOX_NAMESPACE': 'test-ns'}):
        from src.adapters.outbound.shared_sandbox import evaluate_repository
        result = json.loads(evaluate_repository("https://github.com/test/repo", "# Criteria"))

    assert "error" in result
    assert "exited with code 3" in result["error"]
    assert "judge: timed out after 540s" in result["error"]
    mock_sandbox.files.read.assert_not_called()
    mock_sandbox.terminate.assert_called_once()


def test_sandbox_prompt_does_not_ask_model_to_write_files():
    from src.adapters.outbound.shared_sandbox import SANDBOX_PROMPT
    assert "evaluation.json" not in SANDBOX_PROMPT
    assert "@criteria.md" not in SANDBOX_PROMPT
    for field in ("scores", "total_score", "overall_comments", "confidence_score"):
        assert field in SANDBOX_PROMPT


@patch('src.adapters.outbound.shared_sandbox.get_sandbox_client')
def test_evaluate_repository_clone_failure_skips_judge(mock_get_sandbox_client):
    mock_client = MagicMock()
    mock_get_sandbox_client.return_value = mock_client
    mock_sandbox = MagicMock()
    mock_client.create_sandbox = MagicMock(return_value=mock_sandbox)
    mock_sandbox.commands.run = MagicMock(
        return_value=MagicMock(exit_code=128, stdout="", stderr="fatal: repository not found\n")
    )

    with patch.dict('os.environ', {'SANDBOX_WARMPOOL': 'test-pool', 'SANDBOX_NAMESPACE': 'test-ns'}):
        from src.adapters.outbound.shared_sandbox import evaluate_repository
        result = json.loads(evaluate_repository("https://github.com/test/repo", "# Criteria"))

    assert "git clone failed (exit 128)" in result["error"]
    assert "repository not found" in result["error"]
    assert mock_sandbox.commands.run.call_count == 1
    mock_sandbox.files.write.assert_not_called()
    mock_sandbox.terminate.assert_called_once()


def test_sandbox_prompt_asks_for_repo_relative_paths_and_bounded_commands():
    from src.adapters.outbound.shared_sandbox import SANDBOX_PROMPT
    assert "relative to the repository root" in SANDBOX_PROMPT
    assert "file://" in SANDBOX_PROMPT  # named as forbidden
    assert "3 minutes" in SANDBOX_PROMPT


def test_evaluate_repository_uses_injected_client_without_calling_get_sandbox_client():
    injected_client = MagicMock()
    mock_sandbox = MagicMock()
    injected_client.create_sandbox.return_value = mock_sandbox
    mock_sandbox.commands.run.return_value = MagicMock(exit_code=0)
    mock_sandbox.files.read.return_value = '{"total_score": 9.9}'

    from src.adapters.outbound.shared_sandbox import evaluate_repository
    with patch('src.adapters.outbound.shared_sandbox.get_sandbox_client') as mock_get_client:
        result = evaluate_repository(
            "https://github.com/test/repo",
            "# Criteria",
            client=injected_client,
        )

    assert result == '{"total_score": 9.9}'
    mock_get_client.assert_not_called()
    injected_client.create_sandbox.assert_called_once()
