"""
Subtask 4: Google ADK Orchestrator with Model Armor Integration.
"""

import functools
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
from subtask5_closed_loop_eval.telemetry import TelemetryService
from subtask4_agent_runtime.mcp_tools import (
    EnterpriseWikiSearchRequest, ITSMTicketRequest, OutcomeRecordRequest,
    execute_wiki_rag_search, execute_create_itsm_ticket, execute_record_outcome
)

class EnterpriseSupportADKAgent:
    def __init__(self, vector_repo, embedder, telemetry_service, project_id, location):
        self.vector_repo = vector_repo
        self.embedder = embedder
        self.telemetry = telemetry_service
        self.project_id = project_id
        self.location = location
        # Fix 5b: Connect via REST using the regional endpoint
        self.model_armor_client = modelarmor_v1.ModelArmorClient(
            transport="rest",
            client_options=ClientOptions(api_endpoint=f"modelarmor.{location}.rep.googleapis.com")
        )

    def _sanitize_with_model_armor(self, prompt: str) -> str:
        """
        Pre-flight security scan blocking prompt injection or jailbreak attempts via Model Armor API.
        """
        template_name = f"projects/{self.project_id}/locations/{self.location}/templates/default-safety-template"
        
        request = modelarmor_v1.SanitizeUserPromptRequest(
            name=template_name,
            user_prompt_data=modelarmor_v1.DataItem(text=prompt)
        )
        
        response = self.model_armor_client.sanitize_user_prompt(request=request)
        
        # Fix 5a: verdict field does not exist, use filter_match_state
        if response.sanitization_result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
            raise PermissionError("Security alert: Prompt violated enterprise safety policy.")
            
        return prompt

    def handle_user_query(self, user_id: str, audience_tier: str, raw_query: str, conversation_id: str = "conv_1029") -> dict:
        """
        Processes multi-turn requests with On-Behalf-Of (OBO) identity propagation.
        """
        clean_query = self._sanitize_with_model_armor(raw_query)

        # 1. Deterministic MCP Tool Execution (RAG Search)
        search_req = EnterpriseWikiSearchRequest(query=clean_query, user_audience_level=audience_tier)
        retrieved_evidence = execute_wiki_rag_search(search_req, self.vector_repo, self.embedder)

        if not retrieved_evidence or retrieved_evidence[0]["similarity"] < 0.65:
            # Automatic fallback: Record coverage gap and create ticket
            execute_record_outcome(OutcomeRecordRequest(
                conversation_id=conversation_id,
                outcome="no_coverage",
                supporting_article_ids=[]
            ), self.telemetry)

            ticket = execute_create_itsm_ticket(ITSMTicketRequest(
                user_id=user_id,
                issue_summary=clean_query,
                target_component="IT-Triage-Queue"
            ))
            return {
                "answer": "I could not locate an approved runbook for this issue. I have escalated this to our team.",
                "ticket": ticket
            }

        # 2. Synthesize answer with context injection
        best_match = retrieved_evidence[0]
        execute_record_outcome(OutcomeRecordRequest(
            conversation_id=conversation_id,
            outcome="confirmed_resolution",
            supporting_article_ids=[best_match["document_id"]]
        ), self.telemetry)

        return {
            "answer": f"Follow these steps:\n{best_match['content']}",
            "citations": [best_match["hierarchy"]]
        }

# ==============================================================================
# ADK Module-Level Agent Definition
# ==============================================================================

PROJECT_ID = os.environ["PROJECT_ID"]
LOCATION = os.environ.get("LOCATION", "us-central1")
_TEMPLATE = f"projects/{PROJECT_ID}/locations/{LOCATION}/templates/default-safety-template"

@functools.cache
def _embedder() -> VertexVectorService:
    return VertexVectorService(PROJECT_ID, LOCATION)

@functools.cache
def _vector_repo() -> VectorStoreRepository:
    return VectorStoreRepository({
        "host": os.environ["DB_HOST"],
        "dbname": os.environ.get("DB_NAME", "knowledge_base"),
        "user": os.environ.get("DB_USER", "app_agent"),
        "password": os.environ["DB_PASSWORD"],
    })

@functools.cache
def _model_armor() -> modelarmor_v1.ModelArmorClient:
    # Fix 5b: Connect via REST using the regional endpoint for ADK callbacks
    return modelarmor_v1.ModelArmorClient(
        transport="rest",
        client_options=ClientOptions(api_endpoint=f"modelarmor.{LOCATION}.rep.googleapis.com"),
    )

@functools.cache
def _telemetry() -> TelemetryService:
    return TelemetryService(PROJECT_ID, os.environ["TELEMETRY_TOPIC"])

def search_knowledge_base(query: str, audience: str) -> list[dict]:
    """Searches approved runbooks that the caller's audience is allowed to see."""
    return execute_wiki_rag_search(
        EnterpriseWikiSearchRequest(query=query, user_audience_level=audience),
        _vector_repo(), _embedder()
    )

def create_itsm_ticket(user_id: str, issue_summary: str) -> dict:
    """Escalates an issue to the IT triage queue when no runbook applies."""
    return execute_create_itsm_ticket(
        ITSMTicketRequest(user_id=user_id, issue_summary=issue_summary, target_component="IT-Triage-Queue")
    )

def record_outcome(conversation_id: str, outcome: str, article_ids: list[str]) -> dict:
    """Records the outcome of a conversational turn for telemetry and analytics."""
    return execute_record_outcome(
        OutcomeRecordRequest(
            conversation_id=conversation_id,
            outcome=outcome,
            supporting_article_ids=article_ids
        ),
        _telemetry()
    )

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
        
    response = _model_armor().sanitize_user_prompt(
        request=modelarmor_v1.SanitizeUserPromptRequest(
            name=_TEMPLATE,
            user_prompt_data=modelarmor_v1.DataItem(text=user_text)
        )
    )
    
    # Fix 5a: verdict field does not exist, use filter_match_state
    if response.sanitization_result.filter_match_state == modelarmor_v1.FilterMatchState.MATCH_FOUND:
        # Returning a response skips the model call.
        return LlmResponse(content=types.Content(
            role="model", 
            parts=[types.Part(text="This request violates the enterprise safety policy.")]
        ))
        
    return None

root_agent = Agent(
    name="enterprise_support_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Answer only from search_knowledge_base results and cite the heading. "
        "If no result has similarity >= 0.65, call create_itsm_ticket. "
        "Always call record_outcome after providing a final answer to log the result."
    ),
    tools=[search_knowledge_base, create_itsm_ticket, record_outcome],
    before_model_callback=screen_prompt_with_model_armor,
)
