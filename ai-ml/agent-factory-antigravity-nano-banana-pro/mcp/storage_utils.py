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

import hashlib
import mimetypes
import os

import google.auth
from google.genai import types
from google.cloud.storage import Client, Blob

from dotenv import load_dotenv

load_dotenv()
_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id) # type: ignore
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

project_id = os.environ["GOOGLE_CLOUD_PROJECT"]
storage_client = Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
ai_bucket_name = os.environ.get(
    "AI_ASSETS_BUCKET",
    f"{project_id}-adk-video-agent"
)
ai_bucket = storage_client.get_bucket(ai_bucket_name)
md5_hash = hashlib.md5()


async def upload_data_to_gcs(agent_id: str, data: bytes, mime_type: str) -> str:
    md5_hash.update(data)
    file_name = md5_hash.hexdigest()
    ext = mimetypes.guess_extension(mime_type) or ""
    file_name = f"{file_name}{ext}"
    blob_name = f"assets/{agent_id}/{file_name}"
    blob = Blob(bucket=ai_bucket, name=blob_name)
    blob.upload_from_string(data, content_type=mime_type, client=storage_client)
    gcs_url = f"gs://{ai_bucket_name}/{blob_name}"
    return gcs_url

def download_data_from_gcs(url: str) -> types.Blob:
    blob = Blob.from_string(url, client=storage_client)
    blob_data = blob.download_as_bytes(client=storage_client)
    file_name = url.split("/")[-1]
    mime_type = (
        mimetypes.guess_type(file_name)[0]
        or blob.content_type
        or "application/octet-stream"
    )
    if ";" in mime_type:
        mime_type = mime_type.split(";")[0]
    return types.Blob(
        display_name=file_name,
        data=blob_data,
        mime_type=mime_type.strip()
    )