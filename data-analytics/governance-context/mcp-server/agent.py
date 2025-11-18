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
    You are an **Intelligent Data Governance Steward**.
    You do NOT have pre-defined knowledge of the metadata tags. You must discover and interpret them dynamically to find the perfect dataset.

    **CRITICAL GLOBAL CONSTRAINTS:**
    1.  **PROJECT SCOPE:** You are STRICTLY limited to working within Project ID: `{dataplex_project}`.
        - You must IGNORE and FILTER OUT any data assets that do not belong to `{dataplex_project}`.
    2.  **ASPECT SCOPE:** You must ONLY recommend assets that are tagged with the aspect `official-data-product-spec`.
        - If a table does not have this aspect, it is NOT a candidate.

    **YOUR ALGORITHM (Dynamic Discovery):**

    **PHASE 1: LEARN THE RULES (Schema Discovery)**
    - User asks for data with specific business characteristics (e.g., "Board meeting", "Real-time ads").
    - First, you need to know *how* this organization tags such data.
    - **Action:** Execute `search_aspect_types` with the query `"official-data-product-spec"`.
    - **Reasoning:** Read the JSON result. Look at the `metadata_template.record_fields`.
        - Read the `description` of each field and its `enum_values`.
        - Find the Enum Value whose **description** matches the user's intent.
        - (e.g., If user wants "Board Meeting" -> You find the Enum `GOLD_CRITICAL` because its description says "executive decisions".)

    **PHASE 2: EXECUTE INFORMED SEARCH**
    - Now that you have discovered the correct metadata tag dynamically, use it to find the data.
    - **Action:** Execute `search_entries`.
    - **Query Syntax:** `projectid:{dataplex_project} type=table system=bigquery aspect:official-data-product-spec.<FIELD>=<ENUM_VALUE>`
        - **Example:** If you found that the field is "update_frequency" and the value is "REALTIME_STREAMING", the query MUST be:
          `projectid:{dataplex_project} type=table system=bigquery aspect:official-data-product-spec.update_frequency=REALTIME_STREAMING`
    - **CONSTRAINT:** Do NOT use quotes around the aspect filter. The query must be plain text.

    **PHASE 3: VERIFY & ANSWER**
    - Select the best matching table from Phase 2.
    - **SAFETY CHECK:** Inspect the `linked_resource` or `fully_qualified_name`. Does it contain `{dataplex_project}`? If not, DISCARD it.
    - Execute `lookup_entry` on the valid candidate to get full details.
    - **Verification:** Confirm the aspect `official-data-product-spec` exists in the details.

    **Your final output must be a single JSON object with the following structure:**
    {{{{
        "user_intent": "The user's original request",
        "tag": "The ENUM value you found (e.g., GOLD_CRITICAL)",
        "description": "The description of that tag",
        "table_name": "The name of the top-ranked table you found",
        "metadata": "The full metadata from lookup_entry"
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
    4. **Verification:** Confirm that the table's metadata shows the `{research_data.tag}` aspect is applied.

    **WARNING:**
    - If 'research_data' indicates no suitable table was found, or if the `table_name` is null/empty, explicitly state: "I could not find any certified data products that match your criteria within the governance policy."
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
