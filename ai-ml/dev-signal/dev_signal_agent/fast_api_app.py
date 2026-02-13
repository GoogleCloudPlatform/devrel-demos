import os
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as cloud_logging
from vertexai import agent_engines
from dev_signal_agent.app_utils.telemetry import setup_telemetry
from dev_signal_agent.app_utils.typing import Feedback
from dev_signal_agent.app_utils.env import init_environment

setup_telemetry()
PROJECT_ID, MODEL_LOC, SERVICE_LOC = init_environment()
logger = cloud_logging.Client().logger(__name__)

# --- Configuration & Sessions ---
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKET = os.environ.get("LOGS_BUCKET_NAME")
USE_IN_MEMORY = os.environ.get("USE_IN_MEMORY_SESSION", "").lower() in ("true", "1")

# --- MEMORY BANK CONNECTION ---
def _get_memory_bank_uri():
    if USE_IN_MEMORY: return None, None
    name = os.environ.get("AGENT_ENGINE_MEMORY_BANK_NAME", "dev_signal_agent")
    existing = list(agent_engines.list(filter=f"display_name={name}"))
    ae = existing[0] if existing else agent_engines.create(display_name=name)
    uri = f"agentengine://{ae.resource_name}"
    print(f"DEBUG: Connecting to Memory Bank: {uri} (display_name={name})")
    return uri, uri

SESSION_URI, MEMORY_URI = _get_memory_bank_uri()

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=f"gs://{BUCKET}" if BUCKET else None,
    allow_origins=os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None,
    session_service_uri=SESSION_URI,
    memory_service_uri=MEMORY_URI, # <--- Connects the Memory Bank
    otel_to_cloud=True,
)

@app.post("/feedback")
def collect_feedback(feedback: Feedback):
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
