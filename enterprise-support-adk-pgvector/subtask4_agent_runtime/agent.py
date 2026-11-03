"""
Subtask 4: Google ADK Orchestrator with Model Armor Integration.
"""

# ── 1. Imports (top of file) ────────────────────────────────────────────────
import os
from typing import Optional

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.api_core.client_options import ClientOptions
from google.cloud import modelarmor_v1
from google.genai import types

from subtask2_chunking_embedding.embedder import VertexVectorService
from subtask3_vector_store.db import VectorStoreRepository
from subtask4_agent_runtime.mcp_tools import (
    EnterpriseWikiSearchRequest, ITSMTicketRequest, OutcomeRecordRequest,
    execute_wiki_rag_search, execute_create_itsm_ticket, execute_record_outcome
)


# ── 2. Your existing class (unchanged except the item 2 and 5 fixes) ──────────
class EnterpriseSupportADKAgent:
    ...  # __init__, _sanitize_with_model_armor, handle_user_query as you have them


# ── 3. NEW: module-level ADK agent (bottom of file, no indentation) ─────────
PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ.get("LOCATION", "us-central1")

_embedder = VertexVectorService(PROJECT_ID, LOCATION)
_vector_repo = VectorStoreRepository({
    "host": os.environ["DB_HOST"],
    "dbname": os.environ.get("DB_NAME", "knowledge_base"),
    "user": os.environ.get("DB_USER", "app_agent"),
    "password": os.environ["DB_PASSWORD"],
})
_model_armor = modelarmor_v1.ModelArmorClient(
    transport="rest",
    client_options=ClientOptions(api_endpoint=f"modelarmor.{LOCATION}.rep.googleapis.com"),
)
_TEMPLATE = f"projects/{PROJECT_ID}/locations/{LOCATION}/templates/default-safety-template"


def search_knowledge_base(query: str, audience: str) -> list[dict]:
    """Searches approved runbooks that the caller's audience is allowed to see."""
    return execute_wiki_rag_search(
        EnterpriseWikiSearchRequest(query=query, user_audience_level=audience),
        _vector_repo, _embedder)


def create_itsm_ticket(user_id: str, issue_summary: str) -> dict:
    """Escalates an issue to the IT triage queue when no runbook applies."""
    return execute_create_itsm_ticket(
        ITSMTicketRequest(user_id=user_id, issue_summary=issue_summary,
                          target_component="IT-Triage-Queue"))


def screen_prompt_with_model_armor(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Blocks the model call if Model Armor flags the latest user message."""
    user_text = ""
    for content in reversed(llm_request.contents or []):
        if content.role == "user" and content.parts:
            user_text = "".join(p.text or "" for p in content.parts)
            break
    if not user_text:
        return None

    response = _model_armor.sanitize_user_prompt(
        request=modelarmor_v1.SanitizeUserPromptRequest(
            name=_TEMPLATE, user_prompt_data=modelarmor_v1.DataItem(text=user_text)))
    if (response.sanitization_result.filter_match_state
            == modelarmor_v1.FilterMatchState.MATCH_FOUND):
        # Returning a response skips the model call entirely.
        return LlmResponse(content=types.Content(
            role="model",
            parts=[types.Part(text="This request violates the enterprise safety policy.")]))
    return None  # None lets the request continue to Gemini.


root_agent = Agent(
    name="enterprise_support_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Answer only from search_knowledge_base results and cite the heading. "
        "If no result has similarity >= 0.65, call create_itsm_ticket."
    ),
    tools=[search_knowledge_base, create_itsm_ticket],
    before_model_callback=screen_prompt_with_model_armor,
)
