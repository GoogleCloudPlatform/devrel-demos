import os
import logging
import asyncio
import httpx
import google.cloud.logging
from dotenv import load_dotenv

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents import SequentialAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
from google.adk.tools.tool_context import ToolContext

import google.auth
import google.auth.transport.requests
import google.oauth2.id_token

# --- Monkey Patch httpx to dynamically refresh Google Cloud access tokens ---
# This ensures long-running agent instances on Cloud Run do not fail after the initial 1-hour token expires.
original_async_send = httpx.AsyncClient.send
async def patched_async_send(self, request, *args, **kwargs):
    if "dataplex.googleapis.com" in str(request.url):
        token = await asyncio.to_thread(get_access_token)
        request.headers["Authorization"] = f"Bearer {token}"
    return await original_async_send(self, request, *args, **kwargs)
httpx.AsyncClient.send = patched_async_send

original_sync_send = httpx.Client.send
def patched_sync_send(self, request, *args, **kwargs):
    if "dataplex.googleapis.com" in str(request.url):
        token = get_access_token()
        request.headers["Authorization"] = f"Bearer {token}"
    return original_sync_send(self, request, *args, **kwargs)
httpx.Client.send = patched_sync_send

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
mcp_server_url = "https://dataplex.googleapis.com/mcp"

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


from pathlib import Path
from google.adk.skills import load_skill_from_dir
from google.adk.tools import skill_toolset

# Load the governance skill following best practices (progressive disclosure)
base_dir = Path(__file__).parent
governance_skill = load_skill_from_dir(
    base_dir / "skills" / "knowledge-catalog-governance"
)

# Bundle the skill and MCP tools together into a SkillToolset
governance_skill_toolset = skill_toolset.SkillToolset(
    skills=[governance_skill],
    additional_tools=[tools]
)

# --- 1. Governance Researcher Agent ---
governance_researcher = LlmAgent(
    name="governance_researcher",
    model=model_name,
    description="Dynamically interprets metadata schema (Booleans/Enums) and searches for assets using strict syntax.",
    instruction=f"""
    You are a governance researcher. Your job is to verify Knowledge Catalog metadata rules and find compliant assets for the user's query.
    
    YOUR ACTIVE ENVIRONMENT CONTEXT (CRITICAL):
    - Google Cloud Project ID: {project_id} (You MUST use this EXACT string for your tool scope and aspect queries. Never use any other project name, placeholders, or cached names from previous sessions.)
    - Location (Region): {location}

    YOUR WORKFLOW:
    1. First, check if the user query is related to data analytics assets, database tables, or data compliance.
       - If YES: Call `load_skill` with `name="knowledge-catalog-governance"` to load the rules, then use search/lookup tools to locate a certified compliant table.
       - If NO (e.g., general chit-chat, unrelated tasks): Skip skill loading and output a JSON object indicating it is out of scope:
         {{"error": "out_of_scope", "message": "The query does not pertain to data catalog search or governance compliance."}}
    2. Populate the required `projectId` and `location` parameters in tool calls with the active environment parameters. Ensure the `scope` parameter in `search_entries` is precisely set to `projects/{project_id}` using the active Google Cloud Project ID provided above.
    3. Return the verified table's metadata in JSON format as your final research output.
    """,
    tools=[governance_skill_toolset, tools],
    output_key="research_data"
)


# --- 2. Response Formatter Agent ---
compliance_formatter = LlmAgent(
    name="compliance_formatter",
    model=model_name,
    description="Formats the JSON research data into a helpful response for the user.",
    instruction="""
    You are the **Intelligent Data Governance Specialist**.
    Your job is to explain the findings of the governance research clearly to the user.

    **YOUR GOAL:**
    1. If the researcher found a matching table (valid JSON with table metadata):
       - Explain the logical connection between the User's Request, the Governance Schema (translated criteria), and the Recommended Table.
       - Use the following RESPONSE TEMPLATE:
         - **Analysis:** "I analyzed the metadata schema and translated your request into the following technical criteria:..."
         - **Recommendation:** "Based on this, I recommend the following table:"
           - **Table:** [Insert Table Name]
           - **Description:** [Insert Table Description]
         - **Verification:** "This asset is a verified match because: [Explain the verification details]."
    2. If the researcher returned an 'out_of_scope' error or no matching tables were found:
       - Apologize politely and explain that no data asset currently matches the strict governance criteria defined in `official-data-product-spec`.
       - Clearly state what domain of questions this agent is certified to answer (e.g., Data Catalog Search and Data Governance compliance).
    """
)


# --- Root Agent Workflow ---
root_agent = SequentialAgent(
    name="governance_workflow",
    description="Workflow to learn metadata rules, search with strict syntax, and recommend assets.",
    sub_agents=[
        governance_researcher,
        compliance_formatter,
    ]
)