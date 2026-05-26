# main.py
import os
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from google.adk.cli.fast_api import get_fast_api_app
from custom_plugin import customBigQueryPlugin

load_dotenv()

# Get current folder path where chatbot_agent package resides
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Build FastAPI app with ADK multiagent capabilities and web UI enabled
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    allow_origins=["*"],
    web=True,
    extra_plugins=['custom_plugin.customBigQueryPlugin']
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
