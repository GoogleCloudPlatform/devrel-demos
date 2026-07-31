import io
import logging
import os
import time
from collections import defaultdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

from . import config
from .locations import get_location_info

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_selfie_souvenir")

app = FastAPI(
    title=f"{config.EVENT_TITLE} - {config.APP_NAME} API",
    description="Backend API for AI Selfie Souvenir generation.",
    version="1.0.0",
)

rate_limit_records = defaultdict(list)


def is_rate_limited(client_ip: str) -> bool:
    now = time.time()

    # Periodically prune stale IP records to prevent memory leak from one-off client requests
    if len(rate_limit_records) > 1000:
        stale_ips = [
            ip
            for ip, ts_list in list(rate_limit_records.items())
            if not ts_list or now - ts_list[-1] >= config.RATE_LIMIT_WINDOW
        ]
        for ip in stale_ips:
            rate_limit_records.pop(ip, None)

    # Keep only timestamps within the window
    timestamps = [
        t for t in rate_limit_records[client_ip] if now - t < config.RATE_LIMIT_WINDOW
    ]
    if not timestamps:
        rate_limit_records.pop(client_ip, None)
    else:
        rate_limit_records[client_ip] = timestamps

    if len(timestamps) >= config.RATE_LIMIT_MAX:
        return True

    rate_limit_records[client_ip].append(now)
    return False


def get_client_ip(request: Request) -> str:
    """Extracts client IP safely from X-Forwarded-For header, prioritizing the rightmost IP appended by Cloud Run ingress proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ips = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
        if ips:
            return ips[-1]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


@app.middleware("http")
async def secure_origin_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        if config.ENVIRONMENT not in ("local", "testing"):
            sec_fetch_site = request.headers.get("sec-fetch-site")
            if sec_fetch_site != "same-origin":
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Access forbidden: Requests must originate from the same site."
                    },
                )

            if request.url.path == "/api/selfie":
                client_ip = get_client_ip(request)
                if is_rate_limited(client_ip):
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"Rate limit exceeded. Maximum {config.RATE_LIMIT_MAX} requests per minute."
                        },
                    )

    return await call_next(request)


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google GenAI client based on environment variables
client = None
try:
    from google import genai
    from google.genai import types

    logger.info("Initializing Google Gen AI client based on environment configuration.")
    client = genai.Client()
except Exception as e:
    logger.warning(
        f"Failed to initialize Google Gen AI SDK. Fallback mode will be active. Error: {e}"
    )
    client = None


def get_active_prompt() -> str:
    return config.PROMPT_TEMPLATE.strip()


@app.get("/api/config")
def get_config():
    """Returns non-sensitive public configuration for client-side dynamic UI hydration."""
    return config.get_public_config()


@app.post("/api/selfie")
async def selfie_generation(request: Request, image: UploadFile = File(...)):
    # Parse uploaded user image file
    try:
        image_bytes = await image.read()
        if not image_bytes:
            raise ValueError("Empty file upload")
        # Verify the image is valid by opening it
        with Image.open(io.BytesIO(image_bytes)) as img_verify:
            img_verify.verify()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file upload: {e}")

    # Image generation execution (using Gemini)
    if not client:
        error_msg = "Google Gen AI Client is not initialized."
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    model_id = config.NANO_BANANA_MODEL_ID

    try:
        logger.info(f"Calling GenAI model: {model_id}...")
        prompt = get_active_prompt()

        # Parameterized base reference image part construction
        base_part = None
        if config.BASE_IMAGE_URI and config.BASE_IMAGE_URI.strip():
            base_part = types.Part.from_uri(
                file_uri=config.BASE_IMAGE_URI.strip(),
                mime_type="image/*",
            )

        user_part = types.Part.from_bytes(data=image_bytes, mime_type="image/*")
        contents = [p for p in [base_part, user_part, prompt] if p is not None]
        image_config = types.ImageConfig(output_mime_type="image/jpeg")
        gen_config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=image_config,
        )

        response = client.models.generate_content(
            model=model_id,
            contents=contents,
            config=gen_config,
        )

        # Extract resulting image
        result_bytes = None
        mime_type = "image/*"
        parts = getattr(response, "parts", None) or []
        for part in parts:
            if part.inline_data:
                result_bytes = part.inline_data.data
                mime_type = part.inline_data.mime_type
                break

        if not result_bytes:
            finish_reason = None
            if getattr(response, "candidates", None) and len(response.candidates) > 0:
                finish_reason = getattr(response.candidates[0], "finish_reason", None)

            if finish_reason:
                error_msg = f"Gemini API generation stopped or blocked: {finish_reason}"
            else:
                error_msg = "Gemini API response did not contain image data."
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        return Response(content=result_bytes, media_type=mime_type)

    except HTTPException:
        raise
    except Exception as api_err:
        error_msg = f"Gemini API Error: {str(api_err)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/status")
def get_status():
    return {
        "client_initialized": client is not None,
        "prompt": get_active_prompt(),
        "is_cloud_run": bool(os.environ.get("K_SERVICE")),
        "region": config.CLOUD_RUN_REGION,
        "location": get_location_info(config.CLOUD_RUN_REGION),
        "show_cloud_run_region": config.SHOW_CLOUD_RUN_REGION,
        "environment": config.ENVIRONMENT,
    }


# Custom static files class to set custom Cache-Control TTL headers
class CustomStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs) -> Response:
        response = super().file_response(*args, **kwargs)
        if response.media_type and "html" in response.media_type:
            response.headers["Cache-Control"] = (
                "no-store, no-cache, must-revalidate, max-age=0"
            )
        else:
            response.headers["Cache-Control"] = "public, max-age=600, must-revalidate"
        return response


# Mount frontend static directory
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount(
        "/", CustomStaticFiles(directory=str(frontend_dir), html=True), name="static"
    )
