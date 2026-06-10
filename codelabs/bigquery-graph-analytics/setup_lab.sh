#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Provisioning foundational tables and deploying Policy Tag security bindings..."

# 1. Identify active project ID automatically
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
  echo "❌ Error: Unable to determine active Google Cloud project ID. Please set via 'gcloud config set project <YOUR_PROJECT>'."
  exit 1
fi

echo "🎯 Active Project: ${PROJECT_ID}"

# 2. Provision the host dataset container
echo "📦 Ensuring target BigQuery dataset 'lost_cargo_dataset' exists..."
if bq show lost_cargo_dataset >/dev/null 2>&1; then
  LOCATION=$(bq show --format=json lost_cargo_dataset | python3 -c "import sys, json; print(json.load(sys.stdin).get('location', 'us'))")
else
  LOCATION="us"
fi
LOCATION=$(echo "$LOCATION" | tr '[:upper:]' '[:lower:]')
echo "📍 Using location: ${LOCATION}"
bq mk --location="${LOCATION}" -d lost_cargo_dataset 2>/dev/null || true

# 3. Execute base relational tables setup script
echo "📜 Executing relational schema initialization (setup_bq_tables.sql)..."
bq query --use_legacy_sql=false < setup_bq_tables.sql

# 4. Verify/Import Security Taxonomy and Policy Tags
echo "🔐 Verifying 'LostCargoSecurity' taxonomy..."
TAXONOMY_ID=$(gcloud data-catalog taxonomies list --location="${LOCATION}" --filter="display_name=LostCargoSecurity" --format="value(name)" | head -n 1 | xargs)

if [ -z "$TAXONOMY_ID" ]; then
  echo "🌱 Importing missing 'LostCargoSecurity' taxonomy..."
  cat <<EOF > /tmp/taxonomy_import.json
{
  "taxonomies": [
    {
      "displayName": "LostCargoSecurity",
      "description": "Taxonomy for lost cargo classification",
      "activatedPolicyTypes": ["FINE_GRAINED_ACCESS_CONTROL"],
      "policyTags": [
        {
          "displayName": "MaskShippingDetails",
          "description": "Restricts visibility into final override clearance strings"
        }
      ]
    }
  ]
}
EOF
  gcloud data-catalog taxonomies import /tmp/taxonomy_import.json --location="${LOCATION}" || echo "⚠️ Warning: Import failed (likely already exists). Proceeding..."
  rm -f /tmp/taxonomy_import.json
  TAXONOMY_ID=$(gcloud data-catalog taxonomies list --location="${LOCATION}" --filter="display_name=LostCargoSecurity" --format="value(name)" | head -n 1 | xargs)
fi

echo "🏷️ Taxonomy ID: ${TAXONOMY_ID}"
echo "🏷️ Resolving target 'MaskShippingDetails' policy tag..."
POLICY_TAG_ID=$(gcloud data-catalog taxonomies policy-tags list --taxonomy="${TAXONOMY_ID}" --filter="display_name=MaskShippingDetails" --format="value(name)" | head -n 1 | xargs)

echo "🛡️ Target Policy Tag Resource Path: ${POLICY_TAG_ID}"

# 5. Attach Policy Tag programmatically to schema column
echo "⚙️ Retrieving physical schema and injecting security tag..."
bq show --schema --format=prettyjson "${PROJECT_ID}:lost_cargo_dataset.maritime_security_registry" | python3 -c '
import json, sys
schema = json.load(sys.stdin)
for col in schema:
    if col.get("name") == "clc_ovr_cd":
        col["policyTags"] = {"names": [sys.argv[1]]}
json.dump(schema, sys.stdout, indent=2)
' "$POLICY_TAG_ID" > /tmp/schema.json

echo "🔒 Patching BigQuery column-level security constraints natively..."
bq update "${PROJECT_ID}:lost_cargo_dataset.maritime_security_registry" /tmp/schema.json
rm -f /tmp/schema.json

echo "🎉 Success! Foundational tables initialized and Column-Level Policy Tags fully mapped out of the box!"
