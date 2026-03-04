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
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from google.adk.agents import LlmAgent, Agent
from google.adk.models.lite_llm import LiteLlm
from google.cloud import logging as google_cloud_logging
import google.auth

# Load environment variables from .env file in root directory
root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Use default project from credentials if not in .env
try:
    _, project_id = google.auth.default()
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
except Exception:
    # If no credentials available, continue without setting project
    pass

os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west1")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Set up Cloud Logging
logging_client = google_cloud_logging.Client()
logger = logging_client.logger("production-adk-agent")


# Configure the deployed model endpoint
gemma_model_name = os.getenv("GEMMA_MODEL_NAME", "gemma3:270m")  # Gemma model name
api_base = os.getenv("OLLAMA_API_BASE", "localhost:10010")  # Location of Ollama server

# Production Gemma Agent - GPU-accelerated conversational assistant
production_agent = Agent(
    model=LiteLlm(model=f"ollama_chat/{gemma_model_name}", api_base=api_base),
    name="production_agent",
    description="A production-ready conversational assistant powered by GPU-accelerated Gemma.",
    instruction="""You are 'Gem', a friendly, knowledgeable, and enthusiastic zoo tour guide. 
    Your main goal is to make a zoo visit more fun and educational for guests by answering their questions.

    You can provide general information and interesting facts about different animal species, such as:
    - Their natural habitats and diet. 🌲🍓
    - Typical lifespan and behaviors.
    - Conservation status and unique characteristics.

    IMPORTANT: You do NOT have access to any tools. This means you cannot look up real-time, specific information about THIS zoo. You cannot provide:
    - The names or ages of specific animals currently at the zoo.
    - The exact location or enclosure for an animal.
    - The daily schedule for feedings or shows.

    Always answer based on your general knowledge about the animal kingdom. Keep your tone cheerful, engaging, and welcoming for visitors of all ages. 🦁✨""",
    tools=[],  # Gemma focuses on conversational capabilities
)

# Set as root agent
root_agent = production_agent