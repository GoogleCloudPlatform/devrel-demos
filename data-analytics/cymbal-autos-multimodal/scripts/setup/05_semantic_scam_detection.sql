-- ==============================================================================
-- 1. GENERATE MULTIMODAL EMBEDDINGS FOR VEHICLE IMAGES
-- ==============================================================================
-- Embed the images and description for each vehicle to allow semantic search.

CREATE OR REPLACE TABLE `model_dev.vehicle_images_embedded` AS
SELECT
  auction_id,
  AI.EMBED(
    STRUCT(image_ref),
    endpoint => 'gemini-embedding-2-preview').result AS multimodal_embedding
FROM `model_dev.vehicle_multimodal`
WHERE ARRAY_LENGTH(image_ref) > 0;


-- ==============================================================================
-- 2. GENERATE EMBEDDINGS FOR SELLER RISK PROFILES
-- ==============================================================================
-- Embed seller risk descriptions.

CREATE OR REPLACE TABLE `model_dev.seller_risk_profiles_embedded` AS
SELECT 
  profile_id, 
  description AS content, 
  profile_type, 
  AI.EMBED(description, endpoint => 'text-embedding-005').result AS text_embedding
FROM `model_dev.seller_risk_profiles`;


-- ==============================================================================
-- 3. GENERATE EMBEDDINGS FOR VEHICLE LISTINGS
-- ==============================================================================
-- Embed vehicle descriptions for comparison against scam profiles.

CREATE OR REPLACE TABLE `model_dev.vehicle_descriptions_embedded` AS
SELECT 
  auction_id,
  description AS content,
  AI.EMBED(description, endpoint => 'text-embedding-005').result AS text_embedding
FROM `model_dev.vehicle_metadata`
WHERE description IS NOT NULL;


-- ==============================================================================
-- 4. PERFORM VECTOR SEARCH & EXPORT SCAM SCORES
-- ==============================================================================
-- Calculate semantic distance between live listings and scam profiles.
-- Low distance indicates a potential scam.

CREATE OR REPLACE TABLE `model_dev.vehicle_authenticity_scores` AS
SELECT 
  scam_search.query.auction_id,
  CAST(
    GREATEST(0.0, LEAST(100.0, ROUND((MIN(scam_search.distance) - 0.33) / 0.12 * 100.0))) 
    AS INT64
  ) AS authenticity_score
FROM VECTOR_SEARCH(
  TABLE `model_dev.seller_risk_profiles_embedded`,
  'text_embedding',
  (
      SELECT text_embedding, auction_id 
      FROM `model_dev.vehicle_descriptions_embedded`
  ),
  top_k => 15,
  distance_type => 'COSINE'
) AS scam_search
WHERE scam_search.base.profile_type = 'scam'
GROUP BY 1;
