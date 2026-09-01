#!/usr/bin/env bash
# Environment Setup Script for Standalone Bridge Deck

echo "=================================================="
echo "=== SETTING UP STANDALONE BRIDGE DECK VENV ==="
echo "=================================================="

BRIDGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BRIDGE_DIR"

if [ ! -d "venv" ]; then
    echo "[+] Creating virtual environment in venv..."
    python3 -m venv venv
fi

echo "[+] Upgrading pip and installing requirements..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "[+] Standalone Bridge Deck environment ready!"
export BRIDGE_DEFAULT_TENANT=${BRIDGE_DEFAULT_TENANT:-lead}
echo "[!] Launch server with: ./venv/bin/python bridge_runner.py --port 8080"
