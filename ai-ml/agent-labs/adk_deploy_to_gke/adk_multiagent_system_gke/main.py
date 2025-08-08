import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure the session service (e.g., SQLite for local storage)
SESSION_SERVICE_URI = "sqlite:///./sessions.db"

# Configure CORS to allow requests from various origins for this lab
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]

# Enable the ADK's built-in web interface
SERVE_WEB_INTERFACE = True

# Call the ADK function to discover agents and create the FastAPI app
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

# You can add more FastAPI routes or configurations below if needed
# Example:
# @app.get("/hello")
# async def read_root():
#     return {"Hello": "World"}

if __name__ == "__main__":
    # Get the port from the PORT environment variable provided by the container runtime
    # Run the Uvicorn server, listening on all available network interfaces (0.0.0.0)
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))