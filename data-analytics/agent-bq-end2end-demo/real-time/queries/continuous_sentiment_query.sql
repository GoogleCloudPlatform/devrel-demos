-- CDC Incremental SQL query for Sentiment and Entity Analysis
--
-- This query uses Change Data Capture (CDC) via the APPENDS table-valued function
-- to process new rows written to the events table, extracts sentiment and entities
-- using BigQuery ML, and inserts enriched analytical records.

INSERT INTO `{DEST_TABLE}` (timestamp, agent, session_id, invocation_id, span_id, text_content, sentiment, entities)
WITH source_data AS (
  SELECT 
    timestamp, 
    agent, 
    session_id, 
    invocation_id, 
    span_id,
    JSON_VALUE(content, '$.text_summary') as text_content
  FROM APPENDS(TABLE `{SOURCE_TABLE}`)
  WHERE _CHANGE_TIMESTAMP >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 MINUTE)
    AND event_type = 'USER_MESSAGE_RECEIVED'
),
sentiment_results AS (
  -- First pass: Sentiment Analysis on raw user prompt
  SELECT *, TO_JSON_STRING(ml_understand_text_result.document_sentiment) as sentiment
  FROM ML.UNDERSTAND_TEXT(
    MODEL `{MODEL_ID}`,
    (SELECT * FROM source_data WHERE text_content IS NOT NULL),
    STRUCT('analyze_sentiment' AS nlu_option)
  )
)
-- Second pass: Entity Extraction on raw user prompt
SELECT 
  timestamp, 
  agent, 
  session_id, 
  invocation_id, 
  span_id, 
  text_content, 
  sentiment, 
  ml_understand_text_result.entities as entities
FROM ML.UNDERSTAND_TEXT(
  MODEL `{MODEL_ID}`,
  (SELECT * FROM sentiment_results),
  STRUCT('analyze_entities' AS nlu_option)
)
