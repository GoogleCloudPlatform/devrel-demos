#!/bin/bash
set -e

echo "========================================"
echo " AIDA - Emergency Diagnostic Agent Setup"
echo "========================================"

# 1. Install Dependencies
echo "[1/5] Installing Python dependencies..."
uv sync
echo "Dependencies installed."

# 2. Fetch Osquery Specifications & Packs
echo "[2/5] Fetching osquery specifications and packs..."
if [ -d "osquery_data" ]; then
    echo "'osquery_data' directory already exists. Ensuring 'packs' are present..."
    cd osquery_data
    # Ensure both specs and packs are checked out if directory already exists
    git sparse-checkout set specs packs
    git checkout
    cd ..
else
    git clone --depth 1 --filter=blob:none --sparse https://github.com/osquery/osquery.git osquery_data
    cd osquery_data
    git sparse-checkout set specs packs
    cd ..
fi
echo "Osquery data fetched."

# 3. Download Embedding Model
echo "[3/5] Downloading embedding model (embeddinggemma-300m)..."
uv run python -c "from huggingface_hub import hf_hub_download; import os; os.makedirs('models/unsloth/embeddinggemma-300m-GGUF', exist_ok=True); hf_hub_download(repo_id='unsloth/embeddinggemma-300m-GGUF', filename='embeddinggemma-300M-Q8_0.gguf', local_dir='models/unsloth/embeddinggemma-300m-GGUF')"
echo "Embedding model downloaded."

# 4. Pull LLM
echo "[4/5] Pulling LLM (qwen2.5)..."
ollama pull qwen2.5
echo "LLM pulled."

# 5. Run Ingestion
echo "[5/5] Building knowledge base (this may take a moment)..."
echo "  - Ingesting schema..."
uv run python ingest_osquery.py
echo "  - Ingesting query packs..."
uv run python ingest_packs.py
echo "Knowledge base built."

echo "========================================"
echo " Setup Complete!"
echo "========================================"
echo "You can now run the agent with:"
echo "  uv run uvicorn main:app --reload"
echo ""