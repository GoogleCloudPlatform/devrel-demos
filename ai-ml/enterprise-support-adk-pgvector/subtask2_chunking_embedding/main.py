# Copyright 2024 Google LLC
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
Subtask 2 & 3: FastAPI HTTP Handler
Receives the validated document from Subtask 1, chunks it, embeds it, and saves it to the database.
"""

import os
import functools
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

@functools.cache
def _embedder() -> VertexVectorService:
    return VertexVectorService(os.environ["PROJECT_ID"], os.environ.get("LOCATION", "us-central1"))

@functools.cache
def _db() -> VectorStoreRepository:
    return VectorStoreRepository({
        "host": os.environ["DB_HOST"],
        "dbname": os.environ.get("DB_NAME", "knowledge_base"),
        "user": os.environ.get("DB_USER", "app_agent"),
        "password": os.environ["DB_PASSWORD"],
    })

@app.post("/api/v1/process", status_code=status.HTTP_200_OK)
def process_document(req: ProcessDocumentRequest):
    try:
        chunker = HeadingAwareChunker()
        embedder = _embedder()
        db = _db()

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
