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
Subtask 1: Event-Driven Ingestion & Frontmatter Governance Validation.
Why this logic:
- Replaces legacy multi-hour Enterprise Wiki scrapers with an instant HTTP/CloudEvent webhook.
- Guarantees data governance by blocking unverified or unclassified documentation at the threshold.
- Eliminates renderer crashes by rejecting complex proprietary macros before chunking.
"""

import os
import yaml
import re
import requests
import google.auth.transport.requests
import google.oauth2.id_token
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Subtask 1: Ingestion & Governance Validator")

# Permitted audience boundaries for Role-Level Access Control (RLAC)
VALID_AUDIENCES = {"All-Employees", "Engineering-Only", "Contractors", "IT-Support"}
CHUNKER_URL = os.environ.get("CHUNKER_URL", "")

class DocumentPayload(BaseModel):
    document_id: str = Field(..., description="Unique article ID")
    title: str = Field(default="Untitled", description="Document title")
    source_url: str = Field(default="", description="Source URL")
    raw_markdown: str = Field(..., description="Raw Markdown with YAML frontmatter")

def parse_and_validate_frontmatter(content: str) -> tuple[dict, str]:
    """
    Extracts and audits frontmatter metadata.
    Enforces the 'Agent-Ready' governance standard.
    """
    pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        raise ValueError("Document missing mandatory YAML frontmatter block.")
    
    raw_yaml, body = match.group(1), match.group(2)
    meta = yaml.safe_load(raw_yaml)
    
    if not isinstance(meta, dict):
        raise ValueError("YAML frontmatter must be a valid dictionary mapping.")
    
    # 1. Enforce Target_Audience for RLAC
    audience = meta.get("Target_Audience")
    if not audience or audience not in VALID_AUDIENCES:
        raise ValueError(f"Invalid or missing Target_Audience. Must be one of: {VALID_AUDIENCES}")
    
    # 2. Enforce Content Freshness (Staleness cutoff)
    verified_str = meta.get("Last_Verified_Date")
    if not verified_str:
        raise ValueError("Missing Last_Verified_Date frontmatter.")
        
    try:
        verified_date = datetime.strptime(str(verified_str), "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format for Last_Verified_Date (YYYY-MM-DD required): {e}")
        
    # Drop documents untouched for more than 18 months
    if (date.today() - verified_date).days > 540:
        raise ValueError(f"Document expired. Last verified on {verified_date}. Re-verification required.")
    
    # 3. Lint against prohibited macros that break RAG parsing
    prohibited_tags = ["{expand}", "{include}", "<ac:structured-macro"]
    for tag in prohibited_tags:
        if tag in body:
            raise ValueError(f"Found prohibited macro '{tag}'. Document must be clean Markdown.")
    
    return meta, body

def forward_to_chunker(payload: dict) -> dict:
    if not CHUNKER_URL:
        raise ValueError("CHUNKER_URL environment variable is not set.")
    token = google.oauth2.id_token.fetch_id_token(
        google.auth.transport.requests.Request(), CHUNKER_URL)
    resp = requests.post(f"{CHUNKER_URL}/api/v1/process", json=payload,
                         headers={"Authorization": f"Bearer {token}"}, timeout=30)
    resp.raise_for_status()
    return resp.json()

@app.post("/api/v1/ingest", status_code=status.HTTP_200_OK)
async def ingest_document(payload: DocumentPayload):
    try:
        metadata, clean_body = parse_and_validate_frontmatter(payload.raw_markdown)
        
        # TODO(production): For production, connect over Private Service Connect instead of a public endpoint.
        # Forwarding payload to Subtask 2 worker pool:
        # Confirm internal gRPC service mesh routing or 
        # Serverless VPC connector configuration for direct Cloud Run-to-Cloud Run calls.
        
        process_payload = {
            "document_id": payload.document_id,
            "title": payload.title,
            "source_url": payload.source_url,
            "target_audience": metadata.get("Target_Audience", "All-Employees"),
            "content_owner": metadata.get("Content_Owner", "Unknown"),
            "last_verified_date": str(metadata.get("Last_Verified_Date", "")),
            "body": clean_body
        }
        
        chunker_resp = forward_to_chunker(process_payload)
        
        return {
            "status": "VALIDATED_AND_CHUNKED",
            "document_id": payload.document_id,
            "metadata": metadata,
            "chunker_response": chunker_resp
        }
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err))
