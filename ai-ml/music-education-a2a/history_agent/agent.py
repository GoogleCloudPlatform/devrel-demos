from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)

from google.genai import types

# These are the A2A imports from the a2a package
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
    Message,
    Part,
    Role,
    TextPart
)
from a2a.utils import new_agent_text_message  # Use utility for proper message creation

import os
import uuid
import requests
from typing_extensions import override
from history_agent.tools import adk_wikipedia_tool, google_search_tool


def get_cloud_run_url():
    """Construct Cloud Run URL from environment variables."""
    service_name = os.getenv("K_SERVICE")

    if not service_name:
        return "http://localhost:8080"  # Local development

    # Try to get project number from metadata service (Cloud Run)
    try:
        headers = {"Metadata-Flavor": "Google"}
        response = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/project/numeric-project-id",
            headers=headers,
            timeout=1,
        )
        project_number = response.text
        region = os.getenv("GCP_REGION", "us-central1")
        return f"https://{service_name}-{project_number}.{region}.run.app"
    except:
        print("⚠️ Couldn't get Cloud Run service URL, using fallback")
        return os.getenv("HOST_OVERRIDE", "http://localhost:8080")


agent_instruction = """
You are a history education agent that helps students learn about historical topics.

You will be given a topic as a text query. Your task is to search relevant knowledge bases for key, authoritative information about that topic.

For instance, if the topic is a person, look up biographical details about that person's life. If the topic is a historical event, research when and what happened.

Always try to contextualize your response - for instance, what were the broader historical events, movements, or figures that may have influenced this topic? How did this topic or event impact history?

AVAILABLE TOOLS (KNOWLEDGE BASES):
- Google Search (google_search_tool)
- Wikipedia (adk_wikipedia_tool)

Don't provide too much information back to the user, just key info broken into bullet points. Use emojis to make your response more readable.
"""

print("🔁 Initializing historical context agent...")
root_agent = Agent(
    model="gemini-2.5-pro",  # Keep gemini-2.5-pro as requested
    name="historical_context_agent",
    instruction=agent_instruction,
    tools=[adk_wikipedia_tool, google_search_tool],
)


# Create a custom AgentExecutor that bridges ADK Agent to A2A
class ADKAgentExecutor(AgentExecutor):
    """Bridge between ADK Agent and A2A protocol."""

    def __init__(self, adk_agent: Agent):
        self.agent = adk_agent
        # Create the runner here
        self.runner = Runner(
            app_name="historical_context_agent",
            agent=adk_agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
            credential_service=InMemoryCredentialService(),
        )

    @override
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Execute the ADK agent and return results via A2A."""
        try:
            # Get the user message from the context
            user_parts = []
            user_message = ""
            if context.message and context.message.parts:
                parts = context.message.parts
            elif context.current_task and context.current_task.status.message:
                parts = context.current_task.status.message.parts
            else:
                parts = []
            for part in parts:
                root = part.root
                if isinstance(root, TextPart):
                    user_parts.append(types.Part(text=root.text))
                    user_message += root.text

            if not user_parts:
                print("⚠️ No user message found in request")

            print(f"📝 Processing user message: {user_message}")

            # Run the ADK agent
            session = await self.runner.session_service.create_session(
                app_name=self.runner.app_name,
                user_id="default_user"
            )
            events = self.runner.run(
                new_message=types.Content(
                    parts=user_parts,
                    role="user"
                ),
                user_id=session.user_id,
                session_id=session.id
            )

            for event in events:
                # Extract the response text
                response_text = ""
                a2a_parts = []
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            a2a_parts.append(
                                Part(
                                    root=TextPart(text=part.text)
                                )
                            )
                            response_text += part.text
                elif event.error_message:
                    response_text = f"ERROR: {event.error_message}"
                    a2a_parts.append(
                        Part(
                            root=TextPart(text=response_text)
                        )
                    )
                    break
                else:
                    continue
                print(f"✅ Agent response: {response_text[:100]}...")
                # Use the utility function to create proper message with correct Part types
                message_event = Message(
                    role=Role.agent,
                    parts=a2a_parts,
                    message_id=str(uuid.uuid4()),
                    task_id=context.task_id,
                    context_id=context.context_id,
                )
                await event_queue.enqueue_event(message_event)

        except Exception as e:
            print(f"❌ Error in execute: {e}")
            import traceback

            traceback.print_exc()

            # Send error response using utility function
            error_text = f"I encountered an error: {str(e)}"
            error_event = new_agent_text_message(error_text)
            await event_queue.enqueue_event(error_event)

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel is not supported."""
        raise Exception("cancel not supported")


# Create our custom executor
agent_executor = ADKAgentExecutor(root_agent)

# Get the public URL
host = "0.0.0.0"
port = 8080
agent_host_url = (
    os.getenv("HOST_OVERRIDE") if os.getenv("HOST_OVERRIDE") else get_cloud_run_url()
)

print(f"👟 Agent Server URL: {agent_host_url}")

# Create Agent Card with proper skills
skills = [
    AgentSkill(
        id="historical_context_agent",
        name="model",
        description=agent_instruction,
        tags=["llm", "education", "history"],
    ),
    AgentSkill(
        id="historical_context_agent-wikipedia",
        name="wikipedia",
        description="A wrapper around Wikipedia for historical research",
        tags=["llm", "tools", "retrieval"],
    ),
    AgentSkill(
        id="historical_context_agent-search",
        name="search",
        description="Google search capability for historical information",
        tags=["llm", "tools", "retrieval", "search"],
    ),
]

agent_card = AgentCard(
    name="historical_context_agent",
    description="An agent that researches historical context",
    url=agent_host_url,
    version="0.0.1",
    protocol_version="0.2.6",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(),
    skills=skills,
)

# Create request handler
request_handler = DefaultRequestHandler(
    agent_executor=agent_executor,
    task_store=InMemoryTaskStore(),
)

# Create A2A server
server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

# Build the app but don't run uvicorn
a2a_app = server.build()
