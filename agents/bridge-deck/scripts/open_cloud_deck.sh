#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${SCRIPT_DIR}/deploy.env" ]]; then
    source "${SCRIPT_DIR}/deploy.env"
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project 2>/dev/null || echo "")}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="bridge-deck"
PORT=8081

if [[ -z "${PROJECT_ID}" ]]; then
    echo "❌ ERROR: No GCP project configured. Set GOOGLE_CLOUD_PROJECT in deploy.env or run 'gcloud config set project <PROJECT_ID>'."
    exit 1
fi

echo "=================================================="
echo " Bridge Deck: Connecting to Live Cloud Run Service"
echo "=================================================="
echo " Project: ${PROJECT_ID}"
echo " Service: ${SERVICE_NAME} (${REGION})"
echo " Port:    http://127.0.0.1:${PORT}"
echo "=================================================="

# Retrieve application secret token
echo "[*] Fetching BRIDGE_AUTH_TOKEN from Secret Manager..."
TOKEN=$(gcloud secrets versions access latest --secret=BRIDGE_AUTH_TOKEN --project="${PROJECT_ID}")

TARGET_URL="http://127.0.0.1:${PORT}/?token=${TOKEN}"

# Check if proxy is already running on port 8081
if lsof -Pi :${PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "[*] Proxy is already active on port ${PORT}."
    echo "Opening ${TARGET_URL} in browser..."
    open "${TARGET_URL}"
    exit 0
fi

# Start proxy in background
echo "[*] Launching authenticated IAM proxy tunnel on port ${PORT}..."
gcloud run services proxy "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --port="${PORT}" >/dev/null 2>&1 &
PROXY_PID=$!

# Wait for proxy to bind
echo "[*] Waiting for tunnel connection..."
for i in {1..30}; do
    if lsof -Pi :${PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
        break
    fi
    sleep 0.2
done

echo "✅ Connected! Opening Bridge Deck in your browser..."
open "${TARGET_URL}"

# Keep running in foreground so pressing Ctrl+C stops the proxy cleanly
trap "echo -e '\n[*] Closing proxy tunnel...'; kill ${PROXY_PID} 2>/dev/null || true; exit 0" INT TERM
wait ${PROXY_PID}
