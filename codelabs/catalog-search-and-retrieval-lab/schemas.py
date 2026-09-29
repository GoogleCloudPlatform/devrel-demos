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
ASPECT_TYPE_ID = os.environ.get("ASPECT_TYPE_ID", "pii").strip()
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
        description="BigQuery column name bound to the pii aspect."
    )
    pii_type: str = Field(
        description="Classified PII category (EMAIL, NAME, ADDRESS, etc.)."
    )
    masked: bool = Field(
        description="True when column values are masked or de-identified."
    )


class ComplianceAuditReport(BaseModel):
    entry_resource_name: str = Field(
        description="Full Knowledge Catalog entry resource path."
    )
    aspect_key_prefix: str = Field(
        description="Numeric project-number aspect key prefix."
    )
    total_annotated_columns: int = Field(
        description="Count of columns annotated with pii aspects."
    )
    unmasked_violations: List[PiiColumnFinding] = Field(
        description="Columns where masked=False requiring remediation."
    )
    masked_compliant_columns: List[str] = Field(
        description="Column names where masked=True."
    )


class GroundedAgentDecision(BaseModel):
    selected_tables: List[str] = Field(
        description="Tables chosen from lookup_context YAML."
    )
    join_conditions: List[str] = Field(
        description="Cross-table join predicates extracted from context."
    )
    sql_query: str = Field(
        description="Synthesized BigQuery Standard SQL query."
    )
    grounding_rationale: str = Field(
        description="Explanation of how lookup_context guided SQL synthesis."
    )


# Matching Knowledge Catalog AspectType metadata template (1-based indices)
pii_aspect_template = dataplex_v1.AspectType.MetadataTemplate(
    name="pii_metadata",
    type_="record",
    record_fields=[
        dataplex_v1.AspectType.MetadataTemplate(
            name="pii_type",
            type_="enum",
            index=1,
            enum_values=[
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="EMAIL", index=1
                ),
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="NAME", index=2
                ),
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="ADDRESS", index=3
                ),
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="PHONE_NUMBER", index=4
                ),
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="DEMOGRAPHIC", index=5
                ),
                dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                    name="OTHER", index=6
                ),
            ],
            annotations=dataplex_v1.AspectType.MetadataTemplate.Annotations(
                description="Classified category of personal information."
            ),
            constraints=dataplex_v1.AspectType.MetadataTemplate.Constraints(
                required=True
            ),
        ),
        dataplex_v1.AspectType.MetadataTemplate(
            name="masked",
            type_="bool",
            index=2,
            annotations=dataplex_v1.AspectType.MetadataTemplate.Annotations(
                description="Indicates whether column values are masked."
            ),
            constraints=dataplex_v1.AspectType.MetadataTemplate.Constraints(
                required=True
            ),
        ),
    ],
)

COLUMN_GOVERNANCE_RULES = {
    "email": {"pii_type": "EMAIL", "masked": False},
    "first_name": {"pii_type": "NAME", "masked": False},
    "last_name": {"pii_type": "NAME", "masked": False},
    "street_address": {"pii_type": "ADDRESS", "masked": False},
    "postal_code": {"pii_type": "ADDRESS", "masked": True},
    "age": {"pii_type": "DEMOGRAPHIC", "masked": True},
    "gender": {"pii_type": "DEMOGRAPHIC", "masked": True},
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
    print(f"Configured Project ID: {PROJECT_ID}")
    print(f"Catalog Data Plane Region: {DATAPLEX_LOCATION}")
    print(f"Gemini Endpoint Location: {GEMINI_LOCATION}")
    print(f"Target BigQuery Dataset: {DATASET_ID}")
    print(f"Custom AspectType ID: {ASPECT_TYPE_ID}")
    print("✓ Validated PiiColumnFinding, ComplianceAuditReport, and")
    print("  GroundedAgentDecision Pydantic schemas.")
    print("✓ Prepared pii AspectType metadata template.")
