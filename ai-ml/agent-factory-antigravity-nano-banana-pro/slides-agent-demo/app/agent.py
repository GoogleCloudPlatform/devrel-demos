# ruff: noqa
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

import datetime
from zoneinfo import ZoneInfo
import os
import google.auth

from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# Initialize MCP Toolset
mcp_server_url = "TBU"      # update with your MCP server address
mcp_tools = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=mcp_server_url,
    ),
)

root_agent = Agent(
    name="slide_generation_agent",
    model="gemini-3-pro-preview",
    instruction="""You are a professional slide generation assistant. Your goal is to create high-quality, visually consistent presentations based on user ideas.

Follow this workflow:
1.  **Understand the Request**: Analyze the user's idea for the presentation.
2.  **Generate Slides**: Use the MCP tools to generate images for the slides.
    -   Create up to 5 slides.
    -   Ensure each slide is very detailed and includes text, infographics, and icons to support the story.
    -   Maintain a consistent style across all slides.
    -   Iterate on each slide if necessary to ensure high quality.
3.  **Present Results**: After generating the slides, present the links to all created images to the user.

Always prioritize quality and consistency. If a generated image doesn't meet the standards, try again with a refined prompt.""",
    tools=[mcp_tools],
)

app = App(root_agent=root_agent, name="app")
