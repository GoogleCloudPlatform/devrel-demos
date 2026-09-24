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


# change current directory to script directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "${SCRIPT_DIR}"

# Validation check: the lab variables must be exported before anything else runs.
if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
  echo "⚠️   PROJECT_ID or REGION environment variables are not set."
  echo "👉  Please run step 2 after Start Cloud Shell."
  exit 1
fi

echo "  ➡️   Checking for active Google Cloud authentication..."
if ! gcloud auth list --format="value(account)" | grep -q @; then
  echo "⚠️   Not authenticated. Please authenticate now."
  gcloud auth login
fi
echo "  ✅   Authentication check passed."

# The lab provisions a temporary `student-...` account. A personal or corporate
# account will not have the permissions or quota this lab needs.
#
# On the Antigravity VM the IDE terminal is authenticated as the lab's own
# service account (antigravity-sa@PROJECT.iam.gserviceaccount.com) rather than
# as the student user, so that form is accepted too. Both are provisioned by the
# lab; a personal or corporate account is still rejected.
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1)
if [[ "${ACTIVE_ACCOUNT,,}" != *student* && "${ACTIVE_ACCOUNT,,}" != *.iam.gserviceaccount.com ]]; then
  echo "⚠️   Logged in as '${ACTIVE_ACCOUNT:-none}', which is not a lab account."
  echo "👉  Close this tab, open Cloud Shell from the incognito window the lab opened, and sign in with the student credentials."
  exit 1
fi
echo "  ✅   Logged in as $ACTIVE_ACCOUNT"

echo "  🔄   Setting Google Cloud configuration for this session..."
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1
gcloud config set run/region "$REGION" >/dev/null 2>&1

# Read the project back so this validates what gcloud will actually use.
CONFIGURED_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [[ "$CONFIGURED_PROJECT" != qwiklab* ]]; then
  echo "⚠️   The configured project is '${CONFIGURED_PROJECT:-none}', which is not a Qwiklabs project."
  echo "👉  Please run step 2 after Start Cloud Shell, using the Project ID shown in the lab panel."
  exit 1
fi

echo "  ✅   Google Cloud configuration updated."
echo "Project ID: $CONFIGURED_PROJECT"
echo "Region: $REGION"
echo " "

# Persist the two lab variables in the home directory, which Cloud Shell keeps
# across sessions. If the session is reset and the exported variables are lost,
# setenv.sh reads them back from here. Nothing else is stored in this file, and
# it is outside every agent project, so `agents-cli` never sees it.
LAB_ENV_FILE="$HOME/.env"
cat > "$LAB_ENV_FILE" <<EOF
PROJECT_ID="$PROJECT_ID"
REGION="$REGION"
EOF
echo "  ✅   Saved PROJECT_ID and REGION to $LAB_ENV_FILE"
echo " "

# Export the derived environment for the rest of this script. This runs in the
# script's own shell, so the learner sources setenv.sh again in their terminal.
source setenv.sh

# Cloud Storage bucket for the agents' artifacts and logs. The lab instructions
# tell the learner this bucket already exists, and the deploy task passes its
# name to Cloud Run as LOGS_BUCKET_NAME, so create it up front.
LOGS_BUCKET_NAME="$PROJECT_ID-bwg"
echo "  🔄   Creating Cloud Storage bucket gs://$LOGS_BUCKET_NAME..."
if gcloud storage buckets describe "gs://$LOGS_BUCKET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "  ✅   Bucket gs://$LOGS_BUCKET_NAME already exists."
elif gcloud storage buckets create "gs://$LOGS_BUCKET_NAME" \
  --project="$PROJECT_ID" \
  --location="$REGION" \
  --uniform-bucket-level-access >/dev/null 2>&1; then
  echo "  ✅   Bucket gs://$LOGS_BUCKET_NAME created."
else
  echo "⚠️   Could not create gs://$LOGS_BUCKET_NAME."
  echo "👉  Create it manually before the Cloud Storage task:"
  echo "       gcloud storage buckets create gs://$LOGS_BUCKET_NAME --uniform-bucket-level-access --location=$REGION --project=$PROJECT_ID"
fi
echo " "

# Create BigQuery connection if it does not exist
echo "  🔄   Creating BigQuery connection..."
bq mk --connection --location="$REGION" --project_id="$PROJECT_ID" --connection_type=CLOUD_RESOURCE pitch-connection 2>/dev/null || true


# Install Tooling (agents-cli)
echo "  🔄   Installing agents-cli tooling..."
if ! command -v uv >/dev/null 2>&1; then
  echo "  ⚠️   uv not found. Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
fi

export PATH="$HOME/.local/bin:$PATH"
# Cloud Shell pre-installs an older agents-cli system-wide, so presence alone is
# not enough: check the version, and let uv's copy win on PATH.
if ! agents-cli --version 2>/dev/null | grep -q 'version 1\.6\.'; then
  uv tool install --force "google-agents-cli==1.6.*"
fi
hash -r 2>/dev/null || true
if ! grep -q 'export PATH="\$HOME/\.local/bin:\$PATH"' ~/.bashrc 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi

if command -v agents-cli >/dev/null 2>&1; then
  echo "  ✅   agents-cli installed successfully: $(agents-cli --version)"
else
  echo "  ⚠️   agents-cli installed, but not found in current PATH."
fi
echo " "

# BigQuery Connection & IAM Setup
echo "  🔄   Checking the BigQuery connection service account..."

max_retries=5
count=0
SA_ID=""

# The connection's service agent is created asynchronously, so give it a moment.
while [ $count -lt $max_retries ]; do
  ((count++))

  SA_ID=$(bq show --location="$REGION" --format=json --connection pitch-connection 2>/dev/null | jq -r '.cloudResource.serviceAccountId // empty')
  if [ -n "$SA_ID" ]; then
    break
  fi

  echo "⏳   Connection service account not ready. Retrying in 20 seconds... ($count/$max_retries)"
  sleep 20
done

if [ -z "$SA_ID" ]; then
  echo "❌ Error: could not read the 'pitch-connection' service account after $max_retries attempts."
  exit 1
fi

echo "  ✅   Found Connection Service Account: $SA_ID"

# The connection reads key visuals from Cloud Storage and calls Agent Platform for
# AI.SCORE, so its service agent needs these two roles.
#
# Best-effort, not fatal. In the Qwiklabs environment these bindings are already
# created by the lab's Terraform, and the identity running this script has no
# permission to set IAM policy - deliberately, because that permission would let
# the lab environment grant itself owner. Outside Qwiklabs, where you are running
# in your own project against a connection this script just created, the grants
# happen here.
echo "  🔄   Ensuring Storage Object Viewer and Agent Platform User permissions..."
grants_applied=true
for role in "roles/storage.objectViewer" "roles/aiplatform.user"; do
  if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:$SA_ID" \
    --role="$role" >/dev/null 2>&1; then
    echo "  ✅   Granted $role"
  else
    grants_applied=false
    echo "  ℹ️   Could not grant $role here - expected if it is already provisioned."
  fi
done

if [ "$grants_applied" = false ]; then
  echo "  ℹ️   If the brand-fit scoring step later fails with a permission error, ask"
  echo "       your lab administrator to grant $SA_ID"
  echo "       roles/storage.objectViewer and roles/aiplatform.user."
fi

echo " "
echo "  🎉  🦄 Script execution complete."
