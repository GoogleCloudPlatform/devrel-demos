import os
import json
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.context import Context
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.events import Event
from google.adk.workflow import Workflow

from authenticated_httpx import create_authenticated_client

# --- Callbacks ---
def create_save_output_callback(key: str):
    """Creates a callback to save the agent's final response to session state."""
    def callback(callback_context: CallbackContext, **kwargs) -> None:
        ctx = callback_context
        # Find the last event from this agent that has content
        for event in reversed(ctx.session.events):
            if event.author == ctx.agent_name and event.content and event.content.parts:
                text = event.content.parts[0].text
                if text:
                    # Try to parse as JSON if it looks like it, for judge_feedback
                    if key == "judge_feedback" and text.strip().startswith("{"):
                        try:
                            ctx.state[key] = json.loads(text)
                        except json.JSONDecodeError:
                            ctx.state[key] = text
                    else:
                        ctx.state[key] = text
                    print(f"[{ctx.agent_name}] Saved output to state['{key}']")
                    return
    return callback

# --- Remote Agents ---
# Default URLs assume local running on different ports if env vars are not set.

# Connect to the Researcher (Localhost port 8001)
researcher_url = os.environ.get(
    "RESEARCHER_AGENT_CARD_URL",
    "http://localhost:8001/a2a/agent/.well-known/agent-card.json"
)
researcher = RemoteA2aAgent(
    name="researcher",
    agent_card=researcher_url,
    description="Gathers information using Google Search.",
    # IMPORTANT: Save the output to state for the Judge to see
    after_agent_callback=create_save_output_callback("research_findings"),
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(researcher_url)
)

# Connect to the Judge (Localhost port 8002)
judge_url = os.environ.get(
    "JUDGE_AGENT_CARD_URL",
    "http://localhost:8002/a2a/agent/.well-known/agent-card.json"
)
judge = RemoteA2aAgent(
    name="judge",
    agent_card=judge_url,
    description="Evaluates research.",
    after_agent_callback=create_save_output_callback("judge_feedback"),
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(judge_url)
)

# Content Builder (Localhost port 8003)
content_builder_url = os.environ.get(
    "CONTENT_BUILDER_AGENT_CARD_URL",
    "http://localhost:8003/a2a/agent/.well-known/agent-card.json"
)
content_builder = RemoteA2aAgent(
    name="content_builder",
    agent_card=content_builder_url,
    description="Builds the course.",
    # IMPORTANT: httpx client with Id Token Authentication
    httpx_client=create_authenticated_client(content_builder_url)
)

# --- Feedback Router ---

MAX_ITERATIONS = 3


def check_judge_feedback(ctx: Context) -> Event:
    """Checks the judge's feedback and routes to retry or content_builder."""
    feedback = ctx.state.get("judge_feedback")
    iterations = ctx.state.get("research_iterations", 0) + 1

    # Debug log to see what we got from the remote agent
    print(f"[check_judge_feedback] Iteration {iterations}, Feedback received: {feedback}")

    is_pass = False
    if feedback and isinstance(feedback, dict) and feedback.get("status") == "pass":
        is_pass = True
    elif isinstance(feedback, str):
        normalized = feedback.replace(" ", "").replace("'", '"')
        if '"status":"pass"' in normalized:
            is_pass = True

    if is_pass or iterations >= MAX_ITERATIONS:
        return Event(route="pass", state={"research_iterations": iterations})
    return Event(route="retry", state={"research_iterations": iterations})


# --- Orchestration ---

root_agent = Workflow(
    name="course_creation_pipeline",
    description="A pipeline that researches a topic and then builds a course from it.",
    edges=[
        ("START", researcher, judge, check_judge_feedback),
        (
            check_judge_feedback,
            {"retry": researcher, "pass": content_builder},
        ),
    ],
)

