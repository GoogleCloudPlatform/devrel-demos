import os
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as cloud_logging
from vertexai import agent_engines
from dev_signal_agent.app_utils.env import init_environment

# --- Initialization & Secure Secret Retrieval ---
# We now unpack the SECRETS dictionary returned by our updated env.py
PROJECT_ID, MODEL_LOC, SERVICE_LOC, SECRETS = init_environment()
logger = cloud_logging.Client().logger(__name__)

# Access sensitive credentials from the SECRETS dictionary 
# These keys stay in memory and are NOT injected into os.environ
REDDIT_CLIENT_ID = SECRETS.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = SECRETS.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = SECRETS.get("REDDIT_USER_AGENT")
DK_API_KEY = SECRETS.get("DK_API_KEY")

# --- Configuration & Sessions ---
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Non-sensitive configuration still uses environment variables [cite: 207, 208]
BUCKET = os.environ.get("AI_ASSETS_BUCKET") 
USE_IN_MEMORY = os.environ.get("USE_IN_MEMORY_SESSION", "").lower() in ("true", "1")

# --- MEMORY BANK CONNECTION ---
def _get_memory_bank_uri():
    if USE_IN_MEMORY: return None, None
    # We use 'dev_signal_agent' as the display name for the Vertex AI memory bank
    name = os.environ.get("AGENT_ENGINE_MEMORY_BANK_NAME", "dev_signal_agent") 
    existing = list(agent_engines.list(filter=f"display_name={name}"))
    ae = existing[0] if existing else agent_engines.create(display_name=name)
    uri = f"agentengine://{ae.resource_name}"
    print(f"DEBUG: Connecting to Memory Bank: {uri} (display_name={name})")
    return uri, uri

SESSION_URI, MEMORY_URI = _get_memory_bank_uri()

# --- Initialize FastAPI with ADK ---
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=f"gs://{BUCKET}" if BUCKET else None,
    allow_origins=os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None,
    session_service_uri=SESSION_URI,
    memory_service_uri=MEMORY_URI, # <--- Connects the Memory Bank
    otel_to_cloud=True,            # <--- Enables production telemetry
)

if __name__ == "__main__":
    import uvicorn
    # Standard Cloud Run port is 8080 
    uvicorn.run(app, host="0.0.0.0", port=8080)