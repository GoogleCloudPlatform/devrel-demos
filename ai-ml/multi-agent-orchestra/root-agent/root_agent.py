import asyncio
import json
import os
import shutil
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from google.adk.agents import BaseAgent, LlmAgent, SequentialAgent, RemoteA2aAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import BaseModel, Field

# Remove the local import since we're using the remote agent
# from music_production_loop_agent import music_production_loop_agent


class LyriaPrompt(BaseModel):
    """Represents a music generation request in a semi-structured form.
    It is made for a music generation AI model called Lyria.
    """

    original_request: str = Field(
        description="User's original text prompt for music generation"
    )
    generation_config: types.LiveMusicGenerationConfig = Field(
        description="Parameters of music to be generated."
    )
    weighted_prompts: List[types.WeightedPrompt] = Field(
        description="""
        List of weighted prompts. Each prompt
        is an element or an attribute of the produced music piece,
        mapped to a relative weight. Weights cannot be 0.
        https://ai.google.dev/gemini-api/docs/music-generation#prompt-guide-lyria
    """
    )


def _clean_base_models(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Callback for cleaning up response schema for LLM requests
    """

    def _clean(data: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in data.copy().items():
            if key == "additionalProperties":
                data.pop(key)
            if isinstance(value, dict):
                data[key] = _clean(value)
        return data

    if llm_request.config and llm_request.config.response_schema:
        schema = llm_request.config.response_schema
        if isinstance(schema, types.Schema):
            schema = schema.model_dump()
        elif hasattr(schema, "model_json_schema"):
            schema = schema.model_json_schema()  # type: ignore
        elif not isinstance(schema, dict):
            schema = json.loads(str(schema))
        llm_request.config.response_schema = _clean(schema)
    else:
        return None


user_prompt_parser_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="UserPromptParser",
    description="Converts user's free text music prompt into a Lyria API request",
    global_instruction="""
        You are a music brainstorming agent, that transforms musicians' text ideas into snippets of music to use as inspiration for new compositions. 
        Your task is to understand user's request, parse it into a semi-structured form.
        Include suggested values for required parameters when the user doesn't specify them.
        You must split the idea between multiple weighted prompts, each with its own components, such as instrument, mood, performance instructions, etc.
""",
    output_schema=LyriaPrompt,
    output_key="lyria_prompt",
    before_model_callback=_clean_base_models,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)


class SongTitle(BaseModel):
    """Generated title for the composed song"""

    title: str = Field(
        description="A short (up to 4 words) and vivid title for the song"
    )


class FinalSongInfo(BaseModel):
    """Final song information"""

    title: str = Field(description="The generated song title")
    filepath: str = Field(description="The path to the final audio file")


# Title generation agent - saves title to state (output_key)
title_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="TitleAgent",
    description="Generates a creative title for the composed song",
    global_instruction="""
        You are a creative title generator for music compositions. Based on the music generation process,
        critique feedback, and the original user prompt, create a short (up to 4 words) and vivid title
        that captures the essence of the final song.
        
        Consider:
        - The original user's music request
        - The mood and style of the music
        - Any instruments or genres mentioned
        - The critique agent's feedback
        
        Make the title memorable, evocative, and fitting for the music created.
    """,
    output_schema=SongTitle,
    output_key="song_title",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)


class FileRenamerAgent(BaseAgent):
    """Renames the final WAV audio file based on the generated title and cleans up intermediate WAV files"""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # Get the song title from state
        song_title = ctx.session.state.get("song_title", {})
        if isinstance(song_title, dict):
            song_title = SongTitle.model_validate(song_title)

        # Find all output files
        output_files = [
            f for f in os.listdir(".") if f.startswith("output_") and f.endswith(".wav")
        ]
        if not output_files:
            yield Event(
                author=self.name,
                content=types.Content(
                    parts=[types.Part(text="❌ No output file found to rename!")]
                ),
            )
            return

        # Sort by timestamp to get the most recent
        output_files.sort()
        latest_file = output_files[-1]

        # Create new filename from title (replace spaces with underscores)
        safe_title = (
            song_title.title.replace(" ", "_").replace("/", "_").replace("\\", "_")
        )
        new_filename = f"{safe_title}.wav"

        # Rename the file
        try:
            shutil.move(latest_file, new_filename)

            # Clean up all remaining intermediate output files
            cleanup_count = 0
            for old_file in output_files:
                if old_file != latest_file and os.path.exists(old_file):
                    try:
                        os.remove(old_file)
                        cleanup_count += 1
                    except Exception as cleanup_error:
                        print(
                            f"Warning: Could not remove intermediate file {old_file}: {cleanup_error}"
                        )

            # Store final song info in state
            final_info = FinalSongInfo(title=song_title.title, filepath=new_filename)

            # Update state with final song info
            ctx.session.state["final_song_info"] = final_info.model_dump()

            response_text = f"""
🎉 **Song Creation Complete!**

**Title:** {song_title.title}
**File:** {new_filename}

Your musical composition has been successfully created and saved.
            """

            if cleanup_count > 0:
                response_text += (
                    f"\n\n🧹 Cleaned up {cleanup_count} intermediate audio file(s)."
                )

            yield Event(
                author=self.name,
                content=types.Content(parts=[types.Part(text=response_text)]),
            )

        except Exception as e:
            yield Event(
                author=self.name,
                content=types.Content(
                    parts=[types.Part(text=f"❌ Error renaming file: {str(e)}")]
                ),
            )


# Create the file renamer agent
file_renamer_agent = FileRenamerAgent(
    name="FileRenamerAgent",
    description="Renames the final audio file based on the generated title",
)


# Create the remote music production loop agent using RemoteA2aAgent
music_production_loop_agent = RemoteA2aAgent(
    name="MusicProductionLoopAgent",
    description="Remote agent that handles the music production loop with composition and critique",
    agent_card="http://localhost:8001/.well-known/agent.json",
)


# Update the music sequence agent to include title generation and file renaming
root_agent = SequentialAgent(
    name="AIMusicAgent",
    description="AI Music Agent",
    sub_agents=[
        user_prompt_parser_agent,
        music_production_loop_agent,  # Remote agent consumed via A2A 
        title_agent,
        file_renamer_agent,
    ],
)


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
    runner = InMemoryRunner(root_agent, app_name="MusicGenerationApp")

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