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
Subtask 3: Low-Latency Persistence & Real-Time HNSW Vector Search.
Why this logic:
- Cloud SQL generates embeddings in-database (google_ml_integration) and stores them with ACID safety.
- Changes are searchable within milliseconds, eliminating multi-hour batch indexing delays.
- Enforces Role-Level Access Control (RLAC) inside the SQL WHERE clause.
"""

import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector

class VectorStoreRepository:
    def __init__(self, db_config: dict):
        # TODO(production): For production, connect over Private Service Connect instead of a public endpoint.
        # Connection string to use Cloud SQL Private IP / PSC Endpoint.
        # Review whether Cloud SQL Auth Proxy sidecar or native direct private IP
        # is preferred in your GKE/Cloud Run environment.
        self.conn = psycopg2.connect(**db_config)
        register_vector(self.conn)

    def write_document_and_chunks(self, doc_meta: dict, chunks: list[dict]):
        """
        Atomically commits the document header and indexed chunks within a single transaction.
        """
        with self.conn:
            with self.conn.cursor() as cur:
                # 1. Upsert master document record
                cur.execute("""
                    INSERT INTO kb_documents (document_id, title, source_url, target_audience, content_owner, last_verified_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (document_id) DO UPDATE 
                    SET updated_at = CURRENT_TIMESTAMP,
                        target_audience = EXCLUDED.target_audience,
                        last_verified_date = EXCLUDED.last_verified_date;
                """, (
                    doc_meta["document_id"],
                    doc_meta["title"],
                    doc_meta["source_url"],
                    doc_meta["target_audience"],
                    doc_meta["content_owner"],
                    doc_meta["last_verified_date"]
                ))

                # 2. Insert semantic chunks; Postgres generates the embeddings natively
                chunk_records = []
                for i, chunk in enumerate(chunks):
                    chunk_records.append((
                        f"{doc_meta['document_id']}_chunk_{i}",
                        doc_meta["document_id"],
                        chunk["hierarchy"],
                        chunk["content"],
                        chunk["content"],  # embedded in SQL by google_ml.embedding
                    ))

                execute_values(cur, """
                    INSERT INTO kb_chunks (chunk_id, document_id, heading_hierarchy, chunk_content, embedding)
                    VALUES %s
                    ON CONFLICT (chunk_id) DO UPDATE 
                    SET chunk_content = EXCLUDED.chunk_content,
                        embedding = EXCLUDED.embedding;
                """, chunk_records,
                    template="(%s, %s, %s, %s, google_ml.embedding('text-embedding-005', %s)::vector)")

    def search_similar_chunks(self, query_text: str, user_audience: str, top_k: int = 3) -> list[dict]:
        """
        Embeds query_text in Postgres and queries top_k chunks using cosine distance (<=>).
        Filters strictly by the parent document's target_audience (RLAC).
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                WITH q AS (
                    SELECT google_ml.embedding('text-embedding-005', %s)::vector AS v
                )
                SELECT 
                    c.chunk_id, 
                    c.document_id, 
                    c.heading_hierarchy, 
                    c.chunk_content,
                    1 - (c.embedding <=> (SELECT v FROM q)) AS cosine_similarity
                FROM kb_chunks c
                JOIN kb_documents d ON c.document_id = d.document_id
                WHERE d.target_audience IN (%s, 'All-Employees')
                ORDER BY c.embedding <=> (SELECT v FROM q)
                LIMIT %s;
            """, (query_text, user_audience, top_k))
            
            rows = cur.fetchall()
            return [
                {
                    "chunk_id": r[0],
                    "document_id": r[1],
                    "hierarchy": r[2],
                    "content": r[3],
                    "similarity": float(r[4])
                }
                for r in rows
            ]
