from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types
import asyncio

# --- CONFIGURATION ---
APP_NAME = "viral_demo_finder"
USER_ID = "user1"
SESSION_ID = "session_thought_process"

# --- AGENT SETUP ---
# 1. We enforce the "Thinking" behavior in the instructions.
root_agent = Agent(
    name="viral_demo_researcher",
    model="gemini-3-pro-preview",
    description="Agent that researches X (Twitter), Reddit and YouTube for viral tech trends.",
    instruction="""
    You are a transparent Researcher Agent. 
    
    CRITICAL INSTRUCTION: You must exhibit "Chain of Thought" reasoning. 
    Before you use ANY tool, you must output a text response explaining specifically what you are about to do and why.
    
    Process:
    1. verbalize: "I need to find X..." -> Then call Google Search.
    2. verbalize: "I am analyzing the results..." -> Then process the data.
    3. verbalize: "Here are the viral ideas..." -> Then give the final answer.
    
    Task:
    Search X (Twitter), Reddit and Youtube via Google for viral demos related to the user's request.
    """,
    tools=[google_search]
)

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