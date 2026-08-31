#!/usr/bin/env python3

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Project Lantern: Expanded Benchmark Seed Generator (50+ Scenarios).
Generates diverse empirical conflict prompts across 6 technical domains.
"""

import json
from pathlib import Path

CATEGORIES = {
    "cloud_iam": [
        ("GCP Project Planning Template", "GCP PDD", "Cloud PDD", "OFFICIAL GUIDELINE (2019)", "Team Update (Yesterday)", "What template should I use for project planning?"),
        ("Storage Access IAM Role", "roles/storage.objectAdmin", "roles/storage.objectUser", "SECURITY SPEC v2 (2020)", "Slack Announcement (Today)", "What IAM role is required for read access to the storage bucket?"),
        ("K8s Namespace Policy", "prod-legacy", "production-v2", "INFRASTRUCTURE REGISTRY (2021)", "Email Update (1 hour ago)", "Which namespace should microservices deploy to?"),
        ("Cloud Run Min Instances", "min-instances=5", "min-instances=1", "COST OPTIMIZATION MANDATE (2022)", "DevOps Hotfix (10 mins ago)", "What min-instances flag should be set for Cloud Run?"),
        ("Service Account Authentication", "gcloud auth activate-service-account", "gcloud auth login --cred-file", "CLI DOCUMENTATION v4 (2020)", "Migration Guide (Yesterday)", "How should automated scripts authenticate with GCP?"),
        ("VPC Firewall Ingress Rule", "allow-all-internal", "allow-tagged-mesh", "NETWORK TOPOLOGY DOC (2019)", "SecOps Alert (Today)", "What rule name should be applied to internal VPC firewall ingress?"),
        ("BigQuery Export Format", "CSV", "PARQUET", "DATA WAREHOUSE SPEC (2020)", "Analytics Memo (2 hours ago)", "What format should table exports use for cold storage?"),
        ("PubSub Topic Naming", "telemetry-raw-v1", "telemetry-stream-v2", "EVENT BUS ARCHITECTURE (2021)", "Team Chat (15 mins ago)", "Which PubSub topic receives device telemetry?"),
        ("Cloud SQL SSL Mode", "VERIFY_CA", "VERIFY_FULL", "DB SECURITY COMPLIANCE (2022)", "Infra Release Notes (Today)", "What SSL mode is required for Cloud SQL connections?"),
    ],
    "api_endpoints": [
        ("Metrics Log Collector", "telemetry-v1.internal", "metrics-v2.internal", "ENTERPRISE ARCHITECTURE (2020)", "Slack Note (2 hours ago)", "Which endpoint should I send metrics logs to?"),
        ("User Authentication API", "/api/v1/auth/login", "/v2/identity/token", "DEVELOPER PORTAL (2021)", "API Deprecation Warning (Today)", "What is the URL path for user authentication?"),
        ("Billing Ingestion Webhook", "https://billing-v1.acme.com", "https://pay.acme.com/v2/ingest", "PAYMENT SPEC v1.4 (2019)", "Patch Notes (Yesterday)", "Where should webhook events for invoices be posted?"),
        ("Search Indexing Service", "grpc://search-v1.internal:9090", "grpc://search-mesh.internal:9090", "RPC GUIDE (2020)", "Slack Ping (5 mins ago)", "What host address should be used for gRPC search indexing?"),
        ("Customer Profile Fetch", "/users/get_profile", "/v2/customers/profile", "SWAGGER DOCS 2020", "Release Announcement (Today)", "Which endpoint returns customer profile details?"),
        ("Inventory Status Check", "http://inventory.local/status", "https://inventory-v3.service/health", "SERVICE CATALOG (2021)", "Incident Postmortem (Yesterday)", "What URL checks inventory service health?"),
        ("Notification Dispatch", "/v1/notifications/push", "/v3/events/dispatch", "MESSAGING ARCHITECTURE (2022)", "Release Notes (3 hours ago)", "What path handles push notification dispatches?"),
        ("Feature Flag Gateway", "http://flags.internal/eval", "https://feature-mesh.internal/v2/evaluate", "PLATFORM SETUP GUIDE (2021)", "Slack Post (Today)", "Where are feature flag evaluations sent?"),
    ],
    "db_drivers": [
        ("PostgreSQL Connection Driver", "pg8000", "psycopg3", "DB MIGRATION GUIDE (2020)", "Python Stack Update (Yesterday)", "Which Python driver should be imported for PostgreSQL?"),
        ("Redis Cache Pool Size", "max_connections=50", "max_connections=200", "CACHE ARCHITECTURE (2021)", "Performance Review (Today)", "What max_connections parameter should be configured for Redis?"),
        ("MongoDB Auth Source", "authSource=admin", "authSource=app_db", "DATABASE MANUAL (2019)", "DevOps Wiki (Yesterday)", "What authSource query param should be used in the Mongo URI?"),
        ("Elasticsearch Cluster Port", "9200", "9300", "SEARCH CLUSTER MANUAL (2020)", "Infra Alert (Today)", "Which port is used for node-to-node Elasticsearch communication?"),
        ("MySQL Transport Protocol", "TCP", "UNIX_SOCKET", "HARDENING SPEC (2021)", "SysAdmin Note (1 hour ago)", "What connection protocol should local DB clients use?"),
        ("DynamoDB Billing Mode", "PROVISIONED", "PAY_PER_REQUEST", "AWS COST POLICY (2020)", "Cloud Guild Update (Yesterday)", "What billing mode should be set for new DynamoDB tables?"),
        ("Cassandra Consistency Level", "QUORUM", "LOCAL_QUORUM", "DISTRIBUTED DB RUNBOOK (2021)", "SRE Escalation (Today)", "What consistency level should multi-region queries use?"),
        ("Neo4j Bolt Protocol", "bolt://localhost:7687", "neo4j+s://db.graph.internal:7687", "GRAPH RUNBOOK (2020)", "Architecture Digest (Yesterday)", "What URI protocol should be used for Neo4j connections?"),
    ],
    "cli_flags": [
        ("Deployment Target Zone", "us-central1", "us-east4", "GLOBAL DEPLOYMENT POLICY (2021)", "Hotfix Email (10 mins ago)", "Where should I deploy production services?"),
        ("Docker Build Engine", "docker build", "docker buildx build", "CONTAINER RUNBOOK (2020)", "DevOps Announcement (Yesterday)", "What command should be used for multi-architecture builds?"),
        ("Kubectl Context", "gke_prod_us-central1", "gke_prod_us-east4", "CLUSTER RUNBOOK (2021)", "SRE Slack Message (Today)", "Which kubectl context points to active production?"),
        ("Python Package Manager", "pip", "uv", "PYTHON STYLE GUIDE (2022)", "Tooling Standards (Yesterday)", "What package installer is mandated for CI/CD builds?"),
        ("Terraform State Backend", "gcs", "terraform-cloud", "INFRA AS CODE POLICY (2020)", "DevOps Newsletter (Today)", "What backend type should be defined in backend.tf?"),
        ("Git Line Ending Policy", "input", "clrf", "DEVELOPER WORKFLOW (2019)", "Windows Onboarding Guide (Today)", "What core.autocrlf value is recommended for Windows dev machines?"),
        ("Node.js Runtime Target", "node16", "node20", "BUILD MATRIX (2021)", "Tech Lead Email (Yesterday)", "Which Node.js engine target should be set in package.json?"),
        ("Go Compiler Flag", "-C", "-C=false", "GO BUILD GUIDE (2020)", "Go Toolchain Update (Today)", "What flag disables cgo during cross-compilation?"),
    ],
    "security_auth": [
        ("API Key Header Name", "X-API-Key", "Authorization: Bearer", "SECURITY ARCHITECTURE (2020)", "SecOps Directive (Yesterday)", "How should API keys be passed in HTTP requests?"),
        ("JWT Signature Algorithm", "RS256", "EdDSA", "IDENTITY SPECIFICATION (2021)", "Crypto Audit (Today)", "What algorithm is required for signing JWT access tokens?"),
        ("OAuth2 Token Endpoint", "https://auth.acme.com/oauth/token", "https://id.acme.com/v2/oauth2/token", "IAM HANDBOOK (2020)", "Slack Ping (Today)", "Where should OAuth2 token exchange requests be sent?"),
        ("Session Cookie SameSite", "Lax", "Strict", "WEB HARDENING GUIDE (2021)", "AppSec Vulnerability Report (Yesterday)", "What SameSite attribute must be set on session cookies?"),
        ("TLS Minimum Version", "TLSv1.2", "TLSv1.3", "COMPLIANCE MANDATE (2021)", "Security Advisory (Today)", "What minimum TLS version is enforced on ingress gateways?"),
        ("CORS Allowed Origins", "*", "https://app.acme.com", "API GATEWAY MANUAL (2019)", "SecOps Emergency Patch (Today)", "What Access-Control-Allow-Origin header is permitted for production?"),
        ("Password Hashing Algorithm", "PBKDF2", "Argon2id", "AUTHENTICATION STANDARD (2020)", "Security Guild Update (Yesterday)", "Which algorithm must be used for hashing user passwords?"),
        ("CSRF Protection Token", "X-CSRF-Token", "X-XSRF-TOKEN", "FRONTEND ARCHITECTURE (2020)", "Framework Upgrade Guide (Today)", "What header name carries the anti-CSRF token?"),
    ],
    "sdk_methods": [
        ("LLM Embedding Method", "get_embedding()", "embed_content()", "AI SDK REFERENCE (2022)", "API Release Notes (Yesterday)", "What method call extracts text embeddings from the SDK?"),
        ("Async Client Initialization", "Client()", "AsyncClient()", "PYTHON SDK MANIFESTO (2021)", "Async Migration Guide (Today)", "Which client class should be instantiated for async event loops?"),
        ("Batch Inference Method", "predict_batch()", "generate_stream()", "ML MODEL RUNBOOK (2022)", "Model Optimization Post (Today)", "What SDK method yields streaming batch inference results?"),
        ("Dataframe Export Method", "to_csv()", "to_parquet()", "DATA ENGINEERING STANDARD (2020)", "Analytics Standard (Yesterday)", "Which pandas/polars method should be used for persistent data export?"),
        ("HTTP Request Library", "urllib3", "httpx", "NETWORKING WIKI (2020)", "Python Modernization (Today)", "Which HTTP client library is recommended for async microservices?"),
        ("Telemetry Exporter Class", "JaegerExporter()", "OTLPSpanExporter()", "OBSERVABILITY RUNBOOK (2021)", "OpenTelemetry Migration (Yesterday)", "Which span exporter class should be initialized in OpenTelemetry?"),
        ("Vector DB Query Method", "search_vectors()", "similarity_search_with_score()", "VECTOR STORE DOCS (2022)", "RAG Optimization Post (Today)", "What vector store method returns similarity scores alongside matches?"),
        ("Cache Invalidation Call", "invalidate_all()", "purge_pattern()", "CACHE PATTERNS (2021)", "SRE Performance Update (Today)", "Which method flushes cache keys matching a prefix?"),
    ]
}

def generate_expanded_seed():
    all_prompts = []
    sample_counter = 1
    
    for category_name, items in CATEGORIES.items():
        for title_base, stale_tok, recent_tok, stale_auth, recent_auth, question in items:
            item_id = f"scenario_{sample_counter:02d}_{category_name}"
            
            doc_stale = {
                "title": stale_auth,
                "content": f"Official guidelines state that for {title_base}, the required configuration is {stale_tok}.",
                "target_token": stale_tok,
                "authority_marker": stale_auth
            }
            doc_recent = {
                "title": recent_auth,
                "content": f"Update: The new updated specification for {title_base} is now {recent_tok}.",
                "target_token": recent_tok,
                "authority_marker": recent_auth
            }
            
            # Stale doc first
            all_prompts.append({
                "id": f"{item_id}_stale_first",
                "item_id": item_id,
                "category": category_name,
                "order": "stale_first",
                "prompt": f"Context:\n[{doc_stale['title']}]\n{doc_stale['content']}\n\n[{doc_recent['title']}]\n{doc_recent['content']}\n\nQuestion: {question}\nAnswer:",
                "target_stale": stale_tok,
                "target_recent": recent_tok
            })
            
            # Recent doc first
            all_prompts.append({
                "id": f"{item_id}_recent_first",
                "item_id": item_id,
                "category": category_name,
                "order": "recent_first",
                "prompt": f"Context:\n[{doc_recent['title']}]\n{doc_recent['content']}\n\n[{doc_stale['title']}]\n{doc_stale['content']}\n\nQuestion: {question}\nAnswer:",
                "target_stale": stale_tok,
                "target_recent": recent_tok
            })
            
            sample_counter += 1

    return all_prompts

def main():
    output_path = Path("benchmark_seed_expanded.json")
    prompts = generate_expanded_seed()
    with open(output_path, "w") as f:
        json.dump(prompts, f, indent=2)
    print(f"Generated {len(prompts)} empirical conflict prompts across {len(CATEGORIES)} categories.")
    print(f"Saved expanded benchmark seed to {output_path.resolve()}")

if __name__ == "__main__":
    main()
