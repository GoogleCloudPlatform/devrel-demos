import os
import logging
import google.cloud.logging
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StreamableHTTPConnectionParams
from google.adk.tools.tool_context import ToolContext

import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

# --- Setup Logging and Environment ---

cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv()

model_name = os.getenv("MODEL")

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


"""
# Use this code if you are using the public MCP Server and comment out the code below defining mcp_tools
mcp_tools = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
        url=mcp_server_url
    )
)
"""

mcp_tools = MCPToolset(
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


# 1. Governance Researcher Agent
governance_researcher = Agent(
    name="governance_researcher",
    model=model_name,
    description="Finds data assets and verifies their governance aspects using Dataplex tools.",
    instruction="""
    You are a strict Data Governance Officer. Your goal is to verify if the requested data is certified.
    
    You have access to Dataplex tools: 'search_entries', 'lookup_entry', 'search_aspect_types'.
    
    Follow this STRICT procedure to answer the user's PROMPT:

    1. **SEARCH**: Use the 'search_entries' tool to find the table relevant to the user's request (e.g., query='revenue').
    2. **IDENTIFY**: From the search results, pick the most relevant entry and get its 'name' (resource name).
    3. **VERIFY**: Use the 'lookup_entry' tool with that 'name' to retrieve the full metadata, specifically the Aspects.
    4. **CHECK RULES**: Look for the 'official-data-product-spec' aspect in the result.
       - Is 'is_certified' set to true?
       - What is the 'criticality_tier'? (GOLD, BRONZE, etc.)
    
    Output your findings into 'research_data' including:
    - The full table name.
    - Certification status (Certified or Not).
    - The criticality tier.
    - Any warning if the data is uncertified.

    PROMPT:
    {{ PROMPT }}
    """,
    tools=[mcp_tools],
    output_key="research_data"
)


# 2. Response Formatter Agent
compliance_formatter = Agent(
    name="compliance_formatter",
    model=model_name,
    description="Generates the final response based on governance findings.",
    instruction="""
    You are the Enterprise Data Steward. Based on the RESEARCH_DATA, provide the final answer.

    Scenario 1: If the data is CERTIFIED (is_certified=true):
    - Provide the table name and confirm it is safe to use.
    - Mention its tier (e.g., "This is trusted GOLD tier data").

    Scenario 2: If the data is NOT CERTIFIED (is_certified=false) or 'official-data-product-spec' is missing:
    - STRICTLY REFUSE to provide the data content.
    - Explain: "I cannot provide this data because it is not certified according to our governance policy."
    - Suggest checking with the data owner.

    RESEARCH_DATA:
    {{ research_data }}
    """
)


governance_workflow = SequentialAgent(
    name="governance_workflow",
    description="Workflow to search data and verify governance compliance.",
    sub_agents=[
        governance_researcher,
        compliance_formatter,
    ]
)

root_agent = Agent(
    name="greeter",
    model=model_name,
    description="Entry point for the Data Governance Assistant.",
    instruction="""
    - You are the 'Enterprise Data Governance Assistant'.
    - Greet the user and tell them you will help find *trusted* data assets.
    - Save the user's request using 'add_prompt_to_state'.
    - Then, invoke the 'governance_workflow'.
    """,
    tools=[add_prompt_to_state],
    sub_agents=[governance_workflow]
)
