"""FIA Digital Twin Gatekeeper agent.

This agent runs in its own project and is deployed to Agent Runtime. The track
planner calls it over the A2A protocol.
"""

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import verify_infrastructure_checklist

MODEL = "gemini-3.8-flash"

root_agent = Agent(
    # Must match `root_agent_name` in agents-cli-manifest.yaml.
    name="gatekeeper",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description=(
        "FIA Digital Twin Gatekeeper. Runs the final homologation checklist "
        "for a Formula E circuit blueprint."
    ),
    instruction=(
        "You are the FIA Digital Twin Gatekeeper. For every circuit blueprint "
        "you receive, call `verify_infrastructure_checklist` with its circuit "
        "ID, CAD layers, minimum width and peak regeneration. Reply with the "
        "status and any missing CAD layers. Never approve a blueprint the "
        "checklist rejects."
    ),
    # A deterministic checklist needs little reasoning: keep it fast and cheap.
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.LOW,
        ),
    ),
    tools=[verify_infrastructure_checklist],
)

app = App(
    root_agent=root_agent,
    name="app",
)
