# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import dotenv
from google.cloud import aiplatform
from manufacturing_assistant_agent.agent import create_graph_agent

dotenv.load_dotenv("manufacturing_assistant_agent/.env")

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("LOCATION", "us-central1")
MAPS_API_KEY = os.getenv("MAPS_API_KEY")

def deploy():
    print(f"Deploying Agent to Vertex AI Agent Engine in project {PROJECT_ID}...")
    aiplatform.init(project=PROJECT_ID, location=LOCATION)
    
    agent = create_graph_agent()
    print(f"Successfully configured agent: {agent.name}")
    print("Deployment script template ready.")

if __name__ == "__main__":
    deploy()
