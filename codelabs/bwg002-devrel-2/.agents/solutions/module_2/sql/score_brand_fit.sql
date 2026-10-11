-- /**
--  * @file score_brand_fit.sql
--  * @description Grades each campaign key visual in `bwg.key_visuals` against the house
--  *   brand guidelines using BigQuery `AI.SCORE` and writes `bwg.brand_review`.
--  *
--  * Why: Automates multimodal brand compliance auditing in SQL so visuals scoring
--  * below 7.0 (`needs another pass`) trigger targeted prompt and skill tuning (`F14`).
--  */

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
      (
        'Score this campaign key visual from 1 to 10 on how closely it follows the house '
        'brand rules: deep indigo and slate palette with a single warm accent of amber or '
        'terracotta and nothing neon; one low raking light source with long shadows; the '
        'subject off-center with generous empty negative space opposite; a single realistic '
        'photographic subject with shallow depth of field; and no text, logos, or watermarks '
        'in the frame. The campaign concept is: ',
        concept,
        key_visual
      ),
      connection_id => '${REGION}.pitch-connection'
    ) AS brand_fit
  FROM bwg.key_visuals
);

SELECT * FROM bwg.brand_review ORDER BY brand_fit DESC;
