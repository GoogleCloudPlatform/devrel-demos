#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Exit immediately if a command exits with a non-zero status,
# if any undefined variable is referenced, or if any pipeline fails
set -euo pipefail

# Start timing
SCRIPT_START_TIME=$(date +%s)

# ------------------------------------------------------------------------------
# Terminal Styling & Logging Helpers
# ------------------------------------------------------------------------------
# Colors (only if running in a terminal)
if [ -t 1 ]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[0;33m'
  BLUE='\033[0;34m'
  PURPLE='\033[0;35m'
  CYAN='\033[0;36m'
  BOLD='\033[1m'
  NC='\033[0m' # No Color
else
  RED=''
  GREEN=''
  YELLOW=''
  BLUE=''
  PURPLE=''
  CYAN=''
  BOLD=''
  NC=''
fi

log_header() {
  echo -e "\n${BOLD}${BLUE}======================================================================${NC}"
  echo -e "${BOLD}${BLUE}  $1${NC}"
  echo -e "${BOLD}${BLUE}======================================================================${NC}"
}

log_step() {
  echo -e "\n${BOLD}${CYAN}[Step $1] $2${NC}"
}

log_info() {
  echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
  echo -e "${RED}❌ ERROR: $1${NC}"
}

prefix_log() {
  local prefix=$1
  local color=$2
  while IFS= read -r line || [[ -n "$line" ]]; do
    echo -e "${color}[${prefix}]${NC} ${line}"
  done
}

# ------------------------------------------------------------------------------
# CLI Parameter & Mode Configuration
# ------------------------------------------------------------------------------
NON_INTERACTIVE=false

# Default toggles for each step
RUN_APIS=true
RUN_REGISTRY=true
RUN_GKE=true
RUN_PUBSUB=true
RUN_BQ=true
RUN_BUILD=true
RUN_K8S=true

# Track if the user passed ANY positive execution flags
HAS_POSITIVE_FLAG=false

for arg in "$@"; do
  case $arg in
    --apis|--registry|--gke|--pubsub|--bq|--build|--k8s)
      HAS_POSITIVE_FLAG=true
      ;;
  esac
done

# If a positive flag was supplied, default all other steps to false
if [ "$HAS_POSITIVE_FLAG" = "true" ]; then
  RUN_APIS=false
  RUN_REGISTRY=false
  RUN_GKE=false
  RUN_PUBSUB=false
  RUN_BQ=false
  RUN_BUILD=false
  RUN_K8S=false
fi

# Parse all command-line arguments
for arg in "$@"; do
  case $arg in
    --non-interactive)
      NON_INTERACTIVE=true
      ;;
    --apis) RUN_APIS=true ;;
    --no-apis) RUN_APIS=false ;;
    --registry) RUN_REGISTRY=true ;;
    --no-registry) RUN_REGISTRY=false ;;
    --gke) RUN_GKE=true ;;
    --no-gke) RUN_GKE=false ;;
    --pubsub) RUN_PUBSUB=true ;;
    --no-pubsub) RUN_PUBSUB=false ;;
    --bq) RUN_BQ=true ;;
    --no-bq) RUN_BQ=false ;;
    --build) RUN_BUILD=true ;;
    --no-build) RUN_BUILD=false ;;
    --k8s) RUN_K8S=true ;;
    --no-k8s) RUN_K8S=false ;;
    *)
      # Silent ignore or warning for unknown options
      ;;
  esac
done

# Detect if terminal is interactive
if [ "$NON_INTERACTIVE" = "false" ] && [ ! -t 0 ]; then
  log_info "Non-interactive shell detected. Automatically enabling non-interactive mode."
  NON_INTERACTIVE=true
fi

log_header "GOOGLE CLOUD Infrastructure Provisioning, Build & K8s Deployment"

# ------------------------------------------------------------------------------
# Step 1: Environment Configuration & Validation
# ------------------------------------------------------------------------------
log_step "1/11" "Environment Configuration & Validation ⚙️"

ENV_FILE=".env"
ENV_EXAMPLE=".env.example"

# Helper to prompt user for a variable value with default
prompt_var() {
  local var_name=$1
  local description=$2
  local default_val=$3
  local user_input

  echo -e "\n${BOLD}${var_name}${NC}: ${description}"
  read -p "  Enter value [Default: ${default_val}]: " user_input

  if [ -z "${user_input}" ]; then
    eval "${var_name}=\"${default_val}\""
  else
    eval "${var_name}=\"${user_input}\""
  fi
}

# Initialize config values from existing .env if it exists
existing_GOOGLE_CLOUD_PROJECT=""
existing_GOOGLE_CLOUD_REGION=""
existing_ARTIFACT_REGISTRY_LOCATION=""
existing_CLUSTER_NAME=""
existing_ARTIFACT_REPO_NAME=""
existing_TASKS_TOPIC=""
existing_RESULTS_TOPIC=""
existing_TASKS_SUBSCRIPTION=""
existing_RESULTS_SUB=""
existing_BQ_DATASET=""

if [ -f "$ENV_FILE" ]; then
  log_info "Found existing $ENV_FILE file. Parsing values..."
  # Export existing variables safely to parse them
  while IFS= read -r line || [ -n "$line" ]; do
    # Skip comments and empty lines
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "$line" ]]; then
      continue
    fi
    if [[ "$line" =~ ^([^=]+)=(.*)$ ]]; then
      var_name="${BASH_REMATCH[1]}"
      var_val="${BASH_REMATCH[2]}"
      # Strip trailing carriage returns if any
      var_val="${var_val%$'\r'}"
      # Remove surrounding quotes if any
      var_val="${var_val#\"}"
      var_val="${var_val%\"}"
      var_val="${var_val#\'}"
      var_val="${var_val%\'}"

      case "$var_name" in
        GOOGLE_CLOUD_PROJECT) existing_GOOGLE_CLOUD_PROJECT="$var_val" ;;
        GOOGLE_CLOUD_REGION) existing_GOOGLE_CLOUD_REGION="$var_val" ;;
        ARTIFACT_REGISTRY_LOCATION) existing_ARTIFACT_REGISTRY_LOCATION="$var_val" ;;
        CLUSTER_NAME) existing_CLUSTER_NAME="$var_val" ;;
        ARTIFACT_REPO_NAME) existing_ARTIFACT_REPO_NAME="$var_val" ;;
        TASKS_TOPIC) existing_TASKS_TOPIC="$var_val" ;;
        RESULTS_TOPIC) existing_RESULTS_TOPIC="$var_val" ;;
        TASKS_SUBSCRIPTION) existing_TASKS_SUBSCRIPTION="$var_val" ;;
        RESULTS_SUB) existing_RESULTS_SUB="$var_val" ;;
        BQ_DATASET) existing_BQ_DATASET="$var_val" ;;
      esac
    fi
  done < "$ENV_FILE"
fi

is_val_complete() {
  local val=$1
  if [ -z "$val" ] || [[ "$val" == *"<"* ]] || [[ "$val" == *">"* ]] || [[ "$val" == *"your-project-id-here"* ]]; then
    return 1 # Incomplete
  fi
  return 0 # Complete
}

# Check if .env is complete and contains no placeholders
is_env_complete=true
for var in GOOGLE_CLOUD_PROJECT GOOGLE_CLOUD_REGION ARTIFACT_REGISTRY_LOCATION CLUSTER_NAME ARTIFACT_REPO_NAME TASKS_TOPIC RESULTS_TOPIC TASKS_SUBSCRIPTION RESULTS_SUB BQ_DATASET; do
  val=""
  eval "val=\${existing_$var:-}"
  if ! is_val_complete "$val"; then
    is_env_complete=false
  fi
done

user_input_occurred=false

if [ "$is_env_complete" = "true" ]; then
  log_success "Complete $ENV_FILE configuration found. Proceeding immediately without prompting."
  GOOGLE_CLOUD_PROJECT="$existing_GOOGLE_CLOUD_PROJECT"
  GOOGLE_CLOUD_REGION="$existing_GOOGLE_CLOUD_REGION"
  ARTIFACT_REGISTRY_LOCATION="$existing_ARTIFACT_REGISTRY_LOCATION"
  CLUSTER_NAME="$existing_CLUSTER_NAME"
  ARTIFACT_REPO_NAME="$existing_ARTIFACT_REPO_NAME"
  TASKS_TOPIC="$existing_TASKS_TOPIC"
  RESULTS_TOPIC="$existing_RESULTS_TOPIC"
  TASKS_SUBSCRIPTION="$existing_TASKS_SUBSCRIPTION"
  RESULTS_SUB="$existing_RESULTS_SUB"
  BQ_DATASET="$existing_BQ_DATASET"
else
  if [ "$NON_INTERACTIVE" = "true" ]; then
    log_error "Incomplete configuration file '$ENV_FILE' and running in non-interactive mode."
    log_info "Please ensure all variables are populated in $ENV_FILE."
    exit 1
  fi

  log_info "Some configuration variables are missing or incomplete. Let's prompt for them:"
  user_input_occurred=true

  # Google Cloud Project
  if is_val_complete "$existing_GOOGLE_CLOUD_PROJECT"; then
    GOOGLE_CLOUD_PROJECT="$existing_GOOGLE_CLOUD_PROJECT"
  else
    detected_project=""
    if command -v gcloud &> /dev/null; then
      detected_project=$(gcloud config get-value project 2>/dev/null || true)
    fi
    project_id_default="${existing_GOOGLE_CLOUD_PROJECT:-${detected_project}}"
    if [ -z "$project_id_default" ] || [[ "$project_id_default" == *"(unset)"* ]]; then
      project_id_default="your-project-id-here"
    fi

    while [ -z "${GOOGLE_CLOUD_PROJECT:-}" ] || [ "$GOOGLE_CLOUD_PROJECT" = "your-project-id-here" ]; do
      prompt_var "GOOGLE_CLOUD_PROJECT" "Google Cloud Project ID (must be a valid active GCP project)" "$project_id_default"
      if [ -z "${GOOGLE_CLOUD_PROJECT:-}" ] || [ "$GOOGLE_CLOUD_PROJECT" = "your-project-id-here" ]; then
        log_warning "Project ID cannot be empty or 'your-project-id-here'. Please try again."
      fi
    done
  fi

  # Region
  if is_val_complete "$existing_GOOGLE_CLOUD_REGION"; then
    GOOGLE_CLOUD_REGION="$existing_GOOGLE_CLOUD_REGION"
  else
    # Randomly select a default region from a predefined list of supported regions
    REGIONS=("us-central1")
    RANDOM_REGION=${REGIONS[$RANDOM % ${#REGIONS[@]}]}
    prompt_var "GOOGLE_CLOUD_REGION" "GCP Target Region" "${existing_GOOGLE_CLOUD_REGION:-$RANDOM_REGION}"
  fi

  # Registry Location
  if is_val_complete "$existing_ARTIFACT_REGISTRY_LOCATION"; then
    ARTIFACT_REGISTRY_LOCATION="$existing_ARTIFACT_REGISTRY_LOCATION"
  else
    prompt_var "ARTIFACT_REGISTRY_LOCATION" "Artifact Registry Docker Location" "${existing_ARTIFACT_REGISTRY_LOCATION:-${GOOGLE_CLOUD_REGION:-us-central1}}"
  fi

  # Cluster Name
  if is_val_complete "$existing_CLUSTER_NAME"; then
    CLUSTER_NAME="$existing_CLUSTER_NAME"
  else
    prompt_var "CLUSTER_NAME" "GKE Standard Cluster Name" "${existing_CLUSTER_NAME:-hackathon-judge-cluster}"
  fi

  # Repository Name
  if is_val_complete "$existing_ARTIFACT_REPO_NAME"; then
    ARTIFACT_REPO_NAME="$existing_ARTIFACT_REPO_NAME"
  else
    prompt_var "ARTIFACT_REPO_NAME" "Artifact Registry Repository Name" "${existing_ARTIFACT_REPO_NAME:-hackathon-judge-repo}"
  fi

  # Tasks Topic
  if is_val_complete "$existing_TASKS_TOPIC"; then
    TASKS_TOPIC="$existing_TASKS_TOPIC"
  else
    prompt_var "TASKS_TOPIC" "Pub/Sub Judging Tasks Topic Name" "${existing_TASKS_TOPIC:-judging-tasks}"
  fi

  # Results Topic
  if is_val_complete "$existing_RESULTS_TOPIC"; then
    RESULTS_TOPIC="$existing_RESULTS_TOPIC"
  else
    prompt_var "RESULTS_TOPIC" "Pub/Sub Judging Results Topic Name" "${existing_RESULTS_TOPIC:-judging-results}"
  fi

  # Tasks Subscription
  if is_val_complete "$existing_TASKS_SUBSCRIPTION"; then
    TASKS_SUBSCRIPTION="$existing_TASKS_SUBSCRIPTION"
  else
    prompt_var "TASKS_SUBSCRIPTION" "Agent Judging Tasks Subscription Name" "${existing_TASKS_SUBSCRIPTION:-judging-tasks-agent-sub}"
  fi

  # Results Subscription
  if is_val_complete "$existing_RESULTS_SUB"; then
    RESULTS_SUB="$existing_RESULTS_SUB"
  else
    prompt_var "RESULTS_SUB" "Backend Judging Results Subscription Name" "${existing_RESULTS_SUB:-judging-results-backend-sub}"
  fi

  # BigQuery Dataset
  if is_val_complete "$existing_BQ_DATASET"; then
    BQ_DATASET="$existing_BQ_DATASET"
  else
    prompt_var "BQ_DATASET" "BigQuery Dataset Name" "${existing_BQ_DATASET:-hackathon_judge}"
  fi

  # Keep backup of old env just in case
  if [ -f "$ENV_FILE" ]; then
    log_info "Backing up existing $ENV_FILE as $ENV_FILE.old"
    cp "$ENV_FILE" "$ENV_FILE.old"
  fi

  # Write new .env
  log_info "Writing configurations to $ENV_FILE..."
  cat << EOF > "$ENV_FILE"
# ==============================================================================
# Generated Hackathon Judge Environment Settings
# ==============================================================================

# Google Cloud Core
GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
GOOGLE_CLOUD_REGION=${GOOGLE_CLOUD_REGION}
ARTIFACT_REGISTRY_LOCATION=${ARTIFACT_REGISTRY_LOCATION}

# Infrastructure Names
CLUSTER_NAME=${CLUSTER_NAME}
ARTIFACT_REPO_NAME=${ARTIFACT_REPO_NAME}

# Pub/Sub Architecture Setup
TASKS_TOPIC=${TASKS_TOPIC}
RESULTS_TOPIC=${RESULTS_TOPIC}
TASKS_SUBSCRIPTION=${TASKS_SUBSCRIPTION}
RESULTS_SUB=${RESULTS_SUB}

# BigQuery Analytics Setup
BQ_DATASET=${BQ_DATASET}
EOF

  log_success "Successfully wrote $ENV_FILE configuration!"
fi

# Source the variables
log_info "Loading configuration from $ENV_FILE..."
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Final validation double-check
if [ -z "${GOOGLE_CLOUD_PROJECT:-}" ] || [ "$GOOGLE_CLOUD_PROJECT" = "your-project-id-here" ]; then
  log_error "GOOGLE_CLOUD_PROJECT is not set correctly in $ENV_FILE."
  exit 1
fi

log_info "Configuration Active:"
echo "  Project: ${GOOGLE_CLOUD_PROJECT}"
echo "  Region:  ${GOOGLE_CLOUD_REGION}"
echo "  Cluster: ${CLUSTER_NAME}"

# ------------------------------------------------------------------------------
# Step 2: Google Cloud CLI & Authentication Check
# ------------------------------------------------------------------------------
log_step "2/11" "Google Cloud CLI & Authentication Check 🔍"

if ! command -v gcloud &> /dev/null; then
  log_error "gcloud CLI is not installed."
  log_info "Please install it from: https://cloud.google.com/sdk/docs/install"
  exit 1
fi

if ! command -v bq &> /dev/null; then
  log_error "bq CLI (BigQuery command-line tool) is not installed."
  log_info "Please ensure BigQuery tools are available (run 'gcloud components install bq')."
  exit 1
fi

if ! command -v kubectl &> /dev/null; then
  log_error "kubectl CLI is not installed."
  log_info "Please install it from: https://kubernetes.io/docs/tasks/tools/"
  exit 1
fi

if ! command -v envsubst &> /dev/null; then
  log_error "envsubst is not installed."
  log_info "Please install it (usually part of 'gettext' package)."
  exit 1
fi

log_info "Checking Google Cloud Authentication status..."
if ! gcloud auth print-access-token &> /dev/null; then
  log_warning "No valid active Google Cloud credentials found."
  log_info "Please run the following commands in your terminal to authenticate:"
  echo -e "${BOLD}  gcloud auth login${NC}"
  echo -e "${BOLD}  gcloud auth application-default login${NC}"
  exit 1
fi
log_success "Google Cloud credentials are valid."

# ------------------------------------------------------------------------------
# Step 3: Configuring Target Project
# ------------------------------------------------------------------------------
log_step "3/11" "Configuring Target Project 🎯"

log_info "Setting active project in gcloud config..."
gcloud config set project "$GOOGLE_CLOUD_PROJECT"

log_info "Verifying project accessibility..."
if ! gcloud projects describe "$GOOGLE_CLOUD_PROJECT" &> /dev/null; then
  log_error "Unable to access GCP Project: '$GOOGLE_CLOUD_PROJECT'."
  log_info "Please verify that the project ID is correct, you are authenticated with the right account, and billing/permissions are configured."
  exit 1
fi
log_success "Project '$GOOGLE_CLOUD_PROJECT' is accessible and set active."

# ------------------------------------------------------------------------------
# Step 4: Enabling Google Cloud APIs
# ------------------------------------------------------------------------------
if [ "$RUN_APIS" = "true" ]; then
  log_step "4/11" "Enabling Google Cloud APIs ⚡"

  APIS_TO_ENABLE=(
    "container.googleapis.com"            # Google Kubernetes Engine
    "generativelanguage.googleapis.com"   # Gemini API
    "artifactregistry.googleapis.com"     # Artifact Registry
    "cloudbuild.googleapis.com"           # Cloud Build
    "pubsub.googleapis.com"               # Cloud Pub/Sub
    "aiplatform.googleapis.com"           # Gemini Enterprise Agent Platform (Essential for the judge agent)
    "cloudresourcemanager.googleapis.com" # Cloud Resource Manager (Required for project metadata & IAM)
    "iam.googleapis.com"                  # Identity and Access Management (IAM)
    "bigquery.googleapis.com"             # BigQuery (Essential for evaluations analytics)
    "bigqueryconnection.googleapis.com"   # BigQuery Connection API
    "storage.googleapis.com"              # Cloud Storage (Required for Agent Substrate snapshots)
  )

  log_info "Enabling required services on new project. This might take a minute..."
  # Enabling APIs is idempotent and safe to run
  if ! gcloud services enable "${APIS_TO_ENABLE[@]}"; then
    log_error "Failed to enable required Google Cloud APIs."
    log_info "Please ensure billing is enabled on the project: '$GOOGLE_CLOUD_PROJECT'."
    log_info "Verify by visiting: https://console.cloud.google.com/billing"
    exit 1
  fi
  log_success "All required Google Cloud APIs successfully enabled!"
else
  log_info "Skipping Step 4: Google Cloud APIs enablement (Bypassed by CLI flag)."
fi

# ------------------------------------------------------------------------------
# Step 5: Creating Artifact Registry Docker Repository
# ------------------------------------------------------------------------------
if [ "$RUN_REGISTRY" = "true" ]; then
  log_step "5/11" "Creating Artifact Registry Docker Repository 📦"

  log_info "Checking Artifact Registry repository: $ARTIFACT_REPO_NAME in $ARTIFACT_REGISTRY_LOCATION..."
  if ! gcloud artifacts repositories describe "$ARTIFACT_REPO_NAME" --location="$ARTIFACT_REGISTRY_LOCATION" &> /dev/null; then
    log_info "Creating Artifact Registry Docker repository..."
    if gcloud artifacts repositories create "$ARTIFACT_REPO_NAME" \
        --repository-format=docker \
        --location="$ARTIFACT_REGISTRY_LOCATION" \
        --description="Docker repository for Hackathon Judge services"; then
      log_success "Successfully created repository '$ARTIFACT_REPO_NAME'!"
    else
      log_error "Failed to create Artifact Registry repository."
      exit 1
    fi
  else
    log_success "Artifact Registry repository '$ARTIFACT_REPO_NAME' already exists in $ARTIFACT_REGISTRY_LOCATION."
  fi
else
  log_info "Skipping Step 5: Artifact Registry repository configuration (Bypassed by CLI flag)."
fi

# ------------------------------------------------------------------------------
# Step 6: Storage Bucket & READMEs (DISABLED)
# ------------------------------------------------------------------------------
log_info "Skipping Step 6: Storage Bucket & READMEs (Disabled: BigQuery AI Scoring no longer uses GCS READMEs)."

# ------------------------------------------------------------------------------
# PARALLEL EXECUTION: Steps 7, 8, 9, and 10
# ------------------------------------------------------------------------------
log_step "7-10/11" "Parallel Execution: GKE, Pub/Sub, BigQuery, and Cloud Build 🚀📨📊🛠️"
log_info "Running GKE cluster creation, Pub/Sub configuration, BigQuery configuration, and Cloud Build in parallel..."

PIDS=()
RESULTS=()


if [ "$RUN_GKE" = "true" ]; then
  (
    log_info "Starting GKE Standard cluster configuration..."

    log_info "Checking GKE Standard cluster: $CLUSTER_NAME in region $GOOGLE_CLOUD_REGION..."
    if ! gcloud container clusters describe "$CLUSTER_NAME" --region="$GOOGLE_CLOUD_REGION" &> /dev/null; then
      log_warning "GKE Standard Cluster does not exist. Initiating creation..."
      log_info "NOTE: GKE Standard cluster creation usually takes 5 to 10 minutes. Please be patient."

      # Resolve latest GKE 1.37 version in RAPID channel (required by Agent Substrate v1.0.0)
      GKE_VERSION=$(gcloud container get-server-config --project="$GOOGLE_CLOUD_PROJECT" --location="$GOOGLE_CLOUD_REGION" \
        --flatten=channels --filter="channels.channel=RAPID" --format='value(channels.validVersions)' 2>/dev/null | tr ';' '\n' | grep '^1\.37\.' | head -n1 || true)
      GKE_VERSION_ARGS=()
      if [ -n "$GKE_VERSION" ]; then
        GKE_VERSION_ARGS=(--cluster-version="$GKE_VERSION")
      fi

      if gcloud beta container clusters create "$CLUSTER_NAME" \
          --region="$GOOGLE_CLOUD_REGION" \
          --node-locations="${GOOGLE_CLOUD_REGION}-a" \
          --release-channel=rapid \
          "${GKE_VERSION_ARGS[@]}" \
          --machine-type=c3-standard-4 \
          --num-nodes=3 \
          --enable-nested-virtualization \
          --gateway-api=standard \
          --workload-pool="${GOOGLE_CLOUD_PROJECT}.svc.id.goog" \
          --labels dev-tutorial=airoadshow \
          --project="$GOOGLE_CLOUD_PROJECT"; then
        log_success "GKE Standard cluster '$CLUSTER_NAME' successfully created!"
      else
        log_error "Failed to create GKE cluster. Please check your quota settings or regional resources."
        exit 1
      fi
    else
      log_success "GKE Standard cluster '$CLUSTER_NAME' already exists."
    fi
  ) 2>&1 | prefix_log "GKE" "${BLUE}" &
  PIDS+=($!)
  RESULTS+=("GKE")
else
  log_info "Skipping Step 7: GKE Standard cluster configuration (Bypassed by CLI flag)."
fi

# ------------------------------------------------------------------------------
# Step 8: Configuring Pub/Sub Topics & Subscriptions
# ------------------------------------------------------------------------------
if [ "$RUN_PUBSUB" = "true" ]; then
  (
    log_info "Starting Pub/Sub Topics & Subscriptions configuration..."

    # Robust function to create topic
    ensure_pubsub_topic() {
      local topic=$1
      log_info "Checking topic: $topic"
      if ! gcloud pubsub topics describe "$topic" &> /dev/null; then
        log_info "Creating Pub/Sub topic: $topic"
        gcloud pubsub topics create "$topic"
        log_success "Topic '$topic' created!"
      else
        log_success "Topic '$topic' already exists."
      fi
    }

    # Robust function to create subscription bound to topic
    ensure_pubsub_sub() {
      local sub=$1
      local topic=$2
      log_info "Checking subscription: $sub"
      if ! gcloud pubsub subscriptions describe "$sub" &> /dev/null; then
        log_info "Creating Pub/Sub subscription '$sub' for topic '$topic'..."
        gcloud pubsub subscriptions create "$sub" --topic="$topic"
        log_success "Subscription '$sub' created!"
      else
        log_success "Subscription '$sub' already exists."
      fi
    }

    # Configure topics
    ensure_pubsub_topic "$TASKS_TOPIC"
    ensure_pubsub_topic "$RESULTS_TOPIC"

    # Configure subscriptions
    ensure_pubsub_sub "$TASKS_SUBSCRIPTION" "$TASKS_TOPIC"
    ensure_pubsub_sub "$RESULTS_SUB" "$RESULTS_TOPIC"
  ) 2>&1 | prefix_log "PubSub" "${PURPLE}" &
  PIDS+=($!)
  RESULTS+=("PubSub")
else
  log_info "Skipping Step 8: Pub/Sub topics and subscriptions configuration (Bypassed by CLI flag)."
fi

# ------------------------------------------------------------------------------
# Step 9: Configuring BigQuery Datasets & Tables
# ------------------------------------------------------------------------------
if [ "$RUN_BQ" = "true" ]; then
  (
    log_info "Starting BigQuery Datasets & Tables configuration..."
    # Workaround for bq error SystemError: buffer overflow
    export COLUMNS=80
    export LINES=24


    log_info "Checking BigQuery dataset: $BQ_DATASET..."
    if ! bq show --project_id="$GOOGLE_CLOUD_PROJECT" --location="$GOOGLE_CLOUD_REGION" "$BQ_DATASET" &>/dev/null; then
      log_info "Creating BigQuery dataset '$BQ_DATASET' in location: $GOOGLE_CLOUD_REGION..."
      if bq --project_id="$GOOGLE_CLOUD_PROJECT" mk \
          --location="$GOOGLE_CLOUD_REGION" \
          --dataset "$GOOGLE_CLOUD_PROJECT:$BQ_DATASET"; then
        log_success "Dataset '$BQ_DATASET' successfully created!"
      else
        log_error "Failed to create BigQuery dataset."
        exit 1
      fi
    else
      log_success "BigQuery dataset '$BQ_DATASET' already exists."
    fi

    log_info "Applying schema.sql to dataset '$BQ_DATASET'..."
    if [ -f "backend/internal/repository/schema.sql" ]; then
      sed -e "s/<<YOUR PROJECT ID>>/${GOOGLE_CLOUD_PROJECT}/g" \
          -e "s/<<REGION>>/${GOOGLE_CLOUD_REGION}/g" \
          -e "s/hackathon_judge/${BQ_DATASET}/g" \
          backend/internal/repository/schema.sql | bq --project_id="$GOOGLE_CLOUD_PROJECT" query --use_legacy_sql=false --location="$GOOGLE_CLOUD_REGION"
      log_success "schema.sql successfully applied!"
    else
      log_warning "schema.sql not found. Skipping schema setup."
    fi
    log_info "Applying seeds.sql to dataset '$BQ_DATASET'..."
    if [ -f "backend/internal/repository/seeds.sql" ]; then
      sed -e "s/<<YOUR PROJECT ID>>/${GOOGLE_CLOUD_PROJECT}/g" -e "s/hackathon_judge/${BQ_DATASET}/g" backend/internal/repository/seeds.sql | bq --project_id="$GOOGLE_CLOUD_PROJECT" query --use_legacy_sql=false --location="$GOOGLE_CLOUD_REGION"
      log_success "seeds.sql successfully applied!"
    else
      log_warning "seeds.sql not found. Skipping seed ingestion."
    fi
  ) 2>&1 | prefix_log "BigQuery" "${CYAN}" &
  PIDS+=($!)
  RESULTS+=("BigQuery")
else
  log_info "Skipping Step 9: BigQuery dataset and tables configuration (Bypassed by CLI flag)."
fi

# ------------------------------------------------------------------------------
# Step 10: Triggering Service Builds with Cloud Build
# ------------------------------------------------------------------------------
# Detect Git status and determine target tag in the parent shell so Step 11
# (setup-env.sh) uses the exact same COMMIT_SHA even when the tree is dirty.
COMMIT_SHA="${COMMIT_SHA:-}"
IS_DIRTY=false
if [ -z "$COMMIT_SHA" ]; then
  if command -v git &> /dev/null && git rev-parse --short HEAD &> /dev/null; then
    if [ -n "$(git status --porcelain)" ]; then
      log_warning "Git repository has uncommitted changes (dirty state)."
      COMMIT_SHA="dirty-$(date +%s)"
      IS_DIRTY=true
    else
      COMMIT_SHA=$(git rev-parse --short HEAD)
      log_info "Git repository is clean. Active commit SHA: $COMMIT_SHA"
    fi
  else
    log_warning "Git not detected or repository not initialized. Generating timestamp tag."
    COMMIT_SHA="manual-$(date +%s)"
    IS_DIRTY=true
  fi
elif [[ "$COMMIT_SHA" == dirty-* ]] || [[ "$COMMIT_SHA" == manual-* ]]; then
  IS_DIRTY=true
fi
export COMMIT_SHA

if [ "$RUN_BUILD" = "true" ]; then
  (
    log_info "Starting Service Builds with Cloud Build..."

    log_info "Registry Region:     $ARTIFACT_REGISTRY_LOCATION"
    log_info "Registry Repository: $ARTIFACT_REPO_NAME"
    log_info "Target Tag (SHA):    $COMMIT_SHA"

    IMAGES_TO_CHECK=("backend" "frontend" "agent" "agent-sandbox")
    ALL_IMAGES_EXIST=true

    if [ "$IS_DIRTY" = "false" ]; then
      log_info "Checking if all required service images already exist in Artifact Registry..."
      for img in "${IMAGES_TO_CHECK[@]}"; do
        image_path="${ARTIFACT_REGISTRY_LOCATION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${ARTIFACT_REPO_NAME}/${img}"
        log_info "  Checking image '${img}' for tag '${COMMIT_SHA}'..."
        
        # Use gcloud artifacts docker tags list and grep for the specific tag
        if gcloud artifacts docker tags list "$image_path" 2>/dev/null | grep -qE "^${COMMIT_SHA}\s"; then
          log_success "    Image '${img}' with tag '${COMMIT_SHA}' exists."
        else
          log_warning "    Image '${img}' with tag '${COMMIT_SHA}' is missing."
          ALL_IMAGES_EXIST=false
          break
        fi
      done
    else
      ALL_IMAGES_EXIST=false
    fi

    if [ "$ALL_IMAGES_EXIST" = "true" ]; then
      log_success "All required images already exist in Artifact Registry with tag '$COMMIT_SHA'."
      log_success "Skipping Google Cloud Build compilation! (Incremental Skip) 🚀"
    else
      log_info "Triggering Google Cloud Build to compile and package all services..."
      if gcloud builds submit --region="$GOOGLE_CLOUD_REGION" --config cloudbuild.yaml . \
          --substitutions=_REGION="$ARTIFACT_REGISTRY_LOCATION",_REPO="$ARTIFACT_REPO_NAME",COMMIT_SHA="$COMMIT_SHA"; then
        log_success "Cloud Build completed successfully! All containers pushed to registry."
      else
        log_error "Cloud Build submission failed."
        log_info "Please check the Cloud Build logs above for specific compilation/Docker errors."
        exit 1
      fi
    fi
  ) 2>&1 | prefix_log "Build" "${YELLOW}" &
  PIDS+=($!)
  RESULTS+=("Build")
else
  log_info "Skipping Step 10: Cloud Build container packaging (Bypassed by CLI flag)."
fi

# Wait for all parallel jobs to complete
FAILURES=0
for i in "${!PIDS[@]}"; do
  # Capture the exit code without tripping 'set -e', so every failed step is reported.
  wait "${PIDS[$i]}" && STATUS=0 || STATUS=$?
  if [ $STATUS -eq 0 ]; then
    log_success "${RESULTS[$i]} configuration completed successfully."
  else
    log_error "${RESULTS[$i]} configuration failed."
    FAILURES=$((FAILURES + 1))
  fi
done

if [ "$FAILURES" -gt 0 ]; then
  log_error "One or more parallel steps failed. Aborting deployment."
  exit 1
fi

# ------------------------------------------------------------------------------
# Step 11: Kubernetes & Agent Substrate v1.0.0 Deployment
# ------------------------------------------------------------------------------
if [ "$RUN_K8S" = "true" ]; then
  log_step "11/11" "Kubernetes & Agent Substrate Deployment ☸️"

  log_info "Getting credentials for GKE cluster: $CLUSTER_NAME..."
  if ! gcloud container clusters get-credentials "$CLUSTER_NAME" --region "$GOOGLE_CLOUD_REGION"; then
    log_error "Failed to get GKE credentials."
    exit 1
  fi

  # Pin Agent Substrate v1.0.0
  SUBSTRATE_VERSION="v1.0.0"
  SUBSTRATE_IMAGE_REPO="${SUBSTRATE_IMAGE_REPO:-ghcr.io/agent-substrate/substrate}"
  SNAPSHOT_BUCKET="${GOOGLE_CLOUD_PROJECT}-ate-snapshots"
  SNAPSHOT_TRANSFER_GSA_NAME="ate-snapshot-transfer"
  SNAPSHOT_TRANSFER_GSA_EMAIL="${SNAPSHOT_TRANSFER_GSA_NAME}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

  log_info "Ensuring Cloud Storage snapshot buckets for Agent Substrate (${SUBSTRATE_VERSION})..."
  for bkt in "$SNAPSHOT_BUCKET" "${SNAPSHOT_BUCKET}-assets"; do
    if ! gcloud storage buckets describe "gs://${bkt}" &> /dev/null; then
      gcloud storage buckets create "gs://${bkt}" --location="$GOOGLE_CLOUD_REGION" --uniform-bucket-level-access
    fi
  done

  PROJECT_NUMBER=$(gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format="value(projectNumber)")
  ATE_API_SERVER_WI_PRINCIPAL="principal://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${GOOGLE_CLOUD_PROJECT}.svc.id.goog/subject/ns/ate-system/sa/ate-api-server"

  log_info "Ensuring snapshot transfer service account (${SNAPSHOT_TRANSFER_GSA_EMAIL})..."
  if ! gcloud iam service-accounts describe "$SNAPSHOT_TRANSFER_GSA_EMAIL" &> /dev/null; then
    gcloud iam service-accounts create "$SNAPSHOT_TRANSFER_GSA_NAME" \
      --display-name="Agent Substrate Snapshot Transfer"
  fi
  for role in "roles/storage.objectUser" "roles/storage.objectAdmin" "roles/storage.legacyBucketReader"; do
    gcloud storage buckets add-iam-policy-binding "gs://${SNAPSHOT_BUCKET}" \
      --member="serviceAccount:${SNAPSHOT_TRANSFER_GSA_EMAIL}" \
      --role="$role" >/dev/null
    gcloud storage buckets add-iam-policy-binding "gs://${SNAPSHOT_BUCKET}" \
      --member="$ATE_API_SERVER_WI_PRINCIPAL" \
      --role="$role" >/dev/null
  done
  gcloud iam service-accounts add-iam-policy-binding "$SNAPSHOT_TRANSFER_GSA_EMAIL" \
    --member="serviceAccount:${GOOGLE_CLOUD_PROJECT}.svc.id.goog[ate-system/ate-snapshot-controller]" \
    --role="roles/iam.workloadIdentityUser" >/dev/null
  gcloud iam service-accounts add-iam-policy-binding "$SNAPSHOT_TRANSFER_GSA_EMAIL" \
    --member="$ATE_API_SERVER_WI_PRINCIPAL" \
    --role="roles/iam.serviceAccountTokenCreator" >/dev/null

  log_info "Installing Agent Substrate (${SUBSTRATE_VERSION}) and kubectl-ate..."
  SUBSTRATE_SRC_DIR="${TMPDIR:-/tmp}/agent-substrate-${SUBSTRATE_VERSION}"
  if [ ! -d "${SUBSTRATE_SRC_DIR}/.git" ]; then
    git clone --quiet --branch "$SUBSTRATE_VERSION" --depth 1 https://github.com/agent-substrate/substrate "$SUBSTRATE_SRC_DIR"
  fi
  mkdir -p "${HOME}/.local/bin"
  export PATH="${HOME}/.local/bin:${PATH}"
  (cd "$SUBSTRATE_SRC_DIR" && GOWORK=off go build -ldflags "-X=go.ate.dev/substrate/internal/version.Version=${SUBSTRATE_VERSION}" -o "${HOME}/.local/bin/kubectl-ate" ./cmd/kubectl-ate)

  (cd "$SUBSTRATE_SRC_DIR" && GOWORK=off go run ./cmd/ate-setup deploy ate-system \
    --gcp-project-id="$GOOGLE_CLOUD_PROJECT" \
    --gcp-cluster-name="$CLUSTER_NAME" \
    --gcp-cluster-location="$GOOGLE_CLOUD_REGION" \
    --rollout-timeout="10m0s" \
    --sandbox-classes="gvisor" \
    --credential-provider='{"enabled":false}' \
    --snapshot-location="gs://${SNAPSHOT_BUCKET}/snapshots/" \
    --snapshot-transfer-gsa-name="$SNAPSHOT_TRANSFER_GSA_NAME" \
    --ingress-allowed-spiffe-ids="spiffe://cluster.local/ns/hackathon-judge/sa/hackathon-judge-sa,spiffe://cluster.local/ns/ate-system/sa/atenet-router" \
    --image-repo "$SUBSTRATE_IMAGE_REPO" \
    --image-tag "$SUBSTRATE_VERSION")

  log_info "Waiting for Agent Substrate control plane and atenet-router in ate-system..."
  kubectl -n ate-system wait --for=condition=Available deploy --all --timeout=600s
  kubectl -n ate-system rollout status ds/atelet --timeout=600s

  WORKER_DIGEST=$(cd "$SUBSTRATE_SRC_DIR" && GOWORK=off go run github.com/google/go-containerregistry/cmd/crane@latest digest "${SUBSTRATE_IMAGE_REPO}/ateworker-gvisor:${SUBSTRATE_VERSION}")
  export SUBSTRATE_WORKER_IMAGE="${SUBSTRATE_IMAGE_REPO}/ateworker-gvisor:${SUBSTRATE_VERSION}@${WORKER_DIGEST}"

  log_info "Applying Kubernetes Namespace (with ate.dev/api-access=true)..."
  kubectl apply -f k8s/namespace.yaml

  log_info "Applying Kubernetes Service Accounts..."
  kubectl apply -f k8s/service-account.yaml

  log_info "Applying RBAC..."
  kubectl apply -f k8s/rbac.yaml

  log_info "Fetching PROJECT_NUMBER for IAM bindings..."
  PROJECT_NUMBER=$(gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format="value(projectNumber)")
  NAMESPACE="hackathon-judge"

  bind_workload_identity() {
    local ksa_name=$1
    local role=$2
    local attempt=1
    log_info "  Binding $role to $ksa_name..."
    while ! gcloud projects add-iam-policy-binding "projects/$GOOGLE_CLOUD_PROJECT" \
      --role="$role" \
      --member="principal://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$GOOGLE_CLOUD_PROJECT.svc.id.goog/subject/ns/$NAMESPACE/sa/$ksa_name" \
      --condition=None >/dev/null 2>&1; do
      if [ $attempt -ge 3 ]; then
        log_error "Failed to bind role $role to service account $ksa_name."
        exit 1
      fi
      attempt=$((attempt + 1))
      sleep 2
    done
  }

  log_info "Configuring IAM permissions for Judge Orchestrator Service Account via Workload Identity..."
  # Only hackathon-judge-sa receives IAM bindings; Judge Actors run with zero credentials.
  bind_workload_identity "hackathon-judge-sa" "roles/bigquery.dataEditor"
  bind_workload_identity "hackathon-judge-sa" "roles/bigquery.jobUser"
  bind_workload_identity "hackathon-judge-sa" "roles/pubsub.publisher"
  bind_workload_identity "hackathon-judge-sa" "roles/pubsub.subscriber"
  bind_workload_identity "hackathon-judge-sa" "roles/aiplatform.user"

  log_info "Applying Kubernetes ConfigMap with environment variables..."
  # Source setup-env.sh before envsubst to ensure all variables are set and exported
  source ./setup-env.sh >/dev/null
  envsubst < k8s/configmap.yaml | kubectl apply -f -

  AGENT_SANDBOX_DIGEST=$(gcloud artifacts docker images describe "${ARTIFACT_REGISTRY_LOCATION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${ARTIFACT_REPO_NAME}/agent-sandbox:${COMMIT_SHA}" --format='value(image_summary.digest)' 2>/dev/null || true)
  if [ -n "$AGENT_SANDBOX_DIGEST" ]; then
    export AGENT_SANDBOX_IMAGE="${ARTIFACT_REGISTRY_LOCATION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${ARTIFACT_REPO_NAME}/agent-sandbox:${COMMIT_SHA}@${AGENT_SANDBOX_DIGEST}"
  else
    export AGENT_SANDBOX_IMAGE="${ARTIFACT_REGISTRY_LOCATION}-docker.pkg.dev/${GOOGLE_CLOUD_PROJECT}/${ARTIFACT_REPO_NAME}/agent-sandbox:${COMMIT_SHA}"
  fi

  log_info "Applying Agent Substrate WorkerPool, AccessPolicy, and ActorTemplate..."
  envsubst < k8s/substrate.yaml | kubectl apply -f -
  kubectl-ate create atespace "$NAMESPACE" 2>/dev/null || true
  kubectl-ate create access-policy -a "$NAMESPACE" -f k8s/access-policy.yaml || true
  if ! kubectl-ate get actor-template judge-sandbox -a "$NAMESPACE" -o json 2>/dev/null | grep -qF "${AGENT_SANDBOX_DIGEST:-$AGENT_SANDBOX_IMAGE}"; then
    kubectl-ate delete actor-template judge-sandbox -a "$NAMESPACE" 2>/dev/null || true
    envsubst < k8s/actortemplate.yaml | kubectl-ate create actor-template -f -
  fi

  log_info "Waiting for WorkerPool pods and ActorTemplate Golden Snapshot..."
  kubectl -n hackathon-judge wait --for=condition=Ready pod -l workload=hackathon-judge --timeout=600s
  GOLDEN_TAG=""
  for _ in $(seq 1 60); do
    GOLDEN_TAG=$(kubectl-ate get actor-template judge-sandbox -a hackathon-judge -o json 2>/dev/null | grep -oE '"(goldenTag|snapshotTime)"[[:space:]]*:[[:space:]]*"[^"]*"' || true)
    if [ -n "$GOLDEN_TAG" ]; then
      log_success "ActorTemplate 'judge-sandbox' Golden Snapshot ready (${GOLDEN_TAG})."
      break
    fi
    sleep 5
  done
  if [ -z "$GOLDEN_TAG" ]; then
    log_error "Timed out waiting for ActorTemplate 'judge-sandbox' Golden Snapshot (goldenTag remained empty)."
    exit 1
  fi

  log_info "Applying Application Gateway..."
  kubectl apply -f k8s/gateway.yaml

  log_info "Applying Application Services (Backend, Frontend, Agent)..."
  envsubst < k8s/backend.yaml | kubectl apply -f -
  envsubst < k8s/frontend.yaml | kubectl apply -f -
  envsubst < k8s/agent.yaml | kubectl apply -f -

  log_info "Waiting for Application rollouts..."
  kubectl rollout status deployment/backend -n hackathon-judge --timeout=300s
  kubectl rollout status deployment/frontend -n hackathon-judge --timeout=300s
  kubectl rollout status deployment/agent -n hackathon-judge --timeout=300s

  log_info "Waiting for Gateways to be fully ready (Programmed & IP assigned)..."
  
  wait_for_gateway_ip() {
    local gateway_name=$1
    local namespace=$2
    local ip=""
    local retries=0
    
    # Wait for Programmed condition first
    kubectl wait --for=condition=programmed=true gateway/"$gateway_name" -n "$namespace" --timeout=600s >/dev/null 2>&1 || true
    
    # Poll for address
    while [ -z "$ip" ] && [ $retries -lt 40 ]; do
      ip=$(kubectl get gateway "$gateway_name" -n "$namespace" -o jsonpath='{.status.addresses[0].value}' 2>/dev/null || echo "")
      if [ -z "$ip" ]; then
        sleep 10
        retries=$((retries + 1))
      fi
    done
    echo "$ip"
  }

  APP_IP=$(wait_for_gateway_ip "hackathon-judge-gateway" "hackathon-judge")

  log_success "Kubernetes & Agent Substrate resources applied and verified!"
else
  log_info "Skipping Step 11: Kubernetes deployment (Bypassed by CLI flag)."
  APP_IP="<Skipped>"
fi

# ------------------------------------------------------------------------------
# Provisioning Complete!
# ------------------------------------------------------------------------------
log_header "Infrastructure Setup, Build & Application Deployment Complete! 🎉"
log_success "All services built, docker images stored in Artifact Registry, and application deployed to GKE."
log_info "To view your Artifact Registry repository, visit:"
echo "  https://console.cloud.google.com/artifacts/docker/${GOOGLE_CLOUD_PROJECT}/${ARTIFACT_REGISTRY_LOCATION}/${ARTIFACT_REPO_NAME}"
log_info "To view your GKE Standard cluster, visit:"
echo "  https://console.cloud.google.com/kubernetes/list/overview?project=${GOOGLE_CLOUD_PROJECT}"

echo -e "\n${BOLD}Access URLs:${NC}"
if [ "$APP_IP" != "<Skipped>" ] && [ -n "$APP_IP" ]; then
  echo -e "  ${GREEN}Hackathon Judge App:${NC} http://${APP_IP}"
else
  echo -e "  ${YELLOW}Hackathon Judge App:${NC} Pending (Check 'kubectl get gateway hackathon-judge-gateway -n hackathon-judge')"
fi

echo -e "\n${BOLD}Ready to roll! 🚀${NC}\n"

# End timing
SCRIPT_END_TIME=$(date +%s)
DURATION=$((SCRIPT_END_TIME - SCRIPT_START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

log_info "${BOLD}Total execution time: ${MINUTES}m ${SECONDS}s${NC}"
