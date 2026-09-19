# Illuminating Unstructured Dark Data with Metadata-as-Code, Gemini & Knowledge Catalog

Companion sample code for the **Metadata-as-Code Dark Data Governance** codelab.

## Repository Contents

* `LUM-LIG-DES-8G8J_manual.pdf` — Sample unstructured hardware engineering manual and Standard Operating Procedure (SOP) PDF.
* `schemas.py` — Shared Pydantic `BaseModel` schemas (`DarkDataExtractedMetadata`, `DocumentGovernanceMetadata`) and matching **Knowledge Catalog** `AspectType` templates.
* `step2_provision.py` — Provisions the governed `EntryGroup`, `EntryType`, and custom `AspectType` blueprints in **Knowledge Catalog**.
* `step3_register_fileset.py` — Uploads `LUM-LIG-DES-8G8J_manual.pdf` to **Cloud Storage** and registers the logical Fileset `Entry`.
* `step4_extract_metadata.py` — Executes dynamic GA flagship `flash` model discovery and multimodal PDF extraction via the unified `google-genai` SDK.
* `step5_attach_aspects.py` — Attaches the validated JSON metadata payloads to the **Knowledge Catalog** Fileset `Entry` via `UpdateEntryRequest`.
* `step6_search_catalog.py` — Queries governed dark data assets and cross-referenced **Lakehouse for Apache Iceberg** tables via `search_entries()`.
* `step7_verify_assertions.py` — Runs end-to-end assertions against live **Knowledge Catalog** control plane state.
* `cleanup.py` — Standalone reverse-dependency teardown script.
