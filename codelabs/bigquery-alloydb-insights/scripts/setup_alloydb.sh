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

# --- [1/4] Start AlloyDB deployment (takes ~10 minutes) ---
echo "[1/4] Starting AlloyDB deployment (this takes ~10 minutes)..."
(
  set -e
  NETWORK="default"
  PSA_RANGE_NAME="psa-range"
  PASSWORD="lost-cargo"

  # 1. Enable required APIs
  echo "Enabling required APIs..."
  gcloud services enable alloydb.googleapis.com \
                         compute.googleapis.com \
                         servicenetworking.googleapis.com \
                         --quiet

  # 2. Evaluate and prepare network for Private Service Access (PSA)
  echo "Checking network for PSA..."

  # Ensure our range exists
  RANGE_EXISTS=$(gcloud compute addresses list --filter="name=$PSA_RANGE_NAME" --format="value(name)")
  if [[ -z "$RANGE_EXISTS" ]]; then
      echo "Creating PSA range: $PSA_RANGE_NAME"
      gcloud compute addresses create $PSA_RANGE_NAME \
          --global \
          --purpose=VPC_PEERING \
          --prefix-length=24 \
          --network=$NETWORK
  fi

  # Get existing peering connection info
  PEERING_INFO=$(gcloud services vpc-peerings list --network=$NETWORK --service=servicenetworking.googleapis.com --format="json" 2>/dev/null)

  if [[ "$PEERING_INFO" == "[]" || -z "$PEERING_INFO" ]]; then
      echo "PSA Peering not found. Connecting service networking..."
      gcloud services vpc-peerings connect \
          --service=servicenetworking.googleapis.com \
          --ranges=$PSA_RANGE_NAME \
          --network=$NETWORK
  else
      echo "PSA Peering exists. Checking if range $PSA_RANGE_NAME is included..."
      EXISTING_RANGES=$(echo "$PEERING_INFO" | python3 -c "import sys, json; data=json.load(sys.stdin); print(','.join(data[0]['reservedPeeringRanges'])) if data else print('')")
      
      if [[ $EXISTING_RANGES != *"$PSA_RANGE_NAME"* ]]; then
          echo "Range $PSA_RANGE_NAME not in peering. Current ranges: $EXISTING_RANGES"
          echo "Updating connection..."
          NEW_RANGES="${EXISTING_RANGES},${PSA_RANGE_NAME}"
          gcloud services vpc-peerings update \
              --service=servicenetworking.googleapis.com \
              --ranges=$NEW_RANGES \
              --network=$NETWORK
      else
          echo "PSA Peering and range already configured."
      fi
  fi

  # 3. Handle Cluster Creation or Detection
  echo "Checking if cluster $CLUSTER_NAME exists..."
  EXISTING_CLUSTER=$(gcloud alloydb clusters list --region=$REGION --filter="name:clusters/$CLUSTER_NAME" --format="json" 2>/dev/null)

  if [[ "$EXISTING_CLUSTER" != "[]" && -n "$EXISTING_CLUSTER" ]]; then
      echo "Cluster $CLUSTER_NAME already exists."
      CLUSTER_TYPE=$(echo "$EXISTING_CLUSTER" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0].get('subscriptionType', 'STANDARD')) if data else print('STANDARD')")
      echo "Existing cluster type: $CLUSTER_TYPE"
      if [[ "$CLUSTER_TYPE" == "TRIAL" ]]; then
          CPU_COUNT=8
      else
          CPU_COUNT=2
      fi
  else
      echo "Cluster $CLUSTER_NAME not found. Attempting to create..."
      set +e
      CPU_COUNT=8
      gcloud alloydb clusters create $CLUSTER_NAME \
          --region=$REGION \
          --network=$NETWORK \
          --password=$PASSWORD \
          --subscription-type=TRIAL \
          --quiet

      if [ $? -ne 0 ]; then
          echo "Free Trial cluster creation failed or not available. Attempting Standard cluster..."
          CPU_COUNT=2
          gcloud alloydb clusters create $CLUSTER_NAME \
              --region=$REGION \
              --network=$NETWORK \
              --password=$PASSWORD \
              --subscription-type=STANDARD \
              --quiet
          
          if [ $? -ne 0 ]; then
              echo "Error: Failed to create AlloyDB cluster."
              exit 1
          fi
          CLUSTER_TYPE="STANDARD"
      else
          CLUSTER_TYPE="TRIAL"
      fi
      set -e
  fi

  # 4. Create Primary Instance if not exists
  echo "Checking if instance $INSTANCE_NAME exists in cluster $CLUSTER_NAME..."
  EXISTING_INSTANCE=$(gcloud alloydb instances list --cluster=$CLUSTER_NAME --region=$REGION --filter="name:instances/$INSTANCE_NAME" --format="value(name)" 2>/dev/null)

  if [[ -z "$EXISTING_INSTANCE" ]]; then
      echo "Creating primary instance: $INSTANCE_NAME ($CPU_COUNT vCPUs for $CLUSTER_TYPE cluster)"
      gcloud alloydb instances create $INSTANCE_NAME \
          --cluster=$CLUSTER_NAME \
          --region=$REGION \
          --cpu-count=$CPU_COUNT \
          --instance-type=PRIMARY \
          --assign-inbound-public-ip=ASSIGN_IPV4 \
          --outbound-public-ip \
          --database-flags=password.enforce_complexity=on \
          --quiet
  else
      echo "Instance $INSTANCE_NAME already exists. Skipping creation."
  fi
) 2>&1 | tee "${LOG_FILE}"

# --- [2/4] Configure instance settings (IAM, Data API) ---
echo "[2/4] Configuring instance settings (IAM, Data API)..."
echo "Enabling IAM authentication flag on the instance..."
gcloud alloydb instances update "${INSTANCE_NAME}" \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --database-flags=password.enforce_complexity=on,alloydb.iam_authentication=on \
  --quiet || echo "⚠️ Warning: Failed to enable IAM authentication flag."

# Wait for the instance to finish updating the database flags (avoiding 409 conflict)
echo "Waiting for instance to finish updating database flags..."
while true; do
  RECONCILING=$(gcloud alloydb instances describe "${INSTANCE_NAME}" \
    --cluster="${CLUSTER_NAME}" \
    --region="${REGION}" \
    --format="value(reconciling)" 2>/dev/null || echo "False")
  if [[ "$RECONCILING" != "True" ]]; then
    break
  fi
  echo "      Instance is updating, waiting 10s..."
  sleep 10
done

echo "Enabling Data API access on the instance..."
curl -X PATCH \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
"https://alloydb.googleapis.com/v1beta/projects/${PROJECT_ID}/locations/${REGION}/clusters/${CLUSTER_NAME}/instances/${INSTANCE_NAME}?updateMask=dataApiAccess" \
-d '{ "dataApiAccess": "ENABLED" }' || echo "⚠️ Warning: Failed to enable Data API access."

echo "Resetting postgres password to 'lost-cargo'..."
gcloud alloydb users set-password postgres \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --password="lost-cargo" \
  --quiet || echo "⚠️ Warning: Failed to reset postgres password."

# --- [3/4] Create database user for current IAM principal ---
CURRENT_USER=$(gcloud config get-value account)
echo "[3/4] Creating database user for current IAM principal: ${CURRENT_USER}..."
gcloud alloydb users create "${CURRENT_USER}" \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --type=IAM_BASED \
  --superuser=true || echo "⚠️ Warning: Failed to create database user for ${CURRENT_USER}. You may need to create it manually."

# --- [4/4] Configure IAM permissions for AlloyDB Service Agent ---
echo "[4/4] Configuring IAM permissions for AlloyDB..."

# Retrieve project number for the project-wide AlloyDB Service Agent
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)" 2>/dev/null || echo "")
if [[ -n "$PROJECT_NUMBER" ]]; then
  ALLOYDB_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com"
  
  echo "      Granting Vertex AI access to AlloyDB Service Agent..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SERVICE_AGENT}" \
    --role="roles/aiplatform.user" \
    --quiet || echo "⚠️ Warning: Failed to grant Vertex AI User role to AlloyDB Service Agent."
    
  echo "      Granting GCS access to AlloyDB Service Agent..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SERVICE_AGENT}" \
    --role="roles/storage.objectViewer" \
    --quiet || echo "⚠️ Warning: Failed to grant storage.objectViewer to AlloyDB Service Agent."
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
    
  echo "      Granting GCS access to cluster-specific service account..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SA}" \
    --role="roles/storage.objectViewer" \
    --quiet || echo "⚠️ Warning: Failed to grant storage.objectViewer to cluster-specific service account."
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
