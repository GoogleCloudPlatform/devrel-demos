# Copyright 2026 Google LLC
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

# src/main.py
import logging

# Configure logging at the very beginning to ensure all logs are captured correctly
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    force=True
)

from fastapi import FastAPI
import uvicorn
import os
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from src.adapters.outbound.sandbox_direct import SandboxDirectAdapter
from src.adapters.outbound.adk_agent import ADKAgentAdapter
from src.adapters.outbound.pubsub_publisher import PubSubPublisherAdapter, MockPubSubPublisherAdapter
from src.adapters.inbound.pubsub_subscriber import BackgroundSubscriber

# Load environment variables from .env file
load_dotenv()

import sys

def get_required_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if not value:
        print(f"Error: {var_name} environment variable is required", file=sys.stderr)
        sys.exit(1)
    return value

# Configuration from Environment Variables
PROJECT_ID = get_required_env("GOOGLE_CLOUD_PROJECT")
TASKS_SUBSCRIPTION = get_required_env("TASKS_SUBSCRIPTION")
RESULTS_TOPIC = get_required_env("RESULTS_TOPIC")
USE_MOCK = os.getenv("USE_MOCK_PUBSUB", "false").lower() == "true"
AGENT_TYPE = os.getenv("AGENT_TYPE", "sandbox_direct").lower()

# Dependency Injection setup
if AGENT_TYPE == "adk":
    agent_service = ADKAgentAdapter()
    print("Using ADKAgentAdapter.")
else:
    agent_service = SandboxDirectAdapter()
    print("Using SandboxDirectAdapter.")

if USE_MOCK:
    publisher = MockPubSubPublisherAdapter()
    subscriber = BackgroundSubscriber(
        agent_service=agent_service,
        publisher=publisher
    )
else:
    publisher = PubSubPublisherAdapter(project_id=PROJECT_ID, topic_id=RESULTS_TOPIC)
    subscriber = BackgroundSubscriber(
        agent_service=agent_service, 
        publisher=publisher,
        project_id=PROJECT_ID,
        subscription_id=TASKS_SUBSCRIPTION
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up Hackathon Judge Agent...")
    await subscriber.start()
    print("Hackathon Judge Agent started.")
    yield
    # Shutdown
    print("Shutting down Hackathon Judge Agent...")
    await subscriber.stop()
    print("Hackathon Judge Agent stopped.")

app = FastAPI(title="Hackathon Judge Agent", lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Welcome to the Hackathon Judge Agent"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
