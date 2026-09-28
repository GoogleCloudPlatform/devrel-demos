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
target_suffix = f".global.{ASPECT_TYPE_ID}@Schema."
annotated_columns = 0
unmasked_findings = []
masked_columns = []

for aspect_key, aspect_obj in sorted(hydrated_entry.aspects.items()):
    if target_suffix not in aspect_key:
        continue
    annotated_columns += 1
    col_name = aspect_key.split("@Schema.")[-1]
    data_map = dict(aspect_obj.data)
    finding = PiiColumnFinding(
        column_name=col_name,
        pii_type=str(data_map.get("pii_type", "OTHER")),
        masked=bool(data_map.get("masked", False)),
    )
    if not finding.masked:
        unmasked_findings.append(finding)
    else:
        masked_columns.append(finding.column_name)

audit_report = ComplianceAuditReport(
    entry_resource_name=hydrated_entry.name,
    aspect_key_prefix=aspect_key_prefix,
    total_annotated_columns=annotated_columns,
    unmasked_violations=unmasked_findings,
    masked_compliant_columns=masked_columns,
)

if audit_report.total_annotated_columns != 7:
    raise AssertionError(
        f"Expected 7 annotated columns, got {audit_report.total_annotated_columns}"
    )
if len(audit_report.unmasked_violations) != 4:
    raise AssertionError(
        f"Expected 4 unmasked PII columns, got {len(audit_report.unmasked_violations)}"
    )

print("=== lookup_entry (EntryView.CUSTOM) Hydration Report ===")
print(f"Hydrated Entry ID: {hydrated_entry.name.split('/')[-1]}")
print(f"Total Aspects Returned: {len(hydrated_entry.aspects)}")
print(f"Column Aspects Matched: {audit_report.total_annotated_columns}")
print(f"Unmasked PII Violations: {len(audit_report.unmasked_violations)}")
for item in audit_report.unmasked_violations:
    print(
        f"  - {item.column_name}: pii_type={item.pii_type}, "
        f"masked={item.masked}"
    )
masked_csv = ", ".join(audit_report.masked_compliant_columns)
print(f"Masked Compliant Columns: {masked_csv}")
