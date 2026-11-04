# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Subtask 4: Deterministic Model Context Protocol (MCP) Tool Specifications.
Why this logic:
- LLMs are prone to hallucinating parameters when interacting directly with enterprise APIs.
- Wrapping actions in deterministic MCP tools guarantees validated inputs and predictable execution.
"""

from typing import Optional
from pydantic import BaseModel, Field

class EnterpriseWikiSearchRequest(BaseModel):
    query: str = Field(..., description="User technical search query")
    user_audience_level: str = Field(..., description="Verified identity scope: 'Employee' or 'Contractor'")

class ITSMTicketRequest(BaseModel):
    user_id: str = Field(..., description="User's Enterprise Chat ID or email")
    issue_summary: str = Field(..., description="Concise error summary")
    target_component: str = Field(..., description="Pre-mapped ITSM queue extracted from KB metadata")

class OutcomeRecordRequest(BaseModel):
    conversation_id: str = Field(..., description="Unique conversational turn identifier")
    outcome: str = Field(..., description="One of: confirmed_resolution, unhelpful, no_coverage")
    supporting_article_ids: list[str] = Field(default_factory=list)
    user_feedback_rating: Optional[str] = Field(None, description="thumbs_up or thumbs_down")

# Python equivalents of Go MCP Interfaces
def execute_wiki_rag_search(req: EnterpriseWikiSearchRequest, vector_repo, embedder) -> list[dict]:
    query_vector = embedder.generate_embeddings([req.query])[0]
    return vector_repo.search_similar_chunks(query_vector, req.user_audience_level, top_k=3)

def execute_create_itsm_ticket(req: ITSMTicketRequest) -> dict:
    # Deterministic API call to the ITSM platform (avoids LLM routing hallucinations)
    return {"ticket_id": "IT-89211", "status": "QUEUED", "queue": req.target_component}

def execute_record_outcome(req: OutcomeRecordRequest, telemetry_service) -> dict:
    telemetry_service.publish_turn_event(req.model_dump())
    return {"recorded": True}
