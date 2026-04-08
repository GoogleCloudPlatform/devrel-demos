"""
This module defines the core agent-based workflow for the fraud detection application.
"""

# Standard library imports
import os

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import google_search
from google.adk.tools.bigquery import BigQueryToolset
from .tools import log_final_decision

def get_root_agent():
    # --- Config ---
    PROJECT_ID = os.getenv("PROJECT_ID", "missing-project-id")
    MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Initialize the BigQuery toolset inside the factory function
    bigquery_toolset = BigQueryToolset()

    # --- SUB-AGENTS ---
    search_agent = Agent(
        model=MODEL_NAME,
        name="Search_Agent",
        description="Search agent that can look up information on the web, particularly for investigating merchant reputation.",
        tools=[google_search],
    )

    # --- SINGLE AGENT ARCHITECTURE ---
    investigation_agent = Agent(
        model=MODEL_NAME,
        name="Fraud_Investigation_Agent",
        description="Expert fraud analyst agent that autonomously investigates alerts, queries data, performs visual analysis, and makes final decisions.",
        instruction=(
            f"""
            You are an expert fraud investigator for Cymbal Bank.
            Your goal is to investigate financial transaction alerts, determine if they are fraudulent, and take appropriate action.

            **Your Toolkit:**
            1. `bigquery_toolset`: Run SQL queries to find data. 
               *   **Context:** Data is in `{PROJECT_ID}.cymbal_bank`. 
            2. `Search_Agent`: Delegate to this sub-agent to research merchant reputation on the web.

            **Investigation Process:**
            1.  **Analyze the Alert:** Extract `user_id` and `merchant`.
            2.  **Gather Data:**
                *   **Historical Context:** MUST use the `bigquery_toolset` tool to execute a SQL query against the `cymbal_bank.retail_transactions` table. Fetch all available information for the user over the past 7 days. Look for anomalous locations and spending amounts.
                *   **Verify Merchant:** Delegate to `Search_Agent` tool to search for the merchant.
            3.  **Evaluate:**
                *   Is the merchant suspicious?
                *   Do the historical transactions for this user align with their current behavior?
            4.  **Decide:**
                *   **FALSE_POSITIVE**: If evidence explains the alert.
                *   **ESCALATION_NEEDED**: If activity is anomalous, merchant is bad, or vision data is incriminating.
            5. **Log your findings via the `log_final_decision` tool:**

            IMPORTANT: You MUST call `log_final_decision` as your absolute last action BEFORE providing a final natural language response.

            **Output:**
            Provide a concise summary of your findings and the final decision (FALSE_POSITIVE or ESCALATION_NEEDED).           
            
            """
        ),
        tools=[
            bigquery_toolset,
            AgentTool(agent=search_agent),
            log_final_decision,
        ],
    )

    return investigation_agent
