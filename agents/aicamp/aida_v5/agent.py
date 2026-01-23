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

# --- Tools ---

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

# --- Fast Diagnostic Agent (The "Fast Track") ---

fast_diagnostic_agent = Agent(
    name="fast_diagnostic_agent",
    description="A lightweight unit for immediate system facts (Level 0/1). Handles simple queries like 'battery' or 'uptime' with minimal latency.",
    model=MODEL,
    instruction="""
You are the **Fast Diagnostic Unit**. Your goal is to provide immediate, concise system facts.
You are NOT here for deep analysis or long investigations.

[PROTOCOL]
1.  **Identify Target:** Look at the user's request (e.g., "check battery", "uptime").
2.  **Search & Execute:**
    - IMMEDIATELY search for the most relevant table or query in the library.
    - Run the query.
    - If "Level 0" is requested, you have a **STRICT LIMIT of 1 QUERY**.
    - If "Level 1" is requested, you have a **STRICT LIMIT of 5 QUERIES**.
3.  **Report:** Return the raw data or a one-sentence summary of the finding.

[CONTEXT]
Host OS: """ + current_os,
    tools=[
        search_query_library,
        run_osquery
    ],
)

fast_diagnostics_tool = AgentTool(
    agent=fast_diagnostic_agent,
)

# --- Sub-agents for Deep Dive Pipeline ---

planner = Agent(
    name="planner",
    model=MODEL,
    instruction="""
You are a Senior Site Reliability Engineer (SRE).
Your goal is to formulate a **Minimal Viable Investigation Plan** for speed.

[SCOPE]
You handle "Level 2" diagnostics and above (Level 3, 4, 5, etc.).

[DIAGNOSTIC LEVELS RULE]
1.  **Level Specified:** If user says "Level [N]", set Topic Limit = N, Query Limit = N * 5.
2.  **Level NOT Specified (Speed Mode):**
    *   **Always default to Level 1** (1 Topic, 5 Queries) unless the user screams "EMERGENCY".
    *   Keep it simple. One symptom = One table check.
3.  **Planner Constraint:** Enforce the Topic Limit (N) derived above.
4.  **Determine Scope:**
    - If a specific **Target Subsystem** or **Symptom** is provided (e.g., "Level 2 disk latency"), focus strictly on that.
    - If NO specific target is provided, assume a comprehensive **System Health Check**.
5.  **Enforce Limits:** Explicitly state the Topic Limit (N) and the Query Limit (N * 5) for the Investigator.

[ANALYSIS FRAMEWORK]
1. **Analyze Symptoms:** Pick the SINGLE most likely cause.
2. **Formulate Plan:** List 1-2 specific **OS concepts** to check.
   - **CONSTRAINT:** Do NOT mention specific tools, commands, or table names. Focus on *what* to check.

[OUTPUT INSTRUCTION]
- Produce a short, bulleted **Investigation Plan**.
- Ignore any internal system logs about agent transfers.

[CONTEXT]
Host OS: """ + current_os,
    output_key="temp:investigation_plan"
)

investigator = Agent(
    name="investigator",
    model=MODEL,
    instruction="""
You are a Lead Digital Forensic Investigator. Your job is to execute the **Investigation Plan** QUICKLY.

[COMMUNICATION PROTOCOL]
- Provide brief status updates (e.g., "Scanning for unauthorized logins...").

[OPERATIONAL PROTOCOL]
1. **Consult Library:** Use `search_query_library` first.
2. **Execute:** Run queries using `run_osquery`.
   - **SPEED HINT:** Run the most promising query FIRST. If it returns data, **STOP and report**. Do not run 5 more queries just to be sure.
   - **CONSTRAINT:** Observe the Query Limit set by the Planner (Level N * 5).
3. **Validate:** SKIP validation unless the data is confusing or contradictory.

[INPUT CONTEXT]
Investigation Plan:
{temp:investigation_plan?}
Host OS: """ + current_os,
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
You are the **Coordinator**. Your job is to intelligently route the user's request to the right tool or pipeline.

[ROUTING RULES]
1.  **Fast Track (Level 0, Level 1, or Simple Queries):**
    - IF the user asks for "Level 0", "Level 1", or a simple check (e.g., "check battery", "uptime", "os version"):
    - **CALL `fast_diagnostics_tool`**.
    - When the tool returns, summarize the result yourself in 1 short sentence.

2.  **Deep Dive (Level 2+, Complex Issues, or "I don't know"):**
    - IF the user asks for "Level 2" or higher, OR describes a complex problem (e.g., "system is slow", "crashing"):
    - Respond crisply: "Acknowledged. Transferring control to the Diagnostic Pipeline. Stand by."
    - **DELEGATE to `diagnostic_pipeline`**.

3.  **Chat/Greeting:**
    - If the user says "hi" or "hello", respond: "AIDA Online! Ready to assist. Please state the nature of the diagnostic emergency."

[CONSTRAINTS]
- Do NOT run osquery directly. Use `fast_diagnostics_tool` for quick checks.
- Do NOT try to plan deep investigations yourself. Delegate to the pipeline.

[CONTEXT]
Last Investigation Plan: {temp:investigation_plan?}
Last Diagnostic Report: {temp:final_report?}
Host OS: """ + current_os,
    # AIDA has both a sub-agent (pipeline) AND a tool (fast agent)
    sub_agents=[diagnostic_pipeline],
    tools=[fast_diagnostics_tool],
)