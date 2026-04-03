# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
import sys

from google.adk.cli.fast_api import get_fast_api_app
from fastapi import FastAPI

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Discover the customer agent in the current working dir
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Create FastAPI app with enabled cloud tracing
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    auto_create_session=True,
    web=False,
    trace_to_cloud=True,
)

app.title = "secured-ai-agent-demo"
app.description = "A demo of the securely built and operated agents that protecting model and user data"

logger.info(f"Discovered agent dir is {AGENT_DIR}")

# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=os.environ.get("PORT", "8080"))
