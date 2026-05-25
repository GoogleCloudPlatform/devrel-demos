-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- Remember to enable: https://console.cloud.google.com/apis/api/translate.googleapis.com/metrics
-- Setup for ML.TRANSLATE
-- CREATE OR REPLACE MODEL `finance_ds.translate`
-- REMOTE WITH CONNECTION DEFAULT
-- OPTIONS (REMOTE_SERVICE_TYPE = 'CLOUD_AI_TRANSLATE_V3');

-- GRANT `roles/serviceusage.serviceUsageConsumer`
-- ON PROJECT `<<YOUR PROJECT ID>>`
-- TO "connection:us.__default_cloudresource_connection__";

WITH ComplaintData AS (
  -- This CTE extracts data from the graph using GRAPH_TABLE.
  SELECT
    id AS comp_id,
    name AS customer_name,
    complaint_text AS text_content  -- This alias is crucial for ML.TRANSLATE
  FROM GRAPH_TABLE(
    finance_ds.BankGraph_Complaints
    MATCH (cust:Customer)-[:FILED]->(comp:Complaint)
    RETURN
        comp.id,
        cust.name,
        comp.complaint_text
  )
)
SELECT
  tr.customer_name,
  JSON_VALUE(
    -- First, extract the 'translations' array as a SQL ARRAY<JSON>
    JSON_QUERY_ARRAY(tr.ml_translate_result, '$.translations')[SAFE_OFFSET(0)],
    -- Then, from the first JSON object in the array, extract the 'translated_text' string value
    '$.translated_text'
  ) AS spanish_translation,

  -- Example: Extracting detected language code
  JSON_VALUE(
    JSON_QUERY_ARRAY(tr.ml_translate_result, '$.translations')[SAFE_OFFSET(0)],
    '$.detected_language_code'
  ) AS detected_language,

  tr.ml_translate_status
FROM ML.TRANSLATE(
  MODEL `finance_ds.translate`,
  TABLE ComplaintData,
  STRUCT('translate_text' AS translate_mode, 'es' AS target_language_code)
) AS tr;

