import os
import google.auth
import vertexai
from google.cloud import secretmanager
from dotenv import load_dotenv

def _fetch_secrets(project_id: str, secret_ids: list):
    """Fetch secrets from Secret Manager and return them as a dictionary."""
    fetched_secrets = {}

    # 1. First, check local environment (for local development via .env)
    for s in secret_ids:
        val = os.getenv(s)
        if val:
            fetched_secrets[s] = val

    # 2. If keys are missing (common in production), fetch from Secret Manager API
    if len(fetched_secrets) < len(secret_ids):
        client = secretmanager.SecretManagerServiceClient()
        for secret_id in secret_ids:
            if secret_id not in fetched_secrets:
                name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
                try:
                    response = client.access_secret_version(request={"name": name})
                    # CAUTION: Keep it in this dictionary only. DO NOT set os.environ here.
                    fetched_secrets[secret_id] = response.payload.data.decode("UTF-8")
                except Exception as e:
                    print(f"Warning: Could not fetch {secret_id} from Secret Manager: {e}")

    return fetched_secrets

def init_environment():
    """Consolidated environment discovery and secret retrieval."""
    load_dotenv()
    try:
        _, project_id = google.auth.default()
    except Exception:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    # Standard locations for Agent Engine and Models
    model_location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    service_location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    secrets = {}
    if project_id:
        vertexai.init(project=project_id, location=service_location)
        # Define the list of secrets your agent needs
        needed_secrets = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT", "DK_API_KEY"]
        secrets = _fetch_secrets(project_id, needed_secrets)
        
    return project_id, model_location, service_location, secrets
