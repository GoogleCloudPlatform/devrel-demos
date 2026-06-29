#!/bin/bash
# ---------------------------------------------------------------------------
# Lab 2: AlloyDB Deployment Wrapper
# ---------------------------------------------------------------------------
# This script wraps the upstream deploy_alloydb.sh from
# GoogleCloudPlatform/codelabs to provision an AlloyDB cluster + instance
# with naming conventions that match this lab's codelab instructions.
#
# Designed to be kicked off early in the lab (~10-15 min to complete).
# ---------------------------------------------------------------------------
set -e
set -o pipefail

# --- Set Logging Config ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_info()  { echo -e "${CYAN}ℹ️  ${BOLD}$1${NC}"; }
print_ok()    { echo -e "${GREEN}✅ $1${NC}"; }
print_warn()  { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Capture original arguments for re-run instructions in the error trap
ORIGINAL_ARGS="$*"

# Track script success for exit trap
SUCCESS=false

# Print resource status report
print_resource_status() {
    echo ""
    print_info "=============================================="
    print_info " RESOURCE STATUS REPORT"
    print_info "=============================================="
    
    # 1. Check APIs
    echo -n "APIs Enabled: "
    ENABLED_APIS=$(gcloud services list --enabled --filter="config.name:(alloydb.googleapis.com,compute.googleapis.com,servicenetworking.googleapis.com)" --format="value(config.name)" 2>/dev/null | tr '\n' ' ')
    if [[ -z "$ENABLED_APIS" ]]; then
        echo "None"
    else
        echo "$ENABLED_APIS"
    fi

    # 2. Check PSA Network Range
    echo -n "PSA Network Range ($PSA_RANGE_NAME): "
    RANGE_EXISTS=$(gcloud compute addresses list --filter="name=$PSA_RANGE_NAME" --format="value(name)" 2>/dev/null)
    if [[ -n "$RANGE_EXISTS" ]]; then
        echo "Configured"
    else
        echo "Not found"
    fi

    # 3. Check Cluster
    echo -n "AlloyDB Cluster ($CLUSTER_NAME): "
    CLUSTER_INFO=$(gcloud alloydb clusters describe "$CLUSTER_NAME" --region="$REGION" --format="json" 2>/dev/null)
    if [[ -n "$CLUSTER_INFO" ]]; then
        CLUSTER_STATE=$(echo "$CLUSTER_INFO" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("state", "UNKNOWN"))' 2>/dev/null || echo "Exists")
        CLUSTER_TYPE=$(echo "$CLUSTER_INFO" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("subscriptionType", "STANDARD"))' 2>/dev/null || echo "UNKNOWN")
        echo "Exists (State: $CLUSTER_STATE, Type: $CLUSTER_TYPE)"
    else
        echo "Not found"
    fi

    # 4. Check Instance
    echo -n "AlloyDB Instance ($INSTANCE_NAME): "
    INSTANCE_INFO=$(gcloud alloydb instances describe "$INSTANCE_NAME" --cluster="$CLUSTER_NAME" --region="$REGION" --format="json" 2>/dev/null)
    if [[ -n "$INSTANCE_INFO" ]]; then
        INSTANCE_STATE=$(echo "$INSTANCE_INFO" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("state", "UNKNOWN"))' 2>/dev/null || echo "Exists")
        echo "Exists (State: $INSTANCE_STATE)"
    else
        echo "Not found"
    fi

    # 5. Check IAM Permissions
    echo "IAM Permissions:"
    PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)" 2>/dev/null || echo "")
    if [[ -n "$PROJECT_NUMBER" ]]; then
        ALLOYDB_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com"
        
        POLICY=$(gcloud projects get-iam-policy "$PROJECT_ID" --format="json" 2>/dev/null)
        if [[ -n "$POLICY" ]]; then
            has_role() {
                local member="$1"
                local role="$2"
                echo "$POLICY" | MEMBER="$member" ROLE="$role" python3 -c '
import sys, json, os
data = json.load(sys.stdin)
bindings = data.get("bindings", [])
member = os.environ.get("MEMBER")
role = os.environ.get("ROLE")
found = False
for b in bindings:
    if b.get("role") == role and any(m.endswith(member) or m == member for m in b.get("members", [])):
        found = True
        break
print("Granted" if found else "Not granted")
' 2>/dev/null || echo "Unknown"
            }
            
            echo "  - AlloyDB Service Agent ($ALLOYDB_SERVICE_AGENT):"
            echo "      Vertex AI User: $(has_role "serviceAccount:$ALLOYDB_SERVICE_AGENT" "roles/aiplatform.user")"
            echo "      Storage Object Viewer: $(has_role "serviceAccount:$ALLOYDB_SERVICE_AGENT" "roles/storage.objectViewer")"
            
            ALLOYDB_SA=$(echo "$CLUSTER_INFO" | python3 -c 'import sys, json; data=json.load(sys.stdin); print(data.get("serviceAccount", ""))' 2>/dev/null || echo "")
            if [[ -n "$ALLOYDB_SA" ]]; then
                echo "  - Cluster Service Account ($ALLOYDB_SA):"
                echo "      Vertex AI User: $(has_role "serviceAccount:$ALLOYDB_SA" "roles/aiplatform.user")"
                echo "      Storage Object Viewer: $(has_role "serviceAccount:$ALLOYDB_SA" "roles/storage.objectViewer")"
            fi
        else
            echo "  - Could not retrieve IAM policy"
        fi
    else
        echo "  - Could not retrieve project number for IAM checks"
    fi
    print_info "=============================================="
    echo ""
}

cleanup() {
    set +e
    # If the script failed, print the error message and the status report
    if [ "$SUCCESS" = false ]; then
        echo ""
        print_error "❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌"
        print_error " ERROR: AlloyDB deployment failed!"
        print_error " The setup script did not complete successfully."
        if [ -f "${LOG_FILE:-}" ]; then
            print_error " Review the output above or check alloydb_deploy.log."
        else
            print_error " Review the output above."
        fi
        print_error " ----------------------------------------------"
        print_error " Directions to resolve:"
        print_error " 1. Check the resource status report below to see what failed."
        print_error " 2. Verify that your REGION variable matches your assigned lab region."
        print_error " 3. Re-execute this script to attempt re-deployment:"
        print_error "    $0 ${ORIGINAL_ARGS}"
        print_error " 4. If quota or permission errors persist, end the lab and start a new lab session."
        print_error "❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌ ❌"
        echo ""
        print_resource_status 2>/dev/null || print_warn "Could not retrieve full resource status."
    fi
}
trap cleanup EXIT

# --- Command line argument parsing ---
CLUSTER_TYPE_REQ="STANDARD"

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --trial|-t)
            CLUSTER_TYPE_REQ="TRIAL"
            shift
            ;;
        *)
            print_error "Unknown parameter passed: $1"
            print_info "Usage: $0 [--trial|-t]"
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LAB_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${LAB_DIR}/.env"

# Load environment from .env if it exists
if [ -f "$ENV_FILE" ]; then
    print_info "Found existing environment file: $ENV_FILE"
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ "$line" =~ ^[[:space:]]*# || -z "$line" ]] && continue
        export "$line"
    done < "$ENV_FILE"
fi

# --- Lab-specific configuration ---
export CLUSTER_NAME="lost-cargo-cluster"
export INSTANCE_NAME="lost-cargo-instance"
export NETWORK="default"
export PSA_RANGE_NAME="psa-range"
export PASSWORD="lost-cargo"
export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [ -z "$REGION" ]; then
    print_error "REGION environment variable is not set."
    print_info "   This script runs without prompting for input."
    print_info "   Please export REGION first, or run scripts/setup_lab.sh to create .env."
    print_info "   Example: export REGION=us-central1"
    exit 1
fi
export REGION

LOG_FILE="${LAB_DIR}/alloydb_deploy.log"

# Check for valid Project ID
if [[ -z "$PROJECT_ID" ]]; then
  print_error "No Google Cloud Project ID detected."
  print_info "   Please run 'gcloud config set project YOUR_PROJECT_ID' first."
  exit 1
fi

# Write environment variables immediately to .env if not already created
if [ ! -f "$ENV_FILE" ]; then
    print_info "Creating environment file: $ENV_FILE"
    echo "PROJECT_ID=$PROJECT_ID" > "$ENV_FILE"
    echo "REGION=$REGION" >> "$ENV_FILE"
fi

print_info "=============================================="
print_info " Lab 2: AlloyDB Deployment"
print_info "=============================================="
print_info " Project:  ${PROJECT_ID}"
print_info " Region:   ${REGION}"
print_info " Cluster:  ${CLUSTER_NAME}"
print_info " Instance: ${INSTANCE_NAME}"
print_info " Log file: ${LOG_FILE}"
print_info "=============================================="

# --- [1/4] Start AlloyDB deployment (takes ~10 minutes) ---
print_info "[1/4] Starting AlloyDB deployment (this takes ~10 minutes)..."
(
  set -e

  # 1. Enable required APIs
  print_info "Enabling required APIs..."
  gcloud services enable alloydb.googleapis.com \
                         compute.googleapis.com \
                         servicenetworking.googleapis.com \
                         --quiet

  # 2. Evaluate and prepare network for Private Service Access (PSA)
  print_info "Checking network for PSA..."

  # Ensure our range exists
  RANGE_EXISTS=$(gcloud compute addresses list --filter="name=$PSA_RANGE_NAME" --format="value(name)")
  if [[ -z "$RANGE_EXISTS" ]]; then
      print_info "Creating PSA range: $PSA_RANGE_NAME"
      gcloud compute addresses create $PSA_RANGE_NAME \
          --global \
          --purpose=VPC_PEERING \
          --prefix-length=24 \
          --network=$NETWORK
  fi

  # Get existing peering connection info
  PEERING_INFO=$(gcloud services vpc-peerings list --network=$NETWORK --service=servicenetworking.googleapis.com --format="json" 2>/dev/null)

  if [[ "$PEERING_INFO" == "[]" || -z "$PEERING_INFO" ]]; then
      print_info "PSA Peering not found. Connecting service networking..."
      PEER_ATTEMPT=1
      PEER_MAX=4
      PEER_DELAY=10
      while [ $PEER_ATTEMPT -le $PEER_MAX ]; do
          if gcloud services vpc-peerings connect \
              --service=servicenetworking.googleapis.com \
              --ranges=$PSA_RANGE_NAME \
              --network=$NETWORK; then
              print_ok "PSA Peering connected successfully."
              break
          else
              if [ $PEER_ATTEMPT -lt $PEER_MAX ]; then
                  print_warn "Service Networking service agent provisioning delay encountered. Retrying in ${PEER_DELAY}s (Attempt $PEER_ATTEMPT/$PEER_MAX)..."
                  sleep $PEER_DELAY
                  PEER_ATTEMPT=$((PEER_ATTEMPT + 1))
              else
                  print_error "Failed to connect VPC peering after $PEER_MAX attempts."
                  exit 1
              fi
          fi
      done
  else
      print_info "PSA Peering exists. Checking if range $PSA_RANGE_NAME is included..."
      EXISTING_RANGES=$(echo "$PEERING_INFO" | python3 -c "import sys, json; data=json.load(sys.stdin); print(','.join(data[0]['reservedPeeringRanges'])) if data else print('')")
      
      if [[ $EXISTING_RANGES != *"$PSA_RANGE_NAME"* ]]; then
          print_info "Range $PSA_RANGE_NAME not in peering. Current ranges: $EXISTING_RANGES"
          print_info "Updating connection..."
          NEW_RANGES="${EXISTING_RANGES},${PSA_RANGE_NAME}"
          gcloud services vpc-peerings update \
              --service=servicenetworking.googleapis.com \
              --ranges=$NEW_RANGES \
              --network=$NETWORK
      else
          print_ok "PSA Peering and range already configured."
      fi
  fi

  # 3. Handle Cluster Creation or Detection
  print_info "Checking if cluster $CLUSTER_NAME exists..."
  EXISTING_CLUSTER=$(gcloud alloydb clusters list --region=$REGION --filter="name:clusters/$CLUSTER_NAME" --format="json" 2>/dev/null)

  if [[ "$EXISTING_CLUSTER" != "[]" && -n "$EXISTING_CLUSTER" ]]; then
      print_info "Cluster $CLUSTER_NAME already exists."
      CLUSTER_TYPE=$(echo "$EXISTING_CLUSTER" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0].get('subscriptionType', 'STANDARD')) if data else print('STANDARD')")
      print_info "Existing cluster type: $CLUSTER_TYPE"
      if [[ "$CLUSTER_TYPE" == "TRIAL" ]]; then
          CPU_COUNT=8
      else
          CPU_COUNT=2
      fi
  else
      print_info "Cluster $CLUSTER_NAME not found. Attempting to create..."
      set +e
      
      if [[ "$CLUSTER_TYPE_REQ" == "TRIAL" ]]; then
          print_info "Attempting to create Free Trial cluster..."
          CPU_COUNT=8
          gcloud alloydb clusters create $CLUSTER_NAME \
              --region=$REGION \
              --network=$NETWORK \
              --password=$PASSWORD \
              --subscription-type=TRIAL \
              --quiet
          
          if [ $? -eq 0 ]; then
              CLUSTER_TYPE="TRIAL"
          else
              print_warn "Free Trial cluster creation failed. Falling back to Standard cluster..."
              CLUSTER_TYPE_REQ="STANDARD"
          fi
      fi

      if [[ "$CLUSTER_TYPE_REQ" == "STANDARD" ]]; then
          print_info "Attempting to create Standard cluster..."
          CPU_COUNT=2
          gcloud alloydb clusters create $CLUSTER_NAME \
              --region=$REGION \
              --network=$NETWORK \
              --password=$PASSWORD \
              --subscription-type=STANDARD \
              --quiet
          
          if [ $? -ne 0 ]; then
              print_error "Failed to create AlloyDB cluster."
              exit 1
          fi
          CLUSTER_TYPE="STANDARD"
      fi
      set -e
  fi

  # 4. Create Primary Instance if not exists
  print_info "Checking if instance $INSTANCE_NAME exists in cluster $CLUSTER_NAME..."
  EXISTING_INSTANCE=$(gcloud alloydb instances list --cluster=$CLUSTER_NAME --region=$REGION --filter="name:instances/$INSTANCE_NAME" --format="value(name)" 2>/dev/null)

  if [[ -z "$EXISTING_INSTANCE" ]]; then
      print_info "Creating primary instance: $INSTANCE_NAME ($CPU_COUNT vCPUs for $CLUSTER_TYPE cluster)"
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
      print_ok "Instance $INSTANCE_NAME already exists. Skipping creation."
  fi
) 2>&1 | tee "${LOG_FILE}"

# --- [2/4] Configure instance settings (IAM, Data API) ---
print_info "[2/4] Configuring instance settings (IAM, Data API)..."
print_info "Enabling IAM authentication flag on the instance..."
gcloud alloydb instances update "${INSTANCE_NAME}" \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --database-flags=password.enforce_complexity=on,alloydb.iam_authentication=on \
  --quiet || print_warn "Failed to enable IAM authentication flag."

# Wait for the instance to finish updating the database flags (avoiding 409 conflict)
print_info "Waiting for instance to finish updating database flags..."
MAX_WAIT=300
ELAPSED=0
while true; do
  RECONCILING=$(gcloud alloydb instances describe "${INSTANCE_NAME}" \
    --cluster="${CLUSTER_NAME}" \
    --region="${REGION}" \
    --format="value(reconciling)" 2>/dev/null || echo "False")
  if [[ "$RECONCILING" != "True" ]]; then
    break
  fi
  ELAPSED=$((ELAPSED + 10))
  if [[ $ELAPSED -ge $MAX_WAIT ]]; then
    print_warn "Timed out waiting for instance reconciliation after ${MAX_WAIT}s. Proceeding..."
    break
  fi
  print_info "      Instance is updating, waiting 10s..."
  sleep 10
done

print_info "Enabling Data API access on the instance..."
curl -X PATCH \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
"https://alloydb.googleapis.com/v1beta/projects/${PROJECT_ID}/locations/${REGION}/clusters/${CLUSTER_NAME}/instances/${INSTANCE_NAME}?updateMask=dataApiAccess" \
-d '{ "dataApiAccess": "ENABLED" }' > /dev/null 2>&1 || print_warn "Failed to enable Data API access."

print_info "Resetting postgres password to 'lost-cargo'..."
gcloud alloydb users set-password postgres \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --password="lost-cargo" \
  --quiet || print_warn "Failed to reset postgres password."

# --- [3/4] Create database user for current IAM principal ---
CURRENT_USER=$(gcloud config get-value account)
print_info "[3/4] Creating database user for current IAM principal: ${CURRENT_USER}..."
gcloud alloydb users create "${CURRENT_USER}" \
  --cluster="${CLUSTER_NAME}" \
  --region="${REGION}" \
  --type=IAM_BASED \
  --superuser=true || print_warn "Failed to create database user for ${CURRENT_USER}. You may need to create it manually."

# --- [4/4] Configure IAM permissions for AlloyDB Service Agent ---
print_info "[4/4] Configuring IAM permissions for AlloyDB..."

# Retrieve project number for the project-wide AlloyDB Service Agent
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)" 2>/dev/null || echo "")
if [[ -n "$PROJECT_NUMBER" ]]; then
  ALLOYDB_SERVICE_AGENT="service-${PROJECT_NUMBER}@gcp-sa-alloydb.iam.gserviceaccount.com"
  
  print_info "      Granting Vertex AI access to AlloyDB Service Agent..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SERVICE_AGENT}" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet || print_warn "Failed to grant Vertex AI User role to AlloyDB Service Agent."
    
  print_info "      Granting GCS access to AlloyDB Service Agent..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SERVICE_AGENT}" \
    --role="roles/storage.objectViewer" \
    --condition=None \
    --quiet || print_warn "Failed to grant storage.objectViewer to AlloyDB Service Agent."
fi

# Also grant to cluster-specific service account if retrieved
ALLOYDB_SA=$(gcloud alloydb clusters describe "${CLUSTER_NAME}" \
  --region="${REGION}" \
  --format="value(serviceAccount)" 2>/dev/null || echo "")

if [[ -n "$ALLOYDB_SA" ]]; then
  print_info "      Granting Vertex AI access to cluster-specific service account..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SA}" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet || print_warn "Failed to grant Vertex AI User role to cluster-specific service account."
    
  print_info "      Granting GCS access to cluster-specific service account..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --format=none \
    --member="serviceAccount:${ALLOYDB_SA}" \
    --role="roles/storage.objectViewer" \
    --condition=None \
    --quiet || print_warn "Failed to grant storage.objectViewer to cluster-specific service account."
fi

SUCCESS=true
echo ""
print_ok "=============================================="
print_ok " AlloyDB deployment complete!"
echo ""
print_info " Cluster:  ${CLUSTER_NAME}"
print_info " Instance: ${INSTANCE_NAME}"
print_info " Region:   ${REGION}"
echo ""
print_info " Connect via AlloyDB Studio in the Cloud Console:"
print_info " AlloyDB → Clusters → ${CLUSTER_NAME} → AlloyDB Studio"
print_ok "=============================================="
