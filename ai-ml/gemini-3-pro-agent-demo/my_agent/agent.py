from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types
import asyncio

# CONFIGURATION
APP_NAME = "simple_search_agent"
USER_ID = "user_default"
SESSION_ID = "session_01"

# AGENT DEFINITION
root_agent = Agent(
    name="search_agent",
    model="gemini-3-pro-preview",
    description="A helpful assistant that can search Google.",
    instruction="""
    You are a helpful assistant with access to Google Search.
    
    If the user asks a question that requires current information or facts, use the 'google_search' tool.
    Always cite your sources implicitly by providing the answer clearly based on the search results.
    """,
    # This is the only tool enabled
    tools=[google_search]
)

# Session and Runner
async def setup_session_and_runner():
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
    return session, runner

# Agent Interaction
async def call_agent_async(query):
    content = types.Content(role='user', parts=[types.Part(text=query)])
    session, runner = await setup_session_and_runner()
    events = runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

    async for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            print("Agent Response: ", final_response)

if __name__ == "__main__":
    asyncio.run(call_agent_async("what's the latest ai news?"))
