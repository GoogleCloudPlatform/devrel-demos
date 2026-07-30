-- ============================================================================
-- BigQuery Graph Visualization 4: Customer -> Complaint -> Product -> Part -> Material
-- Cross-references Spanner Customer Complaints with Document AI & Gemini extracted knowledge graph
-- ============================================================================

GRAPH `{DATASET_ID}.{GRAPH_TABLE_NAME}`
MATCH (c:Customer)-[comp:HAS_COMPLAINT]->(p:Product)-[e:CONTAINS_PART]->(pt:Part)-[f:IS_MADE_OF]->(m:Material)
WITH DISTINCT *
RETURN
  TO_JSON(c) AS customer,
  TO_JSON(comp) AS filed_complaint,
  TO_JSON(p) AS product,
  TO_JSON(e) AS contains_part,
  TO_JSON(pt) AS part,
  TO_JSON(f) AS made_of,
  TO_JSON(m) AS material;
