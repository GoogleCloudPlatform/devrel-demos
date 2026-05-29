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

# ------------------------------------------------------------------------------
# Premium Terminal Styling & Logging Helpers
# ------------------------------------------------------------------------------
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
  echo -e "\n${BOLD}${RED}======================================================================${NC}"
  echo -e "${BOLD}${RED}  $1${NC}"
  echo -e "${BOLD}${RED}======================================================================${NC}"
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

# ------------------------------------------------------------------------------
# Step 1: Load Environment Config
# ------------------------------------------------------------------------------
log_header "GOOGLE CLOUD Infrastructure Destruction & Cleanup System"
log_step "1/7" "Loading Environment Configuration ⚙️"

ENV_FILE=".env"

if [ ! -f "$ENV_FILE" ]; then
  log_error "Configuration file '$ENV_FILE' not found."
  log_info "Nothing to destroy. Exiting."
  exit 0
fi

log_info "Sourcing configuration variables from $ENV_FILE..."
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Validate essential variables
if [ -z "${GOOGLE_CLOUD_PROJECT:-}" ] || [ -z "${GOOGLE_CLOUD_REGION:-}" ] || [ -z "${CLUSTER_NAME:-}" ] || [ -z "${BQ_DATASET:-}" ]; then
  log_error "Incomplete configurations found in $ENV_FILE."
  exit 1
fi

log_info "Target Infrastructure Details to destroy:"
echo "  Project: ${GOOGLE_CLOUD_PROJECT}"
echo "  Region:  ${GOOGLE_CLOUD_REGION}"
echo "  Cluster: ${CLUSTER_NAME}"
echo "  Dataset: ${BQ_DATASET}"

# ------------------------------------------------------------------------------
# User Safety Warning Prompt
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${RED}🔥 CAUTION: CRITICAL WARNING 🔥${NC}"
echo -e "${RED}This script will PERMANENTLY DELETE all provisioned infrastructure including:${NC}"
echo -e "  - GKE Autopilot Cluster: ${CLUSTER_NAME}"
echo -e "  - Artifact Registry Repo: ${ARTIFACT_REPO_NAME}"
echo -e "  - Pub/Sub Topics & Subscriptions"
echo -e "  - BigQuery Dataset & Tables: ${BQ_DATASET}"
echo -e "${RED}This action is completely irreversible!${NC}\n"

read -p "Are you absolutely sure you want to proceed? Type 'DESTROY' to confirm: " confirmation

if [ "${confirmation}" != "DESTROY" ]; then
  log_warning "Destruction cancelled by user. Exiting safely."
  exit 0
fi

log_info "Destruction confirmed. Proceeding..."

# Set the active project
gcloud config set project "$GOOGLE_CLOUD_PROJECT"

# ------------------------------------------------------------------------------
# Step 2: Delete Pub/Sub Topics & Subscriptions
# ------------------------------------------------------------------------------
log_step "2/7" "Deleting Pub/Sub topics and subscriptions 📨"

delete_pubsub_sub() {
  local sub=$1
  log_info "Checking subscription: $sub"
  if gcloud pubsub subscriptions describe "$sub" &> /dev/null; then
    log_warning "Deleting Pub/Sub subscription: $sub"
    gcloud pubsub subscriptions delete "$sub" --quiet
    log_success "Subscription '$sub' deleted."
  else
    log_info "Subscription '$sub' does not exist. Skipping."
  fi
}

delete_pubsub_topic() {
  local topic=$1
  log_info "Checking topic: $topic"
  if gcloud pubsub topics describe "$topic" &> /dev/null; then
    log_warning "Deleting Pub/Sub topic: $topic"
    gcloud pubsub topics delete "$topic" --quiet
    log_success "Topic '$topic' deleted."
  else
    log_info "Topic '$topic' does not exist. Skipping."
  fi
}

# Subscriptions first
delete_pubsub_sub "${TASKS_SUBSCRIPTION:-}"
delete_pubsub_sub "${RESULTS_SUB:-}"

# Topics second
delete_pubsub_topic "${TASKS_TOPIC:-}"
delete_pubsub_topic "${RESULTS_TOPIC:-}"

# ------------------------------------------------------------------------------
# Step 3: Delete GKE Autopilot Cluster
# ------------------------------------------------------------------------------
log_step "3/7" "Deleting GKE Autopilot Cluster 🚀"

log_info "Checking GKE Autopilot cluster: $CLUSTER_NAME..."
if gcloud container clusters describe "$CLUSTER_NAME" --region="$GOOGLE_CLOUD_REGION" &> /dev/null; then
  log_warning "Initiating deletion of GKE Autopilot cluster '$CLUSTER_NAME'..."
  log_info "NOTE: GKE cluster deletion usually takes 5 to 8 minutes. Please do not interrupt."
  
  if gcloud container clusters delete "$CLUSTER_NAME" \
      --region="$GOOGLE_CLOUD_REGION" \
      --quiet; then
    log_success "GKE Autopilot cluster '$CLUSTER_NAME' successfully deleted!"
  else
    log_error "Failed to delete GKE Autopilot cluster."
    exit 1
  fi
else
  log_info "GKE Autopilot cluster '$CLUSTER_NAME' does not exist. Skipping."
fi

# ------------------------------------------------------------------------------
# Step 4: Delete Artifact Registry
# ------------------------------------------------------------------------------
log_step "4/7" "Deleting Artifact Registry Repository 📦"

log_info "Checking Artifact Registry repository: $ARTIFACT_REPO_NAME..."
if gcloud artifacts repositories describe "$ARTIFACT_REPO_NAME" --location="$ARTIFACT_REGISTRY_LOCATION" &> /dev/null; then
  log_warning "Deleting Artifact Registry repository '$ARTIFACT_REPO_NAME'..."
  if gcloud artifacts repositories delete "$ARTIFACT_REPO_NAME" \
      --location="$ARTIFACT_REGISTRY_LOCATION" \
      --quiet; then
    log_success "Artifact Registry repository '$ARTIFACT_REPO_NAME' deleted!"
  else
    log_error "Failed to delete Artifact Registry repository."
    exit 1
  fi
else
  log_info "Artifact Registry repository '$ARTIFACT_REPO_NAME' does not exist. Skipping."
fi

# ------------------------------------------------------------------------------
# Step 5: Delete BigQuery Dataset & Tables
# ------------------------------------------------------------------------------
log_step "5/7" "Deleting BigQuery Dataset & Tables 📊"

log_info "Checking BigQuery dataset: $BQ_DATASET..."
if bq show --project_id="$GOOGLE_CLOUD_PROJECT" "$BQ_DATASET" &>/dev/null; then
  log_warning "Deleting BigQuery dataset '$BQ_DATASET' and all its tables recursively..."
  if bq --project_id="$GOOGLE_CLOUD_PROJECT" rm -r -f "$GOOGLE_CLOUD_PROJECT:$BQ_DATASET"; then
    log_success "BigQuery dataset '$BQ_DATASET' and tables successfully deleted!"
  else
    log_error "Failed to delete BigQuery dataset."
    exit 1
  fi
else
  log_info "BigQuery dataset '$BQ_DATASET' does not exist. Skipping."
fi

# ------------------------------------------------------------------------------
# Step 6: Delete Stabby Storage Bucket
# ------------------------------------------------------------------------------
log_step "6/7" "Deleting Stabby Storage Bucket 🪣"

log_info "Checking Storage bucket: gs://${GOOGLE_CLOUD_PROJECT}-stabby..."
if gcloud storage buckets describe "gs://${GOOGLE_CLOUD_PROJECT}-stabby" &> /dev/null; then
  log_warning "Deleting Storage bucket 'gs://${GOOGLE_CLOUD_PROJECT}-stabby' recursively..."
  if gcloud storage rm --recursive "gs://${GOOGLE_CLOUD_PROJECT}-stabby"; then
    log_success "Storage bucket successfully deleted!"
  else
    log_error "Failed to delete Storage bucket."
    exit 1
  fi
else
  log_info "Storage bucket 'gs://${GOOGLE_CLOUD_PROJECT}-stabby' does not exist. Skipping."
fi

# ------------------------------------------------------------------------------
# Step 7: Environment Clean up
# ------------------------------------------------------------------------------
log_step "7/7" "Removing Configuration File 🧹"

read -p "Do you want to remove the local $ENV_FILE file as well? [y/N]: " remove_env

case "${remove_env:-N}" in
  [yY] | [yY][eE][sS])
    rm -f "$ENV_FILE"
    log_success "Removed local $ENV_FILE file."
    ;;
  *)
    log_info "Keeping $ENV_FILE for future deployments."
    ;;
esac

log_header "Infrastructure Clean up Complete! 🗑️"
log_success "All deployed GCP resources successfully torn down."
echo -e "\n${BOLD}Cleanup complete. Project is fresh again! ✨${NC}\n"
