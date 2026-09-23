#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Bridge Deck: Google Cloud Run Deployment Script
# ==============================================================================
# Architecture & Governance Gates:
# - Gate G1: --no-allow-unauthenticated is enforced (D55 compliant)
# - Gate G2: --max-instances=1 is enforced (GCS FUSE safe-write model)
# - Zero-PII: Config is strictly sourced from gitignored deploy.env
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [[ ! -f "deploy.env" ]]; then
    echo "❌ ERROR: deploy.env file not found."
    echo "👉 Please copy deploy.env.example to deploy.env and set your target project variables:"
    echo "   cp deploy.env.example deploy.env"
    exit 1
fi

## Load deployment environment
source deploy.env

GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
GCP_REGION="${GCP_REGION:-us-central1}"
: "${BRIDGE_DEFAULT_TENANT:?set BRIDGE_DEFAULT_TENANT in deploy.env}"
GCS_DATA_BUCKET="${GCS_DATA_BUCKET:-${GOOGLE_CLOUD_PROJECT}-bridge-deck-data}"
SERVICE_NAME="bridge-deck"
RUNTIME_SA="bridge-deck-sa"

if [[ -z "${GOOGLE_CLOUD_PROJECT}" ]]; then
    echo "❌ ERROR: GOOGLE_CLOUD_PROJECT must be set in deploy.env"
    exit 1
fi

# Guard against deploying into an empty/non-existent tenant
if [[ ! -d "data/tenants/${BRIDGE_DEFAULT_TENANT}" ]] && ! gcloud storage ls "gs://${GCS_DATA_BUCKET}/tenants/${BRIDGE_DEFAULT_TENANT}/" --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
    echo "❌ ERROR: No data found for tenant '${BRIDGE_DEFAULT_TENANT}' locally (data/tenants/${BRIDGE_DEFAULT_TENANT}) or in bucket (gs://${GCS_DATA_BUCKET}/tenants/${BRIDGE_DEFAULT_TENANT}/)."
    echo "👉 Refusing to deploy into an empty tenant."
    exit 1
fi

echo "=================================================="
echo "=== BRIDGE DECK: CLOUD RUN DEPLOYMENT ==="
echo " Project:       ${GOOGLE_CLOUD_PROJECT}"
echo " Region:        ${GCP_REGION}"
echo " Bucket:        gs://${GCS_DATA_BUCKET}"
echo " Service Name:  ${SERVICE_NAME}"
echo " Default Tenant:${BRIDGE_DEFAULT_TENANT}"
echo "=================================================="

# ------------------------------------------------------------------------------
# 1. Pre-Deployment Test Gate
# ------------------------------------------------------------------------------
echo -e "\n[1/6] Running automated test suite before deployment..."
PYTHON_BIN="python3"
if [[ -x "./venv/bin/python" ]]; then
    PYTHON_BIN="./venv/bin/python"
fi

${PYTHON_BIN} -m unittest discover -s tests
echo "✅ All tests passed cleanly. Proceeding with deployment."

# ------------------------------------------------------------------------------
# 2. Enable Required GCP APIs & Setup Artifact Registry
# ------------------------------------------------------------------------------
echo -e "\n[2/6] Enabling required Google Cloud APIs and Artifact Registry..."
gcloud services enable \
    run.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    cloudtasks.googleapis.com \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com \
    --project="${GOOGLE_CLOUD_PROJECT}"

# Explicitly ensure cloud-run-source-deploy repository exists
gcloud artifacts repositories describe cloud-run-source-deploy \
    --location="${GCP_REGION}" --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1 || \
gcloud artifacts repositories create cloud-run-source-deploy \
    --repository-format=docker --location="${GCP_REGION}" --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1 || \
    echo "Notice: Could not create cloud-run-source-deploy repository (may already exist or insufficient permissions)"

# ------------------------------------------------------------------------------
# 3. Setup Versioned GCS Bucket & One-Time Seeding
# ------------------------------------------------------------------------------
echo -e "\n[3/6] Verifying Google Cloud Storage bucket..."
if ! gcloud storage buckets describe "gs://${GCS_DATA_BUCKET}" --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
    echo "Creating bucket gs://${GCS_DATA_BUCKET}..."
    gcloud storage buckets create "gs://${GCS_DATA_BUCKET}" \
        --project="${GOOGLE_CLOUD_PROJECT}" \
        --location="${GCP_REGION}" \
        --uniform-bucket-level-access
fi

echo "Enabling object versioning on gs://${GCS_DATA_BUCKET}..."
gcloud storage buckets update "gs://${GCS_DATA_BUCKET}" --versioning --project="${GOOGLE_CLOUD_PROJECT}"

echo "Enabling soft-delete retention on gs://${GCS_DATA_BUCKET}..."
gcloud storage buckets update "gs://${GCS_DATA_BUCKET}" --soft-delete-duration=7d --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null
RETENTION_SEC=$(gcloud storage buckets describe "gs://${GCS_DATA_BUCKET}" --project="${GOOGLE_CLOUD_PROJECT}" --format="value(soft_delete_policy.retentionDurationSeconds)" 2>/dev/null || echo "")
if [[ "${RETENTION_SEC}" != "604800" ]]; then
    echo "❌ ERROR: Soft-delete retention on gs://${GCS_DATA_BUCKET} is '${RETENTION_SEC}' (expected 604800s / 7d)"
    exit 1
fi
echo "✅ Verified soft-delete retention: ${RETENTION_SEC}s (7 days)"

# ------------------------------------------------------------------------------
# 4. Service Account & Secret Manager Setup
# ------------------------------------------------------------------------------
echo -e "\n[4/6] Setting up runtime service account and secrets..."
SA_EMAIL="${RUNTIME_SA}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "${SA_EMAIL}" --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
    echo "Creating runtime service account ${SA_EMAIL}...";
    gcloud iam service-accounts create "${RUNTIME_SA}" \
        --display-name="Bridge Deck Cloud Run Runtime SA" \
        --project="${GOOGLE_CLOUD_PROJECT}"
fi

# Grant deployer and runtime SA serviceAccountUser on runtime SA (needed for Cloud Tasks OIDC generation)
DEPLOYER_ACCOUNT=$(gcloud config get-value account 2>/dev/null || echo "")
if [[ -n "${DEPLOYER_ACCOUNT}" ]]; then
    gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
        --member="user:${DEPLOYER_ACCOUNT}" \
        --role="roles/iam.serviceAccountUser" \
        --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1 || \
        echo "⚠️ Notice: Could not grant roles/iam.serviceAccountUser to ${DEPLOYER_ACCOUNT} — Cloud Run deploy may fail if unprivileged"
fi
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser" \
    --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1 || true

# Grant least-privilege roles to runtime SA
echo "Granting roles to ${SA_EMAIL}..."
gcloud storage buckets add-iam-policy-binding "gs://${GCS_DATA_BUCKET}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectUser" \
    --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null

gcloud projects add-iam-policy-binding "${GOOGLE_CLOUD_PROJECT}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user" >/dev/null

gcloud projects add-iam-policy-binding "${GOOGLE_CLOUD_PROJECT}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudtasks.enqueuer" >/dev/null

# Setup Cloud Tasks queue for Phase 4 durable A2A dispatch
A2A_QUEUE_NAME="${A2A_QUEUE_NAME:-bridge-a2a-tasks}"
echo "Verifying Cloud Tasks queue ${A2A_QUEUE_NAME}..."
gcloud tasks queues describe "${A2A_QUEUE_NAME}" --location="${GCP_REGION}" --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1 || \
gcloud tasks queues create "${A2A_QUEUE_NAME}" --location="${GCP_REGION}" --project="${GOOGLE_CLOUD_PROJECT}" \
    --max-attempts=3 --max-retry-duration=1800s --max-dispatches-per-second=2 --max-concurrent-dispatches=3

echo "Updating retry bounds on Cloud Tasks queue ${A2A_QUEUE_NAME}..."
gcloud tasks queues update "${A2A_QUEUE_NAME}" --location="${GCP_REGION}" --project="${GOOGLE_CLOUD_PROJECT}" \
    --max-attempts=3 --max-retry-duration=1800s --max-dispatches-per-second=2 --max-concurrent-dispatches=3

# Setup BRIDGE_AUTH_TOKEN secret
if ! gcloud secrets describe BRIDGE_AUTH_TOKEN --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null 2>&1; then
    echo "Generating new BRIDGE_AUTH_TOKEN secret..."
    GENERATED_TOKEN=$(openssl rand -hex 32)
    printf "%s" "${GENERATED_TOKEN}" | gcloud secrets create BRIDGE_AUTH_TOKEN \
        --data-file=- \
        --replication-policy="automatic" \
        --project="${GOOGLE_CLOUD_PROJECT}"
fi

gcloud secrets add-iam-policy-binding BRIDGE_AUTH_TOKEN \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null

# ------------------------------------------------------------------------------
# 5. Build and Deploy to Cloud Run
# ------------------------------------------------------------------------------
MIN_INSTANCES="${MIN_INSTANCES:-1}"
MAX_INSTANCES="${MAX_INSTANCES:-1}"

echo -e "\n[5/6] Building and deploying ${SERVICE_NAME} to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --project="${GOOGLE_CLOUD_PROJECT}" \
    --region="${GCP_REGION}" \
    --quiet \
    --source="." \
    --no-allow-unauthenticated \
    --max-instances="${MAX_INSTANCES}" \
    --concurrency=20 \
    --no-cpu-throttling \
    --min-instances="${MIN_INSTANCES}" \
    --timeout=3600 \
    --memory=2Gi \
    --service-account="${SA_EMAIL}" \
    --set-secrets="BRIDGE_AUTH_TOKEN=BRIDGE_AUTH_TOKEN:latest" \
    --set-env-vars="BRIDGE_DEFAULT_TENANT=${BRIDGE_DEFAULT_TENANT},CLOUD_RUN=true,GCS_DATA_BUCKET=${GCS_DATA_BUCKET},BRIDGE_DATA_DIR=/mnt/bridge-data,A2A_QUEUE_BACKEND=cloud_tasks,CLOUD_TASKS_QUEUE=${A2A_QUEUE_NAME},CLOUD_TASKS_LOCATION=${GCP_REGION},CLOUD_TASKS_SERVICE_ACCOUNT=${SA_EMAIL},GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},CLOUD_TASKS_PROJECT=${GOOGLE_CLOUD_PROJECT},CLOUD_TASKS_SERVICE_URL=https://pending-bootstrap.internal" \
    --remove-volume-mount=/app/data \
    --add-volume="name=data,type=cloud-storage,bucket=${GCS_DATA_BUCKET}" \
    --add-volume-mount="volume=data,mount-path=/mnt/bridge-data"

# ------------------------------------------------------------------------------
# 6. Post-Deployment Guidance
# ------------------------------------------------------------------------------
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --project="${GOOGLE_CLOUD_PROJECT}" --region="${GCP_REGION}" --format="value(status.url)")

if [[ -n "${SERVICE_URL}" ]]; then
    echo "Configuring self-referential CLOUD_TASKS_SERVICE_URL on ${SERVICE_NAME}..."
    gcloud run services update "${SERVICE_NAME}" \
        --project="${GOOGLE_CLOUD_PROJECT}" \
        --region="${GCP_REGION}" \
        --quiet \
        --update-env-vars="CLOUD_TASKS_SERVICE_URL=${SERVICE_URL},SERVICE_URL=${SERVICE_URL}"

    echo "Ensuring runtime SA has roles/run.invoker on ${SERVICE_NAME} for Cloud Tasks durable queue dispatch..."
    gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
        --region="${GCP_REGION}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/run.invoker" \
        --project="${GOOGLE_CLOUD_PROJECT}" >/dev/null

    echo "Verifying live CLOUD_TASKS_SERVICE_URL configuration..."
    LIVE=$(gcloud run services describe "${SERVICE_NAME}" --project="${GOOGLE_CLOUD_PROJECT}" --region="${GCP_REGION}" \
      --format="json(spec.template.spec.containers[0].env)" | grep -A1 '"name": "CLOUD_TASKS_SERVICE_URL"' | grep '"value":' | sed 's/.*"value": "\(.*\)".*/\1/' | tr -d '[:space:]')
    if [[ "${LIVE}" != "${SERVICE_URL}" ]]; then
        echo "❌ ERROR: URL injection did not take (expected: ${SERVICE_URL}, got: ${LIVE})" >&2
        exit 1
    fi
else
    echo "❌ ERROR: Could not resolve SERVICE_URL; A2A dispatch will fail. Refusing to report success." >&2
    exit 1
fi
echo -e "\n[6/6] ✅ Cloud Run deployment complete!"

echo "=================================================="
echo " Service URL: ${SERVICE_URL}"
echo "=================================================="
echo "To access the Web UI from your local browser (preserving Gate G1 IAM auth):"
echo "  gcloud run services proxy ${SERVICE_NAME} --region ${GCP_REGION} --port 8081"
echo ""
echo "Then retrieve your application access token:"
echo "  TOKEN=\$(gcloud secrets versions access latest --secret=BRIDGE_AUTH_TOKEN --project=${GOOGLE_CLOUD_PROJECT})"
echo ""
echo "Open in your browser:"
echo "  http://127.0.0.1:8081/?token=\${TOKEN}"
echo "=================================================="
