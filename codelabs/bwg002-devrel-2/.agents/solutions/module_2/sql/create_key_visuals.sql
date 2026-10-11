-- /**
--  * @file create_key_visuals.sql
--  * @description Creates the BigQuery `bwg.key_visuals` ObjectRef table referencing
--  *   campaign key visual images in Cloud Storage via the `pitch-connection` connection.
--  *
--  * Why: Pairing campaign concepts with `OBJ.FETCH_METADATA(OBJ.MAKE_REF(...))`
--  * enables BigQuery multimodal functions (`AI.SCORE`) to inspect Cloud Storage images
--  * in place without copying binary payloads into BigQuery storage.
--  */

CREATE OR REPLACE TABLE bwg.key_visuals AS
SELECT
  campaign,
  concept,
  OBJ.FETCH_METADATA(OBJ.MAKE_REF(uri, '${REGION}.pitch-connection')) AS key_visual
FROM UNNEST([
  STRUCT(
    'cats' AS campaign,
    'Flying skateboards for cats' AS concept,
    'gs://${PROJECT_ID}-bwg/key-visuals/cats.png' AS uri
  ),
  STRUCT(
    'bike' AS campaign,
    'A commuter bike built for rainy cities' AS concept,
    'gs://${PROJECT_ID}-bwg/key-visuals/bike.png' AS uri
  )
]);
