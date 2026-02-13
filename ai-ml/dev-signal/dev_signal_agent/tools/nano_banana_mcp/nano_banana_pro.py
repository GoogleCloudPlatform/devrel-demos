import logging
from typing import Literal, Optional
from google import genai
from google.genai import types
from media_models import MediaAsset
from storage_utils import upload_data_to_gcs

AUTHORIZED_URI = "https://storage.mtls.cloud.google.com/"
MAX_RETRIES = 5

async def generate_image(
    prompt: str,
    aspect_ratio: Literal["16:9", "9:16"] = "16:9",
) -> MediaAsset:
    """Generates an image using Gemini 3 Image model."""
    genai_client = genai.Client()
    content = types.Content(parts=[types.Part.from_text(text=prompt)], role="user")
    
    logging.info(f"Starting image generation for prompt: {prompt[:50]}...")
    asset = MediaAsset(uri="")
    
    for _ in range(MAX_RETRIES):
        response = genai_client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[content],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio=aspect_ratio)
            )
        )
        if response and response.parts:
            for part in response.parts:
                if part.inline_data and part.inline_data.data:
                    # Upload the raw bytes to GCS
                    gcs_uri = await upload_data_to_gcs(
                        "mcp-tools",
                        part.inline_data.data,
                        part.inline_data.mime_type
                    )
                    asset = MediaAsset(uri=gcs_uri)
                    break
        if asset.uri: break

    if not asset.uri:
        asset.error = "No image was generated."
    else:
        # Convert gs:// URI to an HTTP accessible URL if needed
        asset.uri = asset.uri.replace('gs://', AUTHORIZED_URI)
        logging.info(f"Image URL: {asset.uri}")
        
    return asset

