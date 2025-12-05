# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import mimetypes
from typing import Literal, Optional

from google import genai
from google.genai import types

from media_models import MediaAsset
from storage_utils import upload_data_to_gcs

AUTHORIZED_URI = "https://storage.mtls.cloud.google.com/"
MAX_RETRIES = 5


async def generate_image(
    prompt: str,
    source_image_gsc_uri: Optional[str] = None,
    aspect_ratio: Literal["16:9", "9:16"] = "16:9",
) -> MediaAsset:
    """Generates an image using Gemini 3 Flash Image model (aka Nano Banana Pro).
    Returns a MediaAsset object with the GCS URI of the generated image or an error text.

    Args:
        prompt (str): Image generation prompt (may refer to the source image if it's provided).
        source_image_gsc_uri (Optional[str], optional): Optional GCS URI
            of source image.
            Defaults to None.
        aspect_ratio (str, optional): Aspect ratio of the video.
            Supported values are "16:9" and "9:16". Defaults to "16:9".

    Returns:
        MediaAsset: object with the GCS URI of the generated image or an error text.
    """

    # gemini_client = Gemini()
    # genai_client = gemini_client.api_client
    genai_client = genai.Client()
    content = types.Content(
        parts=[types.Part.from_text(text=prompt)],
        role="user"
    )
    if source_image_gsc_uri:
        guessed_mime_type, _ = mimetypes.guess_type(source_image_gsc_uri)
        if not guessed_mime_type:
            # Handle the case where mime type is not found, e.g., by raising an error or using a default
            raise ValueError(f"Could not determine mime type for {source_image_gsc_uri}")
        mime_type = guessed_mime_type

        content.parts.insert( # type: ignore
            0,
            types.Part(
                file_data=types.FileData(
                    file_uri=source_image_gsc_uri,
                    mime_type=mime_type
                )
            )
        )

    asset = MediaAsset(uri="")
    for _ in range (0, MAX_RETRIES):
        response = genai_client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=[content],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                )
            )
        )
        response_text = ""
        if response and response.parts:
            for part in response.parts:
                if part.text and not part.thought:
                    response_text += part.text
                if part.file_data and part.file_data.file_uri:
                    asset = MediaAsset(uri=part.file_data.file_uri)
                    break
                if part.inline_data and part.inline_data.data:
                    gcs_uri = await upload_data_to_gcs(
                        "mcp-tools",
                        part.inline_data.data,
                        part.inline_data.mime_type # type: ignore
                    )
                    asset = MediaAsset(uri=gcs_uri)
                    break
        if asset.uri:
            break
        if response_text:
            logging.warning(f"MODEL RESPONSE: \n{response_text}")

    if not asset.uri:
        asset.error = "No image was generated."
    else:
        asset.uri = asset.uri.replace('gs://', AUTHORIZED_URI)
        logging.info(
            f"Image URL: {asset.uri}"
        )   
    return asset
