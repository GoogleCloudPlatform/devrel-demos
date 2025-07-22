import asyncio
from typing import AsyncGenerator, List, Optional, Dict, Tuple
import pyaudio
from google import genai
from google.genai import types
import re

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


class MusicPromptParser:
    """Parses natural language music prompts to extract specific musical parameters."""

    # Define keywords for each category based on the Lyria documentation
    INSTRUMENTS = {
        "303 acid bass",
        "808 hip hop beat",
        "accordion",
        "alto saxophone",
        "bagpipes",
        "balalaika ensemble",
        "banjo",
        "bass clarinet",
        "bongos",
        "boomy bass",
        "bouzouki",
        "buchla synths",
        "cello",
        "charango",
        "clavichord",
        "conga drums",
        "didgeridoo",
        "dirty synths",
        "djembe",
        "drumline",
        "dulcimer",
        "fiddle",
        "flamenco guitar",
        "funk drums",
        "glockenspiel",
        "guitar",
        "hang drum",
        "harmonica",
        "harp",
        "harpsichord",
        "hurdy-gurdy",
        "kalimba",
        "koto",
        "lyre",
        "mandolin",
        "maracas",
        "marimba",
        "mbira",
        "mellotron",
        "metallic twang",
        "moog oscillations",
        "ocarina",
        "persian tar",
        "pipa",
        "precision bass",
        "ragtime piano",
        "rhodes piano",
        "shamisen",
        "shredding guitar",
        "sitar",
        "slide guitar",
        "smooth pianos",
        "spacey synths",
        "steel drum",
        "synth pads",
        "tabla",
        "tr-909 drum machine",
        "trumpet",
        "tuba",
        "vibraphone",
        "viola ensemble",
        "warm acoustic guitar",
        "woodwinds",
        "piano",
        "drums",
        "bass",
        "synthesizer",
        "violin",
        "saxophone",
        "flute",
        "organ",
        "electric guitar",
        "acoustic guitar",
    }

    GENRES = {
        "acid jazz",
        "afrobeat",
        "alternative country",
        "baroque",
        "bengal baul",
        "bhangra",
        "bluegrass",
        "blues rock",
        "bossa nova",
        "breakbeat",
        "celtic folk",
        "chillout",
        "chiptune",
        "classic rock",
        "contemporary r&b",
        "cumbia",
        "deep house",
        "disco funk",
        "drum & bass",
        "dubstep",
        "edm",
        "electro swing",
        "funk metal",
        "g-funk",
        "garage rock",
        "glitch hop",
        "grime",
        "hyperpop",
        "indian classical",
        "indie electronic",
        "indie folk",
        "indie pop",
        "irish folk",
        "jam band",
        "jamaican dub",
        "jazz fusion",
        "latin jazz",
        "lo-fi hip hop",
        "marching band",
        "merengue",
        "new jack swing",
        "minimal techno",
        "moombahton",
        "neo-soul",
        "orchestral score",
        "piano ballad",
        "polka",
        "post-punk",
        "60s psychedelic rock",
        "psytrance",
        "r&b",
        "reggae",
        "reggaeton",
        "renaissance music",
        "salsa",
        "shoegaze",
        "ska",
        "surf rock",
        "synthpop",
        "techno",
        "trance",
        "trap beat",
        "trip hop",
        "vaporwave",
        "witch house",
        "jazz",
        "rock",
        "pop",
        "classical",
        "electronic",
        "hip hop",
        "metal",
        "punk",
        "blues",
        "folk",
        "country",
    }

    MOODS = {
        "acoustic instruments",
        "ambient",
        "bright tones",
        "chill",
        "crunchy distortion",
        "danceable",
        "dreamy",
        "echo",
        "emotional",
        "ethereal ambience",
        "experimental",
        "fat beats",
        "funky",
        "glitchy effects",
        "huge drop",
        "live performance",
        "lo-fi",
        "ominous drone",
        "psychedelic",
        "rich orchestration",
        "saturated tones",
        "subdued melody",
        "sustained chords",
        "swirling phasers",
        "tight groove",
        "unsettling",
        "upbeat",
        "virtuoso",
        "weird noises",
        "happy",
        "sad",
        "energetic",
        "relaxing",
        "dark",
        "bright",
        "mellow",
        "intense",
        "peaceful",
        "aggressive",
        "mysterious",
        "romantic",
        "nostalgic",
        "futuristic",
        "retro",
    }

    # Scale mapping from natural language to enum values
    SCALE_MAPPING = {
        "c major": types.Scale.C_MAJOR_A_MINOR,
        "a minor": types.Scale.C_MAJOR_A_MINOR,
        "d flat major": types.Scale.D_FLAT_MAJOR_B_FLAT_MINOR,
        "db major": types.Scale.D_FLAT_MAJOR_B_FLAT_MINOR,
        "b flat minor": types.Scale.D_FLAT_MAJOR_B_FLAT_MINOR,
        "bb minor": types.Scale.D_FLAT_MAJOR_B_FLAT_MINOR,
        "d major": types.Scale.D_MAJOR_B_MINOR,
        "b minor": types.Scale.D_MAJOR_B_MINOR,
        "e flat major": types.Scale.E_FLAT_MAJOR_C_MINOR,
        "eb major": types.Scale.E_FLAT_MAJOR_C_MINOR,
        "c minor": types.Scale.E_FLAT_MAJOR_C_MINOR,
        "e major": types.Scale.E_MAJOR_D_FLAT_MINOR,
        "c sharp minor": types.Scale.E_MAJOR_D_FLAT_MINOR,
        "c# minor": types.Scale.E_MAJOR_D_FLAT_MINOR,
        "d flat minor": types.Scale.E_MAJOR_D_FLAT_MINOR,
        "db minor": types.Scale.E_MAJOR_D_FLAT_MINOR,
        "f major": types.Scale.F_MAJOR_D_MINOR,
        "d minor": types.Scale.F_MAJOR_D_MINOR,
        "g flat major": types.Scale.G_FLAT_MAJOR_E_FLAT_MINOR,
        "gb major": types.Scale.G_FLAT_MAJOR_E_FLAT_MINOR,
        "e flat minor": types.Scale.G_FLAT_MAJOR_E_FLAT_MINOR,
        "eb minor": types.Scale.G_FLAT_MAJOR_E_FLAT_MINOR,
        "g major": types.Scale.G_MAJOR_E_MINOR,
        "e minor": types.Scale.G_MAJOR_E_MINOR,
        "a flat major": types.Scale.A_FLAT_MAJOR_F_MINOR,
        "ab major": types.Scale.A_FLAT_MAJOR_F_MINOR,
        "f minor": types.Scale.A_FLAT_MAJOR_F_MINOR,
        "a major": types.Scale.A_MAJOR_G_FLAT_MINOR,
        "f sharp minor": types.Scale.A_MAJOR_G_FLAT_MINOR,
        "f# minor": types.Scale.A_MAJOR_G_FLAT_MINOR,
        "g flat minor": types.Scale.A_MAJOR_G_FLAT_MINOR,
        "gb minor": types.Scale.A_MAJOR_G_FLAT_MINOR,
        "b flat major": types.Scale.B_FLAT_MAJOR_G_MINOR,
        "bb major": types.Scale.B_FLAT_MAJOR_G_MINOR,
        "g minor": types.Scale.B_FLAT_MAJOR_G_MINOR,
        "b major": types.Scale.B_MAJOR_A_FLAT_MINOR,
        "g sharp minor": types.Scale.B_MAJOR_A_FLAT_MINOR,
        "g# minor": types.Scale.B_MAJOR_A_FLAT_MINOR,
        "a flat minor": types.Scale.B_MAJOR_A_FLAT_MINOR,
        "ab minor": types.Scale.B_MAJOR_A_FLAT_MINOR,
    }

    @classmethod
    def parse_prompt(cls, prompt: str) -> Dict[str, any]:
        """
        Parse a natural language prompt and extract musical parameters.

        Returns a dictionary with:
        - instruments: List of detected instruments
        - genres: List of detected genres
        - moods: List of detected moods/descriptions
        - bpm: Detected BPM (if any)
        - scale: Detected scale enum (if any)
        - weighted_prompts: List of WeightedPrompt objects
        """
        prompt_lower = prompt.lower()

        # Extract BPM
        bpm = cls._extract_bpm(prompt_lower)

        # Extract scale
        scale = cls._extract_scale(prompt_lower)

        # Extract musical elements
        instruments = cls._extract_elements(prompt_lower, cls.INSTRUMENTS)
        genres = cls._extract_elements(prompt_lower, cls.GENRES)
        moods = cls._extract_elements(prompt_lower, cls.MOODS)

        # Create weighted prompts
        weighted_prompts = []

        # Add instruments
        for instrument in instruments:
            weighted_prompts.append(types.WeightedPrompt(text=instrument, weight=1.0))

        # Add genres
        for genre in genres:
            weighted_prompts.append(types.WeightedPrompt(text=genre, weight=1.0))

        # Add moods
        for mood in moods:
            weighted_prompts.append(types.WeightedPrompt(text=mood, weight=1.0))

        # If no specific elements were found, use the original prompt
        if not weighted_prompts:
            # Split into meaningful phrases instead of just words
            phrases = cls._extract_phrases(prompt)
            for phrase in phrases:
                if phrase.strip():
                    weighted_prompts.append(
                        types.WeightedPrompt(text=phrase, weight=1.0)
                    )

        # Always add quality enhancers
        weighted_prompts.extend(
            [
                types.WeightedPrompt(text="High Quality", weight=0.8),
                types.WeightedPrompt(text="Musical", weight=0.8),
            ]
        )

        return {
            "instruments": instruments,
            "genres": genres,
            "moods": moods,
            "bpm": bpm,
            "scale": scale,
            "weighted_prompts": weighted_prompts,
        }

    @classmethod
    def _extract_bpm(cls, prompt: str) -> Optional[int]:
        """Extract BPM from prompt if specified."""
        # Look for patterns like "120 bpm", "bpm 120", "tempo 120"
        bpm_patterns = [
            r"(\d+)\s*bpm",
            r"bpm\s*(\d+)",
            r"tempo\s*(\d+)",
            r"(\d+)\s*beats?\s*per\s*minute",
        ]

        for pattern in bpm_patterns:
            match = re.search(pattern, prompt)
            if match:
                bpm = int(match.group(1))
                # Clamp to valid range [60, 200]
                return max(60, min(200, bpm))

        # Look for tempo descriptors and map to BPM
        tempo_mapping = {
            "slow": 70,
            "moderate": 100,
            "medium": 100,
            "fast": 140,
            "very fast": 180,
            "presto": 180,
            "allegro": 140,
            "andante": 80,
            "adagio": 70,
        }

        for tempo, bpm in tempo_mapping.items():
            if tempo in prompt:
                return bpm

        return None

    @classmethod
    def _extract_scale(cls, prompt: str) -> Optional[types.Scale]:
        """Extract musical scale from prompt if specified."""
        # Check for exact scale matches
        for scale_name, scale_enum in cls.SCALE_MAPPING.items():
            if scale_name in prompt:
                return scale_enum

        # Check for key references
        key_pattern = r"in\s+([a-g])\s*(sharp|#|flat|b)?\s*(major|minor)?"
        match = re.search(key_pattern, prompt)
        if match:
            key = match.group(1)
            accidental = match.group(2)
            mode = match.group(3)

            # Build the scale name
            scale_name = key
            if accidental:
                if accidental in ["sharp", "#"]:
                    scale_name += " sharp"
                elif accidental in ["flat", "b"]:
                    scale_name += " flat"

            if mode:
                scale_name += f" {mode}"
            else:
                scale_name += " major"  # Default to major

            # Try to find the scale
            return cls.SCALE_MAPPING.get(scale_name, None)

        return None

    @classmethod
    def _extract_elements(cls, prompt: str, element_set: set) -> List[str]:
        """Extract elements from prompt that match the given set."""
        found_elements = []

        # Sort by length (longest first) to match multi-word phrases first
        sorted_elements = sorted(element_set, key=len, reverse=True)

        for element in sorted_elements:
            if element in prompt:
                found_elements.append(element)
                # Remove the found element to avoid partial matches
                prompt = prompt.replace(element, "")

        return found_elements

    @classmethod
    def _extract_phrases(cls, prompt: str) -> List[str]:
        """Extract meaningful phrases from prompt."""
        # Remove common filler words
        filler_words = {
            "a",
            "an",
            "the",
            "with",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
        }

        # Split by punctuation and common separators
        phrases = re.split(r"[,;.]|\s+and\s+|\s+with\s+", prompt)

        meaningful_phrases = []
        for phrase in phrases:
            # Remove filler words from the beginning and end
            words = phrase.strip().split()
            if words:
                # Keep phrases that have meaningful content
                cleaned_words = [
                    w for w in words if w.lower() not in filler_words or len(words) <= 2
                ]
                if cleaned_words:
                    meaningful_phrases.append(" ".join(words))

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
                            text="Please provide a music prompt (e.g., 'dreamy piano in C major at 80 bpm', 'upbeat jazz fusion with saxophone')"
                        )
                    ]
                ),
            )
            return

        # Parse the prompt
        parsed_prompt = self._parser.parse_prompt(user_message)

        # Build a description of what was detected
        description_parts = []
        if parsed_prompt["instruments"]:
            description_parts.append(
                f"Instruments: {', '.join(parsed_prompt['instruments'])}"
            )
        if parsed_prompt["genres"]:
            description_parts.append(f"Genres: {', '.join(parsed_prompt['genres'])}")
        if parsed_prompt["moods"]:
            description_parts.append(f"Mood: {', '.join(parsed_prompt['moods'])}")
        if parsed_prompt["bpm"]:
            description_parts.append(f"Tempo: {parsed_prompt['bpm']} BPM")
        if parsed_prompt["scale"]:
            # Find the scale name for display
            scale_name = "Unknown"
            for name, enum_val in MusicPromptParser.SCALE_MAPPING.items():
                if enum_val == parsed_prompt["scale"]:
                    scale_name = name.title()
                    break
            description_parts.append(f"Key: {scale_name}")

        description = (
            " | ".join(description_parts) if description_parts else "General music"
        )

        # Yield initial response
        yield Event(
            author=self.name,
            content=types.Content(
                parts=[
                    types.Part(
                        text=f"I'll generate music based on your prompt: '{user_message}'\n\n"
                        f"Detected parameters: {description}"
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
        Generate music based on the parsed prompt.

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
        ctx.session.state["music_parameters"] = {
            "instruments": parsed_prompt["instruments"],
            "genres": parsed_prompt["genres"],
            "moods": parsed_prompt["moods"],
            "bpm": parsed_prompt["bpm"],
            "scale": str(parsed_prompt["scale"]) if parsed_prompt["scale"] else None,
        }

        # Yield an event to notify that generation is starting
        yield Event(
            author=self.name,
            content=types.Content(
                parts=[types.Part(text=f"🎵 Starting music generation...")]
            ),
            actions=EventActions(
                state_delta={
                    "music_status": "generating",
                    "music_prompt": original_prompt,
                    "music_parameters": ctx.session.state["music_parameters"],
                }
            ),
        )

        # Initialize PyAudio for streaming
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE,
        )

        try:
            client = self._get_client()
            async with client.aio.live.music.connect(
                model="models/lyria-realtime-exp"
            ) as session:
                # Set the weighted prompts from parsed data
                await session.set_weighted_prompts(
                    prompts=parsed_prompt["weighted_prompts"]
                )

                # Build the music generation config
                config_params = {
                    "temperature": 1.0,
                }

                # Add BPM if detected
                if parsed_prompt["bpm"]:
                    config_params["bpm"] = parsed_prompt["bpm"]

                # Add scale if detected
                if parsed_prompt["scale"]:
                    config_params["scale"] = parsed_prompt["scale"]

                # Configure music generation
                await session.set_music_generation_config(
                    config=types.LiveMusicGenerationConfig(**config_params)
                )

                # Start the music generation
                await session.play()

                # Yield event that music is now playing
                yield Event(
                    author=self.name,
                    content=types.Content(
                        parts=[types.Part(text="🎶 Music is now playing...")]
                    ),
                    actions=EventActions(state_delta={"music_status": "playing"}),
                )

                # Stream the audio
                duration = 0
                chunk_count = 0

                async for message in session.receive():
                    if message.server_content.audio_chunks:
                        for audio_chunk in message.server_content.audio_chunks:
                            audio_data = audio_chunk.data
                            if isinstance(audio_data, bytes):
                                stream.write(audio_data)
                            else:
                                audio_bytes = audio_data.tobytes()
                                stream.write(audio_bytes)

                            chunk_count += 1
                            # Update progress every 10 chunks
                            if chunk_count % 10 == 0:
                                duration = (chunk_count * CHUNK_SIZE) / SAMPLE_RATE
                                yield Event(
                                    author=self.name,
                                    content=types.Content(
                                        parts=[
                                            types.Part(
                                                text=f"♪ Playing... ({duration:.1f}s)"
                                            )
                                        ]
                                    ),
                                    partial=True,  # This is a streaming update
                                )

                # Final status
                total_duration = (chunk_count * CHUNK_SIZE) / SAMPLE_RATE
                yield Event(
                    author=self.name,
                    content=types.Content(
                        parts=[
                            types.Part(
                                text=f"✅ Music generation complete! Generated {total_duration:.1f} seconds of music."
                            )
                        ]
                    ),
                    actions=EventActions(
                        state_delta={
                            "music_status": "complete",
                            "music_duration": total_duration,
                        }
                    ),
                )

        except Exception as e:
            yield Event(
                author=self.name,
                content=types.Content(
                    parts=[types.Part(text=f"❌ Error generating music: {str(e)}")]
                ),
                actions=EventActions(state_delta={"music_status": "error"}),
            )

        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()


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
    agent = MusicAgent()
    runner = InMemoryRunner(agent, app_name="MusicGenerationApp")

    # InMemoryRunner provides its own session service
    user_id = "music_user"
    session_id = "music_session"

    # Create a session
    session = await runner.session_service.create_session(
        app_name="MusicGenerationApp", user_id=user_id, session_id=session_id
    )

    while True:
        # Get user input
        user_input = input("\nEnter a music prompt (or 'quit' to exit): ")

        if user_input.lower() == "quit":
            break

        # Create proper Content object for the message
        new_message = types.Content(role="user", parts=[types.Part(text=user_input)])

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
