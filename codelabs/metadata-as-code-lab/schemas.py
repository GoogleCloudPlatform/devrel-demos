import os
from pydantic import BaseModel, Field

# Load environment configuration with fail-fast validation
PROJECT_ID = os.environ.get("PROJECT_ID", "").strip()
REGION = os.environ.get("REGION", "us-central1").strip()
BUCKET_NAME = os.environ.get("BUCKET_NAME", "").strip()
GEMINI_LOCATION = os.environ.get("GEMINI_LOCATION", "global").strip()

if not PROJECT_ID or PROJECT_ID == "your-project-id":
    raise ValueError(
        "PROJECT_ID environment variable must be set to an active Google Cloud project ID."
    )
if not REGION or REGION == "your-region":
    raise ValueError(
        "REGION environment variable must be set to a valid Google Cloud region (e.g., 'us-central1')."
    )
if not BUCKET_NAME:
    BUCKET_NAME = f"{PROJECT_ID}-dark-data-manuals"

# Canonical Knowledge Catalog resource identifiers
ENTRY_GROUP_ID = "dark-data-fileset-group"
ENTRY_TYPE_ID = "unstructured-pdf-fileset"
EXTRACTED_ASPECT_TYPE_ID = "dark-data-extracted-metadata"
GOVERNANCE_ASPECT_TYPE_ID = "document-governance-aspect"
FILESET_ENTRY_ID = "sop-manuals-fileset-lum8g8j"

# Pre-packaged unstructured dark data PDF manual (Contemporary Linen Desk Lamp SOP & Technical Manual)
LOCAL_PDF_PATH = "LUM-LIG-DES-8G8J_manual.pdf"
VIRTUAL_STORAGE_URI = f"gs://{BUCKET_NAME}/sop-pdfs/LUM-LIG-DES-8G8J_manual.pdf"


def ensure_sample_pdf(path: str = LOCAL_PDF_PATH) -> str:
    """Ensures the sample PDF manual for LUM-LIG-DES-8G8J exists on disk."""
    if os.path.exists(path):
        return path
    stream = (
        b"BT /F1 11 Tf 36 750 Td "
        b"(LUM-LIG-DES-8G8J Contemporary Linen Desk Lamp - Technical Manual & SOP Rev 4.2) Tj "
        b"0 -18 Td (Authoring Division: Global Hardware Safety & Lighting Systems Engineering) Tj "
        b"0 -18 Td (Domain Ontology: Electrical Hardware & Lighting Systems) Tj "
        b"0 -18 Td (Operational Hazard Level: MEDIUM - 120V AC Thermal & Electrical Shock Warning) Tj "
        b"0 -18 Td (Compliance Standards: UL-153 Portable Luminaires, FCC Part 15, CE-LVD, RoHS) Tj "
        b"0 -18 Td (Retention Policy: 10-Year Active Product Lifecycle Archival) Tj "
        b"0 -18 Td (Summary: Standard operating procedures and electrical thermal safety limits for SKU LUM-LIG-DES-8G8J.) Tj ET"
    )
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        + f"4 0 obj << /Length {len(stream)} >> stream\n".encode("ascii")
        + stream
        + b"\nendstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000229 00000 n \n"
        + f"{285 + len(stream):010d} 00000 n \n".encode("ascii")
        + b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n"
        + f"{355 + len(stream)}\n%%EOF\n".encode("ascii")
    )
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path


class DarkDataExtractedMetadata(BaseModel):
    document_title: str = Field(
        description="Official document title or product model name extracted from the PDF manual."
    )
    domain_ontology: str = Field(
        description="Enterprise domain ontology classification (e.g., Electrical Hardware & Lighting Systems)."
    )
    operational_hazard_level: str = Field(
        description="Operational safety hazard classification: LOW, MEDIUM, HIGH, or CRITICAL."
    )
    author_provenance: str = Field(
        description="Authoring engineering division, manufacturer, or technical publications department."
    )
    version_provenance: str = Field(
        description="Document version, revision code, or publication standard identifier."
    )
    document_summary: str = Field(
        description="Concise 2-3 sentence executive technical summary of specifications and safety procedures."
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="AI extraction confidence metric between 0.0 and 1.0.",
    )


class DocumentGovernanceMetadata(BaseModel):
    compliance_classifications: str = Field(
        description="Comma-separated regulatory and safety compliance standards (e.g., UL-153, CE-LVD, RoHS)."
    )
    stewardship_owner: str = Field(
        description="Designated enterprise data governance steward or engineering compliance owner."
    )
    retention_policy: str = Field(
        description="Mandatory document archival and retention schedule (e.g., 10-Year Active Product Lifecycle Archival)."
    )
    lakehouse_cross_ref_table: str = Field(
        description="Associated Lakehouse for Apache Iceberg structured table identifier for cross-asset joins."
    )
    governance_status: str = Field(
        description="Catalog governance lifecycle status (e.g., VERIFIED_PRODUCTION)."
    )


# Matching Knowledge Catalog AspectType metadata templates
extracted_aspect_template = {
    "name": "DarkDataExtractedMetadata",
    "type": "record",
    "record_fields": [
        {
            "name": "document_title",
            "type": "string",
            "index": 1,
            "annotations": {"description": "Official document title or product model name."},
        },
        {
            "name": "domain_ontology",
            "type": "string",
            "index": 2,
            "annotations": {"description": "Enterprise domain ontology classification."},
        },
        {
            "name": "operational_hazard_level",
            "type": "string",
            "index": 3,
            "annotations": {"description": "Assessed operational hazard level (LOW, MEDIUM, HIGH, CRITICAL)."},
        },
        {
            "name": "author_provenance",
            "type": "string",
            "index": 4,
            "annotations": {"description": "Authoring engineering division or technical publications provenance."},
        },
        {
            "name": "version_provenance",
            "type": "string",
            "index": 5,
            "annotations": {"description": "Document version or revision identifier."},
        },
        {
            "name": "document_summary",
            "type": "string",
            "index": 6,
            "annotations": {"description": "Executive technical summary of operating guidelines."},
        },
        {
            "name": "confidence_score",
            "type": "double",
            "index": 7,
            "annotations": {"description": "Multimodal AI extraction confidence metric (0.0 to 1.0)."},
        },
    ],
}

governance_aspect_template = {
    "name": "DocumentGovernanceMetadata",
    "type": "record",
    "record_fields": [
        {
            "name": "compliance_classifications",
            "type": "string",
            "index": 1,
            "annotations": {"description": "Applicable safety and regulatory compliance standards."},
        },
        {
            "name": "stewardship_owner",
            "type": "string",
            "index": 2,
            "annotations": {"description": "Designated enterprise data steward."},
        },
        {
            "name": "retention_policy",
            "type": "string",
            "index": 3,
            "annotations": {"description": "Document retention and archival policy."},
        },
        {
            "name": "lakehouse_cross_ref_table",
            "type": "string",
            "index": 4,
            "annotations": {"description": "Cross-referenced Lakehouse for Apache Iceberg table URI."},
        },
        {
            "name": "governance_status",
            "type": "string",
            "index": 5,
            "annotations": {"description": "Governance certification status."},
        },
    ],
}

if __name__ == "__main__":
    print(f"Configured Project ID         : {PROJECT_ID}")
    print(f"Knowledge Catalog Region      : {REGION}")
    print(f"Gemini Endpoint Location      : {GEMINI_LOCATION}")
    print(f"Governed Fileset Storage URI  : {VIRTUAL_STORAGE_URI}")
    print(f"Target Fileset Entry ID       : {FILESET_ENTRY_ID}")
    print("✓ Defined DarkDataExtractedMetadata and DocumentGovernanceMetadata Pydantic schemas.")
    print("✓ Prepared Knowledge Catalog AspectType metadata templates.")
