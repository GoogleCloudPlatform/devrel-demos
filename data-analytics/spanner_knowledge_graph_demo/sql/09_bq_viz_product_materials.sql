-- ============================================================================
-- BigQuery Graph Visualization 2: Product -> Part -> Material Subgraph
-- Explores engineering relationships between manufactured products, parts, and materials
-- ============================================================================

GRAPH `{DATASET_ID}.{GRAPH_TABLE_NAME}`
MATCH (p:Product)-[e:CONTAINS_PART]->(pt:Part)-[c:IS_MADE_OF]->(m:Material)
RETURN
  TO_JSON(p) AS product,
  TO_JSON(e) AS contains_part,
  TO_JSON(pt) AS part,
  TO_JSON(c) AS made_of,
  TO_JSON(m) AS material;
