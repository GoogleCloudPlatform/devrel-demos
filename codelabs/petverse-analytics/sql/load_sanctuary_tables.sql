-- ============================================================================
-- PetVerse Sanctuary Analytics - Load Legacy Telemetry & Supply Inventory Tables
-- ============================================================================
-- Placeholders:
--   __PROJECT_ID__ -> Your Google Cloud project ID
--   __REGION__     -> Your BigQuery dataset region (e.g., __REGION__)
--   Dataset        -> `petverse` (configurable via DATASET_ID in orchestration scripts)
-- ============================================================================

SET @@location = '__REGION__';

CREATE SCHEMA IF NOT EXISTS `__PROJECT_ID__.petverse`
  OPTIONS (
    location = '__REGION__'
  );

-- ----------------------------------------------------------------------------
-- 1. Undocumented Cryptic Telemetry Table: `petverse.pv_ops_tlm_v2`
--    Intentionally created with NO table description and NO column descriptions
--    so Knowledge Studio Metadata Enrichment decodes it from PAWSTLM2.cpy!
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

-- ----------------------------------------------------------------------------
-- 2. Documented Supply Inventory Table: `petverse.pv_snct_inv_88`
--    Created WITH rich table & column descriptions so users can immediately
--    discover it via natural-language semantic search in Knowledge Catalog!
-- ----------------------------------------------------------------------------
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
