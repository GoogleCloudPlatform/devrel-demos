"""
Subtask 4: Google ADK Orchestrator with Model Armor Integration.
"""

from google.cloud import modelarmor_v1
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
        self.model_armor_client = modelarmor_v1.ModelArmorClient()

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
        
        if response.sanitization_result.verdict == modelarmor_v1.SanitizationResult.Verdict.BLOCK:
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
                conversation_id="conversation_id",
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
            conversation_id="conversation_id",
            outcome="confirmed_resolution",
            supporting_article_ids=[best_match["document_id"]]
        ), self.telemetry)

        return {
            "answer": f"Follow these steps:\n{best_match['content']}",
            "citations": [best_match["hierarchy"]]
        }
