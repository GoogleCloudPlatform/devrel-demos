#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

# ==============================================================================
# Deploy Flow Marketplace to Google Cloud Run & Agent Platform
# Target Console: https://console.cloud.google.com/agent-platform
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# 1. Environment & Python Setup for gcloud
if [[ -f "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    export CLOUDSDK_PYTHON="${SCRIPT_DIR}/.venv/bin/python"
fi
export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.antigravity"

# Load project config from .env if present
if [[ -f ".env" ]]; then
    # shellcheck disable=SC1091
    source .env
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-gcp-project-id}"
REGION="${CLOUD_RUN_REGION:-us-central1}"
SERVICE_NAME="flow-service"
DATA_BUCKET="${FLOW_DATA_BUCKET:-${PROJECT_ID}-flow-data}"

echo "=========================================================="
echo "⚡ Deploying Flow Marketplace to Google Cloud Agent Platform"
echo "   Target GCP Project : ${PROJECT_ID}"
echo "   Target Region      : ${REGION}"
echo "   Service Name       : ${SERVICE_NAME}"
echo "   Persistent Bucket  : gs://${DATA_BUCKET}"
echo "=========================================================="

# 2. Check Authentication
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
if [[ -z "${ACTIVE_ACCOUNT}" ]]; then
    echo "⚠️  No active Google Cloud account detected."
    echo "👉 Please run the following command to authenticate with Google Cloud:"
    echo "   gcloud auth login"
    echo ""
    echo "After logging in, re-run this script: ./deploy_flow_agent_platform.sh"
    exit 1
fi

echo "✅ Authenticated as: ${ACTIVE_ACCOUNT}"

# Set current project
gcloud config set project "${PROJECT_ID}" --quiet

# 3. Enable Required Google Cloud APIs
echo -e "\n[1/4] Enabling required Google Cloud APIs (Cloud Run, Cloud Build, Artifact Registry, Cloud Storage)..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com storage.googleapis.com --project="${PROJECT_ID}"

# 4. Provision Persistent GCS Bucket & Snapshot Live Project Data Before Redeploy
echo -e "\n[2/4] Ensuring persistent storage bucket gs://${DATA_BUCKET} & snapshotting live projects..."
if ! gcloud storage buckets describe "gs://${DATA_BUCKET}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "   Creating persistent bucket gs://${DATA_BUCKET} in ${REGION}..."
    gcloud storage buckets create "gs://${DATA_BUCKET}" --project="${PROJECT_ID}" --location="${REGION}" --uniform-bucket-level-access
fi

EXISTING_URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format="value(status.url)" 2>/dev/null || true)
if [[ -n "${EXISTING_URL}" ]]; then
    TMP_SNAPSHOT=$(mktemp /tmp/flow_projects_snapshot.XXXXXX.json)
    if curl -fsSL --compressed --max-time 60 "${EXISTING_URL}/api/projects/export" -o "${TMP_SNAPSHOT}" 2>/dev/null; then
        echo "   Backed up live multi-project state from ${EXISTING_URL}/api/projects/export to gs://${DATA_BUCKET}/projects_state.json"
        gcloud storage cp "${TMP_SNAPSHOT}" "gs://${DATA_BUCKET}/projects_state.json" --quiet
        gcloud storage cp "${TMP_SNAPSHOT}" "gs://${DATA_BUCKET}/backups/projects_state_$(date -u +%Y%m%dT%H%M%SZ).json" --quiet
    elif ! gcloud storage ls "gs://${DATA_BUCKET}/projects_state.json" >/dev/null 2>&1; then
        echo "   Seeding initial gs://${DATA_BUCKET}/projects_state.json from live ${EXISTING_URL}/api/simulation/export..."
        if curl -fsSL --compressed --max-time 60 "${EXISTING_URL}/api/simulation/export" -o "${TMP_SNAPSHOT}.raw" 2>/dev/null; then
            "${CLOUDSDK_PYTHON:-python3}" -c "
import json, sys
with open('${TMP_SNAPSHOT}.raw', 'r', encoding='utf-8') as f:
    st = json.load(f)
wrapped = {
    'active_project_id': 'default',
    'projects': {
        'default': {
            'project_id': 'default',
            'name': 'Default Project',
            'created_at': '2026-03-01T00:00:00Z',
            'state': st,
        }
    }
}
with open('${TMP_SNAPSHOT}', 'w', encoding='utf-8') as out:
    json.dump(wrapped, out, indent=2)
"
            gcloud storage cp "${TMP_SNAPSHOT}" "gs://${DATA_BUCKET}/projects_state.json" --quiet
            rm -f "${TMP_SNAPSHOT}.raw"
        fi
    fi
    rm -f "${TMP_SNAPSHOT}"
fi

# 5. Deploy Container to Cloud Run with Persistent GCS Volume Mount
echo -e "\n[3/4] Building and deploying ${SERVICE_NAME} to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --port 8090 \
    --allow-unauthenticated \
    --execution-environment=gen2 \
    --add-volume="name=flow-data,type=cloud-storage,bucket=${DATA_BUCKET}" \
    --add-volume-mount="volume=flow-data,mount-path=/mnt/flow_data" \
    --timeout 3600s \
    --no-cpu-throttling \
    --min-instances 1 \
    --max-instances 1 \
    --concurrency 80 \
    --cpu 2 \
    --memory 2Gi \
    --command="python" \
    --args="flow_cli.py,serve,--host,0.0.0.0,--port,8090" \
    --set-env-vars="FLOW_LIVE_MODE=true,PYTHONUNBUFFERED=1,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GEMINI_VERTEX_LOCATION=global,ANTHROPIC_VERTEX_REGION=global,FLOW_PROJECTS_STATE_PATH=/mnt/flow_data/projects_state.json" \
    --quiet

# Fetch deployed URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format="value(status.url)")
echo "✅ Flow Service successfully deployed to: ${SERVICE_URL}"

# 5. Export Updated Agent Platform Assets
echo -e "\n[3/3] Exporting Agent Platform Extension & Agent Cards..."
"${CLOUDSDK_PYTHON:-python3}" -c "
import json
from flow.agent_platform_export import (
    get_dispatcher_agent_card,
    get_security_taskforce_agent_card,
    get_commitment_ledger_openapi_schema,
    get_agent_studio_playbook_instructions,
)

service_url = '${SERVICE_URL}'
openapi = get_commitment_ledger_openapi_schema()
openapi['servers'] = [{'url': service_url}]

dispatcher_card = get_dispatcher_agent_card()
dispatcher_card['url'] = f'{service_url}/agent/dispatcher'

security_card = get_security_taskforce_agent_card()
security_card['url'] = f'{service_url}/agent/security'

bundle = {
    'service_url': service_url,
    'openapi_spec': openapi,
    'agents': {
        'dispatcher': dispatcher_card,
        'security_taskforce': security_card,
    },
    'playbook_instructions': get_agent_studio_playbook_instructions(),
}

with open('agent_platform_bundle.json', 'w') as f:
    json.dump(bundle, f, indent=2)

with open('flow_openapi.json', 'w') as f:
    json.dump(openapi, f, indent=2)

print('Saved: agent_platform_bundle.json & flow_openapi.json')
"

echo "=========================================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo ""
echo "Next steps in Agent Platform (https://console.cloud.google.com/agent-platform):"
echo "1. Go to: https://console.cloud.google.com/agent-platform?project=${PROJECT_ID}"
echo "2. Open Tools / Extensions -> Create Extension"
echo "3. Upload 'flow_openapi.json' (or enter URL: ${SERVICE_URL}/api/openapi.json)"
echo "4. In Agent Studio, configure:"
echo "   - Flow Dispatcher Agent: Link Commitment Ledger Extension"
echo "   - Flow Security Taskforce: Configure Multi-Model Council"
echo "=========================================================="
