"""
Subtask 2 & 3: FastAPI HTTP Handler
Receives the validated document from Subtask 1, chunks it, embeds it, and saves it to the database.
"""

import os
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from subtask2_chunking_embedding.ast_chunker import HeadingAwareChunker
from subtask2_chunking_embedding.embedder import VertexVectorService
from subtask3_vector_store.db import VectorStoreRepository

app = FastAPI(title="Subtask 2: Chunker and Embedder Service")

class ProcessDocumentRequest(BaseModel):
    document_id: str
    title: str
    source_url: str
    target_audience: str
    content_owner: str
    last_verified_date: str
    body: str

@app.post("/api/v1/process", status_code=status.HTTP_200_OK)
def process_document(req: ProcessDocumentRequest):
    try:
        # Initialize services
        project_id = os.environ["PROJECT_ID"]
        location = os.environ.get("LOCATION", "us-central1")
        
        chunker = HeadingAwareChunker()
        embedder = VertexVectorService(project_id, location)
        db = VectorStoreRepository({
            "host": os.environ["DB_HOST"],
            "dbname": os.environ.get("DB_NAME", "knowledge_base"),
            "user": os.environ.get("DB_USER", "app_agent"),
            "password": os.environ["DB_PASSWORD"],
        })

        # 1. Chunk the document
        chunks = chunker.chunk_document(req.title, req.body)
        if not chunks:
            return {"status": "SKIPPED", "reason": "No chunks generated."}

        # 2. Generate embeddings
        chunk_texts = [c["content"] for c in chunks]
        embeddings = embedder.generate_embeddings(chunk_texts)

        # 3. Write securely to pgvector
        doc_meta = {
            "document_id": req.document_id,
            "title": req.title,
            "source_url": req.source_url,
            "target_audience": req.target_audience,
            "content_owner": req.content_owner,
            "last_verified_date": req.last_verified_date
        }
        db.write_document_and_chunks(doc_meta, chunks, embeddings)

        return {"status": "SUCCESS", "chunks_processed": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
