-- Enable the vector extension for low-latency similarity search
CREATE EXTENSION IF NOT EXISTS vector;

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
    target_audience VARCHAR(64) NOT NULL, -- Denormalized for zero-join RLAC filtering
    embedding vector(768) NOT NULL,       -- Sized for Vertex AI text-embedding-005
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Hierarchical Navigable Small World (HNSW) index for sub-10ms approximate nearest neighbor queries.
-- We use m=16, ef_construction=64 to prioritize high recall and low update overhead during writes.
CREATE INDEX IF NOT EXISTS idx_kb_chunks_hnsw 
ON kb_chunks 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- Index for deterministic Role-Level Access Control (RLAC) pre-filtering
CREATE INDEX IF NOT EXISTS idx_kb_chunks_audience 
ON kb_chunks (target_audience);
