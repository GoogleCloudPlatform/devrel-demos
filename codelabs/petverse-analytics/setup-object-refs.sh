#!/usr/bin/env bash
# ============================================================================
# PetVerse Sanctuary Analytics - Populate ObjectRef Media Columns
# ============================================================================
# Adds `profile_picture` and `additional_media` ObjectRef columns (if missing)
# and populates Cloud Storage media object references across `petverse.pets`.
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/setenv.sh" ]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/setenv.sh" >/dev/null
fi

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-$(gcloud config get-value compute/region 2>/dev/null)}"
DATASET_ID="${DATASET_ID:-petverse}"
BUCKET="${BUCKET:-${PROJECT_ID}-petverse}"

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
  echo "❌ Error: PROJECT_ID or REGION is not set."
  echo "   Run 'source ./setenv.sh' or export PROJECT_ID and REGION first."
  exit 1
fi

SQL_FILE="$SCRIPT_DIR/sql/setup_object_refs.sql"
if [ ! -f "$SQL_FILE" ]; then
  echo "❌ Error: Missing SQL file at $SQL_FILE"
  exit 1
fi

RENDERED_SQL="$(sed \
  -e "s/__PROJECT_ID__-petverse/${BUCKET}/g" \
  -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
  -e "s/__REGION__/${REGION}/g" \
  -e "s/\.petverse\./.${DATASET_ID}./g" \
  "$SQL_FILE")"

echo "  🔄   Populating ObjectRef media references on \`${PROJECT_ID}.${DATASET_ID}.pets\`..."

max_attempts=5
attempt=1
output=""
while [ "$attempt" -le "$max_attempts" ]; do
  if output=$(bq query \
    --project_id="$PROJECT_ID" \
    --location="$REGION" \
    --use_legacy_sql=false \
    --quiet \
    <<<"$RENDERED_SQL" 2>&1); then
    echo "  ✅   ObjectRef media references populated for all sanctuary pets!"
    exit 0
  fi

  if [ "$attempt" -lt "$max_attempts" ]; then
    echo "  ⏳   Attempt ${attempt}/${max_attempts} waiting for connection IAM propagation. Retrying in 15s..."
    sleep 15
  fi
  ((attempt++))
done

echo "❌ Error: Failed to populate ObjectRef columns on \`${PROJECT_ID}.${DATASET_ID}.pets\`."
echo "$output"
exit 1
