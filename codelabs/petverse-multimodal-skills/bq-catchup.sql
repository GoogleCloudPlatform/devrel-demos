-- ============================================================================
-- PetVerse Multimodal Lab (DAT004) - Catchup SQL Script
-- ============================================================================
-- This self-contained SQL script executes all relevant DDL and DML commands
-- on BigQuery tables and models from the DAT004 PetVerse Multimodal lab
-- (/labs/dat004-petverse-multimodal/instructions/en.md).
--
-- INSTRUCTIONS:
-- 1. Paste this in the BigQuery SQL Query Editor. Replace all occurrences of:
--      - PROJECT_ID  -> Your Google Cloud project ID (e.g., qwiklabs-gcp-xx-yyy)
--      - REGION      -> Your lab default region      (e.g., us-central1)
-- 2. Make sure the following prerequisite resources exist before running (run petverse-setup.sh):
--      - Storage bucket: gs://PROJECT_ID-petverse (with pet media & CSV)
--      - External connection: REGION.pet-connection
-- 2. a - Run the creation of the storage bucket and copy (replace the placeholders):
-- gcloud storage buckets create gs://"PROJECT_ID"-petverse --uniform-bucket-level-access --location="REGION"
-- gcloud storage cp -r gs://sample-data-and-media/petverse/* gs://"PROJECT_ID"-petverse/
-- bq mk --dataset --location="REGION" --project_id=PROJECT_ID petverse
-- echo "your bucket is gs://PROJECT_ID-petverse"
-- 3. You can run this entire script at once in the BigQuery Studio SQL Editor.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 0. Ensure default region and schema (dataset) exist
-- ----------------------------------------------------------------------------
SET @@location = 'REGION';

CREATE SCHEMA IF NOT EXISTS petverse
  OPTIONS(
    location = 'REGION'
  );

-- ----------------------------------------------------------------------------
-- 1. Create and populate the `petverse.pets` table from Cloud Storage CSV
-- ----------------------------------------------------------------------------
LOAD DATA INTO petverse.pets
OPTIONS(
    description="Table for furry friend data"
  )
FROM FILES (
  skip_leading_rows=1,
  uris = ['gs://PROJECT_ID-petverse/pets.csv'],
  format = 'CSV'
);

-- ----------------------------------------------------------------------------
-- 2. Add storage media reference columns to `petverse.pets`
-- ----------------------------------------------------------------------------
ALTER TABLE petverse.pets
ADD COLUMN IF NOT EXISTS profile_picture STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>,
ADD COLUMN IF NOT EXISTS additional_media ARRAY<STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>>;

-- ----------------------------------------------------------------------------
-- 3. Update `petverse.pets` records with Cloud Storage media object references
-- ----------------------------------------------------------------------------
UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/yoda_profile_picture.png', 'REGION.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/Yoda_asks_for_cuddles.mp4', 'REGION.pet-connection')))]
WHERE Id = 1;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/madonna_profile_picture.jpg', 'REGION.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/Madonna_description.wav', 'REGION.pet-connection')))]
WHERE Id = 2;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/pixel_profile_picture.png', 'REGION.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/pixel_thug_life.mp4', 'REGION.pet-connection'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/pixel_description.wav', 'REGION.pet-connection')))]
WHERE Id = 3;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/sql_profile_picture.png', 'REGION.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/SQL_description.wav', 'REGION.pet-connection'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/SQL_favorite_toy.mp4', 'REGION.pet-connection')))]
WHERE Id = 4;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/buddy_golden_retriever.png', 'REGION.pet-connection'))),
    additional_media = NULL
WHERE Id = 5;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/daisy_french_bulldog.png', 'REGION.pet-connection'))),
    additional_media = NULL
WHERE Id = 6;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/max_german_shepherd.png', 'REGION.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/max_description_tells_jokes.mp4', 'REGION.pet-connection')))]
WHERE Id = 7;

UPDATE petverse.pets SET profile_picture = NULL, additional_media = NULL WHERE Id = 8;

UPDATE petverse.pets SET profile_picture = NULL, additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/rocky_description.mp4', 'REGION.pet-connection')))] WHERE Id = 9;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/pip_hamster.png', 'REGION.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/pip_Hamster_Wheel_Video_Generated.mp4', 'REGION.pet-connection')))]
WHERE Id = 10;

UPDATE petverse.pets SET profile_picture = NULL, additional_media = NULL WHERE Id = 11;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/scales_snake.png', 'REGION.pet-connection'))),
    additional_media = NULL
WHERE Id = 12;

UPDATE petverse.pets SET profile_picture = NULL, additional_media = NULL WHERE Id = 13;

UPDATE petverse.pets
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/Joel_Profile_Picture.jpg', 'REGION.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/Joel_Catwalk.jpg', 'REGION.pet-connection'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/Joel_Flowers.jpg', 'REGION.pet-connection'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://PROJECT_ID-petverse/additional_media/Joel_Plays.jpg', 'REGION.pet-connection')))]
WHERE Id = 14;

-- ----------------------------------------------------------------------------
-- 4. Generate and update missing FavoriteFood using AI.GENERATE
-- ----------------------------------------------------------------------------
UPDATE petverse.pets AS p
SET FavoriteFood = aigen.food
FROM
  (
    SELECT Id, name,
          AI.GENERATE(
                prompt=> ('What are this pet\'s favorite toy and favorite foods', additional_media ),
                connection_id => 'REGION.pet-connection',
                endpoint => 'gemini-2.5-flash-lite',
                output_schema => 'food STRING').food
    FROM petverse.pets ) AS  aigen
WHERE p.Id = aigen.Id
AND p.FavoriteFood IS NULL
AND p.additional_media IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 5. Add MediaDescription column and populate using AI.GENERATE
-- ----------------------------------------------------------------------------
ALTER TABLE petverse.pets ADD COLUMN IF NOT EXISTS MediaDescription STRING;

UPDATE petverse.pets AS p
SET MediaDescription = aigen.description
FROM
  (
    SELECT Id, name,
          AI.GENERATE(
                prompt=> ('Create a description in an epic tone for this pet based on these media: ', additional_media ),
                connection_id => 'REGION.pet-connection',
                endpoint => 'gemini-2.5-flash',
                output_schema => 'description STRING').description
    FROM petverse.pets ) AS  aigen
WHERE p.Id = aigen.Id
AND p.MediaDescription IS NULL
AND p.additional_media IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 6. Create multimodal image embedding model and profile image embeddings table
-- ----------------------------------------------------------------------------
CREATE OR REPLACE MODEL petverse.multimodalembedding
  REMOTE WITH CONNECTION `REGION.pet-connection`
  OPTIONS(ENDPOINT = 'multimodalembedding@001');

CREATE OR REPLACE TABLE petverse.profile_embeddings
AS
SELECT *
FROM ML.GENERATE_EMBEDDING(
  MODEL petverse.multimodalembedding,
    (
      SELECT profile_picture as content,
      Id
      FROM petverse.pets)
 );

-- ----------------------------------------------------------------------------
-- 7. Create text embedding model and text embeddings table
-- ----------------------------------------------------------------------------
CREATE OR REPLACE MODEL petverse.textembedding
  REMOTE WITH CONNECTION `REGION.pet-connection`
  OPTIONS (ENDPOINT = 'text-embedding-005');

CREATE OR REPLACE TABLE petverse.text_embeddings AS
SELECT * FROM ML.GENERATE_EMBEDDING(
  MODEL petverse.textembedding,
  (
    SELECT CONCAT(AdoptionStory, ' . This pet\'s hobby is: ', Hobby, ' and their nickname(s) is: ', COALESCE(Nicknames, Name)) AS content,
    Id, Name
    FROM petverse.pets
    WHERE LENGTH(AdoptionStory) > 0 AND LENGTH(Hobby) > 0
  )
)
WHERE LENGTH(ml_generate_embedding_status) = 0;
