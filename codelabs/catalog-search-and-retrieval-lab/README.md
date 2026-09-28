# Knowledge Catalog Search, Entry Lookup, and Context Grounding Lab

Companion Python scripts for the **Knowledge Catalog Search, Entry Lookup, and
AI Agent Grounding** Google Developer Codelab (`catalog-search-and-retrieval`).

## Script Sequence

1. `schemas.py` — Shared environment validation, Pydantic `BaseModel` contracts
   (`PiiColumnFinding`, `ComplianceAuditReport`, `GroundedAgentDecision`),
   `pii` `AspectType` template, and dynamic GA Gemini Flash discovery.
2. `step2_seed_environment.py` — Provisions the `kc_ecommerce_sandbox` BigQuery
   dataset, copies 4 tables from `bigquery-public-data.thelook_ecommerce`,
   creates the global `pii` `AspectType`, and attaches 7 column-level `pii`
   governance aspects (`4` unmasked, `3` masked) to `users`.
3. `step3_search_entries.py` — Runs `search_entries` (`semantic_search=True`
   natural-language discovery vs. structured aspect existence predicate query)
   and verifies that `search_entries` returns lightweight entry pointers
   (`aspects: {}`).
4. `step4_lookup_entry.py` — Runs `lookup_entry` (`EntryView.CUSTOM`) with
   `PROJECT_ID` request filtering and `PROJECT_NUMBER` key resolution to audit
   all 4 unmasked PII columns alongside the 3 masked compliant columns.
5. `step5_lookup_context_grounding.py` — Validates entry candidates, fetches
   `lookup_context` YAML metadata across all 4 tables, synthesizes a grounded
   multi-table BigQuery SQL query (`order_items` joined with `products`) using
   Gemini Flash (`google-genai`), and executes it.
6. `cleanup.py` — Performs 1:1 reverse-dependency resource cleanup.
