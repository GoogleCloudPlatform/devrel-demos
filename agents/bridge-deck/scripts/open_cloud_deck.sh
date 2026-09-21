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
TOKEN=$(gcloud secrets versions access latest --secret=BRIDGE_AUTH_TOKEN --project="${PROJECT_ID}" 2>/dev/null || \
  curl -s -H "Authorization: Bearer $(gcloud auth application-default print-access-token 2>/dev/null)" "https://secretmanager.googleapis.com/v1/projects/${PROJECT_ID}/secrets/BRIDGE_AUTH_TOKEN/versions/latest:access" | python3 -c 'import sys, json, base64; res = json.load(sys.stdin); print(base64.b64decode(res.get("payload", {}).get("data", "")).decode("utf-8"))' 2>/dev/null || echo "")

TARGET_URL="http://127.0.0.1:${PORT}/?token=${TOKEN}"

# Check if proxy is already running on port 8081 and verify token freshness
if lsof -Pi :${PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
    RESP=$(curl -s "http://127.0.0.1:${PORT}/" --max-time 3 2>/dev/null || echo "")
    if echo "${RESP}" | grep -q "Your client does not have permission"; then
        echo "[!] Existing proxy tunnel on port ${PORT} has expired IAM credentials. Recycling tunnel..."
        EXISTING_PID=$(lsof -Pi :${PORT} -sTCP:LISTEN -t 2>/dev/null || echo "")
        if [[ -n "${EXISTING_PID}" ]]; then
            kill -9 ${EXISTING_PID} 2>/dev/null || true
        fi
        sleep 1
    else
        echo "[*] Proxy is already active on port ${PORT}."
        echo "Opening ${TARGET_URL} in browser..."
        open "${TARGET_URL}"
        exit 0
    fi
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
