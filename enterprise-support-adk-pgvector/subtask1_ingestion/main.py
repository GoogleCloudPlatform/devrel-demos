"""
Subtask 1: Event-Driven Ingestion & Frontmatter Governance Validation.
Why this logic:
- Replaces legacy multi-hour Enterprise Wiki scrapers with an instant HTTP/CloudEvent webhook.
- Guarantees data governance by blocking unverified or unclassified documentation at the threshold.
- Eliminates renderer crashes by rejecting complex proprietary macros before chunking.
"""

import sys
import yaml
import re
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

app = FastAPI(title="Subtask 1: Ingestion & Governance Validator")

# Permitted audience boundaries for Role-Level Access Control (RLAC)
VALID_AUDIENCES = {"All-Employees", "Engineering-Only", "Contractors", "IT-Support"}

class DocumentPayload(BaseModel):
    document_id: str = Field(..., description="Unique article ID")
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
        # Drop documents untouched for more than 18 months
        if (date.today() - verified_date).days > 540:
            raise ValueError(f"Document expired. Last verified on {verified_date}. Re-verification required.")
    except ValueError as e:
        raise ValueError(f"Invalid date format for Last_Verified_Date (YYYY-MM-DD required): {e}")
    
    # 3. Lint against prohibited macros that break RAG parsing
    prohibited_tags = ["{expand}", "{include}", "<ac:structured-macro"]
    for tag in prohibited_tags:
        if tag in body:
            raise ValueError(f"Found prohibited macro '{tag}'. Document must be clean Markdown.")
    
    return meta, body

@app.post("/api/v1/ingest", status_code=status.HTTP_200_OK)
async def ingest_document(payload: DocumentPayload):
    try:
        metadata, clean_body = parse_and_validate_frontmatter(payload.raw_markdown)
        
        # TODO(production): For production, connect over Private Service Connect instead of a public endpoint.
        # Forwarding payload to Subtask 2 worker pool:
        # Confirm internal gRPC service mesh routing or 
        # Serverless VPC connector configuration for direct Cloud Run-to-Cloud Run calls.
        
        return {
            "status": "VALIDATED",
            "document_id": payload.document_id,
            "metadata": metadata,
            "body_length_chars": len(clean_body),
            "next_step": "HANDOFF_TO_SUBTASK_2_AST_CHUNKER"
        }
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err))
