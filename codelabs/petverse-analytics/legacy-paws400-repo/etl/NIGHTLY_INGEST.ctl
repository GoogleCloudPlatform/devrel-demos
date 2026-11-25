# ==============================================================================
# PAWS/400 -> BIGQUERY NIGHTLY BRIDGE CONTROL & VERIFIED SQL LINEAGE SPEC
# JOB_ID: PV_NIGHTLY_INGEST_0200UTC | OWNER: SANCTUARY-DATA-ENG
# ==============================================================================

[SOURCE_STREAMS]
STREAM_01 = QSYS.LIB/PAWSPROD.LIB/PAWSTLM2.FILE -> gs://${BUCKET}/telemetry/pv_ops_tlm_v2.csv -> petverse.pv_ops_tlm_v2
STREAM_02 = QSYS.LIB/PAWSPROD.LIB/PAWSINV8.FILE -> gs://${BUCKET}/telemetry/pv_snct_inv_88.csv -> petverse.pv_snct_inv_88
MASTER_DIM = gs://${BUCKET}/pets.csv -> petverse.pets

[MANDATORY_JOIN_PATHS]
# Join 1: Link cryptic daily telemetry (`pv_ops_tlm_v2`) to resident profiles (`pets`)
# NOTE: Always exclude `st_cd = 9` (`ent_fk = 99` calibration bench) before or during joins!
JOIN_TELEMETRY_TO_PETS = "petverse.pv_ops_tlm_v2.ent_fk = petverse.pets.Id AND petverse.pv_ops_tlm_v2.st_cd != 9"

# Join 2: Link resident species (`pets.Species` mixed case, e.g. 'Capybara', 'Dog')
#         to warehouse supply inventory (`pv_snct_inv_88.sp_cat_cd` uppercase, e.g. 'CAPYBARA', 'DOG')
JOIN_PETS_TO_INVENTORY = "UPPER(petverse.pets.Species) = petverse.pv_snct_inv_88.sp_cat_cd"

[UNIT_CONVERSION_GUARDS]
NUTRITION_GRAMS_TO_KG = "nutr_g_qty / 1000.0"
CARE_CENTS_TO_USD     = "care_c_usd / 100.0"
SKU_UNIT_CENTS_TO_USD = "unit_cost_c / 100.0"
VALID_RESIDENT_FILTER = "st_cd != 9"

[VERIFIED_SQL_TEMPLATE_SPECIES_SPEND]
-- Verified Query 1: Total & average daily care spend in USD by species (excluding calibration bench)
SELECT
  p.Species,
  COUNT(DISTINCT p.Id) AS resident_count,
  ROUND(SUM(t.care_c_usd) / 100.0, 2) AS total_care_spend_usd,
  ROUND(AVG(t.care_c_usd) / 100.0, 2) AS avg_daily_care_spend_per_pet_usd
FROM `petverse.pv_ops_tlm_v2` AS t
JOIN `petverse.pets` AS p
  ON t.ent_fk = p.Id
WHERE t.st_cd != 9
GROUP BY p.Species
ORDER BY total_care_spend_usd DESC;

[VERIFIED_SQL_TEMPLATE_14D_SUPPLY_FORECAST]
-- Verified Query 2: 14-day AI.FORECAST feed demand (kg) vs. warehouse stock & reorder threshold
WITH pet_daily_feed AS (
  SELECT
    t.ent_fk,
    t.ts_dt,
    t.nutr_g_qty
  FROM `petverse.pv_ops_tlm_v2` AS t
  WHERE t.st_cd != 9
),
pet_forecast_14d AS (
  SELECT
    ent_fk,
    forecast_timestamp,
    forecast_value
  FROM AI.FORECAST(
    TABLE pet_daily_feed,
    data_col => 'nutr_g_qty',
    timestamp_col => 'ts_dt',
    id_cols => ['ent_fk'],
    horizon => 14
  )
),
species_demand_14d AS (
  SELECT
    UPPER(p.Species) AS sp_cat_cd,
    ROUND(SUM(f.forecast_value) / 1000.0, 2) AS forecasted_14d_demand_kg
  FROM pet_forecast_14d AS f
  JOIN `petverse.pets` AS p
    ON f.ent_fk = p.Id
  GROUP BY sp_cat_cd
)
SELECT
  i.sku_cd,
  i.sp_cat_cd,
  i.itm_lbl,
  i.cur_stk_kg,
  d.forecasted_14d_demand_kg,
  ROUND(i.cur_stk_kg - d.forecasted_14d_demand_kg, 2) AS projected_ending_stock_kg,
  i.reord_thr_kg,
  (i.cur_stk_kg - d.forecasted_14d_demand_kg) < i.reord_thr_kg AS needs_reorder_within_14d
FROM `petverse.pv_snct_inv_88` AS i
JOIN species_demand_14d AS d
  ON i.sp_cat_cd = d.sp_cat_cd
ORDER BY projected_ending_stock_kg ASC;
