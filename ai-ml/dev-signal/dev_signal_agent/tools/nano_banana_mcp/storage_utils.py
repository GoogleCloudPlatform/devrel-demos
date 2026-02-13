import hashlib
import mimetypes
import os
from google.cloud.storage import Client, Blob
from dotenv import load_dotenv

load_dotenv()
storage_client = Client()
ai_bucket_name = os.environ.get("AI_ASSETS_BUCKET") or os.environ.get("LOGS_BUCKET_NAME")
ai_bucket = storage_client.bucket(ai_bucket_name)

async def upload_data_to_gcs(agent_id: str, data: bytes, mime_type: str) -> str:
    file_name = hashlib.md5(data).hexdigest()
    ext = mimetypes.guess_extension(mime_type) or ""
    blob_name = f"assets/{agent_id}/{file_name}{ext}"
    blob = Blob(bucket=ai_bucket, name=blob_name)
    blob.upload_from_string(data, content_type=mime_type, client=storage_client)
    return f"gs://{ai_bucket_name}/{blob_name}"
