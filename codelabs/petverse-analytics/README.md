# PetVerse Sanctuary Analytics: Companion Code & Legacy Metadata Repository

Companion code, configurable sample telemetry generator, mock PAWS/400 legacy COBOL/ETL repository, BigQuery SQL scripts, Data Quality Assertions, and setup/catch-up/teardown scripts for the **PetVerse Analytics** codelab (Knowledge Catalog, Knowledge Studio Metadata Enrichment, Conversational Analytics, and `AI.FORECAST`).

---

## Repository Structure

```text
petverse-analytics/
├── setenv.sh                         # Exports PROJECT_ID, REGION, DATASET_ID, BUCKET
├── petverse-setup.sh                 # APIs, IAM, bucket & staged assets, BQ dataset, tables & ObjectRefs
├── setup-object-refs.sh              # Populates Cloud Storage ObjectRef media columns across petverse.pets
├── apply-enriched-metadata.sh        # Instant fallback applying decoded COBOL metadata to pv_ops_tlm_v2
├── catchup.sh                        # Full idempotent end-to-end catch-up + DQ assertions
├── bq-catchup.sql                    # Standalone multi-statement BigQuery SQL catch-up script
├── teardown.sh                       # Cleanly deletes dataset, connection, bucket, and kc-enrichment-sa
├── scripts/
│   ├── pet_profiles_seed.txt         # Pipe-delimited baseline telemetry parameters for all 14 pets
│   ├── supply_skus_seed.txt          # Pipe-delimited warehouse feed SKUs & safety reorder thresholds
│   └── generate_telemetry.py         # Deterministic Python 3.14 / uv CSV generator
├── data/
│   ├── pv_ops_tlm_v2.csv             # 1,275 rows (1,260 active 90-day readings + 15 st_cd=9 bench spikes)
│   └── pv_snct_inv_88.csv            # 5 sanctuary feed & cold-storage SKUs
├── legacy-paws400-repo/              # Unstructured legacy docs for Knowledge Studio Enrichment
│   ├── copybooks/
│   │   ├── PAWSTLM2.cpy              # IBM AS/400 COBOL copybook decoding pv_ops_tlm_v2
│   │   └── PAWSINV8.cpy              # IBM AS/400 COBOL copybook decoding pv_snct_inv_88
│   ├── etl/
│   │   └── NIGHTLY_INGEST.ctl        # Verified join paths & AI.FORECAST SQL templates
│   ├── ops/
│   │   └── SYS_DICT_98.ini           # 1998 sanctuary KPI definitions & unit conversion rules
│   └── eval/
│       └── petverse_eval.jsonl       # 4 ground-truth Knowledge Studio evaluation prompt/SQL pairs
└── sql/
    ├── setup_object_refs.sql         # ALTER TABLE & ObjectRef UPDATE statements for petverse.pets
    ├── load_sanctuary_tables.sql     # Loads undocumented pv_ops_tlm_v2 & documented pv_snct_inv_88
    ├── enrich_pv_ops_tlm_fallback.sql# ALTER TABLE/COLUMN descriptions decoded from PAWSTLM2.cpy
    └── dq_assertions.sql             # BigQuery ASSERT suite validating PKs, FKs, continuity & domains
```

---

## Quick Start

### 1. Configure Environment, Provision Prerequisites & Stage Assets

Creates the BigQuery connection (`pet-connection`), Knowledge Studio execution SA (`kc-enrichment-sa`), Cloud Storage bucket (`gs://${PROJECT_ID}-petverse` populated with pet media, `telemetry/*.csv`, and `legacy-paws400-repo/`), and BigQuery `petverse` dataset:

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"

source ./setenv.sh
./petverse-setup.sh
```

### 2. Full Automated Catch-Up (Up to Conversational Analytics)

Runs `petverse-setup.sh`, loads `pets` + ObjectRefs, creates Gemini 3.x multimodal enrichments (`gemini-3.5-flash-lite`, `gemini-3.8-flash`) and embeddings (`multimodalembedding@001`, `gemini-embedding-001`), loads `pv_ops_tlm_v2` and `pv_snct_inv_88`, applies metadata descriptions, and validates all Data Quality Assertions:

```bash
./catchup.sh
```

### 3. Regenerating or Customizing Sample Data (`uv`)

Edit `scripts/pet_profiles_seed.txt` or `scripts/supply_skus_seed.txt` to customize daily nutrition baselines, appetite slopes, or warehouse stock levels, then run:

```bash
uv run --python 3.14 scripts/generate_telemetry.py \
  --days 90 \
  --start-date 2026-08-01 \
  --seed 42
```

*(Falls back cleanly to `uv run scripts/generate_telemetry.py` or `python3 scripts/generate_telemetry.py`.)*

---

## Schema & Legacy Metadata Traps (`PAWSTLM2.cpy` & `SYS_DICT_98.ini`)

`petverse.pv_ops_tlm_v2` is intentionally loaded **without** table or column descriptions so students can enrich it in Knowledge Studio using `legacy-paws400-repo/`:

| Column | Type | Decoded Business Meaning & Critical Analytical Guardrail |
| :--- | :--- | :--- |
| `rec_seq_id` | `STRING` | Sequential mainframe telemetry primary key (`TLM-100001`..`TLM-101275`). |
| `ent_fk` | `INT64` | Foreign key to `petverse.pets.Id` (`1..14`). `99` = non-animal load-cell calibration bench. |
| `ts_dt` | `DATE` | Continuous daily UTC observation date (`2026-08-01`..`2026-10-29`) for `AI.FORECAST`. |
| `nutr_g_qty` | `FLOAT64` | Daily food consumed in **grams (`g`)** — divide by `1000.0` for kilograms (`kg`). |
| `act_k_stp` | `INT64` | Daily collar steps or hamster wheel revolutions (`AVG > 12000` = **High-Energy Resident**). |
| `slp_m_dur` | `INT64` | Daily sleep/rest duration in **minutes**. |
| `care_c_usd` | `INT64` | Daily care cost in **US cents** — divide by `100.0` for US dollars (`$ USD`). |
| `st_cd` | `INT64` | `1` = Standard reading, `2` = Vet checkup day, `9` = Hardware calibration spike (`nutr_g_qty=9999.0`, `care_c_usd=99900`). **Always filter `WHERE st_cd != 9`!** |

If a student's Knowledge Studio Preview enrichment job is still running when they reach Conversational Analytics, apply the decoded metadata immediately with:

```bash
./apply-enriched-metadata.sh
```

---

## Forecasting 14-Day Feed Runway with `AI.FORECAST`

Both **Capybara fresh greens (`SKU-GRN-13`)** (`cur_stk_kg = 15.0`, `reord_thr_kg = 12.0`, ~19.1 kg 14-day demand) and **Dog kibble (`SKU-KBL-05`)** (`cur_stk_kg = 38.0`, `reord_thr_kg = 25.0`, ~26.6 kg 14-day demand) breach their safety reorder thresholds within a 14-day forecast horizon:

```sql
WITH valid_feed AS (
  SELECT ent_fk, ts_dt, nutr_g_qty
  FROM `__PROJECT_ID__.petverse.pv_ops_tlm_v2`
  WHERE st_cd != 9
),
fc AS (
  SELECT ent_fk, forecast_value
  FROM AI.FORECAST(
    TABLE valid_feed,
    data_col => 'nutr_g_qty',
    timestamp_col => 'ts_dt',
    id_cols => ['ent_fk'],
    horizon => 14
  )
),
species_demand AS (
  SELECT
    UPPER(p.Species) AS sp_cat_cd,
    ROUND(SUM(fc.forecast_value) / 1000.0, 2) AS forecasted_14d_demand_kg
  FROM fc
  JOIN `__PROJECT_ID__.petverse.pets` AS p
    ON fc.ent_fk = p.Id
  GROUP BY sp_cat_cd
)
SELECT
  i.sku_cd,
  i.sp_cat_cd,
  i.itm_lbl,
  i.cur_stk_kg,
  s.forecasted_14d_demand_kg,
  ROUND(i.cur_stk_kg - s.forecasted_14d_demand_kg, 2) AS projected_remaining_kg,
  i.reord_thr_kg,
  (i.cur_stk_kg - s.forecasted_14d_demand_kg) < i.reord_thr_kg AS reorder_alert
FROM `__PROJECT_ID__.petverse.pv_snct_inv_88` AS i
JOIN species_demand AS s
  ON i.sp_cat_cd = s.sp_cat_cd
ORDER BY projected_remaining_kg ASC;
```

---

## Running Data Quality Assertions Manually

```bash
sed -e "s/__PROJECT_ID__/${PROJECT_ID}/g" -e "s/__REGION__/${REGION}/g" sql/dq_assertions.sql | \
  bq query --project_id="$PROJECT_ID" --location="$REGION" --use_legacy_sql=false
```

---

## Teardown / Cleanup

To remove the BigQuery dataset, Cloud Resource connection, Cloud Storage bucket, and `kc-enrichment-sa` service account:

```bash
./teardown.sh --yes
```
