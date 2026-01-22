#!/bin/bash
set -e

echo "========================================"
echo " AIDA - AICAMP Setup Script"
echo "========================================"

# 1. Install Dependencies
echo "[1/3] Syncing dependencies..."
uv sync
echo "Dependencies synced."

# 2. Download Embedding Model
echo "[2/3] Downloading embedding model (embeddinggemma-300m)..."
uv run python -c "from huggingface_hub import hf_hub_download; import os; os.makedirs('models/unsloth/embeddinggemma-300m-GGUF', exist_ok=True); hf_hub_download(repo_id='unsloth/embeddinggemma-300m-GGUF', filename='embeddinggemma-300M-Q8_0.gguf', local_dir='models/unsloth/embeddinggemma-300m-GGUF')"
echo "Embedding model downloaded."

# 3. Run Ingestion
echo "[3/3] Building knowledge base..."
echo "  - Ingesting schema..."
uv run python ingest_osquery.py
echo "  - Ingesting query packs..."
uv run python ingest_packs.py
echo "Knowledge base built."

echo "========================================"
echo " Setup Complete!"
echo "========================================"
