import asyncio
from collections import deque
from io import BytesIO
import json
from typing import Any, AsyncGenerator, Dict, List, Optional, Dict
import threading

from pydantic import BaseModel, Field
import pyaudio
import wave

from google import genai
from google.genai import types
from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner


# Audio playback parameters (from Lyria docs)
SAMPLE_RATE = 48000
CHANNELS = 2  # Stereo
CHUNK_SIZE = 1024
CRITIQUE_CHUNK_COUNT = 7 # number of chunks to critique


class ComposerAgent(BaseAgent):
    """Composes and plays music using Lyria model
    """

    buffer: deque = Field(default=deque([], CRITIQUE_CHUNK_COUNT))

    def __init__(self):
        super().__init__(
            name="MusicComposerAgent",
            description="An AI agent that generates music using Lyria model.",
        )
        # Store client and parser as private attributes to avoid Pydantic validation
        self._genai_client = None
        self._last_portion = []
        self._audio_thread = None
        self._session = None
        self._stopped = False
        self._reset_buffer = False
        self._buffer_size = 0

    def __del__(self):
        self._stopped = True
        if self._audio_thread:
            self._audio_thread.join()

    async def _audio_thread_func(self):
        audio = None
        stream = None
        try:
            while not self._stopped:
                self._session = None
                async with self._get_client().aio.live.music.connect(
                    model="models/lyria-realtime-exp"
                ) as session:
                    if self._stopped:
                        return
                    self._session = session
                    if not audio:
                        audio = pyaudio.PyAudio()
                    if not stream:
                        stream = audio.open(
                            format=pyaudio.paInt16,
                            channels=CHANNELS,
                            rate=SAMPLE_RATE,
                            output=True,
                            frames_per_buffer=CHUNK_SIZE,
                        )
                    async for message in session.receive():
                        if self._stopped:
                            break
                        if self._reset_buffer:
                            self._buffer_size = 0
                            self._reset_buffer = False
                            self.buffer.clear()
                        if message.server_content.audio_chunks:
                            for audio_chunk in message.server_content.audio_chunks:
                                audio_data = audio_chunk.data
                                if isinstance(audio_data, bytes):
                                    audio_bytes = audio_data
                                else:
                                    audio_bytes = audio_data.tobytes()
                                stream.write(audio_bytes)
                                self.buffer.append(audio_bytes)
                                self._buffer_size += len(audio_bytes)
        finally:
            self._session = None
            self._audio_thread = None
            if stream:
                stream.close()

    def _get_client(self):
        """Get or create the genai client."""
        if self._genai_client is None:
            self._genai_client = genai.Client(
                http_options={"api_version": "v1alpha"}
        )
        return self._genai_client

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:

        self._stopped = False
        if not self._audio_thread:
            self._audio_thread = threading.Thread(
                target=asyncio.run,
                args=(self._audio_thread_func(),)
            )
            self._audio_thread.start()
        while not self._session:
            await asyncio.sleep(1.0)

        lyria_prompt = ctx.session.state["lyria_prompt"]
        if isinstance(lyria_prompt, dict):
            lyria_prompt = LyriaPrompt.model_validate(lyria_prompt)
        await self._session.set_weighted_prompts(
            prompts=lyria_prompt.weighted_prompts
        )
        await self._session.set_music_generation_config(
            config=lyria_prompt.generation_config
        )
        print("\n================ New music generation ================")
        # print(lyria_prompt.model_dump_json(indent=2))
        await self._session.play()
        # Reset the music buffer
        self._reset_buffer = True
        # Make sure it's been reset
        while len(self.buffer) >= CRITIQUE_CHUNK_COUNT:
            await asyncio.sleep(0.1)
        # Wait for the buffer to be filled with music
        while len(self.buffer) < CRITIQUE_CHUNK_COUNT:
            await asyncio.sleep(0.5)

        with BytesIO() as wav_data:
            with wave.open(wav_data, "wb") as wav:
                wav.setnchannels(CHANNELS)
                wav.setframerate(SAMPLE_RATE)
                wav.setsampwidth(2) # 16 bit
                audio_data = list(self.buffer)
                for d in audio_data:
                    wav.writeframesraw(d)
                yield Event(
                    author=self.name,
                    content=types.Content(
                        role="model",
                        parts=[
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="audio/wav",
                                    data=wav_data.getvalue()
                                )
                            )
                        ]
                    )
                )


class LyriaPrompt(BaseModel):
    """Represents a music generation request in a semi-structured form.
    It is made for a music generation AI model called Lyria.
    """
    original_request: str = Field(description="What the user originally asked for.")
    generation_config: types.LiveMusicGenerationConfig = Field(
        description="Parameters of music to be generated."
    )
    weighted_prompts: List[types.WeightedPrompt] = Field(
        description="""
        List of so-called weighted prompts. Each prompt
        is an element or an attribute of the produced music piece,
        mapped to a relative weight. Weights cannot be 0.
    """
    )


class Critique(BaseModel):
    """
    Critique from a music producer. Tells if the music is great.
    If not, gives recommendations for improvement.
    """
    is_great: bool = Field(description="'Is Great' flag. Sets to True if the music is great.")
    recommendation: str = Field("What should we change about the music.")


class PromptToRevise(BaseModel):
    """
    Music generation prompt with critique of the results.
    """
    prompt: LyriaPrompt = Field(description="Original semi-structured prompt.")
    critique: Critique = Field(description="Critique of the results.")


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
            schema = schema.model_json_schema() # type: ignore
        elif not isinstance(schema, dict):
            schema = json.loads(str(schema))
        llm_request.config.response_schema = _clean(schema)
    else:
        return None


composer_agent = ComposerAgent()


original_music_producer_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="OriginalMusicProducer_",
    description="An AI agent that composes music.",
    global_instruction="""
        You are a Grammy-winner composer, song writer and sound producer specialized in writing big hits for other people.
        Your job is to help people make better music.

        Your user makes a request for music theme or a song.
        Your task is to understand user's request, parse it into a semi-structured form.
        Include suggested values for required parameters when the user doesn't specify them.
        You must split the idea between multiple weighted prompts, each with its own components, such as instrument, mood, performance instructions, etc.
""",
    output_schema=LyriaPrompt,
    output_key="lyria_prompt",
    before_model_callback=_clean_base_models,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


music_producer_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="MusicProducer",
    description="An AI agent that composes music.",
    global_instruction="""
        You are a Grammy-winner composer, song writer and sound producer specialized in writing big hits for other people.
        Your job is to help people make better music.

        Your user made a request for music theme or a song.
        A song was generated.
        Another experienced producer provided feedback and recommendations.
        Your task is:
            1. Understand the original request and recommendations.
            2. Analyze and internalize the critique provided.
            3. Come up with a new revised generation prompt.
        Use many weighted prompts, each with its own components, such as instrument, mood, performance instructions, etc.
""",
    input_schema=PromptToRevise,
    output_schema=LyriaPrompt,
    output_key="lyria_prompt",
    before_model_callback=_clean_base_models,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


class StopConditionVerifier(BaseAgent):
    """Issues Escalation action of critique result states that the music is great.
    """
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        critique = ctx.session.state.get("critique", None)
        if critique:
            if isinstance(critique, dict):
                critique = Critique.model_validate(critique)
            if critique.is_great:
                text = "\nThis is great! 🎉"
                yield Event(
                    author=self.name,
                    content=types.Content(
                        parts=[
                            types.Part(
                                text=text
                            )
                        ]
                    ),
                )
                yield Event(
                    actions=EventActions(escalate=True),
                    author=self.name
                )
            else:
                text = f"The music can be improved. Here is the recommendation:\n\n{critique.recommendation}"
                yield Event(
                    author=self.name,
                    content=types.Content(
                        parts=[
                            types.Part(
                                text=text
                            )
                        ]
                    ),
                )
            # print(text)


critique_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="CritiqueProducer",
    description="An AI agent that listens to music and provides feedback with recommendations for improvements.",
    global_instruction="""
        You are a Grammy-winner sound producer with huge success with viral tracks on social media.
        Your job is to help people make better music.

        Listen to the music provided. Look at the original request.
        Decide if the music sounds great to you AND if it fulfills the original idea of the user.
        If it should be improved, provide your recommendations, and set "Is Great" to false.
        Otherwise, set "Is Great" to true.

        You can only evaluate provided fragment about 30 seconds long.
        You cannot evaluate the structure of the theme. Assume you are providing live recommendations while they are improvising.
""",
    output_schema=Critique,
    output_key="critique",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True
)


improvement_loop_agent = LoopAgent(
    name="MainLoopAgent",
    sub_agents=[
        composer_agent,
        critique_agent,
        StopConditionVerifier(name="StopConditionVerifier"),
        music_producer_agent
    ],
    max_iterations=5
)


music_sequence_agent = SequentialAgent(
    name="AIMusicAgent",
    description="AI Music Agent",
    sub_agents=[
        original_music_producer_agent,
        improvement_loop_agent,
        # title_agent,
        # album_art_agent,
    ])

root_agent = music_sequence_agent


async def main():
    """Main function to run the music generation agent."""
    print("🎵 Enhanced Music Generation Agent with ADK")
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

    user_input = "Engaging uplifting epic trance, peak EDM festival."

    while True:
        # Get user input
        user_input = input("\nEnter a music prompt (or 'quit' to exit): ")

        if user_input.lower() == "quit":
            break

        new_message = types.Content(
            role="user",
            parts=[types.Part(text=user_input)]
        )

        print("-" * 50)
        async for event in runner.run_async(
                user_id=session.user_id,
                session_id=session.id,
                new_message=new_message
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
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())