#!/usr/bin/env bash
# ============================================================================
# PetVerse Multimodal Lab (DAT004) - Full "Catch Me Up" Script
# ============================================================================
# Provisions and populates all prerequisite Google Cloud & BigQuery resources
# up to the Web Application task:
#   1. Environment variables, Antigravity CLI config, BigQuery Cloud Resource
#      connection (`pet-connection`), and connection Service Account IAM roles
#   2. Cloud Storage bucket (`gs://$PROJECT_ID-petverse`) & sample pet media
#   3. BigQuery `petverse` dataset
#   4. `petverse.pets` table loaded from CSV + `ObjectRef` media references
#   5. Multimodal AI enrichments (`FavoriteFood` & `MediaDescription` via Gemini)
#   6. Remote embedding models (`multimodalembedding` & `textembedding`) and
#      embedding tables (`profile_embeddings` & `text_embeddings`)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$HOME/.env" ]; then
  # shellcheck disable=SC1091
  source "$HOME/.env"
elif [ -f "$SCRIPT_DIR/setenv.sh" ]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/setenv.sh"
fi

export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
export REGION="${REGION:-$(gcloud config get-value compute/region 2>/dev/null)}"

if [ -z "$PROJECT_ID" ] || [ -z "$REGION" ]; then
  echo "❌ Error: PROJECT_ID or REGION is not set."
  echo "   Export PROJECT_ID and REGION first, then re-run this script."
  exit 1
fi

BUCKET="${PROJECT_ID}-petverse"
CONN="${REGION}.pet-connection"

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
      "$sql" 2>&1); then
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
echo "🚀 Starting PetVerse Catch-Up for project: $PROJECT_ID ($REGION)"
echo "============================================================================"

# 1. Run base setup (auth check, .env, Antigravity CLI config, BQ connection & IAM)
echo ""
echo "[1/6] Running base setup & BigQuery connection IAM..."
bash "$SCRIPT_DIR/petverse-setup.sh"

# 2. Create Cloud Storage bucket & copy sample pet media
echo ""
echo "[2/6] Setting up Cloud Storage bucket gs://${BUCKET} and copying pet media..."
if ! gcloud storage buckets describe "gs://${BUCKET}" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET}" \
    --project="$PROJECT_ID" \
    --uniform-bucket-level-access \
    --location="$REGION"
fi
gcloud storage cp -r gs://sample-data-and-media/petverse/* "gs://${BUCKET}/"
echo "  ✅   Sample pet media copied to gs://${BUCKET}/."

# 3. Create BigQuery dataset & verify ObjectRef connection readiness
echo ""
echo "[3/6] Creating BigQuery dataset 'petverse' and verifying connection readiness..."
bq --location="$REGION" mk --dataset --project_id="$PROJECT_ID" petverse >/dev/null 2>&1 || true

run_bq_step "Verifying BigQuery connection (${CONN}) access to Cloud Storage" "
SELECT OBJ.FETCH_METADATA(
  OBJ.MAKE_REF('gs://${BUCKET}/yoda_profile_picture.png', '${CONN}')
);
"

# 4. Load petverse.pets and populate ObjectRef media references
echo ""
echo "[4/6] Creating petverse.pets and attaching Cloud Storage ObjectRef metadata..."
run_bq_step "Loading pets.csv and populating profile_picture & additional_media references" "
LOAD DATA OVERWRITE petverse.pets
OPTIONS(description='Table for furry friend data')
FROM FILES (
  skip_leading_rows = 1,
  uris = ['gs://${BUCKET}/pets.csv'],
  format = 'CSV'
);

ALTER TABLE petverse.pets
ADD COLUMN IF NOT EXISTS profile_picture STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>,
ADD COLUMN IF NOT EXISTS additional_media ARRAY<STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>>,
ADD COLUMN IF NOT EXISTS MediaDescription STRING;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/yoda_profile_picture.png', '${CONN}'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/Yoda_asks_for_cuddles.mp4', '${CONN}')))]
WHERE Id = 1;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/madonna_profile_picture.jpg', '${CONN}'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/Madonna_description.wav', '${CONN}')))]
WHERE Id = 2;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/pixel_profile_picture.png', '${CONN}'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/pixel_thug_life.mp4', '${CONN}'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/pixel_description.wav', '${CONN}')))]
WHERE Id = 3;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/sql_profile_picture.png', '${CONN}'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/SQL_description.wav', '${CONN}'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/SQL_favorite_toy.mp4', '${CONN}')))]
WHERE Id = 4;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/buddy_golden_retriever.png', '${CONN}'))),
    additional_media = NULL
WHERE Id = 5;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/daisy_french_bulldog.png', '${CONN}'))),
    additional_media = NULL
WHERE Id = 6;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/max_german_shepherd.png', '${CONN}'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/max_description_tells_jokes.mp4', '${CONN}')))]
WHERE Id = 7;

UPDATE petverse.pets SET profile_picture = NULL, additional_media = NULL WHERE Id = 8;

UPDATE petverse.pets
SET profile_picture = NULL,
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/rocky_description.mp4', '${CONN}')))]
WHERE Id = 9;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/pip_hamster.png', '${CONN}'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/pip_Hamster_Wheel_Video_Generated.mp4', '${CONN}')))]
WHERE Id = 10;

UPDATE petverse.pets SET profile_picture = NULL, additional_media = NULL WHERE Id = 11;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/scales_snake.png', '${CONN}'))),
    additional_media = NULL
WHERE Id = 12;

UPDATE petverse.pets SET profile_picture = NULL, additional_media = NULL WHERE Id = 13;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/Joel_Profile_Picture.jpg', '${CONN}'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/Joel_Catwalk.jpg', '${CONN}'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/Joel_Flowers.jpg', '${CONN}'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://${BUCKET}/additional_media/Joel_Plays.jpg', '${CONN}')))]
WHERE Id = 14;
"

# 5. Populate FavoriteFood and MediaDescription via AI.GENERATE (Gemini 2.5)
echo ""
echo "[5/6] Generating multimodal FavoriteFood and MediaDescription fields with Gemini..."
run_bq_step "Enriching petverse.pets with AI.GENERATE (gemini-2.5-flash-lite & gemini-2.5-flash)" "
UPDATE petverse.pets AS p
SET FavoriteFood = aigen.food
FROM (
  SELECT
    Id,
    AI.GENERATE(
      prompt => ('What are this pet\'s favorite toy and favorite foods', additional_media),
      connection_id => '${CONN}',
      endpoint => 'gemini-2.5-flash-lite',
      output_schema => 'food STRING'
    ).food AS food
  FROM petverse.pets
  WHERE FavoriteFood IS NULL
    AND additional_media IS NOT NULL
) AS aigen
WHERE p.Id = aigen.Id;

UPDATE petverse.pets AS p
SET MediaDescription = aigen.description
FROM (
  SELECT
    Id,
    AI.GENERATE(
      prompt => ('Create a description in an epic tone for this pet based on these media: ', additional_media),
      connection_id => '${CONN}',
      endpoint => 'gemini-2.5-flash',
      output_schema => 'description STRING'
    ).description AS description
  FROM petverse.pets
  WHERE MediaDescription IS NULL
    AND additional_media IS NOT NULL
) AS aigen
WHERE p.Id = aigen.Id;
"

# 6. Create remote embedding models and embedding tables
echo ""
echo "[6/6] Creating remote embedding models and generating profile & text embeddings..."
run_bq_step "Creating multimodalembedding & textembedding models and embedding tables" "
CREATE OR REPLACE MODEL petverse.multimodalembedding
  REMOTE WITH CONNECTION \`${CONN}\`
  OPTIONS(ENDPOINT = 'multimodalembedding@001');

CREATE OR REPLACE TABLE petverse.profile_embeddings AS
SELECT *
FROM ML.GENERATE_EMBEDDING(
  MODEL petverse.multimodalembedding,
  (
    SELECT profile_picture AS content, Id
    FROM petverse.pets
  )
);

CREATE OR REPLACE MODEL petverse.textembedding
  REMOTE WITH CONNECTION \`${CONN}\`
  OPTIONS(ENDPOINT = 'text-embedding-005');

CREATE OR REPLACE TABLE petverse.text_embeddings AS
SELECT *
FROM ML.GENERATE_EMBEDDING(
  MODEL petverse.textembedding,
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
    FROM petverse.pets
    WHERE LENGTH(AdoptionStory) > 0
      AND LENGTH(Hobby) > 0
  )
)
WHERE LENGTH(ml_generate_embedding_status) = 0;
"

echo ""
echo "  🔎   Verifying final BigQuery tables:"
bq query \
  --project_id="$PROJECT_ID" \
  --location="$REGION" \
  --use_legacy_sql=false \
  "SELECT
     (SELECT COUNT(*) FROM petverse.pets) AS pets_count,
     (SELECT COUNT(*) FROM petverse.pets WHERE profile_picture IS NOT NULL) AS pets_with_profile_pic,
     (SELECT COUNT(*) FROM petverse.pets WHERE MediaDescription IS NOT NULL) AS pets_with_ai_description,
     (SELECT COUNT(*) FROM petverse.profile_embeddings WHERE LENGTH(ml_generate_embedding_status) = 0) AS profile_embeddings_count,
     (SELECT COUNT(*) FROM petverse.text_embeddings) AS text_embeddings_count;"

echo ""
echo "🎉 🐾 Catch-up complete! All BigQuery connections, models, and final tables are ready."
echo "👉 You can now skip ahead to the \"Create embeddings and perform similarity search\" step in the lab instructions!"
