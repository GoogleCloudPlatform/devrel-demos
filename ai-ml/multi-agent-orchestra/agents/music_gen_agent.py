import asyncio
from typing import AsyncGenerator, List, Optional, Dict, Tuple
from google import genai
from google.genai import types
import re
import wave
import numpy as np
from datetime import datetime
import sounddevice as sd


from google.adk.agents import Agent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.adk.sessions import Session
from google.adk.artifacts import InMemoryArtifactService


# Audio playback parameters (from Lyria docs)
SAMPLE_RATE = 48000
CHANNELS = 2  # Stereo
CHUNK_SIZE = 1024
MAX_DURATION_SECONDS = 5  # Maximum duration to record


class MusicPromptParser:
    """Parses natural language music prompts to extract weighted terms."""

    @classmethod
    def parse_prompt(cls, prompt: str) -> Dict[str, any]:
        """
        Parse a natural language prompt and extract weighted terms.

        Returns a dictionary with:
        - weighted_prompts: List of WeightedPrompt objects
        """
        # Clean the prompt
        prompt = prompt.strip()

        # Split into meaningful phrases
        phrases = cls._extract_phrases(prompt)

        # Create weighted prompts from phrases
        weighted_prompts = []

        # Assign weights based on position and importance
        # Earlier phrases get slightly higher weight
        for i, phrase in enumerate(phrases):
            if phrase.strip():
                # Calculate weight - first phrases are more important
                weight = 1.5 - (i * 0.1)
                weight = max(0.5, min(2.0, weight))  # Clamp between 0.5 and 2.0

                weighted_prompts.append(
                    types.WeightedPrompt(text=phrase.strip(), weight=weight)
                )

        # If no phrases were extracted, use the whole prompt
        if not weighted_prompts:
            weighted_prompts.append(types.WeightedPrompt(text=prompt, weight=1.0))

        return {
            "weighted_prompts": weighted_prompts,
        }

    @classmethod
    def _extract_phrases(cls, prompt: str) -> List[str]:
        """Extract meaningful phrases from prompt."""
        # Split by punctuation and common separators
        phrases = re.split(r"[,;.]|\s+and\s+|\s+with\s+|\s+but\s+", prompt)

        # Clean up phrases
        meaningful_phrases = []
        for phrase in phrases:
            cleaned = phrase.strip()
            if cleaned and len(cleaned) > 2:  # Skip very short phrases
                meaningful_phrases.append(cleaned)

        return meaningful_phrases


class MusicAgent(Agent):
    """Enhanced agent that generates music based on intelligently parsed user prompts."""

    def __init__(self):
        super().__init__(
            name="MusicAgent",
            description="An AI agent that generates music using Lyria based on text prompts",
        )
        # Store client and parser as private attributes to avoid Pydantic validation
        self._genai_client = None
        self._parser = MusicPromptParser()

    def _get_client(self):
        """Get or create the genai client."""
        if self._genai_client is None:
            self._genai_client = genai.Client(http_options={"api_version": "v1alpha"})
        return self._genai_client

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Process the user's music request."""
        # Get the last user message
        user_message = ""
        for event in reversed(ctx.session.events):
            if event.author == "user":
                if event.content and event.content.parts:
                    user_message = event.content.parts[0].text
                break

        if not user_message:
            yield Event(
                author=self.name,
                content=types.Content(
                    parts=[
                        types.Part(
                            text="Please provide a music prompt (e.g., 'dreamy piano meditation', 'upbeat electronic dance')"
                        )
                    ]
                ),
            )
            return

        # Parse the prompt
        parsed_prompt = self._parser.parse_prompt(user_message)

        # Build description of weighted prompts
        prompt_descriptions = []
        for wp in parsed_prompt["weighted_prompts"][:5]:  # Show first 5
            prompt_descriptions.append(f"'{wp.text}' (weight: {wp.weight:.1f})")

        description = " | ".join(prompt_descriptions)

        # Yield initial response
        yield Event(
            author=self.name,
            content=types.Content(
                parts=[
                    types.Part(
                        text=f"I'll generate music based on your prompt: '{user_message}'\n\n"
                        f"Weighted terms: {description}"
                    )
                ]
            ),
        )

        # Generate the music with parsed parameters
        async for event in self._generate_music(user_message, parsed_prompt, ctx):
            yield event

    async def _generate_music(
        self, original_prompt: str, parsed_prompt: Dict, ctx: InvocationContext
    ):
        """
        Generate music based on the parsed prompt and save to file.

        Args:
            original_prompt: The original user prompt
            parsed_prompt: Dictionary with parsed musical parameters
            ctx: The invocation context

        Yields:
            Events with status updates about the music generation
        """
        # Update state to indicate music generation is starting
        ctx.session.state["music_status"] = "generating"
        ctx.session.state["music_prompt"] = original_prompt

        # Yield an event to notify that generation is starting
        yield Event(
            author=self.name,
            content=types.Content(
                parts=[
                    types.Part(text=f"🎵 Starting music generation (5 seconds max)...")
                ]
            ),
            actions=EventActions(
                state_delta={
                    "music_status": "generating",
                    "music_prompt": original_prompt,
                }
            ),
        )

        # Prepare audio buffer for saving
        audio_buffer = []

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_music_{timestamp}.wav"

        try:
            client = self._get_client()
            async with client.aio.live.music.connect(
                model="models/lyria-realtime-exp"
            ) as session:
                # Set the weighted prompts from parsed data
                await session.set_weighted_prompts(
                    prompts=parsed_prompt["weighted_prompts"]
                )

                # Configure music generation with default temperature
                await session.set_music_generation_config(
                    config=types.LiveMusicGenerationConfig(temperature=1.0)
                )

                # Start the music generation
                await session.play()

                # Yield event that music is being recorded
                yield Event(
                    author=self.name,
                    content=types.Content(
                        parts=[
                            types.Part(
                                text=f"🎶 Recording and streaming music to {filename}..."
                            )
                        ]
                    ),
                    actions=EventActions(state_delta={"music_status": "recording"}),
                )

                # Collect audio data
                duration = 0
                chunk_count = 0
                max_chunks = int((MAX_DURATION_SECONDS * SAMPLE_RATE) / CHUNK_SIZE)

                # Open a WAV file for writing
                with wave.open(filename, "wb") as wav_file:
                    wav_file.setnchannels(CHANNELS)
                    wav_file.setsampwidth(2)  # 16-bit audio
                    wav_file.setframerate(SAMPLE_RATE)

                    # Open a sounddevice stream for playback
                    with sd.OutputStream(
                        samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16"
                    ) as stream:
                        try:
                            async for message in session.receive():
                                if message.server_content.audio_chunks:
                                    for (
                                        audio_chunk
                                    ) in message.server_content.audio_chunks:
                                        # Stop if we've reached 5 seconds
                                        if chunk_count >= max_chunks:
                                            # Stop the session immediately
                                            await session.stop()
                                            # Break out of both loops
                                            raise StopIteration()

                                        audio_data = audio_chunk.data
                                        if isinstance(audio_data, bytes):
                                            # Convert bytes to numpy array
                                            audio_array = np.frombuffer(
                                                audio_data, dtype=np.int16
                                            )
                                        else:
                                            audio_array = audio_data

                                        # Reshape for stereo playback
                                        audio_array = audio_array.reshape(-1, CHANNELS)

                                        # Write to file and stream
                                        wav_file.writeframes(audio_array.tobytes())
                                        stream.write(audio_array)

                                        audio_buffer.append(audio_array)
                                        chunk_count += 1

                                        # Update progress every 10 chunks
                                        if chunk_count % 10 == 0:
                                            duration = (
                                                chunk_count * CHUNK_SIZE
                                            ) / SAMPLE_RATE
                                            progress = (
                                                duration / MAX_DURATION_SECONDS
                                            ) * 100
                                            yield Event(
                                                author=self.name,
                                                content=types.Content(
                                                    parts=[
                                                        types.Part(
                                                            text=f"♪ Recording... {duration:.1f}s / {MAX_DURATION_SECONDS}s ({progress:.0f}%)"
                                                        )
                                                    ]
                                                ),
                                                partial=True,  # This is a streaming update
                                            )
                        except StopIteration:
                            # Expected when we hit the time limit
                            pass

                # Combine all audio chunks
                if audio_buffer:
                    combined_audio = np.concatenate(audio_buffer)

                    # Calculate actual duration
                    actual_duration = len(combined_audio) / (SAMPLE_RATE * CHANNELS)

                    yield Event(
                        author=self.name,
                        content=types.Content(
                            parts=[
                                types.Part(
                                    text=f"✅ Music generation complete!\n"
                                    f"📁 Saved {actual_duration:.1f} seconds of music to: {filename}\n"
                                    f"(Stopped at {MAX_DURATION_SECONDS} second limit)"
                                )
                            ]
                        ),
                        actions=EventActions(
                            state_delta={
                                "music_status": "complete",
                                "music_duration": actual_duration,
                                "output_file": filename,
                            }
                        ),
                    )
                else:
                    yield Event(
                        author=self.name,
                        content=types.Content(
                            parts=[types.Part(text="⚠️ No audio data was generated.")]
                        ),
                        actions=EventActions(state_delta={"music_status": "error"}),
                    )

        except Exception as e:
            # Don't treat StopIteration as an error
            if not isinstance(e, StopIteration):
                yield Event(
                    author=self.name,
                    content=types.Content(
                        parts=[types.Part(text=f"❌ Error generating music: {str(e)}")]
                    ),
                    actions=EventActions(state_delta={"music_status": "error"}),
                )


async def main():
    """Main function to run the music generation agent."""
    print("🎵 Music Generation Agent - Real-time Stream and Writer")

    print("=" * 50)
    print("Examples of prompts you can try:")
    print("- 'jazzy piano meditation'")
    print("- 'ambient electronic space music'")
    print("- 'upbeat funk guitar and drums'")
    print("- 'classical orchestral emotional'")
    print("- 'lo-fi hip hop chill beats'")
    print("\nGenerated music will be streamed and saved as WAV files (max 5 seconds)")
    print("=" * 50)

    # Create agent and runner using InMemoryRunner
    root_agent = MusicAgent()
    runner = InMemoryRunner(root_agent, app_name="MusicGenerationApp")

    # InMemoryRunner provides its own session service
    user_id = "music_user"
    session_id = "music_session"

    # Create a session
    session = await runner.session_service.create_session(
        app_name="MusicGenerationApp", user_id=user_id, session_id=session_id
    )

    # Interactive loop for multiple generations
    while True:
        # Get user input
        print("\n" + "-" * 50)
        user_prompt = input("Enter a music prompt (or 'quit' to exit): ").strip()

        if user_prompt.lower() in ["quit", "exit", "q"]:
            break

        if not user_prompt:
            print("Please enter a valid prompt!")
            continue

        # Create proper Content object for the message
        new_message = types.Content(role="user", parts=[types.Part(text=user_prompt)])

        # Process the user input
        print("\n" + "-" * 50)
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=new_message
        ):
            # Print non-partial events to console
            if not event.partial and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(f"[{event.author}]: {part.text}")

    print("\n👋 Goodbye!")


if __name__ == "__main__":
    asyncio.run(main())
