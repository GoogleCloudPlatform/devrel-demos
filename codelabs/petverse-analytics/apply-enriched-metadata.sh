#!/usr/bin/env bash
# ============================================================================
# PetVerse Sanctuary Analytics - Apply Enriched Metadata Fallback
# ============================================================================
# Substitutes PROJECT_ID, REGION, and DATASET_ID into
# sql/enrich_pv_ops_tlm_fallback.sql and applies table & column descriptions
# to `pv_ops_tlm_v2` immediately. Use if a Knowledge Studio Preview enrichment
# run is still executing when starting Conversational Analytics.
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

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
  echo "❌ Error: PROJECT_ID or REGION is not set."
  echo "   Run 'source ./setenv.sh' or export PROJECT_ID and REGION first."
  exit 1
fi

SQL_FILE="$SCRIPT_DIR/sql/enrich_pv_ops_tlm_fallback.sql"
if [ ! -f "$SQL_FILE" ]; then
  echo "❌ Error: Missing SQL file at $SQL_FILE"
  exit 1
fi

echo "  🔄   Applying decoded PAWS/400 COBOL descriptions to \`${PROJECT_ID}.${DATASET_ID}.pv_ops_tlm_v2\`..."

RENDERED_SQL="$(sed \
  -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
  -e "s/__REGION__/${REGION}/g" \
  -e "s/\.petverse\./.${DATASET_ID}./g" \
  "$SQL_FILE")"

bq query \
  --project_id="$PROJECT_ID" \
  --location="$REGION" \
  --use_legacy_sql=false \
  --quiet \
  <<<"$RENDERED_SQL"

echo "  ✅   Metadata descriptions applied to \`${PROJECT_ID}.${DATASET_ID}.pv_ops_tlm_v2\`."
