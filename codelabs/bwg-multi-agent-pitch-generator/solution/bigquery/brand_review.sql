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

-- Brand-fit review of the generated campaign key visuals.
--
-- Prerequisites:
--   * Images uploaded to gs://PROJECT_ID-bwg/key-visuals/
--   * Dataset `bwg` and connection `pitch-connection` both in REGION
--   * The connection service account holds roles/storage.objectViewer and
--     roles/aiplatform.user (lab-setup.sh grants both)
--
-- Replace PROJECT_ID and REGION before running.

SET @@location = 'REGION';

-- 1. Reference each key visual from BigQuery without copying the bytes.
--    OBJ.MAKE_REF builds the reference; OBJ.FETCH_METADATA populates its
--    `details` field from Cloud Storage and surfaces any permission error.
CREATE OR REPLACE TABLE bwg.key_visuals AS
SELECT
  campaign,
  concept,
  OBJ.FETCH_METADATA(
    OBJ.MAKE_REF(uri, 'REGION.pitch-connection')
  ) AS key_visual
FROM UNNEST([
  STRUCT(
    'cats' AS campaign,
    'Flying skateboards for cats' AS concept,
    'gs://PROJECT_ID-bwg/key-visuals/cats.png' AS uri
  ),
  STRUCT(
    'bike',
    'A commuter bike built for rainy cities',
    'gs://PROJECT_ID-bwg/key-visuals/bike.png'
  )
]);

-- 2. Confirm the references resolved.
SELECT campaign, concept, key_visual.uri, key_visual.details
FROM bwg.key_visuals;

-- 3. Score each image against the same brand guidelines the Visual Director
--    was given. AI.SCORE accepts a tuple mixing strings with ObjectRef values,
--    and returns a FLOAT64.
SELECT
  campaign,
  concept,
  AI.SCORE(
    ('''You are the brand guardian reviewing a campaign key visual.
Score the attached image from 1 to 10 on how closely it follows these house rules:
- Palette: deep indigo and slate, with one warm accent of amber or terracotta. Nothing neon.
- Light: one dominant low, raking source with long shadows. No flat overhead light.
- Composition: subject off-centre with generous empty negative space on the opposite side.
- Subject: one subject only, photographic realism, shallow depth of field.
- Never: text, logos or watermarks anywhere in the frame.
A 10 obeys every rule. A 1 ignores them. The campaign concept is: ''',
      concept,
      key_visual),
    connection_id => 'REGION.pitch-connection',
    endpoint => 'gemini-3.7-flash'
  ) AS brand_fit
FROM bwg.key_visuals
ORDER BY brand_fit DESC;

-- 4. Persist the scores with a pass/fail verdict. The threshold lives in SQL
--    so it can be tuned without touching the prompt.
CREATE OR REPLACE TABLE bwg.brand_review AS
SELECT
  campaign,
  concept,
  brand_fit,
  IF(brand_fit >= 7, 'on brand', 'needs another pass') AS verdict
FROM (
  SELECT
    campaign,
    concept,
    AI.SCORE(
      ('''Score this campaign key visual from 1 to 10 on how closely it follows the house
brand rules: deep indigo and slate palette with a single warm accent and nothing neon; one
low raking light source with long shadows; the subject off-centre with empty negative space
opposite; a single photographic subject; and no text, logos or watermarks in the frame.
The campaign concept is: ''',
        concept,
        key_visual),
      connection_id => 'REGION.pitch-connection',
      endpoint => 'gemini-3.7-flash'
    ) AS brand_fit
  FROM bwg.key_visuals
);

SELECT * FROM bwg.brand_review ORDER BY brand_fit DESC;
