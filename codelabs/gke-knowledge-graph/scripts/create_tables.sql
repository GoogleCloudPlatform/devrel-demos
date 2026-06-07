-- Create a nodes table with Auto Embeddings
CREATE TABLE IF NOT EXISTS `petverse_kg.Nodes` (
  entity_id STRING NOT NULL,
  entity_type STRING,
  name STRING,
  pet_bio STRING,
  properties JSON,
  bio_embedding STRUCT<result ARRAY<FLOAT64>, status STRING> GENERATED ALWAYS AS (
    AI.EMBED(
      pet_bio,
      connection_id => '${REGION}.petverse-embeddings',
      endpoint => 'text-embedding-005'
    )
  ) STORED OPTIONS(asynchronous = TRUE)
);

--  Create an edges table
CREATE TABLE IF NOT EXISTS `petverse_kg.Edges` (
    source_id STRING,
    target_id STRING,
    relationship STRING,
    properties JSON
);
