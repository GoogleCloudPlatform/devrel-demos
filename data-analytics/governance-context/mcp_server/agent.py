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
mcp_server_url = os.getenv("MCP_SERVER_URL")
if not mcp_server_url:
    raise ValueError("The environment variable MCP_SERVER_URL is not set.")


def get_id_token():
    """Get an ID token to authenticate with the MCP server."""
    target_url = os.getenv("MCP_SERVER_URL")
    audience = target_url.split('/mcp/')[0]
    request = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(request, audience)
    return id_token


tools = McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=mcp_server_url,
                headers={
                    "Authorization": f"Bearer {get_id_token()}",
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


# --- Configuration ---
project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
if not project_id:
    raise ValueError("The environment variable GOOGLE_CLOUD_PROJECT is not set.")

location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1") 

# --- 1. Governance Researcher Agent ---
governance_researcher_instruction = f"""
    You are a strict Data Governance AI Agent. Your primary role is to enforce institutional data policies by querying the Dataplex Universal Catalog via MCP tools.
    You MUST NOT guess or assume SQL table names. You MUST rely ONLY on the metadata (Aspects) returned by your tools.

    CRITICAL RULES:
    1. Never hallucinate data. If you cannot find a certified table matching the user's request, you must state: "I cannot find an officially certified table for this request."
    2. Your working environment is restricted to Project ID: {project_id} and Location: {location}.

    EXECUTION WORKFLOW:
    When a user asks for data, you must follow these phases strictly:

    PHASE 1: Understand the Governance Rules
    If you don't know the exact aspect schema, use the `search_aspect_types` tool to look up the governance aspect definitions.
    - Search Query: `official-data-product-spec`

    PHASE 2: Search for Certified Data
    Once you understand the aspect fields (like data_domain, is_certified, data_product_tier), use the `search_entries` tool.

    CRITICAL SYNTAX FOR `search_entries`:
    Do NOT use `projectid:` or `type=table` prefixes. They will break the search API when combined with aspects.
    To search by aspect values, you MUST use the exact following format for each condition, separated by a space:
    {project_id}.{location}.[ASPECT_NAME].[FIELD_NAME]=[VALUE]

    Example Logic for Phase 2:
    - User wants: Certified Financial Data
    - You MUST construct the query exactly like this:
    {project_id}.{location}.official-data-product-spec.data_domain=FINANCE {project_id}.{location}.official-data-product-spec.is_certified=true

    - User wants: Publicly shareable data
    - You MUST construct the query exactly like this:
    {project_id}.{location}.official-data-product-spec.data_product_tier=EXTERNAL_READY
    
    PHASE 3: Verify and Formulate Response
    Use `lookup_entry` if you need to double-check the exact table details before answering.
    Synthesize your final answer explaining WHY you chose this table based on its governance tags (Aspects). Do not expose the raw Dataplex search query to the user.
"""

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