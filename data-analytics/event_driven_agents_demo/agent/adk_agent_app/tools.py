# Copyright 2026 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Custom tools for the Cymbal Bank fraud investigation agent.
"""

import os
import datetime
from google.adk.tools.agent_tool import AgentTool
from google.cloud import bigquery
from vertexai.generative_models import GenerativeModel, Part
from google.adk.tools import ToolContext


# --- Tool Functions ---

def log_final_decision(tool_context: ToolContext, user_id: str, merchant: str, decision: str, summary: str) -> str:
    """Logs the final decision of the fraud investigation to BigQuery.
    
    This MUST be called as the final step of the investigation before you respond to the user.
    
    Args:
        user_id: The ID of the user being investigated.
        merchant: The name of the merchant involved.
        decision: The final decision MUST be exactly 'FALSE_POSITIVE' or 'ESCALATION_NEEDED'.
        summary: A concise 1-sentence summary of the decision.
    """
    try:
        project_id = os.getenv("PROJECT_ID")
        if not project_id:
            return "Failed to log decision: PROJECT_ID is not set in the environment."

        # In modern ADK versions, the context holds the session object directly
        session = getattr(tool_context, "session", None)
        if hasattr(session, "id"):
            session_id = session.id
            app_name = getattr(session, "app_name", "unknown_app")
        else:
            # Fallback for local mocks or older schemas
            state = getattr(tool_context, "state", {}) or {}
            session_id = getattr(tool_context, "session_id", "unknown_session")
            app_name = state.get("app_name", "unknown_app")

        row = {
            "session_id": session_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "app_name": app_name,
            "user_id": user_id,
            "merchant": merchant,
            "decision": decision,
            "summary": summary
        }
                
        dataset_id = os.getenv("BIGQUERY_DATASET", "cymbal_bank")
        errors = bigquery.Client(project=project_id).insert_rows_json(f"{project_id}.{dataset_id}.agent_decisions", [row])
        return f"Failed to log decision: {errors}" if errors else "Decision successfully logged. You may now respond to the user."
    except Exception as e:
        return f"Error logging decision: {e}"
