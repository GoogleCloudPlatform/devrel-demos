from cloudevents.http import from_http
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from processor import process_request
from zookeeper_agent import get_project_id, get_region
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    force=True,
)
logger = logging.getLogger(__name__)

app = FastAPI()

REPLY_TOPIC_ID = os.getenv('REPLY_TOPIC_ID', '')

os.environ.setdefault('GOOGLE_CLOUD_PROJECT', get_project_id())
os.environ.setdefault('GOOGLE_CLOUD_LOCATION', get_region())
os.environ.setdefault('GOOGLE_GENAI_USE_VERTEXAI', 'True')

@app.post('/zookeeper')
async def eventarc_handler(request: Request) -> JSONResponse:
    """Update collection of animals based on incoming event data."""
    try:
        body = await request.body()
        event = from_http(request.headers, body)
        message, code = await process_request(event, REPLY_TOPIC_ID)
        status = 'error' if code != 200 else 'success'
        return JSONResponse(content={'status': status, 'message': message}, status_code=code)
    except Exception as e:
        logger.error(f"❌ failed processing Eventarc event: {e}")
        return JSONResponse(content={'status': 'error', 'message': 'Failed to parse payload to Eventarc event'}, status_code=400)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', '8080')))