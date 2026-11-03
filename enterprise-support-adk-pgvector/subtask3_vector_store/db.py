"""
Subtask 3: Low-Latency Persistence & Real-Time HNSW Vector Search.
Why this logic:
- Directly writes vector embeddings to PostgreSQL with ACID safety.
- Changes are searchable within milliseconds, eliminating multi-hour batch indexing delays.
- Enforces Role-Level Access Control (RLAC) inside the SQL WHERE clause.
"""

import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector

class VectorStoreRepository:
    def __init__(self, db_config: dict):
        # =========================================================================
        # NETWORKING PLACEHOLDER (Review with Deepak Michael)
        # =========================================================================
        # Connection string to use Cloud SQL Private IP / PSC Endpoint.
        # Deepak Michael to review whether Cloud SQL Auth Proxy sidecar or native direct private IP
        # is preferred in our GKE/Cloud Run environment.
        self.conn = psycopg2.connect(**db_config)
        register_vector(self.conn)

    def write_document_and_chunks(self, doc_meta: dict, chunks: list[dict], embeddings: list[list[float]]):
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

            # 2. Insert semantic chunks with HNSW vector indexing
            chunk_records = []
            for i, chunk in enumerate(chunks):
                chunk_records.append((
                    f"{doc_meta['document_id']}_chunk_{i}",
                    doc_meta["document_id"],
                    chunk["hierarchy"],
                    chunk["content"],
                    doc_meta["target_audience"],
                    embeddings[i]
                ))

            execute_values(cur, """
                INSERT INTO kb_chunks (chunk_id, document_id, heading_hierarchy, chunk_content, target_audience, embedding)
                VALUES %s
                ON CONFLICT (chunk_id) DO UPDATE 
                SET chunk_content = EXCLUDED.chunk_content,
                    embedding = EXCLUDED.embedding;
            """, chunk_records)

            self.conn.commit()

    def search_similar_chunks(self, query_embedding: list[float], user_audience: str, top_k: int = 3) -> list[dict]:
        """
        Queries top_k chunks using cosine distance (<=>).
        Pre-filters strictly by the caller's target_audience (RLAC).
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    chunk_id, 
                    document_id, 
                    heading_hierarchy, 
                    chunk_content,
                    1 - (embedding <=> %s::vector) AS cosine_similarity
                FROM kb_chunks
                WHERE target_audience = %s OR target_audience = 'All-Employees'
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
            """, (query_embedding, user_audience, query_embedding, top_k))
            
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
