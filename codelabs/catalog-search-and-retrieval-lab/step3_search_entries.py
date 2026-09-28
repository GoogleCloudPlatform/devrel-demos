import time
from google.cloud import dataplex_v1
from schemas import ASPECT_TYPE_ID, DATASET_ID, PROJECT_ID

catalog_client = dataplex_v1.CatalogServiceClient()
search_scope = f"projects/{PROJECT_ID}/locations/global"
project_scope = f"projects/{PROJECT_ID}"

# 1. Semantic natural-language search (semantic_search=True)
semantic_query = "thelook_ecommerce sandbox tables"
semantic_req = dataplex_v1.SearchEntriesRequest(
    name=search_scope,
    scope=project_scope,
    query=semantic_query,
    semantic_search=True,
    page_size=5,
)
semantic_results = list(catalog_client.search_entries(request=semantic_req))
if not semantic_results:
    raise RuntimeError("Semantic search returned 0 results.")

print("=== Mode A: Semantic Search (semantic_search=True) ===")
print(f"Query: {semantic_query}")
print(f"Matched Candidates: {len(semantic_results)}")
for idx, res in enumerate(semantic_results[:3], start=1):
    entry = res.dataplex_entry
    display_name = entry.entry_source.display_name or entry.name.split("/")[-1]
    print(f"  Hit #{idx} Display Name: {display_name}")
    print(f"  Hit #{idx} System: {entry.entry_source.system}")
    print(f"  Hit #{idx} Aspects Count: {len(entry.aspects)}")

# 2. Structured predicate search filtering on custom aspect existence
structured_query = (
    f"name:users AND system=BIGQUERY AND parent:{DATASET_ID} "
    f"AND aspect:{PROJECT_ID}.global.{ASPECT_TYPE_ID}"
)
structured_results = []
for poll_attempt in range(1, 25):
    structured_results = list(
        catalog_client.search_entries(
            request=dataplex_v1.SearchEntriesRequest(
                name=search_scope,
                scope=project_scope,
                query=structured_query,
                page_size=5,
            )
        )
    )
    if structured_results:
        break
    time.sleep(5)

if not structured_results:
    raise RuntimeError(
        "Structured predicate search returned 0 results after polling."
    )

top_entry = structured_results[0].dataplex_entry
if len(top_entry.aspects) != 0:
    raise AssertionError("Expected search_entries to omit aspect payloads.")

print("=== Mode B: Structured Predicate Search ===")
print(f"Matched Entry ID: {top_entry.name.split('/')[-1]}")
print(f"Fully Qualified Name: {top_entry.fully_qualified_name}")
print(f"Returned Aspects Payload: {dict(top_entry.aspects)} (omitted)")
