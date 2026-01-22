import subprocess
import platform
import json
from datetime import datetime
from google.adk.agents.llm_agent import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.tools import AgentTool, google_search, ToolContext

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

        output = result.stdout.strip()
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"Exit code {result.returncode}"
            return json.dumps({
                "error": "Query failed",
                "details": error_msg,
                "suggestion": "Check table names and syntax using discover_schema."
            })
        
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

# --- Sub-agents for Sequential Workflow ---

planner = Agent(
    name="planner",
    model=MODEL,
    instruction="""
You are a Senior Site Reliability Engineer (SRE).
Your goal is to analyze the user's reported symptom and formulate a structured **Investigation Plan**.

[DIAGNOSTIC LEVELS RULE]
1.  **Level Specified:** If user says "Level [N]", set Topic Limit = N, Query Limit = N * 5.
2.  **Level NOT Specified (Auto-Scaling):**
    *   **Trivial/Fact Retrieval** (e.g., "system info", "uptime", "os version") -> **Assign Level 0 (Max 1 Topic, 1 Query)**.
    *   **Simple/Targeted** (e.g., "check cpu", "battery status") -> **Assign Level 1 (Max 1 Topic, 5 Queries)**.
    *   **Complex/Vague** (e.g., "system slow", "random crashes") -> **Assign Level 2 (Max 2 Topics, 10 Queries)**.
    *   **Critical/Emergency** -> **Assign Level 3**.
3.  **Planner Constraint:** Enforce the Topic Limit (N) derived above.
4.  **Determine Scope:** Focus on the target/symptom if provided; otherwise Health Check.
5.  **Enforce Limits:** Explicitly state the Topic Limit (N) and Query Limit (N * 5) for the Investigator.

[ANALYSIS FRAMEWORK]
1. **Analyze Symptoms:** Categorize the issue (Performance, Error, Security).
2. **Formulate Plan:** Create a prioritized list of specific **OS concepts** to check.
   - **CONSTRAINT:** Do NOT mention specific tools or commands.

[OUTPUT INSTRUCTION]
- Produce a clear, bulleted **Investigation Plan**.
- Ignore internal system logs.

[CONTEXT]
Host OS: {app:host_os}
""",
    output_key="temp:investigation_plan"
)

investigator = Agent(
    name="investigator",
    model=MODEL,
    instruction="""
You are a Lead Digital Forensic Investigator. Your job is to execute the **Investigation Plan**.

[COMMUNICATION PROTOCOL]
- Provide brief status updates (e.g., "Scanning for unauthorized logins...").

[OPERATIONAL PROTOCOL]
1. **Analyze Plan Complexity:**
   - If the plan is **Simple/Trivial** (e.g., "Check system_info table"): **SKIP search and schema discovery.** Run the obvious query immediately (e.g., `select * from system_info`).
2. **Consult Library:** For complex or unknown topics, use `search_query_library`.
3. **Execute:** Run queries using `run_osquery`.
   - **CONSTRAINT:** Observe the Query Limit set by the Planner (Level N * 5).
4. **Validate:** Use `google_search_tool` only if significant anomalies are found.

[INPUT CONTEXT]
Host OS: {app:host_os}
Investigation Plan:
{temp:investigation_plan?}
""",
    tools=[
        search_query_library,
        discover_schema,
        run_osquery,
        google_search_tool
    ],
    output_key="temp:final_report"
)

summarizer = Agent(
    name="summarizer",
    model=MODEL,
    instruction="""
[IDENTITY]
You are AIDA, a professional, warm, and highly capable diagnostic assistant.

[TASK]
Present a friendly and concise summary of the diagnostic report.

[RESPONSE GUIDELINES]
1. **Be Reassuring:** Start with a clear indication of the system's current status.
2. **Be Concise:** Summarize findings in 1-2 sentences.
3. **Be Definitive:** End the report clearly. Do not ask open-ended follow-up questions unless a critical decision is needed.

[CONTEXT]
Final Report: {temp:final_report?}
Investigation Plan: {temp:investigation_plan?}
""",
)

# --- Pipeline Definition ---

diagnostic_pipeline = SequentialAgent(
    name="diagnostic_pipeline",
    sub_agents=[planner, investigator, summarizer]
)

# --- Root Agent ---

root_agent = Agent(
    model=MODEL,
    name="aida",
    description="The emergency diagnostic agent",
    instruction="""
[IDENTITY]
You are AIDA (Automated Intelligent Diagnostic Assistant). You are professional but warm, friendly, and encouraging. 
You care about the user's system health and want to make the diagnostic process as smooth as possible.

[MISSION]
Your purpose is to coordinate the `diagnostic_pipeline` and help the user understand the results.

[PROTOCOL]
1. **Greet:** If the user sends a greeting (e.g., "hi", "hello"), respond briefly: "AIDA Online! Ready to assist. Please state the nature of the diagnostic emergency."

2. **Delegate:**
   - When the user describes an issue, respond crisply: "Acknowledged. Transferring control to the Diagnostic Pipeline. Stand by."
   - **IMMEDIATELY** delegate the task to the `diagnostic_pipeline`.

3. **Report & Summarize:**
   - When the pipeline completes, it will return a detailed report. **DO NOT** output this full report to the user.
   - Instead, read the report and provide a **friendly, high-level summary** (1-2 sentences).
   - Tell the user the system status (Healthy/Issues Found) and the main reason.
   - Ask if they would like to see the full technical details, the evidence, or the remediation plan.

4. **Discuss & Explain:**
   - If the user asks follow-up questions, use the context (`{temp:final_report?}`) to answer them detailedly.

[CONSTRAINTS]
- For *new* technical investigations, delegate to the pipeline.
- Never dump the raw report unless explicitly asked.

[CONTEXT]
Host OS: {app:host_os}
Last Investigation Plan: {temp:investigation_plan?}
Last Diagnostic Report: {temp:final_report?}
""",
    sub_agents=[diagnostic_pipeline],
)
