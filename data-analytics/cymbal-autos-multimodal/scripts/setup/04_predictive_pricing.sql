-- ==============================================================================
-- 1. TRAIN XGBOOST MODEL 
-- ==============================================================================
-- Train pricing model on historical synthetic car data.

CREATE OR REPLACE MODEL `model_dev.car_price_model`
OPTIONS(
  MODEL_TYPE = 'BOOSTED_TREE_REGRESSOR',
  INPUT_LABEL_COLS = ['selling_price'],
  MAX_ITERATIONS = 15,
  TREE_METHOD = 'HIST'
) AS
SELECT
  * EXCEPT(vin, sale_date, market_value, seller)
FROM
  `model_dev.synthetic_cars`;


-- ==============================================================================
-- 2. CREATE PREDICTION FEATURES
-- ==============================================================================
-- Combine metadata with visual features (e.g. condition score) for online predictions.

CREATE OR REPLACE TABLE `model_dev.vehicle_prediction_features` AS
SELECT
  meta.auction_id,
  meta.model_year,
  meta.make,
  meta.model,
  meta.mileage,
  meta.transmission_type,
  meta.state,
  COALESCE(vision.body_style, 'Unknown') AS body_style,
  COALESCE(vision.condition, 50) AS condition,
  COALESCE(meta.color, vision.color, 'Unknown') AS color,
  COALESCE(vision.interior, 'Unknown') AS interior
FROM `model_dev.vehicle_metadata` meta
LEFT JOIN `model_dev.vehicle_vision_features` vision 
  ON meta.auction_id = vision.auction_id;


-- ==============================================================================
-- 3. RUN PREDICTIONS
-- ==============================================================================
-- Predict fair market value using the trained XGBoost model.

CREATE OR REPLACE TABLE `model_dev.vehicle_price_predictions` AS
SELECT 
  auction_id,
  ROUND(predicted_selling_price, 2) AS predicted_market_value
FROM ML.PREDICT(
  MODEL `model_dev.car_price_model`,
  (SELECT * FROM `model_dev.vehicle_prediction_features`)
);
