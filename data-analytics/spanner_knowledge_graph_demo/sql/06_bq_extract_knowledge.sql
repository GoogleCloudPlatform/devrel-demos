-- ============================================================================
-- BigQuery SQL: Unstructured Knowledge Extraction via Gemini AI Functions
-- Uses AI.GENERATE to extract Product, Part, Material entities and relationships from PDFs
-- ============================================================================

CREATE OR REPLACE TABLE `{DATASET_ID}.{EXTRACTED_KG_TABLE_NAME}` AS
SELECT
  uri,
  r.subject,
  r.subject_entity_type,
  r.relationship,
  r.object,
  r.object_entity_type,
  r.domain,
  r.source_snippet
FROM (
  SELECT
    uri,
    AI.GENERATE(
      -- ARGUMENT 1: Prompt concatenated with Document Content
      '''
      You are a technical knowledge graph extractor.
      Your task is to extract a comprehensive list of ALL component relationships from the text.
      You must also identify the ENTITY TYPE for both the subject and object.
      Valid Entity Types: Product, Part, Material, Other.

      ### CRITICAL: HANDLE LISTS EXHAUSTIVELY
      The text often lists multiple items for a single subject.
      You must create a separate entry in the 'relationships' array for EACH item.
      * Example: "Pump is made of Steel" ->
          {subject: 'Pump', subject_entity_type: 'Part', relationship: 'MADE_OF', object: 'Steel', object_entity_type: 'Material'}

      ### RELATIONSHIP TYPES
      * **CONTAINS_PART**: Product -> Part ID
      * **MADE_OF**: Part ID -> Material Name
      * **REQUIRES_FIRMWARE**: Part ID -> Version
      * **CONNECTS_TO**: Part A -> Part B
      * **REQUIRES_PART**: Maintenance Task -> Part ID
      ''' || content,

      -- ARGUMENT 2: Structured Output Schema Enforced for JSON Generation
      output_schema => '''
        relationships ARRAY<STRUCT<
          subject STRING,
          subject_entity_type STRING,
          relationship STRING,
          object STRING,
          object_entity_type STRING,
          domain STRING,
          source_snippet STRING
        >>
      ''',
      endpoint => '{GEMINI_MODEL_VERSION}'
    ) AS extracted_data
  FROM `{DATASET_ID}.{PROCESSED_DOCUMENTS_TABLE}`
),
-- Flatten the array: Turn 1 Document Chunk into N Relationship Rows
UNNEST(extracted_data.relationships) AS r;

-- Preview Extracted Entities & Relationships
SELECT * FROM `{DATASET_ID}.{EXTRACTED_KG_TABLE_NAME}` LIMIT 10;
