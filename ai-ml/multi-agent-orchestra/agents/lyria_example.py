import asyncio
import pyaudio
import numpy as np
from google import genai
from google.genai import types

client = genai.Client(http_options={"api_version": "v1alpha"})

# Audio playback parameters
# Per https://ai.google.dev/gemini-api/docs/music-generation#audio-specs
SAMPLE_RATE = 48000
CHANNELS = 2  # Stereo
CHUNK_SIZE = 1024


async def main():
    print("🎵 Welcome to the music generator with Lyria realtime!")

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,  # 16-bit audio
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        output=True,
        frames_per_buffer=CHUNK_SIZE,
    )

    async def receive_and_play_audio(session):
        """Receive audio from the server and play it in real-time."""
        print("Receiving and playing audio...")
        try:
            while True:
                async for message in session.receive():
                    if message.server_content.audio_chunks:
                        audio_data = message.server_content.audio_chunks[0].data
                        if isinstance(audio_data, bytes):
                            stream.write(audio_data)
                        else:
                            audio_bytes = audio_data.tobytes()
                            stream.write(audio_bytes)

        except Exception as e:
            print(f"Error in audio playback: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

    async with (
        client.aio.live.music.connect(model="models/lyria-realtime-exp") as session,
        asyncio.TaskGroup() as tg,
    ):
        tg.create_task(receive_and_play_audio(session))
        # https://ai.google.dev/gemini-api/docs/music-generation#prompt-guide-lyria
        await session.set_weighted_prompts(
            prompts=[
                types.WeightedPrompt(text="Cello", weight=1.0),
                types.WeightedPrompt(text="Violin", weight=1.0),
                types.WeightedPrompt(text="Virtuoso", weight=1.0),
                types.WeightedPrompt(text="Emotional", weight=1.0),
            ]
        )
        # https://ai.google.dev/gemini-api/docs/music-generation#scale-enum
        await session.set_music_generation_config(
            config=types.LiveMusicGenerationConfig(
                bpm=90, temperature=1.0, scale=types.Scale.G_MAJOR_E_MINOR
            )
        )

        print("Starting stream...")
        await session.play()

        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nExiting...")


if __name__ == "__main__":
    asyncio.run(main())
