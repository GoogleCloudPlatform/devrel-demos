import asyncio
from collections import deque
from io import BytesIO
import json
import os
from typing import Any, AsyncGenerator, Dict, List, Optional, Dict
import threading
import time

from pydantic import BaseModel, Field
import pyaudio
import wave

from google import genai
from google.genai import types
from google.adk.agents import BaseAgent, LlmAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.agents.callback_context import CallbackContext
from google.adk.events import Event, EventActions

from user_prompt_parser_agent import LyriaPrompt, _clean_base_models


# Audio playback parameters (from Lyria docs)
SAMPLE_RATE = 48000
CHANNELS = 2  # Stereo
CHUNK_SIZE = 1024
CRITIQUE_CHUNK_COUNT = 100  # number of chunks to critique
RECORDING_DURATION = 15  # seconds


class ComposerAgent(BaseAgent):
    """Composes and plays music using Lyria model"""

    def __init__(self):
        super().__init__(
            name="ComposerAgent",
            description="An AI agent that generates music using the Lyria RealTime API.",
        )
        self._genai_client = None
        self._audio_buffer = []

    def _get_client(self):
        """Get or create the genai client."""
        if self._genai_client is None:
            self._genai_client = genai.Client(http_options={"api_version": "v1alpha"})
        return self._genai_client

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:

        lyria_prompt = ctx.session.state["lyria_prompt"]
        if isinstance(lyria_prompt, dict):
            lyria_prompt = LyriaPrompt.model_validate(lyria_prompt)

        # Clear the audio buffer
        self._audio_buffer = []

        # Setup PyAudio
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE,
        )

        try:
            # Connect to Lyria and generate music for exactly 30 seconds
            async with self._get_client().aio.live.music.connect(
                model="models/lyria-realtime-exp"
            ) as session:
                # Configure the session
                await session.set_weighted_prompts(
                    prompts=lyria_prompt.weighted_prompts
                )
                await session.set_music_generation_config(
                    config=lyria_prompt.generation_config
                )

                print("\n================ 🎹 Begin Music Stream 🎸 ================")

                # Start playing
                await session.play()

                # Record for exactly 30 seconds
                start_time = time.time()

                async for message in session.receive():
                    # Check if 30 seconds have passed
                    if time.time() - start_time >= RECORDING_DURATION:
                        break

                    if message.server_content.audio_chunks:
                        for audio_chunk in message.server_content.audio_chunks:
                            audio_data = audio_chunk.data
                            if isinstance(audio_data, bytes):
                                audio_bytes = audio_data
                            else:
                                audio_bytes = audio_data.tobytes()

                            # Play the audio
                            stream.write(audio_bytes)
                            # Store for saving later
                            self._audio_buffer.append(audio_bytes)

                # Stop the session
                await session.stop()

        finally:
            # Clean up audio resources
            stream.stop_stream()
            stream.close()
            audio.terminate()

        print("\n================ 🎹 Music Stream Stopped 🎸 ================")

        # Save the recorded audio
        output_filename = f"output_{int(time.time())}.wav"
        with wave.open(output_filename, "wb") as wav:
            wav.setnchannels(CHANNELS)
            wav.setframerate(SAMPLE_RATE)
            wav.setsampwidth(2)  # 16 bit
            for audio_chunk in self._audio_buffer:
                wav.writeframesraw(audio_chunk)

        print(f"\n✅ Saved audio to {output_filename}")

        # Yield the audio file for the critique agent
        with open(output_filename, "rb") as wav_file:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            inline_data=types.Blob(
                                mime_type="audio/wav", data=wav_file.read()
                            )
                        )
                    ],
                ),
            )


class Critique(BaseModel):
    """
    Critique from the music critique agent.
    """

    song_ready: bool = Field(
        description="True if the song is ready to finalize. False if it needs revisions."
    )
    recommendation: str = Field(
        "Critique agent's recommendations to improve the music's quality."
    )


class PromptToRevise(BaseModel):
    """
    Music generation prompt with critique of the results.
    """

    prompt: LyriaPrompt = Field(description="Original semi-structured prompt.")
    critique: Critique = Field(description="Critique of the results.")


composer_agent = ComposerAgent()


prompt_revision_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="PromptRevisionAgent",
    description="Re-generates the Lyria API prompt based on the critique agent's recommendations.",
    global_instruction="""
        You are a prompt revision agent for a music API. The critique agent just analyzed a generated song and provided recommendations for what to change. 
        Your task is:
            1. Understand the original user's request and then the critique agent's recommendations.
            2. Analyze and internalize the critique provided.
            3. Come up with a new revised generation prompt.
        Use many weighted prompts, each with its own components, such as instrument, mood, performance instructions, etc.
""",
    input_schema=PromptToRevise,
    output_schema=LyriaPrompt,
    output_key="lyria_prompt",
    before_model_callback=_clean_base_models,
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)


class StopConditionVerifier(BaseAgent):
    """Issues Escalation action of critique result states that the music is great."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        critique = ctx.session.state.get("critique", None)
        if critique:
            if isinstance(critique, dict):
                critique = Critique.model_validate(critique)
            if critique.song_ready:
                text = "\n✅ Song is ready to share- exiting production loop."
                yield Event(
                    author=self.name,
                    content=types.Content(parts=[types.Part(text=text)]),
                )
                yield Event(actions=EventActions(escalate=True), author=self.name)
            else:
                text = f"🤔 The critique agent suggested improvements to the song:\n\n{critique.recommendation}"
                yield Event(
                    author=self.name,
                    content=types.Content(parts=[types.Part(text=text)]),
                )


critique_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="CritiqueAgent",
    description="An AI agent that listens to generated music and provides feedback with recommendations for improvements.",
    global_instruction="""
        You are a music critique agent. Your task is to listen to the provided music, and provide an analysis of the song's quality, instrumentation, and mood. 
        
        If you think the song is of high quality as-is, set song_ready = true. 
        Otherwise, set song_ready = false and set recommendations to a few sentences' worth of suggested improvements.
        
        Examples of things you could add to the recommendations:
        - Change the tempo (faster, slower)
        - Change the key 
        - Add instruments 
        - Remove instruments
        - Song styles (eg. from pop to jazz), or layer multiple styles  
        - Change the mood (eg. from sad to hopeful)
        
        IMPORTANT: You are only given 30 seconds of audio to analyze. Analyze only the audio provided, as-is, and provide recommendations to the best of your ability. Do not ask for a longer music fragment.
""",
    output_schema=Critique,
    output_key="critique",
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)


music_production_loop_agent = LoopAgent(
    name="MusicProductionLoopAgent",
    sub_agents=[
        composer_agent,
        critique_agent,
        StopConditionVerifier(name="StopConditionVerifier"),
        prompt_revision_agent,
    ],
    max_iterations=3,
)
