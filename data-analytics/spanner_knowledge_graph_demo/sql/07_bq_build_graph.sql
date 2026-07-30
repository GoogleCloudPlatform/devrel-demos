-- ============================================================================
-- BigQuery SQL: Graph Construction (Nodes, Edges, Property Graph Definition)
-- Combines extracted document intelligence with Spanner transactional views
-- ============================================================================

-- 1. Create Node Tables

-- Part Nodes Table
CREATE OR REPLACE TABLE `{DATASET_ID}.part_nodes` AS
SELECT DISTINCT part_id AS part_name, 'Part' AS type
FROM (
  SELECT subject AS part_id
  FROM `{DATASET_ID}.{EXTRACTED_KG_TABLE_NAME}`
  WHERE subject_entity_type = 'Part'
  UNION DISTINCT
  SELECT object AS part_id
  FROM `{DATASET_ID}.{EXTRACTED_KG_TABLE_NAME}`
  WHERE object_entity_type = 'Part'
)
WHERE part_id IS NOT NULL;

-- Material Nodes Table
CREATE OR REPLACE TABLE `{DATASET_ID}.material_nodes` AS
SELECT DISTINCT object AS material_name, 'Material' AS type
FROM `{DATASET_ID}.{EXTRACTED_KG_TABLE_NAME}`
WHERE object_entity_type = 'Material' AND object IS NOT NULL;

-- 2. Create Edge Tables

-- Edge Table: Product Contains Part
CREATE OR REPLACE TABLE `{DATASET_ID}.edges_product_contains` AS
SELECT DISTINCT
  p.product_name AS product_name,
  ekg.object AS part_name
FROM `{DATASET_ID}.{EXTRACTED_KG_TABLE_NAME}` ekg
JOIN `{DATASET_ID}.products` p
  ON ekg.subject = p.product_name
WHERE ekg.relationship = 'CONTAINS_PART';

-- Edge Table: Part Is Made Of Material
CREATE OR REPLACE TABLE `{DATASET_ID}.edges_part_material` AS
SELECT DISTINCT
  subject AS part_name,
  object AS material_name
FROM `{DATASET_ID}.{EXTRACTED_KG_TABLE_NAME}`
WHERE relationship = 'MADE_OF';

-- Edge Table: Customer Purchase Orders (referencing Spanner Federated View)
CREATE OR REPLACE TABLE `{DATASET_ID}.edges_purchase_orders` AS
SELECT DISTINCT
  po.customer_id,
  p.product_name
FROM `{DATASET_ID}.v_spanner_purchase_orders` po
JOIN `{DATASET_ID}.products` p
  ON po.product_id = p.product_id;

-- Edge Table: Customer Complaints (referencing Spanner Federated View)
CREATE OR REPLACE TABLE `{DATASET_ID}.edges_customer_complaints` AS
SELECT DISTINCT
  c.customer_id,
  c.complaint_id,
  p.product_name
FROM `{DATASET_ID}.v_spanner_complaints` c
JOIN `{DATASET_ID}.products` p
  ON c.product_id = p.product_id;


-- 3. Define Property Graph Schema in BigQuery
CREATE OR REPLACE PROPERTY GRAPH `{DATASET_ID}.{GRAPH_TABLE_NAME}`
  NODE TABLES (
    `{DATASET_ID}.v_spanner_customers` AS customer_node
       KEY (customer_id)
       LABEL Customer PROPERTIES (
         customer_id,
         company,
         annual_support_allowance
       ),

    `{DATASET_ID}.v_spanner_complaints` AS complaint_node
       KEY (complaint_id)
       LABEL Complaint PROPERTIES (
         complaint_id,
         issue_category,
         severity,
         status,
         description
       ),

    `{DATASET_ID}.products` AS product_node KEY (product_name) LABEL Product,
    `{DATASET_ID}.part_nodes` AS part_node KEY (part_name) LABEL Part,
    `{DATASET_ID}.material_nodes` AS material_node KEY (material_name) LABEL Material
  )
  EDGE TABLES (
    `{DATASET_ID}.edges_purchase_orders` AS customer_purchases KEY (customer_id)
      SOURCE KEY (customer_id) REFERENCES customer_node
      DESTINATION KEY (product_name) REFERENCES product_node
      LABEL PURCHASED,

    `{DATASET_ID}.edges_customer_complaints` AS customer_filed_complaint KEY (complaint_id)
      SOURCE KEY (customer_id) REFERENCES customer_node
      DESTINATION KEY (product_name) REFERENCES product_node
      LABEL HAS_COMPLAINT,

    `{DATASET_ID}.edges_product_contains` AS product_parts KEY (product_name)
      SOURCE KEY (product_name) REFERENCES product_node
      DESTINATION KEY (part_name) REFERENCES part_node
      LABEL CONTAINS_PART,

    `{DATASET_ID}.edges_part_material` AS part_materials KEY (part_name)
      SOURCE KEY (part_name) REFERENCES part_node
      DESTINATION KEY (material_name) REFERENCES material_node
      LABEL IS_MADE_OF
  );
