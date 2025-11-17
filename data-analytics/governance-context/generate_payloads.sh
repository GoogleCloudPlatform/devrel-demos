#!/bin/bash
set -e

export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-central1"
ASPECT_ID="official-data-product-spec"
ASPECT_KEY="${PROJECT_ID}.${REGION}.${ASPECT_ID}"

echo "🛠️  Configuring payloads for Project: ${PROJECT_ID}, Key: ${ASPECT_KEY}"
mkdir -p aspect_payloads

# ====================================================
# 1. Finance Internal (GOLD / INTERNAL)
# ====================================================
cat <<EOF > aspect_payloads/fin_internal.yaml
${ASPECT_KEY}:
  data:
    product_tier: GOLD_CRITICAL
    data_domain: FINANCE
    usage_scope: INTERNAL_ONLY
    update_frequency: DAILY_BATCH
    is_certified: true
EOF

# ====================================================
# 2. Finance Public (GOLD / EXTERNAL)
# ====================================================
cat <<EOF > aspect_payloads/fin_public.yaml
${ASPECT_KEY}:
  data:
    product_tier: GOLD_CRITICAL
    data_domain: FINANCE
    usage_scope: EXTERNAL_READY
    update_frequency: QUARTERLY_CLOSING
    is_certified: true
EOF

# ====================================================
# 3. Marketing Realtime (SILVER / INTERNAL)
# ====================================================
cat <<EOF > aspect_payloads/mkt_realtime.yaml
${ASPECT_KEY}:
  data:
    product_tier: SILVER_STANDARD
    data_domain: MARKETING
    usage_scope: INTERNAL_ONLY
    update_frequency: REALTIME_STREAMING
    is_certified: true
EOF

# ====================================================
# 4. Analyst Sandbox (BRONZE / NOT CERTIFIED)
# ====================================================
cat <<EOF > aspect_payloads/sandbox_dump.yaml
${ASPECT_KEY}:
  data:
    product_tier: BRONZE_ADHOC
    data_domain: LOGISTICS
    usage_scope: INTERNAL_ONLY
    update_frequency: DAILY_BATCH
    is_certified: false
EOF

echo "✅ Successfully generated 4 YAML payloads in ./aspect_payloads/"
