# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# App arguments for ADK - using in-memory session service for simplicity
app_args = {"agents_dir": AGENT_DIR, "web": True}

# Create FastAPI app with ADK integration
app: FastAPI = get_fast_api_app(**app_args)

# Update app metadata
app.title = "Production ADK Agents - Lab 3"
app.description = "Dual-agent setup: Gemma (conversational) and Llama (with tools for weather and tips)"
app.version = "1.0.0"


class Feedback(BaseModel):
    """Represents user feedback for a conversation."""

    score: int | float
    text: str | None = ""
    invocation_id: str
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["production-adk-agent"] = "production-adk-agent"
    user_id: str = ""


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log user feedback.

    This endpoint allows users to provide feedback on their interactions
    with the agent, which can be used for monitoring and improvement.

    Args:
        feedback: The feedback data including score, text, and metadata

    Returns:
        Success message confirming feedback was received
    """
    # In a production environment, you would typically log this to
    # Cloud Logging, store in a database, or send to analytics service
    print(f"Received feedback: {feedback}")
    
    return {"status": "success", "message": "Feedback received successfully"}


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint for monitoring and load balancing.

    This endpoint is used by Cloud Run and load balancers to verify
    that the service is healthy and ready to receive traffic.

    Returns:
        Health status and service information
    """
    return {
        "status": "healthy", 
        "service": "production-adk-agent",
        "version": "1.0.0"
    }


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint with service information.

    Returns:
        Basic information about the service
    """
    return {
        "service": "Production ADK Agent - Lab 3",
        "description": "Business intelligence and strategic planning agent",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Main execution for local development
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")