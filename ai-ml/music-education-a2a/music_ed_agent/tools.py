import yt_dlp
from pydub import AudioSegment
import os
import logging
import re
from google.adk.tools.langchain_tool import LangchainTool
from langchain_community.tools import YouTubeSearchTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# https://python.langchain.com/docs/integrations/tools/youtube/
#  📹 YouTube Search Tool - LangChain 3p tool
youtube_search_tool_instance = YouTubeSearchTool()
adk_youtube_search_tool = LangchainTool(tool=youtube_search_tool_instance)


#  🌐 Wikipedia Search Tool - LangChain 3p tool
wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
adk_wikipedia_tool = LangchainTool(tool=wikipedia)


def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from URL

    Args:
        url: YouTube URL

    Returns:
        Video ID or None if not found
    """
    patterns = [
        r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?]*)",
        r"(?:youtube\.com\/v\/)([^&\n?]*)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def download_youtube_video_mp3(youtube_url: str) -> str:
    """
    Download a YouTube video and extract the first 60 seconds of audio as MP3.

    Args:
        youtube_url: The YouTube video URL as a string

    Returns:
        str: Full filepath where the audio was saved, or empty string if failed
    """
    # Extract video ID and create output filename
    duration = 60
    id_chars = 8
    video_id = extract_video_id(youtube_url)
    if not video_id:
        logger.error("Could not extract video ID from URL")
        return ""

    output_filename = f"{video_id[:id_chars]}.mp3"
    output_filepath = os.path.abspath(output_filename)
    logger.info(f"Output filepath will be: {output_filepath}")

    # Configure yt-dlp options
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": "temp_audio.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "logger": logger,
    }

    try:
        # Download the audio
        logger.info(f"Downloading audio from: {youtube_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

        # Load the downloaded audio file
        logger.info("Loading audio file...")
        audio = AudioSegment.from_mp3("temp_audio.mp3")

        # Extract first N seconds
        logger.info(f"Extracting first {duration} seconds...")
        first_n_seconds = audio[: duration * 1000]  # pydub works in milliseconds

        # Export as MP3
        logger.info(f"Saving as {output_filepath}...")
        first_n_seconds.export(output_filepath, format="mp3")

        # Clean up temporary file
        if os.path.exists("temp_audio.mp3"):
            os.remove("temp_audio.mp3")
            logger.debug("Cleaned up temporary file")

        logger.info(
            f"Successfully saved {duration} seconds of audio to {output_filepath}"
        )
        return output_filepath

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        # Clean up temporary file if it exists
        if os.path.exists("temp_audio.mp3"):
            os.remove("temp_audio.mp3")
            logger.debug("Cleaned up temporary file after error")
        return ""
