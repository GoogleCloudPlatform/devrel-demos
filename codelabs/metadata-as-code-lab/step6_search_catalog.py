import time
from google.cloud import dataplex_v1

from schemas import (
    ENTRY_GROUP_ID,
    EXTRACTED_ASPECT_TYPE_ID,
    FILESET_ENTRY_ID,
    GOVERNANCE_ASPECT_TYPE_ID,
    PROJECT_ID,
    REGION,
)

catalog_client = dataplex_v1.CatalogServiceClient()
parent_location = f"projects/{PROJECT_ID}/locations/{REGION}"
entry_group_resource_name = f"{parent_location}/entryGroups/{ENTRY_GROUP_ID}"

search_query = f"entrygroup={entry_group_resource_name} name:{FILESET_ENTRY_ID}"
print(f"Executing Knowledge Catalog search query: '{search_query}'...")

max_wait_seconds = 120
elapsed_seconds = 0
attempt = 0
catalog_search_results = []

while elapsed_seconds < max_wait_seconds:
    catalog_search_results = list(
        catalog_client.search_entries(
            request=dataplex_v1.SearchEntriesRequest(
                name=parent_location,
                query=search_query,
            )
        )
    )
    if catalog_search_results:
        break
    backoff_seconds = min(5 * (2 ** attempt), 30)
    time.sleep(backoff_seconds)
    elapsed_seconds += backoff_seconds
    attempt += 1
    print(
        f"  Waiting for asynchronous search index propagation (exponential backoff: {backoff_seconds}s, elapsed: {elapsed_seconds}/{max_wait_seconds}s)..."
    )

if not catalog_search_results:
    raise RuntimeError(f"Search index did not return entries for '{search_query}' within {max_wait_seconds} seconds.")

print(f"\n✓ Discovered {len(catalog_search_results)} governed asset(s) in Knowledge Catalog:\n")

for idx, res in enumerate(catalog_search_results, 1):
    discovered_entry = res.dataplex_entry
    print(f"[{idx}] Entry Resource Name : {discovered_entry.name}")
    print(f"    Fully Qualified Name: {discovered_entry.fully_qualified_name}")
    print(f"    Entry Type          : {discovered_entry.entry_type}")
    print(f"    Physical Storage URI: {discovered_entry.entry_source.resource}")

    # Inspect cross-referenced Lakehouse table and hazard level from full entry view
    detailed_entry = catalog_client.get_entry(
        request=dataplex_v1.GetEntryRequest(
            name=discovered_entry.name,
            view=dataplex_v1.EntryView.ALL,
        )
    )
    for k, asp in detailed_entry.aspects.items():
        if k.endswith(f".{REGION}.{EXTRACTED_ASPECT_TYPE_ID}"):
            print(f"    Domain Ontology     : {asp.data.get('domain_ontology')}")
            print(f"    Hazard Level        : {asp.data.get('operational_hazard_level')}")
        elif k.endswith(f".{REGION}.{GOVERNANCE_ASPECT_TYPE_ID}"):
            print(f"    Compliance Codes    : {asp.data.get('compliance_classifications')}")
            print(f"    Lakehouse Join Table: {asp.data.get('lakehouse_cross_ref_table')}")
