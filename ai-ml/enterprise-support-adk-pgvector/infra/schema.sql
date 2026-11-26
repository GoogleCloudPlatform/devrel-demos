-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     https://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- Enable the vector extension for low-latency similarity search
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS google_ml_integration CASCADE;

-- Document master table preserving auditability and ownership
CREATE TABLE IF NOT EXISTS kb_documents (
    document_id VARCHAR(64) PRIMARY KEY,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    target_audience VARCHAR(64) NOT NULL, -- ACL boundary: 'All-Employees', 'Contractors', 'Engineering'
    content_owner VARCHAR(128) NOT NULL,  -- Enterprise Chat handle or team LDAP
    last_verified_date DATE NOT NULL,     -- Enforces freshness; used to filter obsolete SOPs
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Chunk storage table: Decouples document metadata from high-density embedding vectors
CREATE TABLE IF NOT EXISTS kb_chunks (
    chunk_id VARCHAR(64) PRIMARY KEY,
    document_id VARCHAR(64) REFERENCES kb_documents(document_id) ON DELETE CASCADE,
    heading_hierarchy TEXT NOT NULL,       -- Injected breadcrumbs: e.g. "[App: ZTNA] > [OS: Desktop]"
    chunk_content TEXT NOT NULL,          -- Markdown body strictly bounded by AST headings
    embedding vector(768) NOT NULL,       -- Sized for Vertex AI text-embedding-005
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Hierarchical Navigable Small World (HNSW) index for sub-10ms approximate nearest neighbor queries.
-- We use m=16, ef_construction=64 to prioritize high recall and low update overhead during writes.
CREATE INDEX IF NOT EXISTS idx_kb_chunks_hnsw 
ON kb_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Register the Vertex AI embedding model so Postgres can generate embeddings natively.
-- Auth uses the Cloud SQL service account, which needs roles/aiplatform.user (see main.tf).
-- Note: create_model is not idempotent; skip this statement when re-running the schema.
CALL google_ml.create_model(
    model_id => 'text-embedding-005',
    model_provider => 'google',
    model_qualified_name => 'text-embedding-005',
    model_type => 'text_embedding',
    model_auth_type => 'cloudsql_service_agent_iam');
