import os
import logging
import google.cloud.logging
from dotenv import load_dotenv

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents import SequentialAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from google.adk.tools.tool_context import ToolContext

import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

# --- Setup Logging and Environment ---
cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv()

model_name = "gemini-2.5-flash"

# --- Configuration ---
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
if not project_id:
    raise ValueError("The environment variable GOOGLE_CLOUD_PROJECT is not set.")

location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

# Connect directly to the Google-Managed Knowledge Catalog MCP Server
mcp_server_url = f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/{location}/mcp/sse"

def get_access_token():
    """Get a Google Cloud access token to authenticate with the Managed MCP server."""
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    auth_request = google.auth.transport.requests.Request()
    credentials.refresh(auth_request)
    return credentials.token


tools = McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=mcp_server_url,
                headers={
                    "Authorization": f"Bearer {get_access_token()}",
                },
            ),
        )


# Greet user and save their prompt
def add_prompt_to_state(
    tool_context: ToolContext, prompt: str
) -> dict[str, str]:
    """Saves the user's initial prompt to the state."""
    tool_context.state["PROMPT"] = prompt
    logging.info(f"[State updated] Added to PROMPT: {prompt}")
    return {"status": "success"}


def load_skill_instruction(skill_path: str) -> str:
    """Reads the SKILL.md file and returns the instruction content."""
    with open(skill_path, "r") as f:
        content = f.read()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2].strip()
    # Inject runtime variables if present in the skill template
    content = content.replace("[PROJECT_ID]", project_id)
    content = content.replace("[LOCATION]", location)
    return content.strip()

# --- 1. Governance Researcher Agent ---
# Load the shared governance instruction from the Agent Skill (Single Source of Truth)
governance_researcher_instruction = load_skill_instruction("./.agents/skills/knowledge_catalog_governance/SKILL.md")

governance_researcher = LlmAgent(
    name="governance_researcher",
    model=model_name,
    description="Dynamically interprets metadata schema (Booleans/Enums) and searches for assets using strict syntax.",
    instruction=governance_researcher_instruction,
    tools=[tools],
    output_key="research_data"
)


# --- 2. Response Formatter Agent ---
compliance_formatter = LlmAgent(
    name="compliance_formatter",
    model=model_name,
    description="Formats the JSON research data into a helpful response for the user.",
    instruction="""
    You are the **Intelligent Data Governance Specialist**.
    You have received technical research data (RESEARCH_DATA) from your internal analysis.
    Your job is to explain the findings clearly to the user.

    **YOUR GOAL:**
    Explain the logical connection between the User's Request, the Governance Schema (translated criteria), and the Recommended Table.

    **RESPONSE TEMPLATE:**
    1. **Analysis:** "I analyzed the metadata schema and translated your request '{research_data.user_intent}' into the following technical criteria:..."
       (List the criteria from 'technical_criteria' cleanly).
    2. **Recommendation:** "Based on this, I recommend the following table:"
       - **Table:** {research_data.table_name}
       - **Description:** {research_data.description}
    3. **Verification:** "This asset is a verified match because: {research_data.verification_details}."

    **HANDLING NO RESULTS:**
    If `research_data.found_match` is false, apologize politely and explain that no data asset currently matches the strict governance criteria defined in `official-data-product-spec`.

    RESEARCH_DATA:
    {{ research_data }}
    """
)


governance_workflow = SequentialAgent(
    name="governance_workflow",
    description="Workflow to learn metadata rules, search with strict syntax, and recommend assets.",
    sub_agents=[
        governance_researcher,
        compliance_formatter,
    ]
)


root_agent = LlmAgent(
    model=model_name,
    name="greeter",
    description="Entry point for the Data Governance Assistant.",
    instruction="""
        - You are the 'Enterprise Data Governance Assistant'.
        - Greet the user warmly.
        - Save the user's request using 'add_prompt_to_state'.
        - Then, invoke the 'governance_workflow' to find the best data product for them.
        - **IMPORTANT:** Do not output the raw JSON from the workflow. Only show the final natural language explanation.
    """,
    tools=[add_prompt_to_state],
    sub_agents=[governance_workflow]
)