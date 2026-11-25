      *>*****************************************************************
      *> COPYBOOK : PAWSINV8.CPY                                        *
      *> SYSTEM   : PAWS/400 SANCTUARY WAREHOUSE & COLD VAULT V8.8      *
      *> TARGET   : BIGQUERY TABLE `petverse.pv_snct_inv_88`            *
      *> EXTRACT  : NIGHTLY_INGEST.CTL -> gs://.../pv_snct_inv_88.csv   *
      *>*****************************************************************
      *> TABLE BUSINESS DESCRIPTION:
      *>   Sanctuary cold-storage and dry-goods pet food supply inventory
      *>   vault, safety reorder thresholds in kilograms, and wholesale
      *>   unit costs in US cents. Joins to `petverse.pets` on
      *>   `UPPER(pets.Species) = pv_snct_inv_88.sp_cat_cd`.
      *>*****************************************************************
       01  PAWS-SNCT-INV-REC-88.
      *>   Warehouse stock-keeping unit primary key (e.g. SKU-GRN-13).
      *>   Maps to BigQuery column: `sku_cd` (STRING, PK).
           05  SKU-CD              PIC X(10).

      *>   Uppercase species feed category code (`CAT`, `DOG`, `HAMSTER`,
      *>   `SNAKE`, `CAPYBARA`). Joins to `UPPER(petverse.pets.Species)`.
      *>   Maps to BigQuery column: `sp_cat_cd` (STRING).
           05  SP-CAT-CD           PIC X(12).

      *>   Human-readable sanctuary ration / feed bundle description.
      *>   Maps to BigQuery column: `itm_lbl` (STRING).
           05  ITM-LBL             PIC X(64).

      *>   Current physical on-hand warehouse stock in KILOGRAMS (kg).
      *>   Compare against forecasted `nutr_g_qty / 1000.0`!
      *>   Maps to BigQuery column: `cur_stk_kg` (FLOAT64).
           05  CUR-STK-KG          PIC S9(05)V9(02) COMP-3.

      *>   Minimum safety reorder threshold in KILOGRAMS (kg). Trigger a
      *>   restock alert whenever projected remaining stock drops below
      *>   `reord_thr_kg`!
      *>   Maps to BigQuery column: `reord_thr_kg` (FLOAT64).
           05  REORD-THR-KG        PIC S9(05)V9(02) COMP-3.

      *>   Wholesale replacement cost per kilogram in US CENTS (divide
      *>   `unit_cost_c / 100.0` for USD per kg).
      *>   Maps to BigQuery column: `unit_cost_c` (INT64).
           05  UNIT-COST-C         PIC S9(07) COMP-3.

      *>   Refrigerated / cryogenic cold-chain storage required flag:
      *>   `Y` = Cold-storage vault required, `N` = Ambient dry storage.
      *>   Maps to BigQuery column: `cold_flg` (STRING).
           05  COLD-FLG            PIC X(01).
               88  COLD-CHAIN-REQ      VALUE 'Y'.
               88  DRY-AMBIENT-OK      VALUE 'N'.
      *>*****************************************************************
