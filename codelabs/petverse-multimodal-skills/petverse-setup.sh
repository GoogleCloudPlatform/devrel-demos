#!/bin/bash

# Retrieve environment variables or gcloud configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-$(gcloud config get-value compute/region 2>/dev/null)}"

# Validation check: if variables are not set AND project ID doesn't start with "qwiklabs"
if { [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; } && [[ "$PROJECT_ID" != qwiklabs* ]]; then
  echo "⚠️   PROJECT_ID or REGION environment variables are not set, and project ID does not start with 'qwiklabs'."
  echo "👉  Please run step 2 after Start Cloud Shell."
  exit 1
fi

echo "  ➡️   Checking for active Google Cloud authentication..."
if ! gcloud auth list --format="value(account)" | grep -q @; then
  echo "⚠️   Not authenticated. Please authenticate now."
  gcloud auth login
fi
echo "  ✅   Authentication check passed."

echo "  🔄   Setting Google Cloud configuration for this session..."
gcloud config set project "$PROJECT_ID" >/dev/null 2>&1
gcloud config set compute/region "$REGION" >/dev/null 2>&1

echo "  ✅   Google Cloud configuration updated."
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo " "

# Save variables to .env file in Cloud Shell
cat > ~/.env << EOF
export PROJECT_ID=$PROJECT_ID
export REGION=$REGION
export AGY_ADC_AUTH=true
export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
export GOOGLE_CLOUD_QUOTA_PROJECT=$PROJECT_ID
export GOOGLE_CLOUD_LOCATION=global
export AGY_CLI_DISABLE_AUTO_UPDATE=true
EOF
if [ "$PWD" != "$HOME" ]; then
  cp ~/.env .env
fi
grep -q 'source ~/.env' ~/.bashrc 2>/dev/null || echo '[ -f ~/.env ] && source ~/.env' >> ~/.bashrc
echo "  ✅   Environment variables saved to .env file."
echo " "

# Pre-configure Antigravity CLI (agy) to skip interactive onboarding & trust prompts
echo "  🔄   Pre-configuring Antigravity CLI..."
APP_DIR="$HOME/petverse-profiles"
mkdir -p "$APP_DIR" "$HOME/.gemini/antigravity-cli/cache"

cat > "$HOME/.gemini/antigravity-cli/cache/onboarding.json" << 'EOF'
{
  "consumerOnboardingComplete": true,
  "enterpriseOnboardingComplete": true,
  "onboardingComplete": true
}
EOF

cat > "$HOME/.gemini/antigravity-cli/settings.json" << EOF
{
  "allowNonWorkspaceAccess": true,
  "gcp": {
    "project": "$PROJECT_ID",
    "location": "global"
  },
  "permissions": {
    "allow": [
      "command(ls)",
      "command(mkdir)",
      "command(gcloud help)",
      "command(gcloud dataplex)",
      "command(gcloud config)",
      "command(bq query)",
      "command(gcloud storage)",
      "command(curl)",
      "command(gcloud artifacts)",
      "command(gcloud builds)",
      "command(gcloud run)"
    ]
  },
  "trustedWorkspaces": [
    "$APP_DIR"
  ]
}
EOF
echo "  ✅   Antigravity CLI pre-configured."
echo " "

# BigQuery Connection & IAM Setup
echo "  🔄   Creating BigQuery connection and granting permissions..."

max_retries=5
count=0
success=false

# Create BigQuery connection if it does not exist
bq mk --connection --location="$REGION" --project_id="$PROJECT_ID" --connection_type=CLOUD_RESOURCE pet-connection 2>/dev/null || true

while [ $count -lt $max_retries ]; do
  ((count++))
  echo "Attempt $count to grant IAM permissions..."

  # Extract Service Account ID of the connection
  SA_ID=$(bq show --location="$REGION" --format=json --connection pet-connection 2>/dev/null | jq -r '.cloudResource.serviceAccountId')

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
