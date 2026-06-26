---
name: knowledge_catalog_governance
description: Enforces data governance by verifying Knowledge Catalog Aspects before recommending BigQuery tables.
---

# Knowledge Catalog Governance Skill

This skill enables the agent to act as a Data Governance Specialist. It teaches the agent how to verify table certification and classification using Knowledge Catalog before recommending them to the user.

## Required Capabilities
This skill requires access to the following tools:
- `search_entries`: To find tables matching specific aspect values.
- `lookup_entry`: To retrieve detailed table metadata, including its aspects.
- `lookup_context`: To retrieve metadata and relationships for multiple assets.

## Governance Workflow
The agent must follow a strict verification process before recommending or querying any data asset.

### Phase 1: Environment Discovery (If needed)
To search by aspect values, you need the active Google Cloud **Project ID** and **Location** (Region). 
If these are not already present in your system context or provided by the user, you must discover them automatically:
1. Call `search_entries` with a simple query (e.g., `official-data-product-spec` or `type:table`) and a `pageSize` of `1`.
2. Inspect the returned entry's `name` field (format: `projects/{project_id}/locations/{location}/entryGroups/...`).
3. Extract the `{project_id}` and `{location}`. These are your active environment parameters.

### Phase 2: Search and Filter
Use the `search_entries` tool to find tables that match the user's request. You must filter by the governance aspect `official-data-product-spec`.

#### Tool Call Parameters:
- **`query`**: Construct a query string matching the aspect values.
  - Format: `[PROJECT_ID].[LOCATION].official-data-product-spec.[FIELD_NAME]=[VALUE]`
  - Use the Project ID and Location discovered in Phase 1.
  - Do not use prefixes like `projectid:` or `type=table` when performing aspect-based searches.
- **`scope`**: Set this to `projects/[PROJECT_ID]` to restrict the search space.

#### Examples:
- To find certified financial data:
  ```json
  {
    "name": "search_entries",
    "arguments": {
      "query": "my-project.us-central1.official-data-product-spec.data_domain=FINANCE my-project.us-central1.official-data-product-spec.is_certified=true",
      "scope": "projects/my-project"
    }
  }
  ```

### Phase 3: Detailed Verification
Extract the resource `name` (entry path) for the candidate tables from the search results.
Call `lookup_entry` with the entry path and set `view` to `4` (`ALL`) to verify:
- **Certification:** Check if `is_certified` is `true`. If `false` or missing, the table is untrusted.
- **Data Tiering:** Check the `product_tier` (e.g., `GOLD_CRITICAL`, `SILVER_STANDARD`, `BRONZE_ADHOC`).
- **Usage Scope:** Verify the `usage_scope` (e.g., `INTERNAL_ONLY`, `EXTERNAL_READY`) matches the user's target audience.

### Phase 4: Formulate Response
Synthesize your final answer explaining WHY you chose this table based on its governance tags (Aspects). Do not expose the raw Knowledge Catalog search query or entry paths to the user.
