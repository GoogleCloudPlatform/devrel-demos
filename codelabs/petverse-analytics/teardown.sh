#!/usr/bin/env bash
# ============================================================================
# PetVerse Sanctuary Analytics - Teardown & Resource Cleanup Script
# ============================================================================
# Cleanly removes resources created by petverse-setup.sh and catchup.sh:
#   1. BigQuery dataset `${DATASET_ID}` (default: `petverse`, including tables & models)
#   2. BigQuery Cloud Resource connection `pet-connection`
#   3. Cloud Storage bucket `gs://${PROJECT_ID}-petverse`
#   4. Customer-managed service account `kc-enrichment-sa@${PROJECT_ID}.iam.gserviceaccount.com`
#
# Usage:
#   ./teardown.sh          # Interactive confirmation
#   ./teardown.sh --yes    # Non-interactive cleanup
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
ENRICH_SA_EMAIL="kc-enrichment-sa@${PROJECT_ID}.iam.gserviceaccount.com"

if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: PROJECT_ID is not set."
  exit 1
fi

AUTO_APPROVE=false
if [[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]]; then
  AUTO_APPROVE=true
fi

echo "⚠️  About to permanently delete PetVerse Analytics resources in project '${PROJECT_ID}':"
echo "   - BigQuery dataset:    ${PROJECT_ID}:${DATASET_ID}"
echo "   - BigQuery connection: ${REGION:-<region>}.pet-connection"
echo "   - Cloud Storage:       gs://${BUCKET}"
echo "   - Service Account:     ${ENRICH_SA_EMAIL}"

if [ "$AUTO_APPROVE" = false ]; then
  read -r -p "Continue with teardown? [y/N] " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted teardown."
    exit 0
  fi
fi

echo ""
echo "  🗑️   [1/4] Removing BigQuery dataset ${PROJECT_ID}:${DATASET_ID}..."
bq rm -r -f -d "${PROJECT_ID}:${DATASET_ID}" >/dev/null 2>&1 || true
echo "  ✅   BigQuery dataset removed (or already absent)."

echo "  🗑️   [2/4] Removing BigQuery connection pet-connection..."
if [ -n "$REGION" ]; then
  bq rm --connection --force --project_id="$PROJECT_ID" --location="$REGION" pet-connection >/dev/null 2>&1 || true
fi
echo "  ✅   BigQuery connection removed (or already absent)."

echo "  🗑️   [3/4] Removing Cloud Storage bucket gs://${BUCKET}..."
if gcloud storage buckets describe "gs://${BUCKET}" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud storage rm --recursive "gs://${BUCKET}" >/dev/null 2>&1 || true
fi
echo "  ✅   Cloud Storage bucket removed (or already absent)."

echo "  🗑️   [4/4] Removing service account ${ENRICH_SA_EMAIL} and project IAM bindings..."
ENRICH_SA_ROLES=(
  "roles/serviceusage.serviceUsageConsumer"
  "roles/dataplex.contentEditor"
  "roles/dataplex.catalogEditor"
  "roles/dataplex.catalogViewer"
  "roles/dataplex.workflowApprover"
  "roles/bigquery.dataViewer"
  "roles/bigquery.jobUser"
  "roles/bigquery.resourceViewer"
  "roles/storage.objectViewer"
)
for role in "${ENRICH_SA_ROLES[@]}"; do
  gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${ENRICH_SA_EMAIL}" \
    --role="$role" \
    --all >/dev/null 2>&1 || true
done

if gcloud iam service-accounts describe "$ENRICH_SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts delete "$ENRICH_SA_EMAIL" --project="$PROJECT_ID" --quiet >/dev/null 2>&1 || true
fi
echo "  ✅   Service account ${ENRICH_SA_EMAIL} removed (or already absent)."

echo ""
echo "✅ Teardown complete."
