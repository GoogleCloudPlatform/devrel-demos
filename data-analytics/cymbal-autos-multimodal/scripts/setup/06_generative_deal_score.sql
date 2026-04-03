-- ==============================================================================
-- 1. CONSOLIDATE ALL FEATURES
-- ==============================================================================
-- Join metadata with extracted vision features, pricing, and authenticity scores.

CREATE OR REPLACE TABLE `model_dev.vehicle_features_enhanced` AS
SELECT
  meta.auction_id,
  meta.item_name,
  meta.model_year,
  meta.make,
  meta.model,
  meta.mileage,
  meta.current_bid,
  meta.listing_url,
  meta.transmission_type,
  meta.description,
  meta.state,
  COALESCE(vision.body_style, 'Unknown') AS body_style,
  COALESCE(vision.condition, 50) AS condition,
  COALESCE(meta.color, vision.color, 'Unknown') AS color,
  COALESCE(vision.interior, 'Unknown') AS interior,
  COALESCE(scam.authenticity_score, 100) AS authenticity_score,
  vision.description_summary,
  prices.predicted_market_value
FROM `model_dev.vehicle_metadata` meta
LEFT JOIN `model_dev.vehicle_vision_features` vision 
  ON meta.auction_id = vision.auction_id
LEFT JOIN `model_dev.vehicle_price_predictions` prices
  ON meta.auction_id = prices.auction_id
LEFT JOIN `model_dev.vehicle_authenticity_scores` scam
  ON meta.auction_id = scam.auction_id;


-- ==============================================================================
-- 2. CALCULATE THE DEAL SCORE
-- ==============================================================================
-- Calculate a 0-100 deal score by combining price, condition, and authenticity.
-- Note: We create this as a TABLE because AI.SCORE incurs API calls to Gemini; 
-- materializing it prevents re-running the LLM on every frontend page load.

CREATE OR REPLACE TABLE `model_dev.marketplace_listings` AS
WITH score_elements AS (
  SELECT 
    *,
    -- 1. SELLER DESCRIPTION SCORE (use AI.SCORE on seller description)
      AI.SCORE(
        FORMAT("Rate the vehicle condition (0-100) based ONLY on this text: '%s'", description)
    ) AS description_score,

    -- 2. PRICE SCORE
    -- Higher impact for underpricing, lower impact for overpricing.
    CAST(LEAST(100.0, GREATEST(0.0, 
      75.0 + (
        IF((predicted_market_value - current_bid) > 0, 
           ((predicted_market_value - current_bid) / NULLIF(predicted_market_value, 0)) * 250.0,
           ((predicted_market_value - current_bid) / NULLIF(predicted_market_value, 0)) * 40.0
        )
      )
    )) AS INT64) AS price_score
  FROM `model_dev.vehicle_features_enhanced`
),
final_calcs AS (
  SELECT 
    *,
    
    -- 3. Combine scores: Price (40%), Condition (30%), Description (15%), Authenticity (15%)
    ROUND(
      (
        (price_score * 0.40) + 
        (CAST(condition AS INT64) * 0.30) + 
        (COALESCE(description_score, 50) * 0.15) + 
        (CAST(authenticity_score AS INT64) * 0.15)
      )
      -- Authenticity penalty for scores below 50.
      * (IF(CAST(authenticity_score AS INT64) < 50, 0.20, 1.05)) 
    ) AS raw_score
  FROM score_elements
)
SELECT 
  * EXCEPT(raw_score),
  
  -- 4. Set floor values: low authenticity scores drop to 10; others floor at 35.
  CAST(GREATEST(
    (IF(CAST(authenticity_score AS INT64) < 50, 10, 35)), 
    LEAST(100, raw_score)
  ) AS INT64) AS deal_score
FROM final_calcs;
