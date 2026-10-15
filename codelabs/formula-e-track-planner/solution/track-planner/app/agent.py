"""Formula E track planner: Lead Architect, FIA Assessor and remote Gatekeeper.

- The Lead Architect (root agent) designs the circuit and stays in charge.
- The FIA Assessor checks the layout and is called as a tool (`AgentTool`).
- The Gatekeeper runs in a separate project. It is also called as a tool, over
  A2A, so its verdict comes back to the Lead Architect.
"""

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from app.auth import create_remote_gatekeeper_agent
from app.tools import build_fia_skill_toolset
from app.tools import evaluate_track_layout
from app.tools import get_track_topology

MODEL = "gemini-3.8-flash"

fia_skill_toolset = build_fia_skill_toolset()

# 1. FIA Assessor: MEDIUM thinking to weigh several rules without much latency.
assessor_agent = Agent(
    name="fia_assessor",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description=(
        "FIA safety and energy assessor. Audits a proposed circuit against "
        "the geometry, regeneration and CAD layer rules."
    ),
    instruction=(
        "You are the FIA Assessor. Load the `fia-compliance-skill` and follow "
        "it. Estimate regeneration for each braking zone with "
        "`calculate_regen_zones.py`, then call `evaluate_track_layout` with "
        "the highest value. Reply with the verdict, the score and every "
        "remediation note."
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MEDIUM,
        ),
    ),
    tools=[fia_skill_toolset, evaluate_track_layout],
)

# 2. Remote Gatekeeper, reached over A2A (see app/auth.py).
remote_gatekeeper = create_remote_gatekeeper_agent()

# 3. Lead Architect: HIGH thinking for multi-step planning and trade-offs.
root_agent = Agent(
    # Must match `root_agent_name` in agents-cli-manifest.yaml.
    name="track_planner",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description=(
        "Lead Formula E circuit architect. Designs FIA-compliant street "
        "circuits and gets them homologated."
    ),
    instruction=(
        "You are the Lead Formula E Circuit Architect. For every request:\n"
        "1. Call `get_track_topology` for the venue.\n"
        "2. Call the `fia_assessor` tool with the full topology.\n"
        "3. If the Assessor rejects the layout, propose concrete fixes (for "
        "example widen a sector to 10.0m or add missing CAD layers) and "
        "re-assess the fixed layout.\n"
        "4. Once the Assessor passes it, call the `remote_gatekeeper` tool "
        "with the circuit ID, CAD layers, minimum width and peak "
        "regeneration for final approval.\n"
        "5. Finish with a short blueprint: circuit ID, length, minimum width, "
        "peak regeneration, every CAD layer by name, and the Gatekeeper's "
        "status."
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.HIGH,
        ),
    ),
    # Both helpers are tools, so their answers come back to the Lead Architect
    # and it writes the final blueprint.
    tools=[
        get_track_topology,
        AgentTool(agent=assessor_agent),
        AgentTool(agent=remote_gatekeeper),
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
