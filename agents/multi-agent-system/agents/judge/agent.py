from typing import Literal
from google.adk.agents import Agent
from google.adk.apps.app import App
from pydantic import BaseModel, Field


MODEL = "gemini-2.5-pro"

# --- Data Models ---
class JudgeFeedback(BaseModel):

    """Structured feedback from the Judge agent."""
    status: Literal["pass", "fail"] = Field(
        description="Whether the research is sufficient ('pass') or needs more work ('fail')."
    )
    feedback: str = Field(
        description="Detailed feedback on what is missing or needs clarification if status is 'fail'. If 'pass', a brief confirmation."
    )

# --- Judge Agent ---
judge = Agent(
    name="judge",
    model=MODEL,
    description="Evaluates research findings for completeness and accuracy.",
    instruction="""
    You are a strict editor and fact-checker.
    Evaluate the 'research_findings' against the user's original request.
    Determine if the findings are sufficient to create a high-quality course.
    If they are good enough, output status='pass'.
    If they are missing key information, are too vague, or likely inaccurate, output status='fail' and provide specific, constructive 'feedback' on what to research next.
    """,
    output_schema=JudgeFeedback,
    # Disallow transfers as it uses output_schema
    disallow_transfer_to_parent=True,
    disallow_transfer_to_peers=True,
)

root_agent = judge
