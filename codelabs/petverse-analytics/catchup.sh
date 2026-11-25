#!/usr/bin/env bash
# ============================================================================
# PetVerse Sanctuary Analytics - Idempotent Full "Catch Me Up" Script
# ============================================================================
# Provisions and populates all prerequisite Google Cloud & BigQuery assets
# up to Conversational Analytics & AI.FORECAST:
#   1. Runs `petverse-setup.sh` (APIs, `pet-connection`, `kc-enrichment-sa` IAM,
#      `gs://${PROJECT_ID}-petverse` bucket, staged media/telemetry/legacy repo,
#      and `petverse` BigQuery dataset)
#   2. Loads `pets` + ObjectRefs, runs `AI.GENERATE` (`gemini-3.5-flash-lite` &
#      `gemini-3.8-flash`) and `AI.GENERATE_EMBEDDING` (`multimodalembedding@001`
#      & `gemini-embedding-001`)
#   3. Loads `pv_ops_tlm_v2` & `pv_snct_inv_88` (`sql/load_sanctuary_tables.sql`)
#   4. Applies fallback metadata (`apply-enriched-metadata.sh`)
#   5. Runs BigQuery SQL Data Quality Assertions (`sql/dq_assertions.sql`)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$HOME/.env" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.env"
elif [ -f "$SCRIPT_DIR/setenv.sh" ]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/setenv.sh" >/dev/null
fi

export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-$(gcloud config get-value compute/region 2>/dev/null)}"
export DATASET_ID="${DATASET_ID:-petverse}"
export BUCKET="${BUCKET:-${PROJECT_ID}-petverse}"
CONN="${REGION}.pet-connection"

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
  echo "❌ Error: PROJECT_ID or REGION is not set."
  echo "   Export PROJECT_ID and REGION first, then re-run ./catchup.sh."
  exit 1
fi

render_sql_file() {
  local file_path="$1"
  sed \
    -e "s/__PROJECT_ID__-petverse/${BUCKET}/g" \
    -e "s/__PROJECT_ID__/${PROJECT_ID}/g" \
    -e "s/__REGION__/${REGION}/g" \
    -e "s/\.petverse\./.${DATASET_ID}./g" \
    -e "s/SCHEMA IF NOT EXISTS \`${PROJECT_ID}\.petverse\`/SCHEMA IF NOT EXISTS \`${PROJECT_ID}.${DATASET_ID}\`/g" \
    "$file_path"
}

run_bq_step() {
  local step_label="$1"
  local sql="$2"
  local max_attempts=6
  local attempt=1
  local output=""

  echo "  🔄   ${step_label}..."
  while [ "$attempt" -le "$max_attempts" ]; do
    if output=$(bq query \
      --project_id="$PROJECT_ID" \
      --location="$REGION" \
      --use_legacy_sql=false \
      --quiet \
      <<<"$sql" 2>&1); then
      echo "  ✅   ${step_label} complete."
      return 0
    fi

    if [ "$attempt" -lt "$max_attempts" ]; then
      echo "  ⏳   Attempt ${attempt}/${max_attempts} waiting for IAM/service agents to propagate. Retrying in 20s..."
      sleep 20
    fi
    ((attempt++))
  done

  echo "❌ Failed during: ${step_label}"
  echo "$output"
  return 1
}

echo "============================================================================"
echo "🚀 Starting PetVerse Analytics Catch-Up for project: $PROJECT_ID ($REGION)"
echo "============================================================================"

# 1. Base setup, APIs, connection, IAM, GCS bucket, BigQuery tables & ObjectRefs
echo ""
echo "[1/4] Running base setup, bucket staging, table loads & ObjectRef setup..."
bash "$SCRIPT_DIR/petverse-setup.sh"

# 2. Run Gemini AI.GENERATE & AI.GENERATE_EMBEDDING steps
echo ""
echo "[2/4] Running Gemini AI.GENERATE & AI.GENERATE_EMBEDDING enrichments..."

run_bq_step "Enriching ${DATASET_ID}.pets via AI.GENERATE (gemini-3.5-flash-lite & gemini-3.8-flash)" "
ALTER TABLE \`${PROJECT_ID}.${DATASET_ID}.pets\`
ADD COLUMN IF NOT EXISTS MediaDescription STRING
OPTIONS(description = 'AI-generated epic personality and media summary extracted from unstructured pet videos, audio clips, and photos.');

UPDATE \`${PROJECT_ID}.${DATASET_ID}.pets\` AS p
SET FavoriteFood = aigen.food
FROM (
  SELECT
    Id,
    AI.GENERATE(
      prompt => ('What are this pet\'s favorite toy and favorite foods', additional_media),
      connection_id => '${CONN}',
      endpoint => 'gemini-3.5-flash-lite',
      output_schema => 'food STRING'
    ).food AS food
  FROM \`${PROJECT_ID}.${DATASET_ID}.pets\`
  WHERE FavoriteFood IS NULL
    AND additional_media IS NOT NULL
) AS aigen
WHERE p.Id = aigen.Id;

UPDATE \`${PROJECT_ID}.${DATASET_ID}.pets\` AS p
SET MediaDescription = aigen.description
FROM (
  SELECT
    Id,
    AI.GENERATE(
      prompt => ('Create a description in an epic tone for this pet based on these media: ', additional_media),
      connection_id => '${CONN}',
      endpoint => 'gemini-3.8-flash',
      output_schema => 'description STRING'
    ).description AS description
  FROM \`${PROJECT_ID}.${DATASET_ID}.pets\`
  WHERE MediaDescription IS NULL
    AND additional_media IS NOT NULL
) AS aigen
WHERE p.Id = aigen.Id;
"

run_bq_step "Creating multimodalembedding@001 & gemini-embedding-001 models and AI.GENERATE_EMBEDDING tables" "
CREATE OR REPLACE MODEL \`${PROJECT_ID}.${DATASET_ID}.multimodalembedding\`
  REMOTE WITH CONNECTION \`${CONN}\`
  OPTIONS (ENDPOINT = 'multimodalembedding@001');

CREATE OR REPLACE TABLE \`${PROJECT_ID}.${DATASET_ID}.profile_embeddings\` AS
SELECT *
FROM AI.GENERATE_EMBEDDING(
  MODEL \`${PROJECT_ID}.${DATASET_ID}.multimodalembedding\`,
  (
    SELECT profile_picture AS content, Id
    FROM \`${PROJECT_ID}.${DATASET_ID}.pets\`
  )
);

CREATE OR REPLACE MODEL \`${PROJECT_ID}.${DATASET_ID}.textembedding\`
  REMOTE WITH CONNECTION \`${CONN}\`
  OPTIONS (ENDPOINT = 'gemini-embedding-001');

CREATE OR REPLACE TABLE \`${PROJECT_ID}.${DATASET_ID}.text_embeddings\` AS
SELECT *
FROM AI.GENERATE_EMBEDDING(
  MODEL \`${PROJECT_ID}.${DATASET_ID}.textembedding\`,
  (
    SELECT
      CONCAT(
        AdoptionStory,
        ' . This pet\'s hobby is: ',
        Hobby,
        ' and their nickname(s) is: ',
        COALESCE(Nicknames, Name)
      ) AS content,
      Id,
      Name
    FROM \`${PROJECT_ID}.${DATASET_ID}.pets\`
    WHERE LENGTH(AdoptionStory) > 0
      AND LENGTH(Hobby) > 0
  )
)
WHERE LENGTH(status) = 0;
"

# 3. Apply fallback enriched metadata descriptions to pv_ops_tlm_v2
echo ""
echo "[3/4] Applying decoded COBOL metadata descriptions to pv_ops_tlm_v2..."
bash "$SCRIPT_DIR/apply-enriched-metadata.sh"

# 4. Execute Data Quality Assertions
echo ""
echo "[4/4] Running BigQuery SQL Data Quality Assertions (sql/dq_assertions.sql)..."
run_bq_step "Validating data quality assertions" "$(render_sql_file "$SCRIPT_DIR/sql/dq_assertions.sql")"

echo ""
echo "  🔎   Verifying final BigQuery tables:"
bq query \
  --project_id="$PROJECT_ID" \
  --location="$REGION" \
  --use_legacy_sql=false \
  "SELECT
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${DATASET_ID}.pets\`) AS pets_count,
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${DATASET_ID}.pv_ops_tlm_v2\` WHERE st_cd != 9) AS active_telemetry_rows,
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${DATASET_ID}.pv_ops_tlm_v2\` WHERE st_cd = 9) AS calibration_rows,
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${DATASET_ID}.pv_snct_inv_88\`) AS supply_skus_count,
     (SELECT COUNT(*) FROM \`${PROJECT_ID}.${DATASET_ID}.text_embeddings\`) AS text_embeddings_count;"

echo ""
echo "🎉 🐾 Catch-up complete! All BigQuery tables, embeddings, metadata descriptions, and DQ assertions passed."
echo "👉 You are ready for BigQuery Conversational Analytics and AI.FORECAST!"
