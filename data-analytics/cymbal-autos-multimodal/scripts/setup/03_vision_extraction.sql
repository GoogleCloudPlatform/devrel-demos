-- ==============================================================================
-- 1. PREPARATION: Create the Multimodal Table (ObjectRefs)
-- ==============================================================================
-- This creates a new table with a native image_ref column using ObjectRef functions

CREATE OR REPLACE TABLE `model_dev.vehicle_multimodal` AS
SELECT 
  *,
  ARRAY(
    SELECT OBJ.FETCH_METADATA(OBJ.MAKE_REF(uri, 'us.conn')) 
    FROM UNNEST(images) AS uri
  ) AS image_ref
FROM `model_dev.vehicle_metadata`;

-- ==============================================================================
-- 2. MULTIMODAL FEATURE EXTRACTION
-- ==============================================================================
-- Extract condition, body style, color, and interior from images into a feature table.

CREATE OR REPLACE TABLE `model_dev.vehicle_vision_features` AS
WITH generated_data AS (
   SELECT
   auction_id,
   AI.GENERATE(
     prompt => ('Rate the condition of this car on a scale from 0-100. Output a 1 sentence description of any glaring red flags', image_ref),
     output_schema => 'condition INT64, description_summary STRING'
   ).* EXCEPT(full_response,status)
 FROM
   `model_dev.vehicle_multimodal`
),

-- Attribute classification
classified_data AS (
 SELECT
   auction_id,
   AI.CLASSIFY(
     ('What type of automobile is this?', image_ref[0]),
     categories => ['Truck', 'Sedan', 'SUV']) AS body_style,
   AI.CLASSIFY(
     ('Color of the exterior of the automobile', image_ref[0]),
     categories => ['Black', 'White', 'Silver', 'Gray', 'Red', 'Blue', 'Brown', 'Green', 'Beige', 'Gold']) AS color,
   AI.CLASSIFY(
     ('Color of the interior of the automobile', image_ref[0]),
     categories => ['Black', 'Gray', 'Beige', 'Tan', 'Brown', 'White', 'Red']) AS interior
 FROM `model_dev.vehicle_multimodal`
)

-- Join features into the final table
SELECT
 g.auction_id,
 g.condition,
 g.description_summary,
 c.body_style,
 c.color,
 c.interior
FROM generated_data g
JOIN classified_data c ON g.auction_id = c.auction_id;
