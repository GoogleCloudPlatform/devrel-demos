import subprocess
import platform
import json
from google.adk.agents.llm_agent import Agent
from google.adk.tools import AgentTool, google_search

# Import RAG tools from the local package
from .queries_rag import search_query_library
from .schema_rag import discover_schema

# Hardcoded Model
MODEL = "gemini-3-flash-preview"

def run_osquery(query: str) -> str:
    """Runs a query using osquery.

    Args:
      query: The osquery query to run. Example: 'select * from battery'

    Returns:
      The query result as a JSON string.
    """
    try:
        # Run osqueryi as a one-off command with a 60s timeout.
        # --json forces JSON output format.
        result = subprocess.run(
            ["osqueryi", "--json", query], capture_output=True, text=True, timeout=60
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"Exit code {result.returncode}"
            return json.dumps({
                "error": "Query failed",
                "details": error_msg,
                "suggestion": "Check table names and syntax using discover_schema."
            })

        output = result.stdout.strip()
        
        # Sometimes osqueryi outputs nothing if the table is empty
        if not output:
            return "[]"

        # Validate that we actually got JSON back
        try:
            json.loads(output)
            return output
        except json.JSONDecodeError:
            return json.dumps({
                "error": "Invalid output format",
                "details": "osqueryi did not return valid JSON",
                "raw_output": output
            })

    except subprocess.TimeoutExpired:
        return json.dumps({
            "error": "Query timeout",
            "details": "The query exceeded the 60s time limit. It might be scanning too many files or a slow table."
        })
    except FileNotFoundError:
        return json.dumps({
            "error": "Dependency missing",
            "details": "'osqueryi' executable not found in PATH."
        })
    except Exception as e:
        return json.dumps({
            "error": "Unexpected error",
            "details": str(e)
        })


current_os = platform.system().lower()

# Define a dedicated google search agent and tool
google_search_agent = Agent(
    name="google_search",
    instruction="You are a google search agent. Use the available tools to find information on the web.",
    tools=[google_search],
    model=MODEL,
)

google_search_tool = AgentTool(
    agent=google_search_agent
)

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
- Tools: search_query_library, discover_schema, run_osquery, google_search_tool

[OPERATIONAL WORKFLOW]
Follow this sequence for most investigations to ensure efficiency and accuracy:
1. SEARCH: For all tasks, FIRST use `search_query_library` to find query candidates.
2. DISCOVER: If no suitable query is found using SEARCH, you MUST use `discover_schema` and build a custom query
3. EXECUTE: Use `run_osquery` to execute the query.
4. EXTERNAL: If you need information about a specific error message, software version, or known issue that isn't in your local library, use `google_search_tool`.
    """,
    tools=[
        search_query_library,
        discover_schema,
        run_osquery,
        google_search_tool,
    ],
)
