import os
import google.auth
import vertexai
from dotenv import load_dotenv

def init_environment():
    """Consolidated environment discovery."""
    load_dotenv()
    try:
        # Attempt to get project ID from Google Auth (local/gcloud)
        _, project_id = google.auth.default()
    except Exception:
        # Fallback to environment variable (often used in Cloud Run)
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    # We assume 'global' for the model to access Preview features
    model_location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    # Services like Agent Engine are regional (e.g., us-central1)
    service_location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    # Initialize the Vertex AI SDK globally with these values
    vertexai.init(project=project_id, location=service_location)
    return project_id, model_location, service_location
