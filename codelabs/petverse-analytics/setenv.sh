#!/usr/bin/env bash
# ============================================================================
# PetVerse Sanctuary Analytics - Environment Configuration
# Usage: source ./setenv.sh
# ============================================================================

if [ -f "$HOME/.env" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.env"
elif [ -f ".env" ]; then
  # shellcheck disable=SC1091
  source ".env"
fi

export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-$(gcloud config get-value compute/region 2>/dev/null)}"
export DATASET_ID="${DATASET_ID:-petverse}"
export BUCKET="${BUCKET:-${PROJECT_ID}-petverse}"

export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"
export GOOGLE_CLOUD_QUOTA_PROJECT="$PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="global"
export AGY_ADC_AUTH=true
export AGY_CLI_DISABLE_AUTO_UPDATE=true

if [ -n "$PROJECT_ID" ]; then
  gcloud config set project "$PROJECT_ID" >/dev/null 2>&1 || true
fi
if [ -n "$REGION" ]; then
  gcloud config set compute/region "$REGION" >/dev/null 2>&1 || true
fi

echo "Environment configured:"
echo "  PROJECT_ID: $PROJECT_ID"
echo "  REGION:     $REGION"
echo "  DATASET_ID: $DATASET_ID"
echo "  BUCKET:     gs://$BUCKET"
