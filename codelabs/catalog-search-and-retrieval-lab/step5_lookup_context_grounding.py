from typing import List
from google import genai
from google.api_core.exceptions import GoogleAPICallError, InvalidArgument
from google.cloud import bigquery, dataplex_v1
from google.genai import types
from schemas import (
    DATAPLEX_LOCATION,
    DATASET_ID,
    GEMINI_LOCATION,
    PROJECT_ID,
    GroundedAgentDecision,
    discover_gemini_flash_model,
)

catalog_client = dataplex_v1.CatalogServiceClient()
bq_client = bigquery.Client(project=PROJECT_ID)
lookup_scope = f"projects/{PROJECT_ID}/locations/{DATAPLEX_LOCATION}"


def validate_context_candidates(
    client: dataplex_v1.CatalogServiceClient,
    scope: str,
    candidate_names: List[str],
) -> List[str]:
    """Validates candidate entry names before calling lookup_context."""
    valid_names = []
    for entry_name in candidate_names:
        try:
            client.lookup_entry(
                request=dataplex_v1.LookupEntryRequest(
                    name=scope,
                    entry=entry_name,
                    view=dataplex_v1.EntryView.BASIC,
                )
            )
            valid_names.append(entry_name)
        except (InvalidArgument, GoogleAPICallError) as exc:
            short_id = entry_name.split("/")[-1]
            print(f"Filtered invalid candidate: {short_id} ({type(exc).__name__})")
    return valid_names


# 1. Discover all 4 sandbox tables and test defensive pre-validation
search_hits = list(
    catalog_client.search_entries(
        request=dataplex_v1.SearchEntriesRequest(
            name=f"projects/{PROJECT_ID}/locations/global",
            query=f"system=BIGQUERY AND parent:{DATASET_ID}",
            page_size=10,
        )
    )
)
discovered_names = sorted([h.dataplex_entry.name for h in search_hits])
stale_entry = f"{discovered_names[0]}_deleted_replica"
validated_names = validate_context_candidates(
    catalog_client, lookup_scope, discovered_names + [stale_entry]
)

# 2. Retrieve LLM-formatted YAML context via lookup_context
context_resp = catalog_client.lookup_context(
    request=dataplex_v1.LookupContextRequest(
        name=lookup_scope,
        resources=validated_names[:10],
        options={"format": "YAML"},
    )
)
if not context_resp.context:
    raise RuntimeError("lookup_context returned an empty context payload.")

print(f"Validated Entry Resources: {len(validated_names)} (1 stale filtered)")
print(f"Hydrated YAML Context Len: {len(context_resp.context)} chars")

# 3. Synthesize and execute PII-safe SQL with Gemini Flash
genai_client = genai.Client(
    vertexai=True, project=PROJECT_ID, location=GEMINI_LOCATION
)
model_id = discover_gemini_flash_model(genai_client)

agent_prompt = f"""
You are an enterprise data governance SQL agent.
Using ONLY the Knowledge Catalog lookup_context YAML below, write a BigQuery
Standard SQL query that calculates total orders and gross revenue by country
and age bracket (`<25`, `25-44`, `45-64`, `65+`) for completed orders.

CRITICAL GOVERNANCE INVARIANTS:
1. Never select or expose columns marked with sensitivity_level: HIGH or
   is_pii: true (`email`, `first_name`, `last_name`, `street_address`).
2. Aggregate `age` (sensitivity_level: MEDIUM) into age brackets instead of
   exposing raw individual ages.
3. Fully qualify table names using `{PROJECT_ID}.{DATASET_ID}.<table_name>`.
4. Limit the final result to the top 5 rows ordered by gross_revenue DESC.

KNOWLEDGE CATALOG LOOKUP_CONTEXT YAML:
{context_resp.context}
"""

gen_response = genai_client.models.generate_content(
    model=model_id,
    contents=agent_prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GroundedAgentDecision,
        temperature=0.0,
    ),
)
decision = GroundedAgentDecision.model_validate_json(gen_response.text)

sql_upper = decision.sql_query.upper()
for forbidden_col in ("EMAIL", "FIRST_NAME", "LAST_NAME", "STREET_ADDRESS"):
    if forbidden_col in sql_upper:
        raise AssertionError(f"Generated SQL leaked PII column: {forbidden_col}")

df = bq_client.query(decision.sql_query).to_dataframe()
if df.empty:
    raise AssertionError("Grounded BigQuery SQL returned 0 rows.")

print(f"Selected Gemini Model: {model_id}")
print(f"Excluded PII Columns: {', '.join(decision.excluded_pii_columns)}")
print("=== Executed Grounded BigQuery Result (Top 5 Rows) ===")
for idx, row in df.head(5).iterrows():
    items = [f"{col}={row[col]}" for col in df.columns]
    print(f"  Row {idx + 1}: " + " | ".join(items)[:65])
