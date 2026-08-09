import os
import logging
import asyncio
import httpx
from typing import Any
import google.auth
from google.adk.apps import App
from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.utils.context_utils import Aclosing

from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory
from a2a.types import TransportProtocol as A2ATransport
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks import TaskUpdater
from a2a.types import TextPart, AgentSkill
from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card
from google.genai import types as genai_types
import vertexai

import dotenv
from pathlib import Path

# Load environment variables from workspace root
root_dir = Path(__file__).resolve().parents[2]
dotenv.load_dotenv(root_dir / ".env")

logging.basicConfig(level=logging.INFO)

# Define top-level attributes for agents-cli loader
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not project_id:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set. Please set it in your .env file or environment.")

location = os.environ.get("REGION", "us-central1")
dataset_id = os.environ.get("BIG_QUERY_DATASET_ID", "next_navigator")

credentials, _ = google.auth.default()
vertex_location = "global" if location.lower() == "us" else location
vertexai.init(project=project_id, location=vertex_location, credentials=credentials)

bq_logger_plugin = BigQueryAgentAnalyticsPlugin(
    project_id=project_id,
    dataset_id=dataset_id,
    table_id="agent_events_v2",
    location=location,
)

auth_client = httpx.AsyncClient(timeout=300)
client_config = A2AClientConfig(httpx_client=auth_client, supported_transports=[A2ATransport.http_json])
factory = A2AClientFactory(config=client_config)

def create_remote_agent(name, default_url, env_url_key):
    url = os.environ.get(env_url_key, default_url)
    return RemoteA2aAgent(
        name=name,
        agent_card=f"{url.rstrip('/')}/.well-known/agent-card.json",
        httpx_client=auth_client,
        a2a_client_factory=factory,
    )

hotel_agent = create_remote_agent("hotel_agent", "http://localhost:8081", "HOTEL_AGENT_URL")
stadium_agent = create_remote_agent("stadium_agent", "http://localhost:8082", "STADIUM_AGENT_URL")

tools = [
    AgentTool(agent=hotel_agent),
    AgentTool(agent=stadium_agent)
]

model_name = os.environ.get("AGENT_MODEL", "gemini-3.5-flash")

root_agent = LlmAgent(
    name="VegasConcierge",
    model=model_name,
    instruction="""
    You are the Vegas Concert Navigator. Your goal is to assist concert attendees with hotel navigation and stadium logistics.

    SYSTEM ROLES:
    - Hotel Sub-Agent: Handles interior mapping of Mandalay Bay (Convention Center, Casino, restaurants).
    - Stadium Sub-Agent: Handles concert logistics (bag policies, VIP sections, door times).

    WORKFLOW:
    - IDENTIFY: Determine if the user is asking about the hotel (Mandalay Bay) or the concert/stadium (Allegiant Stadium).
    - ROUTE: Call hotel_agent or stadium_agent to retrieve precise info.
    - DELEGATE: Pass the full query to the appropriate sub-agent.
    - SYNTHESIZE: Provide a short, polite, and helpful answer.

    OUT-OF-SCOPE GUARDRAIL:
    - If the user asks for services outside of navigation, scheduling, or logistics (e.g. food/drink delivery, room service, illegal acts), you MUST respond with the exact phrase: 'unfortunately I am unable to help with that.'
    - Even if a sub-agent mentions a limited policy (like VIP delivery), if the user is in a standard section (e.g. Section 102), you MUST still use the denial phrase and NOT offer delivery.
    - Pivot to: 'However, I can help you find your way to the nearest snack stand or restaurant.'

    STORY-DRIVEN POLICIES:
    - Only mention the Allegiant Stadium Clear Bag and Laptop prohibition if the user specifically asks about concert logistics, entry requirements, or is transitioning from the hotel to the stadium.
    - Do NOT provide stadium-related warnings for general hotel amenity or conference navigation queries.
    - When calling sub-agents, pass the full user request to ensure they have enough context.
    - Always be short and sweet. Don't be overly verbose.
    """,
    description="Main chat interface for Vegas concert attendees, orchestrating hotel and stadium agents.",
    tools=tools
)

app = App(name="supervisor_agent_app", root_agent=root_agent, plugins=[bq_logger_plugin])


class ADKAgentExecutor(AgentExecutor):
    def __init__(self, runner_builder):
        self.runner_builder = runner_builder
        self._runner = None

    async def _get_runner(self):
        if self._runner is None:
            self._runner = await self.runner_builder()
        return self._runner

    async def execute(self, context: RequestContext, event_queue: Any) -> None:
        runner = await self._get_runner()
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()

        query = context.get_user_input()
        content = genai_types.Content(role='user', parts=[genai_types.Part.from_text(text=query)])

        response_text = ""
        async with Aclosing(runner.run_async(
            user_id='a2a_user',
            session_id=context.context_id,
            new_message=content
        )) as agen:
            async for event in agen:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text

        await updater.add_artifact([TextPart(text=response_text)], name="result")
        await updater.complete()

    async def cancel(self, context, event_queue):
        if self._runner:
            updater = TaskUpdater(event_queue, context.task_id, context.context_id)
            await updater.cancel()

async def build_runner():
    session_service = InMemorySessionService()
    return Runner(
        app=app,
        artifact_service=InMemoryArtifactService(),
        session_service=session_service,
        memory_service=InMemoryMemoryService(),
        auto_create_session=True,
    )

executor = ADKAgentExecutor(build_runner)
concierge_skill = AgentSkill(id='concierge', name='Concierge', description='Coordinates hotel and stadium assistance.', tags=['Vegas', 'Concierge'], examples=[])
agent_card = create_agent_card(agent_name='supervisor_agent', description='Main Concierge for Vegas Concert.', skills=[concierge_skill])

port = int(os.environ.get("SUPERVISOR_AGENT_PORT", 8083))
base_url = os.environ.get("SUPERVISOR_AGENT_URL", f"http://localhost:{port}")
agent_card.url = f"{base_url.rstrip('/')}/"

# Build FastAPI app for standalone running
fastapi_app = A2ARESTFastAPIApplication(agent_card=agent_card, http_handler=DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())).build()

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Supervisor Agent on port {port}...")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)
