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

# tests/adapters/test_inbound.py
import pytest
import asyncio
from src.core.models.message import AgentRequest, AgentResponse
from src.adapters.outbound.adk_agent import ADKAgentAdapter
from src.adapters.outbound.pubsub_publisher import MockPubSubPublisherAdapter
from src.adapters.inbound.pubsub_subscriber import BackgroundSubscriber
import json

@pytest.mark.asyncio
async def test_subscriber_processing():
    agent = ADKAgentAdapter()
    publisher = MockPubSubPublisherAdapter()
    subscriber = BackgroundSubscriber(agent_service=agent, publisher=publisher)

    # Simulate receiving a message
    req_json = json.dumps({
        "task_id": "tsk_123",
        "project_name": "Test",
        "github_url": "https://github.com/test/test",
        "submission_text": "text",
        "judging_rubric": "rubric",
        "scoring_criteria": [{"name": "Innovate", "description": "test", "weight": 1.0, "max_score": 10}]
    })

    await subscriber.process_raw_message("123", req_json)

    assert len(publisher.published_messages) == 1
    assert publisher.published_messages[0].task_id == "tsk_123"
