#!/bin/bash

set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "${SCRIPT_DIR}"

if [ -f ".env" ]; then
  source .env
fi

if [[ "${GOOGLE_CLOUD_PROJECT}" == "" ]]; then
  GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project -q)
fi
if [[ "${GOOGLE_CLOUD_PROJECT}" == "" ]]; then
  echo "ERROR: Run 'gcloud config set project' command to set active project, or set GOOGLE_CLOUD_PROJECT environment variable."
  exit 1
fi

REGION="${GOOGLE_CLOUD_LOCATION}"
if [[ "${REGION}" == "global" ]]; then
  echo "GOOGLE_CLOUD_LOCATION is set to 'global'. Getting a default location for Cloud Run."
  REGION=""
fi

if [[ "${REGION}" == "" ]]; then
  REGION=$(gcloud config get-value compute/region -q)
  if [[ "${REGION}" == "" ]]; then
    REGION="us-east4"
    echo "WARNING: Cannot get a configured compute region. Defaulting to ${REGION}."
  fi
fi
echo "Using project ${GOOGLE_CLOUD_PROJECT}."
echo "Using compute region ${REGION}."

# --- Deploy Ollama Backend (Self-hosted LLM on GPU) ---
# Must be deployed FIRST as content-builder depends on its URL.
# GPU availability varies by region — override with OLLAMA_REGION if needed.
OLLAMA_REGION="${OLLAMA_REGION:-${REGION}}"
GEMMA_MODEL="${GEMMA_MODEL_NAME:-gemma3:270m}"
echo "Deploying Ollama backend with GPU in ${OLLAMA_REGION}..."

gcloud run deploy ollama-gemma-gpu \
  --source ollama-backend \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $OLLAMA_REGION \
  --concurrency 4 \
  --cpu 8 \
  --set-env-vars OLLAMA_NUM_PARALLEL=4 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --max-instances 3 \
  --memory 16Gi \
  --no-allow-unauthenticated \
  --no-cpu-throttling \
  --no-gpu-zonal-redundancy \
  --timeout 600
OLLAMA_URL=$(gcloud run services describe ollama-gemma-gpu --region $OLLAMA_REGION --format='value(status.url)')
echo "Ollama backend deployed at: ${OLLAMA_URL}"

gcloud run deploy researcher \
  --source agents/researcher \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
RESEARCHER_URL=$(gcloud run services describe researcher --region $REGION --format='value(status.url)')

gcloud run deploy content-builder \
  --source agents/content_builder \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars OLLAMA_API_BASE="${OLLAMA_URL}" \
  --set-env-vars GEMMA_MODEL_NAME="${GEMMA_MODEL}"
CONTENT_BUILDER_URL=$(gcloud run services describe content-builder --region $REGION --format='value(status.url)')

gcloud run deploy judge \
  --source agents/judge \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
JUDGE_URL=$(gcloud run services describe judge --region $REGION --format='value(status.url)')

gcloud run deploy orchestrator \
  --source agents/orchestrator \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --no-allow-unauthenticated \
  --set-env-vars RESEARCHER_AGENT_CARD_URL=$RESEARCHER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars JUDGE_AGENT_CARD_URL=$JUDGE_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars CONTENT_BUILDER_AGENT_CARD_URL=$CONTENT_BUILDER_URL/a2a/agent/.well-known/agent-card.json \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI="true"
ORCHESTRATOR_URL=$(gcloud run services describe orchestrator --region $REGION --format='value(status.url)')

gcloud run deploy course-creator \
  --source app \
  --project $GOOGLE_CLOUD_PROJECT \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars AGENT_SERVER_URL=$ORCHESTRATOR_URL \
  --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}"
