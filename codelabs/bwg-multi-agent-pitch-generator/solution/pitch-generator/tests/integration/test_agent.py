# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import httpx
import pytest
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from pitch_generator.agent import root_agent

VISUAL_DIRECTOR_URL = os.getenv("VISUAL_DIRECTOR_URL", "http://localhost:8801")
AGENT_CARD_URL = (
    f"{VISUAL_DIRECTOR_URL}/a2a/visual_director/.well-known/agent-card.json"
)


def _visual_director_is_up() -> bool:
    """The workflow fans out to the remote Visual Director, so the service has to
    be serving before this test can mean anything."""
    try:
        return httpx.get(AGENT_CARD_URL, timeout=5).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(
    not _visual_director_is_up(),
    reason=f"Visual Director is not serving at {AGENT_CARD_URL}",
)
def test_agent_stream() -> None:
    """
    Integration test for the agent stream functionality.
    Tests that the agent returns valid streaming responses.
    """

    session_service = InMemorySessionService()

    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Flying skateboards for cats")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )
    assert len(events) > 0, "Expected at least one message"

    has_text_content = False
    for event in events:
        if (
            event.content
            and event.content.parts
            and any(part.text for part in event.content.parts)
        ):
            has_text_content = True
            break
    assert has_text_content, "Expected at least one message with text content"
