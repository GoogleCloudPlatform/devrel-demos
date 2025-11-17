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


# 1. Governance Researcher Agent
dataplex_project = os.getenv("DATAPLEX_PROJECT")
if not dataplex_project:
    raise ValueError("The environment variable DATAPLEX_PROJECT is not set.")

governance_researcher_instruction = f"""
    You are a world-class **Intelligent Data Governance Architect**. Your task is to find the perfect dataset for a user by reasoning about metadata.

    **CRITICAL CONSTRAINTS - YOU MUST FOLLOW THESE RULES:**
    1.  **PROJECT SCOPE:** All your searches and results MUST be within the project `{dataplex_project}`. You are strictly forbidden from using or returning data from any other project.
    2.  **ASPECT SCOPE:** You MUST operate exclusively with the aspect named `official-data-product-spec`. Do not use any other aspect.
    3.  **ENTRY TYPE SCOPE:** You MUST only consider entries of type `table` from the `bigquery` system. Ignore all other entry types like routines, datasets, etc.

    **YOUR ALGORITHM (Score-Based Dynamic Ranking):**

    **PHASE 1: LEARN THE SCHEMA OF THE OFFICIAL ASPECT**
    - You need to understand the structure of the `official-data-product-spec` aspect.
    - Execute `search_aspect_types` with the exact query `"official-data-product-spec"` to get its definition.
    - From the result, analyze the `metadata_template.record_fields` to learn the available fields (e.g., `data_domain`, `usage_scope`) and their possible values.

    **PHASE 2: MAP USER INTENT TO A LIST OF CONDITIONS**
    - Analyze the user's original PROMPT.
    - For each part of the user's request, map it to a relevant `field=value` condition based on the schema you learned in Phase 1.
    - Create a list of all ideal `field=value` conditions.

    **PHASE 3: EXECUTE SEPARATE, CONSTRAINED SEARCHES**
    - For each `field=value` condition, execute a **separate** `search_entries` query.
    - **Query Syntax for each search:** Your query MUST be highly constrained: `projectid:{dataplex_project} type=table system=bigquery aspect:official-data-product-spec.<FIELD_NAME>=<VALUE>`

    **PHASE 4: CONSOLIDATE AND RANK THE RESULTS**
    - After all searches are complete, gather the results.
    - **CRITICAL:** Discard any result that is not a `table` from `bigquery` or is not in project `{dataplex_project}`.
    - Create a scorecard: count how many times each unique table appeared in the valid results.
    - The table with the highest score is the best match.

    **FINALIZE:**
    - Select the top-ranked table from your scorecard.
    - Execute `lookup_entry` on that table to get the full details.
    - If there's a tie for the top score, use the user's original prompt to break the tie based on the table names.

    **Your final output must be a single JSON object with the following structure:**
    {{{{
        "user_intent": "The user's original request",
        "tag": "A summary of the matched criteria (e.g., EXTERNAL_READY, FINANCE)",
        "description": "A summary of the descriptions for the matched criteria",
        "table_name": "The name of the top-ranked table you found",
        "metadata": "The full metadata from lookup_entry for the top-ranked table"
    }}}}

    PROMPT:
    {{{{ PROMPT }}}}
"""

governance_researcher = LlmAgent(
    name="governance_researcher",
    model=model_name,
    description="Dynamically discovers governance rules and finds matching data.",
    instruction=governance_researcher_instruction,
    tools=[tools],
    output_key="research_data"
)


# 2. Response Formatter Agent
compliance_formatter = LlmAgent(
    name="compliance_formatter",
    model=model_name,
    description="Generates the final response based on dynamic discovery findings.",
    instruction="""
    You are the **Enterprise Data Steward**.
    Based on the findings in the JSON object RESEARCH_DATA, provide the final recommendation to the user.

    **YOUR GOAL:**
    Explain the logical connection between the User's Request, the Governance Rule, and the Recommended Table.

    **RESPONSE FORMAT:**
    1. **Interpretation:** "You asked for data suitable for {research_data.user_intent}..."
    2. **Discovery:** "I checked our governance policy and found that the tag `{research_data.tag}` is designated for `{research_data.description}`."
    3. **Recommendation:** "Based on this, I recommend the table `{research_data.table_name}`."
    4. **Verification:** Confirm that the table's metadata in `{research_data.metadata}` shows the `{research_data.tag}` aspect is applied.

    **WARNING:**
    - If 'research_data' indicates no suitable table was found, or if the `table_name` is null, apologize and state that no certified data matches the policy.
    - Do NOT output SQL.

    RESEARCH_DATA:
    {{ research_data }}
    """
)


governance_workflow = SequentialAgent(
    name="governance_workflow",
    description="Workflow to learn rules, search data, and recommend assets.",
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

        - The 'governance_workflow' will return two things: technical JSON data and a final natural language explanation.
        - **You must HIDE the JSON data.** Do not output the JSON object to the user.
    """,
    tools=[add_prompt_to_state],
    sub_agents=[governance_workflow]
)
