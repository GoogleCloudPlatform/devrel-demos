#!/bin/bash
# ==============================================================================
# 🚀 Sentiment Agent Codelab: Automated Environment Setup & Database Bootstrap
# ==============================================================================
set -e

# ANSI Color Codes for Premium Terminal Aesthetics
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${CYAN}======================================================================${NC}"
echo -e "${BOLD}🚀 Welcome to the Sentiment Agent Codelab Developer Bootstrap! 🚀${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo -e "This script will automatically establish a clean development environment,"
echo -e "install all required dependencies, and bootstrap your BigQuery cloud database."
echo ""

# 1. Detect standard python interpreter
echo -e "${BLUE}[1/4] Checking System Requirements...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: python3 is required but was not found on your system.${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
echo -e "  ✔️ Found Python version: ${GREEN}${PYTHON_VERSION}${NC}"

if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ ERROR: 'uv' package manager is required for this codelab but was not found.${NC}"
    echo -e "Please install 'uv' to proceed: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi
echo -e "  ✔️ Found 'uv' package manager."

# 2. Setup root-level virtual environment
echo -e "\n${BLUE}[2/4] Setting up Root Virtual Environment...${NC}"
if [ ! -d ".venv" ]; then
    echo -e "  📦 Creating virtual environment using ${CYAN}uv venv${NC}..."
    uv venv .venv
    echo -e "  ✔️ Virtual environment established at ${GREEN}.venv/${NC}"
else
    echo -e "  ✔️ Virtual environment already exists."
fi

# 3. Install orchestration dependencies inside venv
echo -e "\n${BLUE}[3/4] Installing Required Packages...${NC}"
echo -e "  ⚡ Resolving and installing setup dependencies using 'uv'..."
uv pip install --python .venv/bin/python3 --quiet google-genai google-cloud-bigquery rich python-dotenv google-cloud-bigquery-reservation
echo -e "  ⚡ Installing agent application dependencies from agents/..."
uv pip install --python .venv/bin/python3 --quiet -e agents/
echo -e "  ✔️ Dependencies installed successfully inside the virtual environment."

# 3.5 Enable Required Google Cloud Platform APIs
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
fi
if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
  echo -e "\n${BLUE}[3.5/4] Enabling Required Google Cloud APIs...${NC}"
  echo -e "  ⚡ Enabling BigQuery, Vertex AI, Natural Language, and Connection APIs..."
  gcloud services enable bigquery.googleapis.com aiplatform.googleapis.com language.googleapis.com bigqueryconnection.googleapis.com bigqueryreservation.googleapis.com --project="$GOOGLE_CLOUD_PROJECT" --quiet || true
  echo -e "  ✔️ APIs enabled or verified successfully."
fi

# 4. Bootstrap BigQuery Dataset, Remote Models, and Seed Policies
echo -e "\n${BLUE}[4/4] Provisioning BigQuery & Seeding Vector Database...${NC}"
echo -e "  ✨ Executing BigQuery database bootstrap..."
.venv/bin/python3 scripts/setup_bigquery.py

echo ""
echo -e "${GREEN}======================================================================${NC}"
echo -e "${BOLD}🎉 CODELAB BOOTSTRAP COMPLETED SUCCESSFULLY! 🎉${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "Your local development environment and BigQuery database are ready."
echo -e "To launch your conversational agents and visual developer playground, refer to:"
echo -e "  👉 ${GREEN}agents/README.md${NC}"
echo -e "======================================================================"
