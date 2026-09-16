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
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1)
if [[ "${ACTIVE_ACCOUNT,,}" != *student* ]]; then
  echo "⚠️   Logged in as '${ACTIVE_ACCOUNT:-none}', which is not the lab's student account."
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
agents-cli >/dev/null 2>&1 || uv tool install "google-agents-cli==1.6.*"
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
echo "  🔄   Granting permissions to BQ connection..."

max_retries=5
count=0
success=false

while [ $count -lt $max_retries ]; do
  ((count++))
  echo "Attempt $count to grant IAM permissions..."

  # Extract Service Account ID of the connection
  SA_ID=$(bq show --location="$REGION" --format=json --connection pitch-connection 2>/dev/null | jq -r '.cloudResource.serviceAccountId')

  if [ -n "$SA_ID" ]; then
    echo "  ✅   Found Connection Service Account: $SA_ID"

    echo "  🔄   Granting Storage Object Viewer and Vertex AI User permissions..."
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:$SA_ID" \
      --role="roles/storage.objectViewer" >/dev/null 2>&1 && \
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:$SA_ID" \
      --role="roles/aiplatform.user" >/dev/null 2>&1

    if [ $? -eq 0 ]; then
      echo "  ✅   IAM permissions successfully granted."
      success=true
      break
    fi
  fi

  echo "⚠️   Setup failed or service account not ready. Retrying in 20 seconds..."
  sleep 20
done

if [ "$success" = false ]; then
  echo "❌ Error: Failed to setup BigQuery connection and IAM permissions after $max_retries attempts."
  exit 1
fi

echo " "
echo "  🎉  🦄 Script execution complete."
