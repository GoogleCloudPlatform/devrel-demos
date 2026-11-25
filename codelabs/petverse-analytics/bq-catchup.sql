-- ============================================================================
-- PetVerse Sanctuary Analytics - Full BigQuery Catch-Up SQL Script
-- ============================================================================
-- Idempotent multi-statement GoogleSQL script that provisions and populates
-- all BigQuery resources up to Conversational Analytics:
--   1. `petverse` dataset in `__REGION__`
--   2. `petverse.pets` loaded with Cloud Storage ObjectRef multimodal columns
--   3. Multimodal AI enrichments (`FavoriteFood`, `MediaDescription`) via
--      `AI.GENERATE` using `gemini-3.5-flash-lite` and `gemini-3.8-flash`
--   4. Remote embedding models (`multimodalembedding@001`, `gemini-embedding-001`)
--      and vector tables (`profile_embeddings`, `text_embeddings`)
--   5. Sanctuary telemetry (`pv_ops_tlm_v2`) and supply vault (`pv_snct_inv_88`)
--   6. Enriched COBOL metadata descriptions on `pv_ops_tlm_v2`
--
-- Placeholders:
--   __PROJECT_ID__ -> Your Google Cloud project ID
--   __REGION__     -> Your BigQuery dataset region (e.g., __REGION__)
-- ============================================================================

SET @@location = '__REGION__';

CREATE SCHEMA IF NOT EXISTS `__PROJECT_ID__.petverse`
  OPTIONS (
    location = '__REGION__'
  );

-- ----------------------------------------------------------------------------
-- 1. Load `petverse.pets` and attach Cloud Storage ObjectRef media columns
-- ----------------------------------------------------------------------------
LOAD DATA OVERWRITE `__PROJECT_ID__.petverse.pets`
OPTIONS (
  description = 'Master registry of PetVerse animal sanctuary residents, adoption stories, hobbies, and multimodal media.'
)
FROM FILES (
  skip_leading_rows = 1,
  uris = ['gs://__PROJECT_ID__-petverse/pets.csv'],
  format = 'CSV'
);

ALTER TABLE `__PROJECT_ID__.petverse.pets`
ADD COLUMN IF NOT EXISTS profile_picture STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>,
ADD COLUMN IF NOT EXISTS additional_media ARRAY<STRUCT<uri STRING, version STRING, authorizer STRING, details JSON>>,
ADD COLUMN IF NOT EXISTS MediaDescription STRING;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/yoda_profile_picture.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Yoda_asks_for_cuddles.mp4', '__REGION__.pet-connection')))]
WHERE Id = 1;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/madonna_profile_picture.jpg', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Madonna_description.wav', '__REGION__.pet-connection')))]
WHERE Id = 2;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/pixel_profile_picture.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/pixel_thug_life.mp4', '__REGION__.pet-connection'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/pixel_description.wav', '__REGION__.pet-connection')))]
WHERE Id = 3;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/sql_profile_picture.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/SQL_description.wav', '__REGION__.pet-connection'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/SQL_favorite_toy.mp4', '__REGION__.pet-connection')))]
WHERE Id = 4;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/buddy_golden_retriever.png', '__REGION__.pet-connection'))),
    additional_media = NULL
WHERE Id = 5;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/daisy_french_bulldog.png', '__REGION__.pet-connection'))),
    additional_media = NULL
WHERE Id = 6;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/max_german_shepherd.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/max_description_tells_jokes.mp4', '__REGION__.pet-connection')))]
WHERE Id = 7;

UPDATE `__PROJECT_ID__.petverse.pets` SET profile_picture = NULL, additional_media = NULL WHERE Id = 8;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = NULL,
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/rocky_description.mp4', '__REGION__.pet-connection')))]
WHERE Id = 9;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/pip_hamster.png', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/pip_Hamster_Wheel_Video_Generated.mp4', '__REGION__.pet-connection')))]
WHERE Id = 10;

UPDATE `__PROJECT_ID__.petverse.pets` SET profile_picture = NULL, additional_media = NULL WHERE Id = 11;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/scales_snake.png', '__REGION__.pet-connection'))),
    additional_media = NULL
WHERE Id = 12;

UPDATE `__PROJECT_ID__.petverse.pets` SET profile_picture = NULL, additional_media = NULL WHERE Id = 13;

UPDATE `__PROJECT_ID__.petverse.pets`
SET profile_picture = (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/Joel_Profile_Picture.jpg', '__REGION__.pet-connection'))),
    additional_media = [(SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Joel_Catwalk.jpg', '__REGION__.pet-connection'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Joel_Flowers.jpg', '__REGION__.pet-connection'))),
                       (SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF('gs://__PROJECT_ID__-petverse/additional_media/Joel_Plays.jpg', '__REGION__.pet-connection')))]
WHERE Id = 14;

-- ----------------------------------------------------------------------------
-- 2. Enrich `FavoriteFood` & `MediaDescription` via AI.GENERATE (Gemini 3.x)
-- ----------------------------------------------------------------------------
UPDATE `__PROJECT_ID__.petverse.pets` AS p
SET FavoriteFood = aigen.food
FROM (
  SELECT
    Id,
    AI.GENERATE(
      prompt => ('What are this pet\'s favorite toy and favorite foods', additional_media),
      connection_id => '__REGION__.pet-connection',
      endpoint => 'gemini-3.5-flash-lite',
      output_schema => 'food STRING'
    ).food AS food
  FROM `__PROJECT_ID__.petverse.pets`
  WHERE FavoriteFood IS NULL
    AND additional_media IS NOT NULL
) AS aigen
WHERE p.Id = aigen.Id;

UPDATE `__PROJECT_ID__.petverse.pets` AS p
SET MediaDescription = aigen.description
FROM (
  SELECT
    Id,
    AI.GENERATE(
      prompt => ('Create a description in an epic tone for this pet based on these media: ', additional_media),
      connection_id => '__REGION__.pet-connection',
      endpoint => 'gemini-3.8-flash',
      output_schema => 'description STRING'
    ).description AS description
  FROM `__PROJECT_ID__.petverse.pets`
  WHERE MediaDescription IS NULL
    AND additional_media IS NOT NULL
) AS aigen
WHERE p.Id = aigen.Id;

-- ----------------------------------------------------------------------------
-- 3. Create Remote Embedding Models & Embedding Tables
-- ----------------------------------------------------------------------------
CREATE OR REPLACE MODEL `__PROJECT_ID__.petverse.multimodalembedding`
  REMOTE WITH CONNECTION `__REGION__.pet-connection`
  OPTIONS (ENDPOINT = 'multimodalembedding@001');

CREATE OR REPLACE TABLE `__PROJECT_ID__.petverse.profile_embeddings` AS
SELECT *
FROM AI.GENERATE_EMBEDDING(
  MODEL `__PROJECT_ID__.petverse.multimodalembedding`,
  (
    SELECT profile_picture AS content, Id
    FROM `__PROJECT_ID__.petverse.pets`
  )
);

CREATE OR REPLACE MODEL `__PROJECT_ID__.petverse.textembedding`
  REMOTE WITH CONNECTION `__REGION__.pet-connection`
  OPTIONS (ENDPOINT = 'gemini-embedding-001');

CREATE OR REPLACE TABLE `__PROJECT_ID__.petverse.text_embeddings` AS
SELECT *
FROM AI.GENERATE_EMBEDDING(
  MODEL `__PROJECT_ID__.petverse.textembedding`,
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
    FROM `__PROJECT_ID__.petverse.pets`
    WHERE LENGTH(AdoptionStory) > 0
      AND LENGTH(Hobby) > 0
  )
)
WHERE LENGTH(status) = 0;

-- ----------------------------------------------------------------------------
-- 4. Load Sanctuary Telemetry (`pv_ops_tlm_v2`) & Supply Vault (`pv_snct_inv_88`)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE `__PROJECT_ID__.petverse.pv_ops_tlm_v2` (
  rec_seq_id STRING,
  ent_fk INT64,
  ts_dt DATE,
  nutr_g_qty FLOAT64,
  act_k_stp INT64,
  slp_m_dur INT64,
  care_c_usd INT64,
  st_cd INT64
);

LOAD DATA OVERWRITE `__PROJECT_ID__.petverse.pv_ops_tlm_v2` (
  rec_seq_id STRING,
  ent_fk INT64,
  ts_dt DATE,
  nutr_g_qty FLOAT64,
  act_k_stp INT64,
  slp_m_dur INT64,
  care_c_usd INT64,
  st_cd INT64
)
FROM FILES (
  format = 'CSV',
  skip_leading_rows = 1,
  uris = ['gs://__PROJECT_ID__-petverse/telemetry/pv_ops_tlm_v2.csv']
);

CREATE OR REPLACE TABLE `__PROJECT_ID__.petverse.pv_snct_inv_88` (
  sku_cd STRING OPTIONS (
    description = 'Unique sanctuary warehouse stock-keeping unit (SKU) identifier for pet food and cold-storage rations (e.g., SKU-GRN-13, SKU-KBL-05).'
  ),
  sp_cat_cd STRING OPTIONS (
    description = 'Uppercase pet species category code (CAT, DOG, HAMSTER, SNAKE, CAPYBARA). Joins to `petverse.pets` via `UPPER(pets.Species) = pv_snct_inv_88.sp_cat_cd`.'
  ),
  itm_lbl STRING OPTIONS (
    description = 'Human-readable ration and feed bundle description in the sanctuary supply vault.'
  ),
  cur_stk_kg FLOAT64 OPTIONS (
    description = 'Current physical on-hand warehouse feed inventory measured in kilograms (kg). Compare against forecasted feed demand converted from grams (`nutr_g_qty / 1000.0`).'
  ),
  reord_thr_kg FLOAT64 OPTIONS (
    description = 'Minimum safety stock reorder threshold in kilograms (kg). Trigger a restock order when projected ending inventory falls below `reord_thr_kg`.'
  ),
  unit_cost_c INT64 OPTIONS (
    description = 'Wholesale replacement cost per kilogram stored in US cents (divide `unit_cost_c / 100.0` for USD per kg).'
  ),
  cold_flg STRING OPTIONS (
    description = 'Refrigerated or cryogenic cold-storage requirement flag (`Y` = refrigerated vault required, `N` = dry ambient storage).'
  )
)
OPTIONS (
  description = 'Sanctuary cold-storage and dry-goods pet food supply inventory vault, safety reorder thresholds in kilograms, and wholesale unit costs in US cents.'
);

LOAD DATA OVERWRITE `__PROJECT_ID__.petverse.pv_snct_inv_88` (
  sku_cd STRING OPTIONS (
    description = 'Unique sanctuary warehouse stock-keeping unit (SKU) identifier for pet food and cold-storage rations (e.g., SKU-GRN-13, SKU-KBL-05).'
  ),
  sp_cat_cd STRING OPTIONS (
    description = 'Uppercase pet species category code (CAT, DOG, HAMSTER, SNAKE, CAPYBARA). Joins to `petverse.pets` via `UPPER(pets.Species) = pv_snct_inv_88.sp_cat_cd`.'
  ),
  itm_lbl STRING OPTIONS (
    description = 'Human-readable ration and feed bundle description in the sanctuary supply vault.'
  ),
  cur_stk_kg FLOAT64 OPTIONS (
    description = 'Current physical on-hand warehouse feed inventory measured in kilograms (kg). Compare against forecasted feed demand converted from grams (`nutr_g_qty / 1000.0`).'
  ),
  reord_thr_kg FLOAT64 OPTIONS (
    description = 'Minimum safety stock reorder threshold in kilograms (kg). Trigger a restock order when projected ending inventory falls below `reord_thr_kg`.'
  ),
  unit_cost_c INT64 OPTIONS (
    description = 'Wholesale replacement cost per kilogram stored in US cents (divide `unit_cost_c / 100.0` for USD per kg).'
  ),
  cold_flg STRING OPTIONS (
    description = 'Refrigerated or cryogenic cold-storage requirement flag (`Y` = refrigerated vault required, `N` = dry ambient storage).'
  )
)
OPTIONS (
  description = 'Sanctuary cold-storage and dry-goods pet food supply inventory vault, safety reorder thresholds in kilograms, and wholesale unit costs in US cents.'
)
FROM FILES (
  format = 'CSV',
  skip_leading_rows = 1,
  uris = ['gs://__PROJECT_ID__-petverse/telemetry/pv_snct_inv_88.csv']
);

-- ----------------------------------------------------------------------------
-- 5. Apply Decoded COBOL Metadata Descriptions to `pv_ops_tlm_v2`
-- ----------------------------------------------------------------------------
ALTER TABLE `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
SET OPTIONS (
  description = 'Daily sanctuary pet resident nutrition, physical activity, sleep duration, and care-cost telemetry extracted from the legacy PAWS/400 system. Joins to `petverse.pets` on `pv_ops_tlm_v2.ent_fk = pets.Id`. CRITICAL RULE: Always filter `WHERE st_cd != 9` to exclude hardware bench calibration rows (`ent_fk = 99`) from all analytics, spend totals, and `AI.FORECAST` queries.'
);

ALTER TABLE `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
ALTER COLUMN rec_seq_id SET OPTIONS (
  description = 'Sequential PAWS/400 mainframe telemetry primary key identifier (e.g., TLM-100001).'
),
ALTER COLUMN ent_fk SET OPTIONS (
  description = 'Sanctuary resident pet identifier (foreign key to `petverse.pets.Id`, values 1..14). Value `99` represents the non-animal load-cell hardware calibration bench and must be excluded (`st_cd != 9`).'
),
ALTER COLUMN ts_dt SET OPTIONS (
  description = 'Daily UTC telemetry observation date (`YYYY-MM-DD`). Continuous daily time-series timestamp column for `AI.FORECAST`.'
),
ALTER COLUMN nutr_g_qty SET OPTIONS (
  description = 'Daily food and nutrition consumed measured in grams (g). Divide by 1000.0 (`nutr_g_qty / 1000.0`) to convert to kilograms (kg) when comparing against `pv_snct_inv_88.cur_stk_kg`.'
),
ALTER COLUMN act_k_stp SET OPTIONS (
  description = 'Daily physical activity sensor count (collar pedometer steps or hamster exercise wheel revolutions). Residents with `AVG(act_k_stp) > 12000` (where `st_cd != 9`) are classified as High-Energy Residents.'
),
ALTER COLUMN slp_m_dur SET OPTIONS (
  description = 'Daily total sleep and rest duration measured in minutes (divide by 60.0 for hours).'
),
ALTER COLUMN care_c_usd SET OPTIONS (
  description = 'Daily nutrition, supplement, and enrichment care cost stored in US cents (1/100 USD). Divide by 100.0 (`care_c_usd / 100.0`) to calculate Daily Care Spend in US dollars ($ USD).'
),
ALTER COLUMN st_cd SET OPTIONS (
  description = 'Telemetry operational status code: `1` = Valid Active Resident Standard Reading, `2` = Valid Active Resident Vet Checkup Observation Day, `9` = Hardware Calibration Test Row (`ent_fk = 99`). MUST exclude `st_cd = 9` (`WHERE st_cd != 9`) from all analytics, aggregations, and `AI.FORECAST` queries!'
);
