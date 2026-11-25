-- ============================================================================
-- PetVerse Sanctuary Analytics - Fallback Metadata Enrichment for pv_ops_tlm_v2
-- ============================================================================
-- Applies the decoded AS/400 COBOL Copybook (`PAWSTLM2.cpy`) and Sanctuary KPI
-- (`SYS_DICT_98.ini`) business descriptions directly to `petverse.pv_ops_tlm_v2`.
-- Use this script if a student's Knowledge Studio Preview enrichment job is
-- still running when they start Conversational Analytics!
--
-- Placeholders:
--   __PROJECT_ID__ -> Your Google Cloud project ID
--   __REGION__     -> Your BigQuery dataset region (e.g., __REGION__)
-- ============================================================================

SET @@location = '__REGION__';

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
