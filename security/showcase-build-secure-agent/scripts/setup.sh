#!/bin/bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# setup.sh - Prepares a Google Cloud project for the demo application deployment.

# ==========================================
# 0. Environment Setup & Helper Functions
# ==========================================

# Define verbose color variables for output formatting
COLOR_RED='\e[31m'
COLOR_GREEN='\e[32m'
COLOR_BLUE='\e[34m'
COLOR_RESET='\e[0m'

# Determine Execution Mode
if [[ ! -t 0 ]] || [[ "${BASH_SOURCE[0]}" == *"bash"* ]] || [[ -z "${BASH_SOURCE[0]}" ]]; then
    EXECUTION_MODE="INDIRECT"
else
    EXECUTION_MODE="DIRECT"
fi

# Determine PROJECT_ID: check PROJECT_ID, then GOOGLE_CLOUD_PROJECT, then gcloud config
if [[ -z "${PROJECT_ID}" ]]; then
    if [[ -n "${GOOGLE_CLOUD_PROJECT}" ]]; then
        PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
    else
        PROJECT_ID=$(gcloud config get project 2>/dev/null)
    fi
fi

# Determine LOCATION: check GOOGLE_CLOUD_LOCATION, then LOCATION, then use "us-west1" as default
LOCATION="${GOOGLE_CLOUD_LOCATION:-${LOCATION:-us-west1}}"

# Ensure we have a valid PROJECT_ID after fallbacks
if [[ -z "${PROJECT_ID}" ]]; then
    echo -e "[${COLOR_RED}ERROR${COLOR_RESET}] Could not determine PROJECT_ID."
    echo "Please set PROJECT_ID, GOOGLE_CLOUD_PROJECT, or run: gcloud config set project <your-project-id>"
    exit 1
fi

echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] Execution Mode: ${EXECUTION_MODE}"
echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] Using Project ID: ${PROJECT_ID}"
echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] Using Location: ${LOCATION}"

# Handle indirect Execution Mode
if [[ "${EXECUTION_MODE}" == "INDIRECT" ]]; then
    echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] Preparing local environment from GitHub repository..."
    
    # Create a temporary directory for cloning
    TEMP_DIR=$(mktemp -d)
    
    # Use a subshell to prevent directory changes from affecting the rest of the script
    (
        cd "${TEMP_DIR}" || exit 1
        
        # Clone only the needed directory with no history to speed up the process
        git clone --depth 1 --filter=blob:none --sparse https://github.com/GoogleCloudPlatform/devrel-demos.git >/dev/null 2>&1
        cd devrel-demos || exit 1
        git sparse-checkout set security/showcase-build-secure-agent >/dev/null 2>&1
        git checkout >/dev/null 2>&1
        
        # Copy to the home directory
        cp -r security/showcase-build-secure-agent "${HOME}/"
    )
    
    # Clean up the temporary directory
    rm -rf "${TEMP_DIR}"
    
    # Set the root for the rest of the script
    PROJECT_ROOT="${HOME}/showcase-build-secure-agent"
    echo -e "[${COLOR_GREEN}OK${COLOR_RESET}] Copied repository files to ${PROJECT_ROOT}"
else
    # Resolve the physical location of the script without changing the current directory
    SCRIPT_PATH="$(realpath "${BASH_SOURCE[0]}")"
    SCRIPT_DIR="$(dirname "${SCRIPT_PATH}")"
    
    # Since the script is in the 'scripts' folder, the project root is one level up
    PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
fi

# Helper function to execute commands with hidden output and verbose error handling
execute() {
    local msg="$1"
    shift
    echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] $msg..."
    
    local output
    # Run command and capture stdout and stderr
    if output=$("$@" 2>&1); then
        echo -e "[${COLOR_GREEN}OK${COLOR_RESET}] Completed: $msg\n"
    else
        local exit_code=$?
        # Idempotency fallback check just in case
        if echo "$output" | grep -qiE "already exists|already present|409|ALREADY_EXISTS"; then
            echo -e "[${COLOR_GREEN}OK${COLOR_RESET}] Already exists (Skipped): $msg\n"
        else
            echo -e "[${COLOR_RED}ERROR${COLOR_RESET}] Failed: $msg"
            echo "--- Error Details ---"
            echo "$output"
            echo "---------------------"
            exit $exit_code
        fi
    fi
}

# ==========================================
# 1. Enable APIs
# ==========================================
# Keeping Binary Authorization and related APIs enabled as requested.
execute "Enabling required Google Cloud APIs" \
    gcloud services enable \
    aiplatform.googleapis.com \
    artifactregistry.googleapis.com \
    bigquery.googleapis.com \
    binaryauthorization.googleapis.com \
    cloudbuild.googleapis.com \
    cloudkms.googleapis.com \
    cloudresourcemanager.googleapis.com \
    containeranalysis.googleapis.com \
    containerscanning.googleapis.com \
    modelarmor.googleapis.com \
    run.googleapis.com \
    --project="${PROJECT_ID}"

execute "Enabling BigQuery MCP Beta Service" \
    gcloud beta services mcp enable bigquery.googleapis.com \
    --project="${PROJECT_ID}"

# ==========================================
# 2. Create Docker Repository
# ==========================================
echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] Checking if Docker repository 'approved-docker-repo' exists..."
if gcloud artifacts repositories describe approved-docker-repo \
    --location=us \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo -e "[${COLOR_GREEN}OK${COLOR_RESET}] Already exists (Skipped): Docker repository 'approved-docker-repo'\n"
else
    execute "Creating Docker repository 'approved-docker-repo' with vulnerability scanning" \
        gcloud artifacts repositories create approved-docker-repo \
        --repository-format=docker \
        --location=us \
        --mode=standard-repository \
        --allow-vulnerability-scanning \
        --description="Standard Docker repository with scanning enabled" \
        --project="${PROJECT_ID}"
fi

# ==========================================
# 3. Create Cloud Build Service Account & Assign Roles
# ==========================================
SA_NAME="cloud-builder-sa"
SA_MAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] Checking if Cloud Builder service account exists..."
if gcloud iam service-accounts describe "${SA_MAIL}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo -e "[${COLOR_GREEN}OK${COLOR_RESET}] Already exists (Skipped): Service Account '${SA_NAME}'\n"
else
    execute "Creating Cloud Builder service account" \
        gcloud iam service-accounts create "${SA_NAME}" \
        --display-name="Cloud Builder service account" \
        --project="${PROJECT_ID}"
fi

ROLES=(
    "roles/cloudbuild.builds.builder"
    "roles/logging.logWriter"
    "roles/iam.serviceAccountAdmin"
    "roles/bigquery.dataEditor"
    "roles/bigquery.jobUser"
    "roles/cloudkms.signerVerifier"
    "roles/containeranalysis.notes.attacher"
)

for ROLE in "${ROLES[@]}"; do
    execute "Granting role ${ROLE} to ${SA_MAIL}" \
        gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SA_MAIL}" \
        --role="${ROLE}" \
        --condition=None \
        --quiet
done

# ==========================================
# 4. Grant Limited IAM Admin Permissions
# ==========================================
echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] Setting up Limited IAM Admin permissions..."

# Use a safe temporary file to avoid polluting the user's current directory
COND_FILE=$(mktemp)
cat <<EOF > "${COND_FILE}"
title: LimitedIAMAdmin
expression: "api.getAttribute('iam.googleapis.com/modifiedGrantsByRole', []).hasOnly(['roles/aiplatform.user','roles/mcp.toolUser','roles/modelarmor.user','roles/bigquery.jobUser','roles/bigquery.dataViewer','roles/cloudtrace.agent','roles/logging.logWriter'])"
EOF

execute "Granting roles/resourcemanager.projectIamAdmin with condition" \
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_MAIL}" \
    --role="roles/resourcemanager.projectIamAdmin" \
    --condition-from-file="${COND_FILE}" \
    --quiet

rm -f "${COND_FILE}"

# ==========================================
# 5. Grant Artifact Registry Admin on Repo
# ==========================================
execute "Granting Artifact Registry Admin to Service Account on Docker Repo" \
    gcloud artifacts repositories add-iam-policy-binding approved-docker-repo \
    --location="us" \
    --member="serviceAccount:${SA_MAIL}" \
    --role="roles/artifactregistry.admin" \
    --project="${PROJECT_ID}" \
    --quiet

# ==========================================
# 6. Creating Cloud Run Robot
# ==========================================
execute "Activating Cloud Run System Agent" \
    gcloud beta services identity create \
    --service=run.googleapis.com \
    --format='value(email)' \
    --project=${PROJECT_ID} \
    --quiet

# ==========================================
# 7. Grant Artifact Registry on Repo
# ==========================================
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format="value(projectNumber)")
CLOUDRUN_ROBOT_SA="service-${PROJECT_NUMBER}@serverless-robot-prod.iam.gserviceaccount.com"
execute "Granting Artifact Registry Reader to Cloud Run Robot on Docker Repo" \
    gcloud artifacts repositories add-iam-policy-binding approved-docker-repo \
    --location="us" \
    --member="serviceAccount:${CLOUDRUN_ROBOT_SA}" \
    --role="roles/artifactregistry.reader" \
    --project="${PROJECT_ID}" \
    --quiet

# ==========================================
# 8. Provision BigQuery Datasets & Tables
# ==========================================
DATASETS=(
    "customer_service"
    "admin"
)

for DATASET in "${DATASETS[@]}"; do
    echo -e "[${COLOR_BLUE}INFO${COLOR_RESET}] Checking for the existence of BigQuery dataset '${DATASET}'..."
    if bq show "${PROJECT_ID}:${DATASET}" >/dev/null 2>&1; then
        echo -e "[${COLOR_GREEN}OK${COLOR_RESET}] Dataset '${DATASET}' already exists. Skipping creation.\n"
    else
        execute "Creating BigQuery dataset '${DATASET}'" \
            bq mk --location="${LOCATION}" --dataset "${PROJECT_ID}:${DATASET}"
    fi
done

TABLES=(
    "customer_service.customers"
    "customer_service.orders"
    "customer_service.products"
    "admin.audit_log"
)

for FULL_TABLE in "${TABLES[@]}"; do
    # Extract just the table name (everything after the dot) to use for file matching
    TABLE_NAME="${FULL_TABLE##*.}"
    
    # Note: bq load handles idempotency via the --replace flag.
    # Paths strictly reference $PROJECT_ROOT to decouple from the user's current directory.
    execute "Configuring schema and loading data to '${FULL_TABLE}'" \
        bq load \
        --source_format=CSV \
        --skip_leading_rows=1 \
        --replace \
        "${PROJECT_ID}:${FULL_TABLE}" \
        "${PROJECT_ROOT}/seed-data/${TABLE_NAME}.csv" \
        "${PROJECT_ROOT}/seed-data/${TABLE_NAME}_schema.json"
done

echo -e "[${COLOR_GREEN}SUCCESS${COLOR_RESET}] Project setup completed successfully!"