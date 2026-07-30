-- ============================================================================
-- Spanner Graph Queries (GQL)
-- Traverses operational relationships directly in Spanner Database
-- ============================================================================

-- Query 1: Find all Customers and the Products they have purchased
GRAPH spanner_manufacturing_graph
MATCH (c:Customer)-[p:PURCHASED]->(prod:Product)
RETURN c.company, prod.product_name, p.order_date, p.total_amount;

-- Query 2: Trace Customer Complaints to Products and Customer details
GRAPH spanner_manufacturing_graph
MATCH (c:Customer)-[:FILED_COMPLAINT]->(comp:Complaint)-[:REGARDING_PRODUCT]->(p:Product)
RETURN 
  c.company AS customer_name, 
  c.email AS contact_email, 
  comp.complaint_id, 
  comp.issue_category, 
  comp.severity, 
  p.product_name AS affected_product;
