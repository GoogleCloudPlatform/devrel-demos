#!/usr/bin/env bash
# ============================================================================
# PetVerse Sanctuary Analytics - Infrastructure, IAM & Knowledge Studio Setup
# ============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Retrieve environment variables or gcloud configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-$(gcloud config get-value compute/region 2>/dev/null)}"
DATASET_ID="${DATASET_ID:-petverse}"

# Validation check: if variables are not set AND project ID doesn't start with "qwiklabs"
if { [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; } && [[ "$PROJECT_ID" != qwiklabs* ]]; then
  echo "⚠️   PROJECT_ID or REGION environment variables are not set, and project ID does not start with 'qwiklabs'."
  echo "👉  Export PROJECT_ID and REGION first, then re-run ./petverse-setup.sh."
  exit 1
fi

BUCKET="${BUCKET:-${PROJECT_ID}-petverse}"

echo "  ➡️   Checking for active Google Cloud authentication..."
if ! gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null | grep -q @; then
  echo "⚠️   Not authenticated. Please authenticate now."
  gcloud auth login
fi
ACTIVE_ACCOUNT="$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null | head -n 1)"
echo "  ✅   Authentication check passed (${ACTIVE_ACCOUNT})."

echo "  🔄   Setting Google Cloud configuration for this session..."
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1
gcloud config set compute/region "$REGION" >/dev/null 2>&1
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null)"

echo "  ✅   Google Cloud configuration updated."
echo "Project ID:     $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo "Region:         $REGION"
echo "Dataset ID:     $DATASET_ID"
echo "Bucket:         gs://$BUCKET"
echo " "

# Save variables to ~/.env and ./.env
cat > "$HOME/.env" << EOF
export PROJECT_ID=$PROJECT_ID
export REGION=$REGION
export DATASET_ID=$DATASET_ID
export BUCKET=$BUCKET
export AGY_ADC_AUTH=true
export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
export GOOGLE_CLOUD_QUOTA_PROJECT=$PROJECT_ID
export GOOGLE_CLOUD_LOCATION=global
export AGY_CLI_DISABLE_AUTO_UPDATE=true
EOF
if [ "$PWD" != "$HOME" ]; then
  cp "$HOME/.env" .env
fi
grep -q 'source ~/.env' "$HOME/.bashrc" 2>/dev/null || echo '[ -f ~/.env ] && source ~/.env' >> "$HOME/.bashrc"
echo "  ✅   Environment variables saved to ~/.env and .env."
echo " "

# Enable required Google Cloud APIs
echo "  🔄   Enabling required Google Cloud APIs (BigQuery, Vertex AI, Knowledge Catalog, Conversational Analytics)..."
APIS=(
  "bigquery.googleapis.com"
  "bigqueryconnection.googleapis.com"
  "aiplatform.googleapis.com"
  "storage.googleapis.com"
  "dataplex.googleapis.com"
  "datacatalog.googleapis.com"
  "iamcredentials.googleapis.com"
  "geminidataanalytics.googleapis.com"
  "cloudaicompanion.googleapis.com"
)
if ! gcloud services enable "${APIS[@]}" --project="$PROJECT_ID"; then
  echo "❌ Error: Failed to enable required Google Cloud APIs."
  exit 1
fi
echo "  ✅   Required APIs enabled."
echo " "

# BigQuery Cloud Resource Connection & IAM Setup
echo "  🔄   Creating BigQuery connection 'pet-connection' and granting IAM permissions..."
bq mk --connection \
  --location="$REGION" \
  --project_id="$PROJECT_ID" \
  --connection_type=CLOUD_RESOURCE \
  pet-connection >/dev/null 2>&1 || true

max_retries=5
count=0
conn_success=false

while [ "$count" -lt "$max_retries" ]; do
  ((count++))
  echo "  ➡️   Attempt ${count}/${max_retries} to configure BigQuery connection IAM..."

  SA_ID="$(bq show --project_id="$PROJECT_ID" --location="$REGION" --format=json --connection pet-connection 2>/dev/null | jq -r '.cloudResource.serviceAccountId // empty')"

  if [ -n "$SA_ID" ]; then
    echo "  ✅   Found Connection Service Account: $SA_ID"
    if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:${SA_ID}" \
      --role="roles/storage.objectViewer" \
      --condition=None >/dev/null 2>&1 && \
       gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:${SA_ID}" \
      --role="roles/aiplatform.user" \
      --condition=None >/dev/null 2>&1; then
      echo "  ✅   Granted Storage Object Viewer and Vertex AI User to ${SA_ID}."
      conn_success=true
      break
    fi
  fi

  echo "  ⏳   Connection service account not ready yet. Retrying in 15 seconds..."
  sleep 15
done

if [ "$conn_success" = false ]; then
  echo "❌ Error: Failed to setup BigQuery connection and IAM permissions after ${max_retries} attempts."
  exit 1
fi
echo " "

# Provision Knowledge Studio Metadata Enrichment Prerequisites
echo "  🔄   Provisioning Knowledge Studio Enrichment Service Account & Dataplex Service Agent IAM..."

# 1. Trigger Dataplex / Knowledge Catalog Service Agent identity creation
gcloud beta services identity create --service=dataplex.googleapis.com --project="$PROJECT_ID" >/dev/null 2>&1 || true
KC_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-dataplex.iam.gserviceaccount.com"

# 2. Create customer-managed service account `kc-enrichment-sa`
ENRICH_SA_NAME="kc-enrichment-sa"
ENRICH_SA_EMAIL="${ENRICH_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$ENRICH_SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$ENRICH_SA_NAME" \
    --project="$PROJECT_ID" \
    --display-name="Knowledge Catalog Metadata Enrichment SA" \
    --description="Customer-managed SA for Knowledge Studio metadata enrichment workflows" >/dev/null
fi
echo "  ✅   Customer-managed SA ready: ${ENRICH_SA_EMAIL}"

# 3. Grant project IAM roles to `kc-enrichment-sa`
ENRICH_SA_ROLES=(
  "roles/serviceusage.serviceUsageConsumer"
  "roles/dataplex.contentEditor"
  "roles/dataplex.catalogEditor"
  "roles/dataplex.catalogViewer"
  "roles/dataplex.workflowApprover"
  "roles/bigquery.dataViewer"
  "roles/bigquery.jobUser"
  "roles/bigquery.resourceViewer"
  "roles/storage.objectViewer"
)
for role in "${ENRICH_SA_ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${ENRICH_SA_EMAIL}" \
    --role="$role" \
    --condition=None >/dev/null 2>&1 || true
done
echo "  ✅   Granted project enrichment roles to ${ENRICH_SA_EMAIL}."

# 4. Grant Knowledge Catalog Service Agent token creator on `kc-enrichment-sa` + BigQuery viewer roles
sa_agent_ready=false
for attempt in 1 2 3 4; do
  if gcloud iam service-accounts add-iam-policy-binding "$ENRICH_SA_EMAIL" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${KC_SERVICE_AGENT}" \
    --role="roles/iam.serviceAccountTokenCreator" >/dev/null 2>&1; then
    sa_agent_ready=true
    break
  fi
  echo "  ⏳   Waiting for Dataplex Service Agent (${KC_SERVICE_AGENT}) propagation (attempt ${attempt}/4)..."
  sleep 10
done

if [ "$sa_agent_ready" = true ]; then
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${KC_SERVICE_AGENT}" \
    --role="roles/bigquery.dataViewer" \
    --condition=None >/dev/null 2>&1 || true
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${KC_SERVICE_AGENT}" \
    --role="roles/bigquery.resourceViewer" \
    --condition=None >/dev/null 2>&1 || true
  echo "  ✅   Granted Token Creator & BigQuery Viewer roles to Knowledge Catalog Service Agent (${KC_SERVICE_AGENT})."
else
  echo "  ⚠️   Warning: Could not bind ${KC_SERVICE_AGENT} yet; Dataplex agent may still be initializing."
fi

# 5. Best-effort IAM bindings for the active user / lab account
if [ -n "$ACTIVE_ACCOUNT" ]; then
  if [[ "$ACTIVE_ACCOUNT" == *.gserviceaccount.com ]]; then
    MEMBER_PREFIX="serviceAccount"
  else
    MEMBER_PREFIX="user"
  fi

  gcloud iam service-accounts add-iam-policy-binding "$ENRICH_SA_EMAIL" \
    --project="$PROJECT_ID" \
    --member="${MEMBER_PREFIX}:${ACTIVE_ACCOUNT}" \
    --role="roles/iam.serviceAccountUser" >/dev/null 2>&1 || true

  USER_ROLES=(
    "roles/dataplex.editor"
    "roles/dataplex.contentAdmin"
    "roles/dataplex.workflowApprover"
    "roles/geminidataanalytics.dataAgentCreator"
    "roles/geminidataanalytics.dataAgentUser"
    "roles/cloudaicompanion.user"
  )
  for role in "${USER_ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="${MEMBER_PREFIX}:${ACTIVE_ACCOUNT}" \
      --role="$role" \
      --condition=None >/dev/null 2>&1 || true
  done
  echo "  ✅   Configured Knowledge Studio & Conversational Analytics roles for ${ACTIVE_ACCOUNT}."
fi
echo " "

# Create Cloud Storage bucket, stage PetVerse assets & legacy repository, and create BigQuery dataset
echo "  🔄   Creating Cloud Storage bucket gs://${BUCKET} and staging PetVerse assets..."

if [ ! -f "$SCRIPT_DIR/data/pv_ops_tlm_v2.csv" ] || [ ! -f "$SCRIPT_DIR/data/pv_snct_inv_88.csv" ]; then
  if command -v uv >/dev/null 2>&1; then
    uv run --python 3.14 "$SCRIPT_DIR/scripts/generate_telemetry.py" >/dev/null 2>&1 || \
      uv run "$SCRIPT_DIR/scripts/generate_telemetry.py" >/dev/null
  else
    python3 "$SCRIPT_DIR/scripts/generate_telemetry.py" >/dev/null
  fi
fi

if ! gcloud storage buckets describe "gs://${BUCKET}" --project="$PROJECT_ID" >/dev/null 2>&1; then
  if ! gcloud storage buckets create "gs://${BUCKET}" \
    --project="$PROJECT_ID" \
    --uniform-bucket-level-access \
    --location="$REGION"; then
    echo "❌ Error: Failed to create Cloud Storage bucket gs://${BUCKET}."
    exit 1
  fi
fi

if ! gcloud storage cp -r gs://sample-data-and-media/petverse/* "gs://${BUCKET}/" || \
   ! gcloud storage cp \
       "$SCRIPT_DIR/data/pv_ops_tlm_v2.csv" \
       "$SCRIPT_DIR/data/pv_snct_inv_88.csv" \
       "gs://${BUCKET}/telemetry/"; then
  echo "❌ Error: Failed to stage PetVerse media and telemetry CSVs to gs://${BUCKET}/."
  exit 1
fi

STAGE_DIR="$(mktemp -d)"
trap 'rm -rf "$STAGE_DIR"' EXIT
cp -R "$SCRIPT_DIR/legacy-paws400-repo" "$STAGE_DIR/legacy-paws400-repo"
sed -i \
  -e "s/__PROJECT_ID__\.petverse\./${PROJECT_ID}.${DATASET_ID}./g" \
  -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
  -e "s/__REGION__/${REGION}/g" \
  "$STAGE_DIR/legacy-paws400-repo/eval/petverse_eval.jsonl"

if ! gcloud storage cp -r "$STAGE_DIR/legacy-paws400-repo" "gs://${BUCKET}/"; then
  echo "❌ Error: Failed to stage legacy-paws400-repo to gs://${BUCKET}/."
  exit 1
fi
echo "  ✅   Staged PetVerse media, telemetry CSVs, and legacy-paws400-repo to gs://${BUCKET}/."

echo "  🔄   Creating BigQuery dataset '${DATASET_ID}' in ${REGION}..."
bq --location="$REGION" mk --dataset --project_id="$PROJECT_ID" "$DATASET_ID" >/dev/null 2>&1 || true
echo "  ✅   BigQuery dataset '${PROJECT_ID}:${DATASET_ID}' ready."

echo " "
echo "  📦   Your bucket is: gs://${BUCKET}"
echo "🎉  🦄 Script execution complete."
