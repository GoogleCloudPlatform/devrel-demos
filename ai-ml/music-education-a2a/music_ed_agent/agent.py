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

from google.adk.agents import Agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from music_ed_agent.tools import (
    adk_youtube_search_tool,
    adk_wikipedia_tool,
)

from auth_utils import create_authenticated_client


# Get env var - location of Remote A2A agent
remote_agent_card = os.getenv("REMOTE_AGENT_CARD")
if not remote_agent_card:
    raise RuntimeError("REMOTE_AGENT_CARD environment variable must be set.")

# Create an authenticated HTTP client for A2A client.
httpx_client = create_authenticated_client(remote_agent_card)

# Remote agent (historical context)
historical_context_agent = RemoteA2aAgent(
    name="historical_context_agent",
    description="Agent that researches the historical context of a classical music composition, and its composer.",
    agent_card=remote_agent_card,
    httpx_client=httpx_client
)

# Root agent info
agent_instruction = """

You are a music education agent that helps students learn about classical compositions.

As input, the user will provide the name of a composition, along with the composer. Your task is to educate the student about the composition. Suggested workflow:
1. Use the model to verify that the composition is a valid classical piece. If not, request that the user provides another piece.
2. Use the Youtube Search Tool to find the first YouTube search result URL for that classical piece. eg. it might return ['/watch?v=jOofzffyDSA'].
3. Call the Gemini model with the name of the composition and the audio. Ask Gemini to analyze the classical piece based on what it knows and the audio, providing the student with key info about the following. (Use plenty of emojis and text formatting to make this more readable.)
    - The piece's form and structure (is there a key theme or melody?)
    - Instrumentation, including which musical familes are involved (is there a brass section?)
    - Key
    - Tempo
    - Mood
    - Technical elements (eg. harmonic progressions)
4. Search Wikipedia for the composition to get definitive information about things like tempo.
5. Provide the full youtube link for the student to listen to as they learn about the piece. Ask the user if they want more information on the classical piece.

Then stop and ask the user if they want to hear about the historical context of the composition. If they say yes, invoke the historical_context_agent to get more info.

TOOLS:
- adk_youtube_search_tool - langchain tool that lets you search youtube for videos, can limit to 1 result tool.run("mozart violin concerto no 3,1").
- adk_wikipedia_tool - langchain tool to search wikipedia articles. (string search query)

SUB AGENTS:
- historical_context_agent - Searches the web for historical context about the composer, influences, and time period.
"""


root_agent = Agent(
    model="gemini-2.5-pro",
    name="music_ed_agent",
    instruction=agent_instruction,
    tools=[adk_youtube_search_tool, adk_wikipedia_tool],
    sub_agents=[historical_context_agent],
)
