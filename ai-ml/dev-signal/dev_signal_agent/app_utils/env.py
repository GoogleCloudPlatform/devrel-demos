import os
import google.auth
import vertexai
from dotenv import load_dotenv

def _load_secrets(project_id: str):
    """Fetch secrets from Google Secret Manager and set them in the environment."""
    # Only try fetching if the application is running in an environment that needs it 
    # (e.g. not having them already populated from .env during local dev)
    secrets_to_fetch = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT", "DK_API_KEY"]
    if all(os.getenv(s) for s in secrets_to_fetch):
        return

    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        for secret_id in secrets_to_fetch:
            if not os.getenv(secret_id):
                name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
                try:
                    response = client.access_secret_version(request={"name": name})
                    os.environ[secret_id] = response.payload.data.decode("UTF-8")
                    print(f"DEBUG: Loaded secret {secret_id} from Secret Manager.")
                except Exception as e:
                    print(f"Warning: Failed to fetch secret {secret_id}: {e}")
    except ImportError:
        print("google-cloud-secret-manager not installed, skipping secret manager integration.")

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
    if project_id:
        vertexai.init(project=project_id, location=service_location)
        _load_secrets(project_id)
        
    return project_id, model_location, service_location
