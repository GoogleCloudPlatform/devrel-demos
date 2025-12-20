from google.adk.agents.llm_agent import Agent
from .queries_rag import search_query_library
from .schema_rag import discover_schema

import subprocess
import platform

# Replace it with your favourite model as long as it supports tool calling
# MODEL = LiteLlm(model="ollama_chat/qwen2.5")
MODEL = "gemini-2.5-flash"


def run_osquery(query: str) -> str:
    """Runs a query using osquery.

    Args:
      query: The osquery query to run. Example: 'select * from battery'

    Returns:
      The query result as a JSON string.

      If the query result is empty "[]" it can mean:
      1) the table doesn't exist
      2) the query is malformed (e.g. a column doesn't exist)
      3) the table is empty
    """
    try:
        # Run osqueryi as a one-off command with a 60s timeout.
        # --json forces JSON output format.
        result = subprocess.run(
            ["osqueryi", "--json", query], capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            # Return stderr as error message if it failed (e.g. syntax error)
            return f"Error running osquery: {result.stderr.strip() or 'Unknown error (exit code ' + str(result.returncode) + ')'}"

        output = result.stdout.strip()
        # Sometimes osqueryi outputs nothing if the table is empty, instead of []
        if not output:
            return "[]"

        return output

    except subprocess.TimeoutExpired:
        return "Error: Query timed out after 60 seconds (table might be too slow or locked)."
    except FileNotFoundError:
        return (
            "Error: 'osqueryi' executable not found. Is it installed and in your PATH?"
        )
    except Exception as e:
        return f"Unexpected error running osquery: {e}"


current_os = platform.system().lower()

root_agent = Agent(
    model=MODEL,
    name="aida",
    description="The emergency diagnostic agent",
    instruction=f"""
[IDENTITY]
You are AIDA, the Emergency Diagnostic Agent. You are a cute, friendly, and highly capable expert.
Your mission is to help the user identify and resolve system issues efficiently.

[PROTOCOL]
- Greet: If no initial request is provided, ask: "Please state the nature of the diagnostic emergency"
- Tone: Professional yet warm and encouraging.
- Reporting: Provide brief, actionable summaries of findings first. Only show raw data or detailed logs if explicitly requested.

[ENVIRONMENT]
- Host OS: {current_os}
- Tools: search_query_library, discover_schema, run_osquery

[OPERATIONAL WORKFLOW]
Follow this sequence for most investigations to ensure efficiency and accuracy:
1. SEARCH: For all tasks, FIRST use `search_query_library` to find query candidates.
2. DISCOVER: If no suitable query is found using SEARCH, you MUST use `discover_schema` and build a custom query
3. EXECUTE: Use `run_osquery` to execute the query.
    """,
    tools=[
        search_query_library,
        discover_schema,
        run_osquery,
    ],
)
