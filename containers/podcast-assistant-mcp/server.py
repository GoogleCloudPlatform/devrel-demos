"""
    * Copyright 2025 Google LLC
    *
    * Licensed under the Apache License, Version 2.0 (the "License");
    * you may not use this file except in compliance with the License.
    * You may obtain a copy of the License at
    *
    *     http://www.apache.org/licenses/LICENSE-2.0
    *
    * Unless required by applicable law or agreed to in writing, software
    * distributed under the License is distributed on an "AS IS" BASIS,
    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    * See the License for the specific language governing permissions and
    * limitations under the License.
"""

import asyncio
import logging
import os
from google import genai
from google.genai import types
from google.cloud import storage
from urllib.parse import urlparse

from fastmcp import FastMCP

logger = logging.getLogger(__name__)
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.INFO)

mcp = FastMCP("Podcast Asistant")

# --- Configuration ---
# Load configuration from environment variables.
# This makes the code reusable and keeps sensitive info out of the source code.
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")

if not GCP_PROJECT_ID or not GCS_BUCKET_NAME:
    raise ValueError("Essential environment variables GCP_PROJECT_ID and GCS_BUCKET_NAME are not set.")

client = genai.Client(
    vertexai=True,
    project=GCP_PROJECT_ID,
    location=GCP_REGION,
)

storage_client = storage.Client()
gcs_bucket = storage_client.bucket(GCS_BUCKET_NAME)

# --- Helper Functions for reading to & writing from GCS ---
def read_from_gcs(gcs_uri: str) -> str:
    """Helper function to read text content from a GCS URI."""
    logger.info(f"Reading from GCS: {gcs_uri}")
    # Parse the GCS URI (e.g., "gs://bucket-name/path/to/file.txt")
    parsed_uri = urlparse(gcs_uri)
    bucket_name = parsed_uri.netloc
    blob_name = parsed_uri.path.lstrip('/')
    
    # Get the specific bucket and blob
    # Note: Assumes file is in the *same project*
    # If not, you may need a more complex client initialization
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    if not blob.exists():
        raise FileNotFoundError(f"GCS file not found: {gcs_uri}")
        
    return blob.download_as_text()

def upload_to_gcs(content: str, destination_blob_name: str) -> str:
    """Helper function to upload text content to GCS and return its URI."""
    logger.info(f"Writing to GCS: gs://{GCS_BUCKET_NAME}/{destination_blob_name}")
    blob = gcs_bucket.blob(destination_blob_name)
    blob.upload_from_string(content, content_type='text/plain; charset=utf-8')
    
    # Return the GCS URI
    return f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"

# --- Function 1: Generate Transcript ---
@mcp.tool()
def generate_transcript(audio_file_uri: str, episode_name: str) -> str:
    """
    Generates a transcript from an audio file and saves it to GCS.

    Args:
        audio_file_uri: The URI of the audio file (e.g., "gs://bucket-name/audio.mp3").
        episode_name: The name of the episode, used to create the output filename.

    Returns:
        The GCS URI of the generated transcript file.
    """

    logger.info(f">>> 🛠️ Tool: 'generate_transcript' called for '{audio_file_uri}'")
    if not audio_file_uri:
        raise ValueError("audio_file_uri cannot be empty.")
    if not episode_name:
        raise ValueError("episode_name cannot be empty.")

    # Determine mime_type based on file extension
    if audio_file_uri.lower().endswith(".mp3"):
        file_mime_type = "audio/mpeg"
    elif audio_file_uri.lower().endswith(".wav"):
        file_mime_type = "audio/wav"
    else:
        raise ValueError("Unsupported audio file type. Only .mp3 and .wav are supported.")

    # The text prompt to send to the model
    prompt = """
    You are a professional transcriptionist.
    Transcribe the following audio interview into a plain text format.
    Each line should represent a single utterance and follow this structure:
    [HH:MM:SS] Speaker Name: Spoken text
    
    -   The timecode should be in square brackets, in the format [HH:MM:SS].
    -   Use "Speaker A," "Speaker B," etc., to identify different speakers.
    -   Each speaker's utterance should be on a new line.
    -   Do not use JSON or any other structured data format.
    -   Do not include any extra information, just the transcript.

    Example:
    [00:00:05] Speaker A: Hello, welcome to the show.
    [00:00:10] Speaker B: Thanks for having me.
    [00:00:15] Speaker A: Let's get started.

    Avoid breaking up quotes. If a comment was made that overlapped another,
    represent them in separate rows, with the comment that started first, first.
    Now, transcribe the interview from the audio file.
    """

    audio_file_part = types.Part.from_uri(file_uri=audio_file_uri, mime_type=file_mime_type)

    response = client.models.generate_content(model=MODEL_NAME, contents=[prompt, audio_file_part])

    transcript_filename = f"{episode_name}_transcript.txt"
    gcs_uri = upload_to_gcs(response.text, transcript_filename)
    print(f"Transcription saved to {gcs_uri}")
    return gcs_uri

# --- Function 2: Generate Show Notes ---
@mcp.tool()
def generate_shownotes(transcript_gcs_uri: str, episode_name: str) -> str:
    """
    Generates show notes from a transcript file in GCS and saves them to GCS.

    Args:
        transcript_gcs_uri: The GCS URI of the transcript file.
        episode_name: The name of the episode, used to create the output filename.
    
    Returns:
        The GCS URI of the generated shownotes file.
    """
    logger.info(f">>> 🛠️ Tool: 'generate_shownotes' called for '{transcript_gcs_uri}'")
    
    try:
        transcript = read_from_gcs(transcript_gcs_uri)
    except FileNotFoundError as e:
        logger.error(str(e))
        raise e

    prompt = f"""
    You are a podcast producer. Based on the following transcript, please generate a set of show notes that includes:

    1.  A concise and engaging episode title.
    2.  A one-paragraph summary of the episode's main points.
    3.  A bulleted list of the key topics and themes discussed.

Here is the transcript:
    Transcript:
    ```
    {transcript}
    ```
    """

    response = client.models.generate_content(model=MODEL_NAME, contents=[prompt])

    shownotes_filename = f"{episode_name}_shownotes.md"
    gcs_uri = upload_to_gcs(response.text, shownotes_filename)
    print(f"Shownotes saved to {gcs_uri}")
    return gcs_uri

# --- Function 3: Generate Blog Post ---
@mcp.tool()
def generate_blog_post(transcript_gcs_uri: str, episode_name: str) -> str:
    """
    Generates a blog post summarizing the episode from a transcript file in GCS and saves it to GCS.

    Args:
        transcript_gcs_uri: The GCS URI of the transcript file.
        episode_name: The name of the episode, used to create the output filename.

    Returns:
        The GCS URI of the generated blog post file.
    """
    logger.info(f">>> 🛠️ Tool: 'generate_blog_post' called for '{transcript_gcs_uri}'")
    
    try:
        transcript = read_from_gcs(transcript_gcs_uri)
    except FileNotFoundError as e:
        logger.error(str(e))
        raise e

    prompt = f"""
    Write a detailed blog post summarizing the key topics and takeaways from the following transcript.
    Use Markdown formatting for headings, lists, and any other relevant elements.
    Make it engaging and informative for readers who may not have listened to the episode.
    Transcript:
    ```
    {transcript}
    ```
    """

    response = client.models.generate_content(model=MODEL_NAME, contents=[prompt])

    blog_post_filename = f"{episode_name}_blogpost.md"
    gcs_uri = upload_to_gcs(response.text, blog_post_filename)
    print(f"Blog post saved to {gcs_uri}")
    return gcs_uri


# --- Function 4: Generate Social Media Posts ---
@mcp.tool()
def generate_social_media_posts(transcript_gcs_uri: str, episode_name: str) -> str:
    """
    Generates social media post drafts for X (Twitter) and LinkedIn based on the transcript from GCS.

    Args:
        transcript_gcs_uri: The GCS URI of the transcript file.
        episode_name: The name of the episode, used to create the output filename.

    Returns:
        The GCS URI of the generated social media posts file.
    """
    logger.info(f">>> 🛠️ Tool: 'generate_social_media_posts' called for '{transcript_gcs_uri}'")
    
    try:
        transcript = read_from_gcs(transcript_gcs_uri)
    except FileNotFoundError as e:
        logger.error(str(e))
        raise e

    prompt = f"""
    Based on the following transcript, generate:
    1.  One draft social media posts for X (formerly Twitter), under 280 characters.
    2.  One draft social media posts for LinkedIn, with no character limit.
    Make the posts engaging and encourage people to listen to the episode.
    Use relevant hashtags.
    Format the output as follows:

    --- X Post 1 ---
    [X post text]

    --- LinkedIn Post 1 ---
    [LinkedIn post text]

    Transcript:
    ```
    {transcript}
    ```
    """

    response = client.models.generate_content(model=MODEL_NAME, contents=[prompt])

    social_posts_filename = f"{episode_name}_socialposts.txt"
    gcs_uri = upload_to_gcs(response.text, social_posts_filename)
    print(f"Social media posts saved to {gcs_uri}")
    return gcs_uri


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀Podcast MCP server started on port {port}")
    asyncio.run(
        mcp.run_async(
            transport="http",
            host="0.0.0.0",
            port=port,
        )
    )