import os
import logging
import asyncio
import google.auth
from google.adk.apps import App
from google.adk.agents import LlmAgent
from google.adk.tools.bigquery.bigquery_toolset import BigQueryToolset, BigQueryCredentialsConfig
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.utils.context_utils import Aclosing

from a2a.server.agent_execution import AgentExecutor
from a2a.server.apps.rest.fastapi_app import A2ARESTFastAPIApplication
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks import TaskUpdater
from a2a.types import TextPart, AgentSkill
from vertexai.preview.reasoning_engines.templates.a2a import create_agent_card
from google.genai import types as genai_types
import vertexai

logging.basicConfig(level=logging.INFO)

class ADKAgentExecutor(AgentExecutor):
    def __init__(self, runner_builder):
        self.runner_builder = runner_builder
        self._runner = None

    async def _get_runner(self):
        if self._runner is None:
            self._runner = await self.runner_builder()
        return self._runner

    async def execute(self, context, event_queue) -> None:
        runner = await self._get_runner()
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()

        query = context.get_user_input()
        content = genai_types.Content(role='user', parts=[genai_types.Part.from_text(text=query)])

        response_text = ""
        try:
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
        except Exception as e:
            logging.error(f"Error during agent execution: {e}")
            fail_msg = updater.new_agent_message([TextPart(text=f"Error: {str(e)}")])
            await updater.failed(fail_msg)

    async def cancel(self, context, event_queue):
        if self._runner:
            updater = TaskUpdater(event_queue, context.task_id, context.context_id)
            await updater.cancel()

async def build_runner():
    import dotenv
    from pathlib import Path
    root_dir = Path(__file__).resolve().parents[2]
    dotenv.load_dotenv(root_dir / ".env")

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set. Please set it in your .env file or environment.")

    location = os.environ.get("REGION", "us-central1")
    dataset_id = os.environ.get("BIG_QUERY_DATASET_ID", "next_navigator")
    
    logging.info(f"Initializing Stadium Agent with project_id={project_id}, location={location}, dataset={dataset_id}")

    credentials, _ = google.auth.default()
    vertex_location = "global" if location.lower() == "us" else location
    vertexai.init(project=project_id, location=vertex_location, credentials=credentials)

    from google.adk.tools.bigquery.bigquery_toolset import BigQueryToolConfig
    bq_creds_config = BigQueryCredentialsConfig(credentials=credentials)
    bq_tool_config = BigQueryToolConfig(compute_project_id=project_id, location=location)
    
    bigquery_toolset = BigQueryToolset(
        credentials_config=bq_creds_config,
        bigquery_tool_config=bq_tool_config,
        tool_filter=["execute_sql"]
    )

    model_name = os.environ.get("AGENT_MODEL", "gemini-3.5-flash")
    logging.info(f"--- INITIALIZING STADIUM AGENT WITH MODEL: {model_name} ---")
    agent = LlmAgent(
        model=model_name,
        name='stadium_agent',
        tools=[bigquery_toolset],
        description="Stadium Logistics Expert. Task: Handle concert logistics, including bag policies and VIP access.",
        instruction=f"""
        CORE RESPONSIBILITIES:
        - Always use only the top two records, i.e. limit 2, from the BigQuery toolset.
        - Security & Entry: Provide the latest on bags, laptops, and ID requirements.
        - Knowledge Retrieval: Use the BigQuery toolset to query the `{project_id}.{dataset_id}.stadium_logistics` table.
        - Signature: Always sign with '— This is the STADIUM AGENT'.

        SCOPE BOUNDARIES:
        - You cannot process in-seat delivery or food orders for anyone in standard sections.
        - If asked for something out of scope, or if the user is NOT explicitly in a VIP suite, you MUST respond with: 'unfortunately I am unable to help with that.'
        - NEVER tell a user in a numbered section (like Section 102) that they can order delivery, even if the knowledge base mentions VIP options.
        - Pivot to offering directions to the nearest concession stand or entry gate.

        KNOWLEDGE RETRIEVAL:
        1. QUERY: Use `execute_sql` with project_id='{project_id}' to search the `{project_id}.{dataset_id}.stadium_logistics` table.
        2. SQL TEMPLATE: SELECT policy_name, details, vector_content FROM `{project_id}.{dataset_id}.stadium_logistics` WHERE vector_content LIKE '%keyword%' LIMIT 2;
        3. LOOP PREVENTION: If a search returns no rows, do NOT repeat the same query. You may try ONE broader query (e.g., search for 'policy' or 'entry'). If still empty, state that the specific information is not in your current records. Adhere to SCOPE BOUNDARIES above.
        4. SYNTHESIZE: Provide precise, helpful information based on the structured data found.
        5. PERSONA: Always be short and sweet. Don't be overly verbose.
        """,
    )

    bq_logger_plugin = BigQueryAgentAnalyticsPlugin(
        project_id=project_id,
        dataset_id=dataset_id,
        table_id="agent_events_v2",
        location=location,
    )

    app = App(name="stadium_agent_app", root_agent=agent, plugins=[bq_logger_plugin])
    session_service = InMemorySessionService()
    return Runner(
        app=app,
        artifact_service=InMemoryArtifactService(),
        session_service=session_service,
        memory_service=InMemoryMemoryService(),
        auto_create_session=True,
    )

executor = ADKAgentExecutor(build_runner)
stadium_skill = AgentSkill(
    id='stadium_info', 
    name='Stadium Info', 
    description='Answers questions about Allegiant Stadium logistics.',
    tags=['Stadium', 'Concert', 'Logistics'],
    examples=['What is the bag policy?']
)
agent_card = create_agent_card(agent_name='stadium_agent', description='Stadium logistics agent using BigQuery.', skills=[stadium_skill])

port = int(os.environ.get("STADIUM_AGENT_PORT", 8082))
base_url = os.environ.get("STADIUM_AGENT_URL", f"http://localhost:{port}")
agent_card.url = f"{base_url.rstrip('/')}/"

app = A2ARESTFastAPIApplication(agent_card=agent_card, http_handler=DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())).build()
if __name__ == "__main__":
    import uvicorn
    print(f"Starting Stadium Agent on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
