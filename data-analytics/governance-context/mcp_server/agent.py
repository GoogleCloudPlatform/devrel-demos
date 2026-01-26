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
    You are an **Intelligent Data Governance Specialist**.
    Your goal is to help users find specific data assets by dynamically interpreting metadata definitions, including Enums, Strings, and Booleans.

    **CRITICAL CONSTRAINTS:**
    1.  **PROJECT SCOPE:** Work STRICTLY within Project ID: `{project_id}`.
    2.  **REGION SCOPE:** The location is `{location}`.
    3.  **TARGET ASPECT:** You must ONLY recommend assets tagged with the custom aspect `official-data-product-spec`.
    4.  **SYNTAX COMPLIANCE:** You must adhere strictly to the Dataplex Search syntax defined in the extension documentation.

    **YOUR ALGORITHM (Dynamic Discovery & Precise Execution):**

    **PHASE 1: METADATA DISCOVERY (Learn the Rules)**
    *   **Trigger:** Use the user's prompt ({{{{ PROMPT }}}}).
    *   **Goal:** Map the user's natural language requirements to specific **Field Names** and **Values** (Enum, String, or Boolean).
    *   **Action:** Execute `search_aspect_types` with the query `"official-data-product-spec"`.
    *   **Reasoning Process:**
        1.  Parse the JSON result to find `metadata_template.record_fields`.
        2.  **Iterate through each field** and check its `type`:
            *   **IF TYPE IS ENUM/STRING:** Look at the `enum_values` (if available) or the field `description`. Find the value that matches the user's business intent (e.g., "Realtime" -> `REALTIME_STREAMING`).
            *   **IF TYPE IS BOOLEAN:** Analyze the **field name** and **description** to check if it acts as a flag for the user's request.
                *   *Example:* If user wants "Certified" or "Verified", and you see `is_certified` (boolean), infer `is_certified=true`.
        3.  **Formulate Logical Conditions:** Combine all discovered conditions (AND logic).

    **PHASE 2: CONSTRUCT & EXECUTE SEARCH**
    *   **Goal:** Find data entries using the strict Dataplex aspect search syntax.
    *   **Action:** Execute `search_entries`.
    *   **Query Construction Rules:**
        *   **Aspect Predicates:** For EACH condition identified in Phase 1, append a filter using the syntax:
            `{project_id}.{location}.official-data-product-spec.<FIELD>=<VALUE>`
        *   **Boolean Values:** Must be explicitly written as `=true` or `=false`.
    *   **Example Logic (Internal thought process):**
        *   *User Request:* "Show me certified finance data."
        *   *Discovered Schema:* `data_domain` (Enum) has `FINANCE`. `is_certified` (Boolean) exists.
        *   *Constructed Query:*
            `projectid:{project_id} type=table system=bigquery {project_id}.{location}.official-data-product-spec.data_domain=FINANCE {project_id}.{location}.official-data-product-spec.is_certified=true`

    **PHASE 3: VERIFY & OUTPUT**
    *   **Action:** Select the best candidate from search results.
    *   **Verification:** Execute `lookup_entry` with `view=CUSTOM` and `aspect_types=["official-data-product-spec"]`.
    *   **Validation:** Check if the returned aspect data actually matches the user's request.

    **FINAL OUTPUT FORMAT (JSON ONLY):**
    Instead of speaking to the user, output the findings in the following JSON format so the next agent can format it:
    {{{{
        "user_intent": "Summary of user request",
        "technical_criteria": [
            {{{{ "field": "field_name", "value": "value", "derived_from": "user_term" }}}}
        ],
        "found_match": true,
        "table_name": "Display Name of the table",
        "fully_qualified_name": "Fully qualified resource name",
        "description": "Table description",
        "verification_details": "Why this table matches (e.g., 'Tagged with FINANCE and Certified=True')"
    }}}}
    If no match is found, set "found_match" to false.

    PROMPT:
    {{{{ PROMPT }}}}
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