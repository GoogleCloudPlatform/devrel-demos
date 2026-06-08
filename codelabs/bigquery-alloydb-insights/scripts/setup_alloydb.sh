#!/bin/bash
# ---------------------------------------------------------------------------
# Lab 2: AlloyDB Background Deployment Wrapper
# ---------------------------------------------------------------------------
# This script wraps the upstream deploy_alloydb.sh from
# GoogleCloudPlatform/codelabs to provision an AlloyDB cluster + instance
# with naming conventions that match this lab's codelab instructions.
#
# Designed to be kicked off early in the lab and run in the background
# while attendees work through BigQuery tasks (~10-15 min to complete).
# ---------------------------------------------------------------------------
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${LAB_DIR}/.env"

# Load environment from .env if it exists
if [ -f "$ENV_FILE" ]; then
    echo "Found existing environment file: $ENV_FILE"
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# || -z "$line" ]] && continue
        export "$line"
    done < "$ENV_FILE"
fi

# --- Lab-specific configuration ---
export CLUSTER_NAME="lost-cargo-cluster"
export INSTANCE_NAME="lost-cargo-instance"
export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-us-central1}"

# Check for valid Project ID
if [[ -z "$PROJECT_ID" ]]; then
  echo "❌ ERROR: No Google Cloud Project ID detected."
  echo "   Please run 'gcloud config set project YOUR_PROJECT_ID' first."
  exit 1
fi

# Write environment variables immediately to .env if not already created
if [ ! -f "$ENV_FILE" ]; then
    echo "Creating environment file: $ENV_FILE"
    echo "PROJECT_ID=$PROJECT_ID" > "$ENV_FILE"
    echo "REGION=$REGION" >> "$ENV_FILE"
fi

DEPLOY_DIR="/tmp/alloydb-deploy-$$"
LOG_FILE="${LAB_DIR}/alloydb_deploy.log"

echo "=============================================="
echo " Lab 2: AlloyDB Background Deployment"
echo "=============================================="
echo " Project:  ${PROJECT_ID}"
echo " Region:   ${REGION}"
echo " Cluster:  ${CLUSTER_NAME}"
echo " Instance: ${INSTANCE_NAME}"
echo " Log file: ${LOG_FILE}"
echo "=============================================="

# --- Fetch the upstream deployment script ---
echo "[1/5] Fetching deployment script from GoogleCloudPlatform/codelabs..."
mkdir -p "${DEPLOY_DIR}"
cd "${DEPLOY_DIR}"

git clone --no-checkout --filter=blob:none \
  https://github.com/GoogleCloudPlatform/codelabs.git repo 2>&1
cd repo
git sparse-checkout set alloydb-querydata 2>&1
git checkout 2>&1

# --- Run the upstream script with public IP for AlloyDB Studio access ---
echo "[2/5] Starting AlloyDB deployment (this takes ~10 minutes)..."
cd alloydb-querydata
bash deploy_alloydb.sh --public-ip 2>&1 | tee "${LOG_FILE}"

# --- Enable IAM authentication flag ---
echo "Enabling IAM authentication flag on the instance..."
gcloud alloydb instances update "${INSTANCE_NAME}" \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --database-flags=password.enforce_complexity=on,alloydb.iam_authentication=on \
  --quiet || echo "⚠️ Warning: Failed to enable IAM authentication flag."

# --- Enable Data API access ---
echo "Enabling Data API access on the instance..."
curl -X PATCH \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
"https://alloydb.googleapis.com/v1beta/projects/${PROJECT_ID}/locations/${REGION}/clusters/${CLUSTER_NAME}/instances/${INSTANCE_NAME}?updateMask=dataApiAccess" \
-d '{ "dataApiAccess": "ENABLED" }' || echo "⚠️ Warning: Failed to enable Data API access."

# --- Reset postgres password to a known value for the lab ---
echo "Resetting postgres password to 'lost-cargo'..."
gcloud alloydb users set-password postgres \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --password="lost-cargo" \
  --quiet || echo "⚠️ Warning: Failed to reset postgres password."

# --- Clean up temp files ---
echo "[3/5] Cleaning up temporary files..."
rm -rf "${DEPLOY_DIR}"

# --- Create database user for current IAM principal ---
CURRENT_USER=$(gcloud config get-value account)
echo "[4/5] Creating database user for current IAM principal: ${CURRENT_USER}..."
gcloud alloydb users create "${CURRENT_USER}" \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --type=IAM_BASED \
  --superuser=true || echo "⚠️ Warning: Failed to create database user for ${CURRENT_USER}. You may need to create it manually."

# --- Grant GCS Bucket and Vertex AI access to the AlloyDB Service Agent and cluster account ---
echo "[5/5] Configuring IAM permissions for AlloyDB..."

# Retrieve project number for the project-wide AlloyDB Service Agent
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)" 2>/dev/null || echo "")
if [[ -n "$PROJECT_NUMBER" ]]; then
  ALLOYDB_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com"
  
  echo "      Granting Vertex AI access to AlloyDB Service Agent..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SERVICE_AGENT}" \
    --role="roles/aiplatform.user" \
    --quiet || echo "⚠️ Warning: Failed to grant Vertex AI User role to AlloyDB Service Agent."
fi

# Also grant to cluster-specific service account if retrieved
ALLOYDB_SA=$(gcloud alloydb clusters describe "${CLUSTER_NAME}" \
  --region="${REGION}" \
  --format="value(serviceAccount)" 2>/dev/null || echo "")

if [[ -n "$ALLOYDB_SA" ]]; then
  echo "      Granting Vertex AI access to cluster-specific service account..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SA}" \
    --role="roles/aiplatform.user" \
    --quiet || echo "⚠️ Warning: Failed to grant Vertex AI User role to cluster-specific service account."
fi

echo ""
echo "=============================================="
echo " ✅ AlloyDB deployment complete!"
echo ""
echo " Cluster:  ${CLUSTER_NAME}"
echo " Instance: ${INSTANCE_NAME}"
echo " Region:   ${REGION}"
echo ""
echo " Connect via AlloyDB Studio in the Cloud Console:"
echo " AlloyDB → Clusters → ${CLUSTER_NAME} → AlloyDB Studio"
echo "=============================================="
