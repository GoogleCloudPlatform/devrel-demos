from google.auth.compute_engine import _metadata
from google.auth.transport import requests as google_auth_requests
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    force=True,
)
logger = logging.getLogger(__name__)

def get_project_id() -> str:
    request = google_auth_requests.Request()
    project_id = os.environ.get('GOOGLE_CLOUD_PROJECT') or _metadata.get_project_id(request)
    logger.info(f"⚙️ configured project id: {project_id}")
    return project_id

def get_region() -> str:
    location = os.environ.get('GOOGLE_CLOUD_LOCATION')
    if location is None or not location:
        request = google_auth_requests.Request()
        location = _metadata.get(request, 'instance/region')
        if location:
            location = location.split('/')[-1]
        else:
            location = 'global'
    logger.info(f"⚙️ configured location: {location}")
    return location    

def get_model_id() -> str:
    model_id = os.getenv('MODEL_ID', 'gemini-2.5-flash')
    logger.info(f"⚙️ configured model ID: {model_id}")
    return model_id
