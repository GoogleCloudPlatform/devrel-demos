import os
import re
from typing import List
from google import genai
from google.cloud import dataplex_v1
from pydantic import BaseModel, Field

# Load environment configuration with fail-fast validation
PROJECT_ID = os.environ.get("PROJECT_ID", "").strip()
DATAPLEX_LOCATION = os.environ.get("DATAPLEX_LOCATION", "us").strip()
GEMINI_LOCATION = os.environ.get("GEMINI_LOCATION", "global").strip()
DATASET_ID = os.environ.get("DATASET_ID", "kc_ecommerce_sandbox").strip()
ASPECT_TYPE_ID = os.environ.get("ASPECT_TYPE_ID", "pii-governance").strip()
STATE_FILE = "catalog_state.json"

if not PROJECT_ID or PROJECT_ID == "your-project-id":
    raise ValueError(
        "PROJECT_ID environment variable must be set to a valid project ID."
    )
if not DATAPLEX_LOCATION or DATAPLEX_LOCATION == "your-location":
    raise ValueError(
        "DATAPLEX_LOCATION must be set to a valid region (e.g., 'us')."
    )


class PiiColumnFinding(BaseModel):
    column_name: str = Field(
        description="BigQuery column name bound to the pii-governance aspect."
    )
    is_pii: bool = Field(
        description="True when the column contains personal information."
    )
    sensitivity_level: str = Field(
        description="Sensitivity classification: HIGH, MEDIUM, or LOW."
    )
    governance_note: str = Field(
        description="Mandatory handling rule attached to the column aspect."
    )


class ComplianceAuditReport(BaseModel):
    entry_resource_name: str = Field(
        description="Canonical Knowledge Catalog entry resource path."
    )
    aspect_key_prefix: str = Field(
        description="Numeric project-number aspect key prefix."
    )
    total_annotated_columns: int = Field(
        description="Count of columns annotated with pii-governance aspects."
    )
    high_sensitivity_columns: List[PiiColumnFinding] = Field(
        description="Columns classified with sensitivity_level=HIGH."
    )


class GroundedAgentDecision(BaseModel):
    selected_tables: List[str] = Field(
        description="Tables chosen from lookup_context YAML."
    )
    excluded_pii_columns: List[str] = Field(
        description="PII columns excluded from SELECT due to governance rules."
    )
    sql_query: str = Field(
        description="Standard SQL query safe for unmasked execution."
    )
    governance_rationale: str = Field(
        description="Explanation of how lookup_context guided SQL generation."
    )


# Matching Knowledge Catalog AspectType metadata template (1-based indices)
pii_aspect_template = dataplex_v1.AspectType.MetadataTemplate(
    name="PiiGovernanceTemplate",
    type_="record",
    record_fields=[
        dataplex_v1.AspectType.MetadataTemplate(
            name="is_pii",
            type_="bool",
            index=1,
            annotations=dataplex_v1.AspectType.MetadataTemplate.Annotations(
                description="Indicates if the column stores personal data."
            ),
            constraints=dataplex_v1.AspectType.MetadataTemplate.Constraints(
                required=True
            ),
        ),
        dataplex_v1.AspectType.MetadataTemplate(
            name="sensitivity_level",
            type_="enum",
            index=2,
            enum_values=[
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="HIGH", index=1
                ),
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="MEDIUM", index=2
                ),
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="LOW", index=3
                ),
            ],
            annotations=dataplex_v1.AspectType.MetadataTemplate.Annotations(
                description="Data sensitivity classification level."
            ),
            constraints=dataplex_v1.AspectType.MetadataTemplate.Constraints(
                required=True
            ),
        ),
        dataplex_v1.AspectType.MetadataTemplate(
            name="governance_note",
            type_="string",
            index=3,
            annotations=dataplex_v1.AspectType.MetadataTemplate.Annotations(
                description="Mandatory handling note for AI agents and SQL."
            ),
        ),
    ],
)

COLUMN_GOVERNANCE_RULES = {
    "email": {
        "is_pii": True,
        "sensitivity_level": "HIGH",
        "governance_note": "Direct identifier; exclude from unmasked SELECT.",
    },
    "first_name": {
        "is_pii": True,
        "sensitivity_level": "HIGH",
        "governance_note": "Personal name; restrict from analytics output.",
    },
    "last_name": {
        "is_pii": True,
        "sensitivity_level": "HIGH",
        "governance_note": "Personal surname; restrict from analytics output.",
    },
    "street_address": {
        "is_pii": True,
        "sensitivity_level": "HIGH",
        "governance_note": "Physical residential address; PII restricted.",
    },
    "age": {
        "is_pii": False,
        "sensitivity_level": "MEDIUM",
        "governance_note": "Quasi-identifier; aggregate into brackets.",
    },
    "country": {
        "is_pii": False,
        "sensitivity_level": "LOW",
        "governance_note": "Safe geographic dimension for group-by analytics.",
    },
    "traffic_source": {
        "is_pii": False,
        "sensitivity_level": "LOW",
        "governance_note": "Safe acquisition channel attribute.",
    },
}


def discover_gemini_flash_model(genai_client: genai.Client) -> str:
    """Dynamically resolves the newest GA Gemini Flash model."""
    candidates = []
    pattern = re.compile(r"^gemini-(\d+)\.(\d+)-flash(?:-(.+))?$")
    for m in genai_client.models.list():
        short_name = (m.name or "").split("/")[-1]
        match = pattern.match(short_name)
        if not match:
            continue
        major, minor, suffix = (
            int(match.group(1)),
            int(match.group(2)),
            match.group(3) or "",
        )
        if any(
            x in suffix
            for x in ("lite", "image", "audio", "tts", "live", "thinking")
        ):
            continue
        is_ga = 1 if (suffix == "" or suffix == "001") else 0
        candidates.append(((is_ga, major, minor), short_name))
    if not candidates:
        raise RuntimeError(
            "No active Gemini Flash model discovered from google-genai."
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


if __name__ == "__main__":
    print(f"Configured Project ID    : {PROJECT_ID}")
    print(f"Catalog Data Plane Region: {DATAPLEX_LOCATION}")
    print(f"Gemini Endpoint Location : {GEMINI_LOCATION}")
    print(f"Target BigQuery Dataset  : {DATASET_ID}")
    print(f"Custom AspectType ID     : {ASPECT_TYPE_ID}")
    print("✓ Validated PiiColumnFinding, ComplianceAuditReport, and")
    print("  GroundedAgentDecision Pydantic schemas.")
    print("✓ Prepared pii-governance AspectType metadata template.")
