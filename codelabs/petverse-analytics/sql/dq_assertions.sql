-- ============================================================================
-- PetVerse Sanctuary Analytics - BigQuery SQL Data Quality Assertions
-- ============================================================================
-- Validates primary key uniqueness, NOT NULL constraints, foreign key
-- referential integrity against `petverse.pets`, continuous daily time-series
-- completeness for `AI.FORECAST`, and domain constraints.
--
-- Placeholders:
--   __PROJECT_ID__ -> Your Google Cloud project ID
--   __REGION__     -> Your BigQuery dataset region (e.g., __REGION__)
-- ============================================================================

SET @@location = '__REGION__';

-- ----------------------------------------------------------------------------
-- 1. `petverse.pets` Master Dimension Assertions
-- ----------------------------------------------------------------------------
ASSERT (
  SELECT COUNT(*) = 14
  FROM `__PROJECT_ID__.petverse.pets`
) AS 'Expected exactly 14 sanctuary residents in petverse.pets';

ASSERT (
  SELECT COUNT(*) = COUNT(DISTINCT Id) AND COUNTIF(Id IS NULL OR Name IS NULL OR Species IS NULL) = 0
  FROM `__PROJECT_ID__.petverse.pets`
) AS 'petverse.pets.Id must be unique and Id/Name/Species must be NOT NULL';

-- ----------------------------------------------------------------------------
-- 2. `petverse.pv_ops_tlm_v2` Telemetry Completeness, PK/Grain & Domain Checks
-- ----------------------------------------------------------------------------
ASSERT (
  SELECT COUNT(*) = 1260
  FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
  WHERE st_cd != 9
) AS 'Expected 1,260 active resident telemetry rows (14 pets * 90 days) where st_cd != 9';

ASSERT (
  SELECT COUNT(*) = 15
  FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
  WHERE st_cd = 9 AND ent_fk = 99
) AS 'Expected 15 hardware bench calibration rows (ent_fk = 99, st_cd = 9)';

ASSERT (
  SELECT COUNTIF(
    rec_seq_id IS NULL
    OR ent_fk IS NULL
    OR ts_dt IS NULL
    OR nutr_g_qty IS NULL
    OR act_k_stp IS NULL
    OR slp_m_dur IS NULL
    OR care_c_usd IS NULL
    OR st_cd IS NULL
  ) = 0
  FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
) AS 'Zero NULL values permitted across key and metric columns in pv_ops_tlm_v2';

ASSERT (
  SELECT COUNT(*) = COUNT(DISTINCT rec_seq_id)
  FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
) AS 'Primary key rec_seq_id in pv_ops_tlm_v2 must be unique';

ASSERT (
  SELECT COUNT(*) = (
    SELECT COUNT(*)
    FROM (
      SELECT DISTINCT ent_fk, ts_dt
      FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
    )
  )
  FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
) AS 'Composite key (ent_fk, ts_dt) in pv_ops_tlm_v2 must be unique with one reading per entity per day';

ASSERT (
  SELECT COUNT(*) = 0
  FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2` AS t
  LEFT JOIN `__PROJECT_ID__.petverse.pets` AS p
    ON t.ent_fk = p.Id
  WHERE t.st_cd != 9
    AND p.Id IS NULL
) AS 'Foreign key violation: all active telemetry rows (st_cd != 9) must reference a valid petverse.pets.Id';

ASSERT (
  SELECT COUNTIF(
    st_cd NOT IN (1, 2, 9)
    OR nutr_g_qty <= 0
    OR act_k_stp < 0
    OR slp_m_dur < 0
    OR slp_m_dur > 1440
    OR care_c_usd <= 0
  ) = 0
  FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
) AS 'Domain violation in pv_ops_tlm_v2: invalid st_cd or out-of-range metric values';

-- Date continuity check required for gap-free daily `AI.FORECAST` series per pet
ASSERT (
  SELECT COUNT(*) = 0
  FROM (
    SELECT
      ent_fk,
      COUNT(*) AS row_cnt,
      COUNT(DISTINCT ts_dt) AS distinct_days,
      DATE_DIFF(MAX(ts_dt), MIN(ts_dt), DAY) + 1 AS span_days
    FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
    WHERE st_cd != 9
    GROUP BY ent_fk
    HAVING row_cnt != 90 OR distinct_days != span_days
  )
) AS 'Date continuity violation: every active resident must have 90 consecutive gap-free daily observations for AI.FORECAST';

-- ----------------------------------------------------------------------------
-- 3. `petverse.pv_snct_inv_88` Warehouse Inventory Integrity Checks
-- ----------------------------------------------------------------------------
ASSERT (
  SELECT COUNT(*) = 5 AND COUNT(*) = COUNT(DISTINCT sku_cd)
  FROM `__PROJECT_ID__.petverse.pv_snct_inv_88`
) AS 'pv_snct_inv_88 must have 5 unique supply SKUs keyed by sku_cd';

ASSERT (
  SELECT COUNTIF(
    sku_cd IS NULL
    OR sp_cat_cd IS NULL
    OR itm_lbl IS NULL
    OR cur_stk_kg IS NULL
    OR reord_thr_kg IS NULL
    OR unit_cost_c IS NULL
    OR cold_flg IS NULL
    OR cur_stk_kg <= 0
    OR reord_thr_kg <= 0
    OR unit_cost_c <= 0
    OR cold_flg NOT IN ('Y', 'N')
  ) = 0
  FROM `__PROJECT_ID__.petverse.pv_snct_inv_88`
) AS 'pv_snct_inv_88 must have non-null SKUs, positive stock/thresholds/costs, and cold_flg IN (Y, N)';

ASSERT (
  SELECT COUNT(*) = 0
  FROM (
    SELECT DISTINCT UPPER(Species) AS sp_cat_cd
    FROM `__PROJECT_ID__.petverse.pets`
  ) AS p
  LEFT JOIN `__PROJECT_ID__.petverse.pv_snct_inv_88` AS i
    ON p.sp_cat_cd = i.sp_cat_cd
  WHERE i.sku_cd IS NULL
) AS 'Referential coverage failure: every species in petverse.pets must map to a supply SKU in pv_snct_inv_88';
