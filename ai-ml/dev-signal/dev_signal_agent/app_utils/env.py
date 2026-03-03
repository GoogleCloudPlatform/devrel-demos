import os
import google.auth
import vertexai
from google.cloud import secretmanager
from dotenv import load_dotenv

def _fetch_secrets(project_id: str):
    """Fetch secrets from Secret Manager and return them as a dictionary."""
    secrets_to_fetch = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT", "DK_API_KEY"]
    fetched_secrets = {}

    # First, check local environment (for local development via .env)
    for s in secrets_to_fetch:
        val = os.getenv(s)
        if val:
            fetched_secrets[s] = val

    # If keys are missing (common in production), fetch from Secret Manager API
    if len(fetched_secrets) < len(secrets_to_fetch):
        client = secretmanager.SecretManagerServiceClient()
        for secret_id in secrets_to_fetch:
            if secret_id not in fetched_secrets:
                name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
                try:
                    response = client.access_secret_version(request={"name": name})
                    # DO NOT set os.environ[secret_id] here. 
                    # Keep it in this dictionary only.
                    fetched_secrets[secret_id] = response.payload.data.decode("UTF-8")
                except Exception as e:
                    print(f"Warning: Could not fetch {secret_id} from Secret Manager: {e}")

    return fetched_secrets

def init_environment():
    """Consolidated environment discovery."""
    load_dotenv()
    try:
        _, project_id = google.auth.default()
    except Exception:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    
    model_location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    service_location = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    secrets = {}
    if project_id:
        vertexai.init(project=project_id, location=service_location)
        # Fetch secrets into a local variable
        secrets = _fetch_secrets(project_id)
        
    return project_id, model_location, service_location, secrets