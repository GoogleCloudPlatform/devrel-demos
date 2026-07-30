-- ============================================================================
-- BigQuery Graph Visualization 1: Full Graph Traversals
-- Returns all Source Nodes, Relationships, and Target Nodes for interactive rendering
-- ============================================================================

GRAPH `{DATASET_ID}.{GRAPH_TABLE_NAME}`
MATCH (source)-[r]->(target)
WITH DISTINCT *
RETURN
  TO_JSON(source) AS Source_Node,
  TO_JSON(r) AS Edge,
  TO_JSON(target) AS Target_Node;
