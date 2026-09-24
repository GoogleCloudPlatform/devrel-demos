import json
from google.cloud import dataplex_v1
from schemas import (
    ASPECT_TYPE_ID,
    DATAPLEX_LOCATION,
    PROJECT_ID,
    STATE_FILE,
    ComplianceAuditReport,
    PiiColumnFinding,
)

with open(STATE_FILE, "r", encoding="utf-8") as f:
    state = json.load(f)

users_entry_name = state["users_entry_name"]
aspect_type_path = state["aspect_type_path"]
aspect_key_prefix = state["aspect_key_prefix"]
catalog_client = dataplex_v1.CatalogServiceClient()

# 1. Hydrate the entry using EntryView.CUSTOM and PROJECT_ID aspect_types filter
lookup_scope = f"projects/{PROJECT_ID}/locations/{DATAPLEX_LOCATION}"
lookup_req = dataplex_v1.LookupEntryRequest(
    name=lookup_scope,
    entry=users_entry_name,
    view=dataplex_v1.EntryView.CUSTOM,
    aspect_types=[aspect_type_path],
)
hydrated_entry = catalog_client.lookup_entry(request=lookup_req)

# 2. Extract column-level aspects keyed by numeric PROJECT_NUMBER
target_suffix = f".global.{ASPECT_TYPE_ID}@Schema.fields."
annotated_columns = 0
high_findings = []

for aspect_key, aspect_obj in sorted(hydrated_entry.aspects.items()):
    if target_suffix not in aspect_key:
        continue
    annotated_columns += 1
    col_name = aspect_key.split("@Schema.fields.")[-1]
    data_map = dict(aspect_obj.data)
    finding = PiiColumnFinding(
        column_name=col_name,
        is_pii=bool(data_map.get("is_pii", False)),
        sensitivity_level=str(data_map.get("sensitivity_level", "")),
        governance_note=str(data_map.get("governance_note", "")),
    )
    if finding.sensitivity_level == "HIGH":
        high_findings.append(finding)

audit_report = ComplianceAuditReport(
    entry_resource_name=hydrated_entry.name,
    aspect_key_prefix=aspect_key_prefix,
    total_annotated_columns=annotated_columns,
    high_sensitivity_columns=high_findings,
)

if audit_report.total_annotated_columns != 7:
    raise AssertionError(
        f"Expected 7 annotated columns, got {audit_report.total_annotated_columns}"
    )
if len(audit_report.high_sensitivity_columns) != 4:
    raise AssertionError(
        f"Expected 4 HIGH PII columns, got {len(audit_report.high_sensitivity_columns)}"
    )

print("=== lookup_entry (EntryView.CUSTOM) Hydration Report ===")
print(f"Hydrated Entry ID: {hydrated_entry.name.split('/')[-1]}")
print(f"Total Aspects Returned: {len(hydrated_entry.aspects)}")
print(f"Column Aspects Matched: {audit_report.total_annotated_columns}")
print(f"HIGH Sensitivity Columns: {len(audit_report.high_sensitivity_columns)}")
for item in audit_report.high_sensitivity_columns:
    print(f"  - {item.column_name} (PII={item.is_pii}): {item.governance_note}")
