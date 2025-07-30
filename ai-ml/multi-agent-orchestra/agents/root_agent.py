import asyncio
import json
from dotenv import load_dotenv

from google.genai import types
from google.adk.agents import SequentialAgent
from google.adk.runners import InMemoryRunner

from user_prompt_parser_agent import user_prompt_parser_agent
from music_production_loop_agent import music_production_loop_agent

music_sequence_agent = SequentialAgent(
    name="AIMusicAgent",
    description="AI Music Agent",
    sub_agents=[
        user_prompt_parser_agent,
        music_production_loop_agent,
    ],
)

root_agent = music_sequence_agent


async def main():
    """Main function to run the music generation agent."""
    print(
        """
                              .#%              
                             .+#%%.            
                             -%*#%%-           
                            .*#*#%%%:          
                            :%*#%@%%@:         
                           .@##%@%%%%@-        
                           *%#%%#.%#%%%=       
                          -%*%%@. -%#%@%-      
                         .*##%@=. .###@@*.     
                         -%#%%%:   +%#@@%:     
                        .##%%%+    +@#%@%.     
                        =%%%%#.   :%%#@@*.     
                       .@%%%@=   :%@@@@%-      
           .-++**+=:.  #%%%@#  -%@@@@@@=       
         +%*++++***#%*+@%%@@. .#@@@@@%.        
       =%*+++******###@%%%@+   -%@@*.          
      =%*+******##%%%%%%@@%:                   
     .##*****###%%%%%%@@@@=                    
     :%#**####%%%%%%%@@@@%:                    
     .#%###%%%%%%%%@@@@@@=                     
      -%%%%%%%%%%@@@@@@@+                      
       -%%%%%%%%@@@@@@@=                       
         =@%%%@@@@@@@*.                        
           .=*####*-.                          
         """
    )
    print("🎵 Music Production Agent with ADK, Lyria RealTime, and Gemini ✨")
    print("=" * 50)
    print("Examples of prompts you can try:")
    print("- 'jazzy piano in C major at 120 bpm'")
    print("- 'ambient electronic music with spacey synths, dreamy and ethereal'")
    print("- 'upbeat funk with guitar and drums, 140 bpm'")
    print("- 'classical orchestral score in D minor, emotional and rich'")
    print("- 'lo-fi hip hop beat with rhodes piano, chill mood at 85 bpm'")
    print("=" * 50)

    # Create agent and runner using InMemoryRunner
    agent = root_agent
    runner = InMemoryRunner(agent, app_name="MusicGenerationApp")

    # InMemoryRunner provides its own session service
    user_id = "music_user"
    session_id = "music_session"

    # Create a session
    session = await runner.session_service.create_session(
        app_name="MusicGenerationApp", user_id=user_id, session_id=session_id
    )

    user_input = ""

    while True:
        # Get user input
        user_input = input("\nEnter a music prompt (or 'quit' to exit): ")

        if user_input.lower() == "quit":
            break

        new_message = types.Content(role="user", parts=[types.Part(text=user_input)])

        print("-" * 50)
        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=new_message
        ):
            # Print non-partial events to console
            if not event.partial:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            print(f"[{event.author}]: {part.text}")
                fc = event.get_function_calls()
                fr = event.get_function_responses()
                if fc:
                    print(json.dumps(fc, indent=2))
                if fr:
                    print(json.dumps(fr, indent=2))
                if event.actions.state_delta:
                    print(json.dumps(event.actions.state_delta, indent=2))
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())
