import asyncio
import sys
from aida.agent import root_agent
from google.adk.runners import InMemoryRunner
from google.adk.runners import types
from dotenv import load_dotenv

load_dotenv()

async def main():
    # Initialize runner with the agent
    runner = InMemoryRunner(agent=root_agent)
    
    # Create a session. We use the runner's app_name to ensure compatibility.
    await runner.session_service.create_session(
        user_id="repro_user", 
        session_id="repro_session", 
        app_name=runner.app_name
    )

    prompt = "show me the first query for malware diagnostics (k=1)"
    print(f"Sending prompt: '{prompt}'")
    
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    try:
        async for event in runner.run_async(
            user_id="repro_user", 
            session_id="repro_session", 
            new_message=message
        ):
            # Print the response text
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text)
            
    except Exception as e:
        print(f"\nCaught error:\n{e}")
        # We expect a ValueError here if the bug is reproduced
        sys.exit(1)

    print("Finished successfully.")

if __name__ == "__main__":
    asyncio.run(main())