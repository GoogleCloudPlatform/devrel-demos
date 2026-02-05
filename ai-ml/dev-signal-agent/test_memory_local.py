import asyncio
import os
import google.auth
import vertexai
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.memory.vertex_ai_memory_bank_service import VertexAiMemoryBankService
from google.adk.sessions import InMemorySessionService
from vertexai import agent_engines
from google.genai import types
from dev_signal_agent.agent import root_agent

# Load environment variables
load_dotenv()

async def main():
    # 1. Setup Configuration
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    # Agent Engine (Memory) MUST use a regional endpoint
    resource_location = "us-central1"
    agent_name = "dev-signal"
    
    print(f"--- Initializing Vertex AI in {resource_location} ---")
    vertexai.init(project=project_id, location=resource_location)

    # 2. Find the Agent Engine Resource for Memory
    existing_agents = list(agent_engines.list(filter=f"display_name={agent_name}"))
    if existing_agents:
        agent_engine = existing_agents[0]
        agent_engine_id = agent_engine.resource_name.split("/")[-1]
        print(f"✅ Using persistent Memory Bank from Agent: {agent_engine_id}")
    else:
        print(f"❌ Error: Agent Engine '{agent_name}' not found. Please deploy with Terraform first.")
        return

    # 3. Initialize Services
    # We use InMemorySessionService for easier local testing (IDs are flexible)
    # BUT we use VertexAiMemoryBankService for REAL cloud persistence
    session_service = InMemorySessionService()
    
    memory_service = VertexAiMemoryBankService(
        project=project_id,
        location=resource_location,
        agent_engine_id=agent_engine_id
    )

    # 4. Create a Runner
    runner = Runner(
        agent=root_agent,
        app_name="dev-signal",
        session_service=session_service,
        memory_service=memory_service 
    )

    # 5. Run a Test Loop
    user_id = "local-tester"
    
    print("\n--- TEST SCENARIO ---")
    print("1. Start a session, tell the agent your preference (e.g., 'write in rhymes').")
    print("2. Type 'new' to start a FRESH session (local state wiped).")
    print("3. Ask for a blog post. The agent should retrieve your preference from the CLOUD memory.")
    
    current_session_id = "session-1"
    await session_service.create_session(
        app_name="dev-signal",
        user_id=user_id,
        session_id=current_session_id
    )
    print(f"\n--- Chat Session (ID: {current_session_id}) ---")

    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() in ["exit", "quit"]:
            break
            
        if user_input.lower() == "new":
            # Simulate starting a completely fresh session
            import uuid
            current_session_id = f"session-{str(uuid.uuid4())[:8]}"
            await session_service.create_session(
                app_name="dev-signal",
                user_id=user_id,
                session_id=current_session_id
            )
            print(f"\n--- Fresh Session Started (ID: {current_session_id}) ---")
            print("(Local history is empty, retrieval must come from Memory Bank)")
            continue

        print("Agent is thinking...")
        async for event in runner.run_async(
            user_id=user_id,
            session_id=current_session_id,
            new_message=types.Content(parts=[types.Part(text=user_input)])
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"Agent: {part.text}")
            
            if event.get_function_calls():
                for fc in event.get_function_calls():
                    print(f"🛠️  Tool Call: {fc.name}")

if __name__ == "__main__":
    asyncio.run(main())