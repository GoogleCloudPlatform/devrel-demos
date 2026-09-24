import json
import re
import time
import pandas as pd
from google import genai
from google.genai import types

from schemas import (
    GEMINI_LOCATION,
    LOCAL_PDF_PATH,
    PROJECT_ID,
    DarkDataExtractedMetadata,
    DocumentGovernanceMetadata,
    ensure_sample_pdf,
)

# 1. Initialize unified GenAI client on decoupled global endpoint
genai_client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=GEMINI_LOCATION,
)

# 2. Dynamic Gemini Flagship Model Currency Discovery (Case 3: Newest GA Flash Tier)
special_purpose_keywords = (
    "embedding",
    "tts",
    "transcribe",
    "computer-use",
    "robotics",
    "native-audio",
    "image",
)
preview_keywords = ("preview", "experimental", "exp")

discovered_candidates = []
for model_obj in genai_client.models.list():
    raw_id = (model_obj.name or "").split("/")[-1]
    id_lower = raw_id.lower()
    if "gemini" not in id_lower or "flash" not in id_lower or "flash-lite" in id_lower:
        continue
    if any(kw in id_lower for kw in special_purpose_keywords):
        continue
    ver_match = re.search(r"gemini-(\d+(?:\.\d+)*)", id_lower)
    if not ver_match:
        continue
    ver_parts = [int(p) for p in ver_match.group(1).split(".")]
    if len(ver_parts) == 1:
        ver_parts.append(0)
    ver_tuple = tuple(ver_parts)
    if ver_tuple[0] < 3:
        continue
    is_ga_channel = not any(kw in id_lower for kw in preview_keywords)
    discovered_candidates.append((is_ga_channel, ver_tuple, raw_id))

if not discovered_candidates:
    raise RuntimeError("Dynamic discovery failed: zero active flagship Gemini flash models returned by API.")

# Sort prioritizing GA channel first, then highest semantic version tuple
discovered_candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)

MODEL_NAME = None
for is_ga_channel, ver_tuple, candidate_model_id in discovered_candidates:
    try:
        probe_resp = genai_client.models.generate_content(
            model=candidate_model_id,
            contents="ping",
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=15000)
            ),
        )
        assert probe_resp is not None
        MODEL_NAME = candidate_model_id
        print(f"Dynamically discovered active GA model currency : {MODEL_NAME} (version {ver_tuple})")
        break
    except Exception as probe_err:
        print(f"Model candidate {candidate_model_id} busy ({type(probe_err).__name__}); probing next discovered GA model...")

if not MODEL_NAME:
    raise RuntimeError("All dynamically discovered Gemini flash models were unreachable or quota-exhausted.")

# 3. Load pre-packaged unstructured PDF manual from repository directory
ensure_sample_pdf(LOCAL_PDF_PATH)
print(f"Loaded unstructured PDF manual at: {LOCAL_PDF_PATH}")

with open(LOCAL_PDF_PATH, "rb") as pdf_file:
    raw_pdf_bytes = pdf_file.read()

print(f"Read unstructured PDF document ({len(raw_pdf_bytes)} bytes). Executing multimodal extraction with {MODEL_NAME}...")

extraction_prompt = """You are an enterprise data governance engineer analyzing an unstructured product manual PDF.
Analyze the document thoroughly and extract:
1. Official document title or product model name.
2. Enterprise domain ontology classification.
3. Operational safety hazard level (LOW, MEDIUM, HIGH, or CRITICAL) based on electrical/thermal warnings.
4. Authoring division or manufacturer provenance.
5. Version or revision provenance.
6. Concise 2-3 sentence technical summary of specifications and safety operating procedures (begin with "This document outlines standard operating procedures").
7. Extraction confidence score between 0.0 and 1.0."""

candidate_models = [cid for _, _, cid in discovered_candidates]
extraction_response = None
for candidate_model in candidate_models:
    try:
        extraction_response = genai_client.models.generate_content(
            model=candidate_model,
            contents=[
                types.Part.from_bytes(data=raw_pdf_bytes, mime_type="application/pdf"),
                extraction_prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DarkDataExtractedMetadata,
                temperature=0.1,
            ),
        )
        print(f"✓ Multimodal extraction completed using model: {candidate_model}")
        break
    except Exception as err:
        if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
            print(f"Model {candidate_model} rate-limited (429); trying next GA Flash model...")
            time.sleep(2)
        else:
            raise

extracted_dark_data = json.loads(extraction_response.text)
validated_extraction = DarkDataExtractedMetadata(**extracted_dark_data)

governance_prompt = f"""You are an enterprise compliance steward classifying an unstructured manual titled '{validated_extraction.document_title}'.
Based on the PDF manual contents and electrical lighting safety standards, generate the governance metadata:
1. Applicable safety and regulatory compliance classifications (e.g. UL-153 Portable Luminaires, FCC Part 15, CE-LVD).
2. Designated stewardship owner (e.g. Global Hardware Safety & Quality Assurance Team).
3. Document retention policy (e.g. 10-Year Active Product Lifecycle Archival).
4. Cross-referenced structured inventory table URI: 'lakehouse.{PROJECT_ID}.retail_hardware.luminaire_sku_inventory_iceberg'.
5. Governance certification status: 'VERIFIED_PRODUCTION'."""

governance_response = None
for candidate_model in candidate_models:
    try:
        governance_response = genai_client.models.generate_content(
            model=candidate_model,
            contents=[
                types.Part.from_bytes(data=raw_pdf_bytes, mime_type="application/pdf"),
                governance_prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DocumentGovernanceMetadata,
                temperature=0.1,
            ),
        )
        print(f"✓ Governance classification completed using model: {candidate_model}")
        break
    except Exception as err:
        if "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
            print(f"Model {candidate_model} rate-limited (429); trying next GA Flash model...")
            time.sleep(2)
        else:
            raise

governance_metadata = json.loads(governance_response.text)
validated_governance = DocumentGovernanceMetadata(**governance_metadata)

# Persist validated JSON payloads for subsequent control plane attachment steps
with open("extracted_metadata.json", "w", encoding="utf-8") as f_ext:
    json.dump(validated_extraction.model_dump(), f_ext, indent=2)

with open("governance_metadata.json", "w", encoding="utf-8") as f_gov:
    json.dump(validated_governance.model_dump(), f_gov, indent=2)

print("\n--- Extracted Multimodal Operational Metadata ---")
df_extracted = pd.DataFrame(
    list(validated_extraction.model_dump().items()),
    columns=["Extracted Attribute", "Multimodal Value"],
)
print("Extracted Attribute       Multimodal Value")
for attr_k, attr_v in df_extracted.itertuples(index=False):
    val_str = str(attr_v).replace("\n", " ")
    if len(val_str) > 52:
        val_str = val_str[:49] + "..."
    print(f"{attr_k:<24}  {val_str}")

print("\n--- Extracted Governance & Inventory Cross-Reference Metadata ---")
df_governance = pd.DataFrame(
    list(validated_governance.model_dump().items()),
    columns=["Governance Attribute", "Classification Value"],
)
print("Governance Attribute        Classification Value")
for gov_k, gov_v in df_governance.itertuples(index=False):
    val_str = str(gov_v).replace("\n", " ")
    if len(val_str) > 50:
        val_str = val_str[:47] + "..."
    print(f"{gov_k:<26}  {val_str}")
