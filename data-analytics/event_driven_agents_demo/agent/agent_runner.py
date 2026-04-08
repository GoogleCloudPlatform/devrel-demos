# Copyright 2026 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A script to run the agent conversation locally for testing."""

import asyncio
import os
import uuid
import vertexai
from dotenv import load_dotenv
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.apps import App
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin
from adk_agent_app.agent import get_root_agent

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
DATASET_ID = os.getenv("BIGQUERY_DATASET")
APP_NAME = "cymbal_bank_fraud_agent"
USER_ID = "local_test_user"

async def run_conversation(message_payload: str):
    
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # Setup App & Runner
    plugin = BigQueryAgentAnalyticsPlugin(project_id=PROJECT_ID, dataset_id=DATASET_ID, table_id="agent_events")
    app = App(name=APP_NAME, root_agent=get_root_agent(), plugins=[plugin])
    runner = Runner(app=app, session_service=InMemorySessionService())
    
    # Create Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=f"session-{uuid.uuid4().hex[:6]}"
    )
    
    print(f"session_id: {session.id}")
    
    # Run Agent
    async for event in runner.run_async(
        user_id=USER_ID, 
        session_id=session.id, 
        new_message=types.Content(role='user', parts=[types.Part(text=message_payload)])
    ):
        if event.is_final_response() and event.content:
            print(f"\n[Final Response]: {event.content.parts[0].text}\n")

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(script_dir, "../simulator/test_event.json"), 'r') as f:
            asyncio.run(run_conversation(f.read()))
    except FileNotFoundError:
        print("Error: test_event.json not found.")