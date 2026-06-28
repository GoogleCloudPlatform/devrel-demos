#!/bin/bash
# ==============================================================================
# cleanup_data_lake.sh
# Cleans up all BigQuery datasets, tables, and Knowledge Catalog Aspect Types created
# by the setup script.
# ==============================================================================
set -e

# --- Configuration ---
export PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "${PROJECT_ID}" ]; then
  echo "❌ Error: Google Cloud Project ID is not set. Run 'gcloud config set project [PROJECT_ID]' first."
  exit 1
fi

export REGION="${REGION:-us-central1}"
echo "🗑️ [Start] Cleaning up Data Lake in Project: ${PROJECT_ID}, Region: ${REGION}"

# --- 1. Delete Knowledge Catalog Aspect Type ---
echo "🏷️ Deleting Knowledge Catalog Aspect Type 'official-data-product-spec'..."
if gcloud dataplex aspect-types describe official-data-product-spec --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  gcloud dataplex aspect-types delete official-data-product-spec \
      --location="${REGION}" \
      --project="${PROJECT_ID}" \
      --quiet
  echo "  -> ✅ Deleted."
else
  echo "  -> Aspect Type 'official-data-product-spec' does not exist."
fi

# --- 2. Delete BigQuery Datasets (and all tables inside) ---
echo "📊 Deleting BigQuery Datasets..."
for dataset in finance_mart marketing_prod analyst_sandbox; do
  if bq show --dataset "${PROJECT_ID}:${dataset}" >/dev/null 2>&1; then
    echo "  -> Deleting dataset ${dataset}..."
    bq rm -r -f -d "${PROJECT_ID}:${dataset}"
    echo "  -> ✅ Deleted."
  else
    echo "  -> Dataset ${dataset} does not exist."
  fi
done

echo "✨ [Success] Data Lake cleanup completed successfully!"
