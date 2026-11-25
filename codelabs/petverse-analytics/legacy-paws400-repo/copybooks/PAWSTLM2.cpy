      *>*****************************************************************
      *> COPYBOOK : PAWSTLM2.CPY                                        *
      *> SYSTEM   : PAWS/400 SANCTUARY BIOMETRIC & FEED MAINFRAME V2.4  *
      *> TARGET   : BIGQUERY TABLE `petverse.pv_ops_tlm_v2`             *
      *> EXTRACT  : NIGHTLY_INGEST.CTL -> gs://.../pv_ops_tlm_v2.csv    *
      *>*****************************************************************
      *> TABLE BUSINESS DESCRIPTION:
      *>   Daily resident pet nutrition, physical activity, rest duration,
      *>   and care-cost telemetry feed extracted from legacy PAWS/400
      *>   smart bowls and collar sensors into `petverse.pv_ops_tlm_v2`.
      *>   CRITICAL ANALYTICS RULE: Always filter `WHERE st_cd != 9`
      *>   (or `WHERE st_cd IN (1, 2)`) to exclude non-animal hardware
      *>   calibration bench test rows (`ent_fk = 99`) from all metrics,
      *>   aggregations, spend totals, and `AI.FORECAST` queries!
      *>*****************************************************************
       01  PAWS-TLM-REC-V2.
      *>   Sequential mainframe telemetry record primary key (e.g. TLM-100001).
      *>   Maps to BigQuery column: `rec_seq_id` (STRING, PK).
           05  REC-SEQ-ID          PIC X(10).

      *>   Sanctuary resident pet identifier. Foreign key referencing
      *>   `petverse.pets.Id` (values 1..14). Value `99` denotes the
      *>   non-animal load-cell hardware calibration bench!
      *>   Maps to BigQuery column: `ent_fk` (INT64, FK -> pets.Id).
           05  ENT-FK              PIC S9(04) COMP-3.

      *>   Daily UTC telemetry observation date formatted YYYY-MM-DD.
      *>   Continuous daily grain required for BigQuery `AI.FORECAST`.
      *>   Maps to BigQuery column: `ts_dt` (DATE).
           05  TS-DT               PIC X(10).

      *>   Daily food and nutrition consumed in GRAMS (g), NOT kilograms!
      *>   Divide `nutr_g_qty / 1000.0` when converting to kilograms (kg)
      *>   to compare against `pv_snct_inv_88.cur_stk_kg`.
      *>   Maps to BigQuery column: `nutr_g_qty` (FLOAT64).
           05  NUTR-G-QTY          PIC S9(05)V9(01) COMP-3.

      *>   Daily physical activity count from collar pedometer steps or
      *>   small-mammal exercise wheel revolutions (count/steps).
      *>   Maps to BigQuery column: `act_k_stp` (INT64).
           05  ACT-K-STP           PIC S9(07) COMP-3.

      *>   Daily total sleep and rest duration measured in MINUTES.
      *>   Divide by 60.0 for hours.
      *>   Maps to BigQuery column: `slp_m_dur` (INT64).
           05  SLP-M-DUR           PIC S9(04) COMP-3.

      *>   Daily direct nutrition, supplement, and enrichment care cost
      *>   stored in US CENTS (1/100 USD). MUST divide by `100.0` to
      *>   report spend in US Dollars ($ USD)!
      *>   Maps to BigQuery column: `care_c_usd` (INT64).
           05  CARE-C-USD          PIC S9(07) COMP-3.

      *>   Telemetry record operational status code (`st_cd` INT64):
      *>     1 = Valid Active Resident Standard Daily Reading
      *>     2 = Valid Active Resident Vet Checkup Observation Day
      *>     9 = Hardware Calibration Spike Row (`ent_fk = 99`,
      *>         `nutr_g_qty = 9999.0`, `care_c_usd = 99900`).
      *>         MUST EXCLUDE `st_cd = 9` FROM ALL ANALYTICS & FORECASTS!
           05  ST-CD               PIC 9(01).
               88  TLM-VALID-STD       VALUE 1.
               88  TLM-VALID-VET       VALUE 2.
               88  TLM-CALIB-BENCH     VALUE 9.
      *>*****************************************************************
