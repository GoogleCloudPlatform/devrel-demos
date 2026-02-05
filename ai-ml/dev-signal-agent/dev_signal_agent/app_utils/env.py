import os
import logging
import google.auth
import vertexai
from dotenv import load_dotenv

def init_environment():
    """
    Consolidated environment discovery.
    Decouples model location (global) from regional services (us-central1).
    """
    load_dotenv()
    
    try:
        _, project_id = google.auth.default()
    except Exception:
        project_id = None
        
    project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
    
    # Model location: global (required for Gemini 3 Flash Preview)
    model_location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    
    # Service location: regional (required for Agent Engine/Reasoning Engines)
    service_location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    # Bucket unification
    if bucket := os.getenv("LOGS_BUCKET_NAME"):
        os.environ.setdefault("AI_ASSETS_BUCKET", bucket)
    
    if not project_id:
        logging.warning("Proceeding without explicit Project ID.")
    
    # Initialize Vertex AI with regional location (default for services)
    vertexai.init(project=project_id, location=service_location)
    
    return project_id, model_location, service_location
