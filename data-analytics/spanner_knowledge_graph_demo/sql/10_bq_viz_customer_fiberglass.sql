-- ============================================================================
-- BigQuery Graph Visualization 3: Customer -> Product -> Part -> Material (Fiberglass)
-- Traverses Spanner customer purchases across BigQuery extracted component materials
-- ============================================================================

GRAPH `{DATASET_ID}.{GRAPH_TABLE_NAME}`
MATCH (c:Customer)-[r:PURCHASED]->(p:Product)-[e:CONTAINS_PART]->(pt:Part)-[f:IS_MADE_OF]->(m:Material {material_name:"Fiberglass"})
WITH DISTINCT *
RETURN
  TO_JSON(c) AS customer,
  TO_JSON(r) AS purchased,
  TO_JSON(p) AS product,
  TO_JSON(e) AS contains_part,
  TO_JSON(pt) AS part,
  TO_JSON(f) AS made_of,
  TO_JSON(m) AS material;
