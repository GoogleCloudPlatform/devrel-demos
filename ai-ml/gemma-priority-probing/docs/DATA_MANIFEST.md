# Master Classification Chart

| # | Artifact | Grade | Current Location | Basis (verified) |
|---|---|---|---|---|
| 1 | `o2_results_ad_series_FINAL.json/.txt` | ✅ **PUBLISHABLE** | `data/results/` | AD-series, n=13, CIs, 3 retractions documented |
| 2 | `conflict_dataset_counterbalanced.json` | ✅ **PUBLISHABLE** | `data/` | Complete design artifact; ab/ba × auth/recent |
| 3 | `patching_results_authority_CELLS_FINAL_DO_NOT_CITE_AS_AGGREGATE.json` | ⚠️ **CELLS VALID / AGGREGATES INVALID** | `data/no_cite_but_useful/` | `cpu`, `float32`, correct authority flips. But 8 cells = 2 items × 4 conditions; 3/8 cells fail F5; `overshoot_flag` both items; avg-ceiling figures are means over invalid cells |
| 4 | `gemma_4_e4b_empirical_results_FINAL_UNCOUNTERBALANCED_DO_NOT_CITE_AS_AGGREGATE.json` | ⚠️ **UNCOUNTERBALANCED** | `data/no_cite_but_useful/` | Right model, single-order prompts → a ~0.79-nat GCP prior, producing a 1.58-nat swing between orders. |
| 5 | `patching_results.json` | 🔴 **QUARANTINE (2 independent grounds)** | `internal/archive/quarantine/` | (a) `mps`/`bfloat16`/`parity_checked: false`; (b) **mode/flip mismatch** — labeled `authority`, executes date flips. `"note": "PILOT n=8"` vs `"n_items": 4` |
| 6 | `patching_results_recency.log` | 🔴 **QUARANTINE** | `internal/archive/quarantine/` | 0 bytes — no run occurred |
| 7 | `patching_results_date_recency.log` | 🔴 **QUARANTINE** | `internal/archive/quarantine/` | Weight-loading only; died before first forward |
| 8 | `jspace_results.json` | 🔴 **QUARANTINE** | `internal/archive/quarantine/` | Probes stop at L25/42; L0–24 all exactly `0.0` |
| 9 | `lantern_telemetry_traces.json` | 🔴 **DEPRECATED** | `internal/archive/deprecated/` | `gemma-2-2b` — violates standing model constraint |
| 10 | `internal/scratch/*` | 🔴 **NON-CITABLE** | `internal/scratch/` | Ad-hoc launchers incl. `_deprecated_launchers/run_parallel_mps_bf16.sh`, `_deprecated_launchers/run_sequential_mps_bf16.sh` — origin of #5 |

## Code & Documentation Resources
| # | Artifact | Location |
|---|---|---|
| 1 | `activation_patching.py` | `src/` |
| 2 | `counterbalance_dataset.py` | `src/` |
| 3 | `run_ad_series.py` | `src/` |
| 4 | `REPLICATION_LOG.md` | `docs/` |
| 5 | `METHOD.md` | `docs/` |


## Important Note on Security Scanners
The `data/` directory (specifically `corpus_in_distribution.txt` and `benchmark_seed_expanded.json`) contains synthetic conflict prompts designed to test the model. These prompts contain fictional API keys, bearer tokens, webhook endpoints, and credentials (e.g., `X-API-Key`, `*.acme.com`). **These are not real secrets.** Downstream secret scanners (like GitHub Push Protection) may flag them as false positives.
