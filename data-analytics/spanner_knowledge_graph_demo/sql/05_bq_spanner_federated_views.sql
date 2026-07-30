-- ============================================================================
-- BigQuery Federated Views: Linking Spanner Transactional Data into BigQuery
-- Uses EXTERNAL_QUERY to query live Spanner tables directly from BigQuery
-- Note: Replace {SPANNER_CONNECTION_ID} with your BigQuery Connection ID (e.g. `us.spanner_kg_conn`)
-- ============================================================================

-- 1. Federated View for Spanner Customers Table
CREATE OR REPLACE VIEW `{DATASET_ID}.v_spanner_customers` AS
SELECT * FROM EXTERNAL_QUERY(
  '{SPANNER_CONNECTION_ID}',
  '''SELECT customer_id, company, email, annual_support_allowance, city, country FROM Customers'''
);

-- 2. Federated View for Spanner Purchase Orders Table
CREATE OR REPLACE VIEW `{DATASET_ID}.v_spanner_purchase_orders` AS
SELECT * FROM EXTERNAL_QUERY(
  '{SPANNER_CONNECTION_ID}',
  '''SELECT order_id, customer_id, product_id, order_date, quantity, total_amount, status FROM PurchaseOrders'''
);

-- 3. Federated View for Spanner Customer Complaints Table
CREATE OR REPLACE VIEW `{DATASET_ID}.v_spanner_complaints` AS
SELECT * FROM EXTERNAL_QUERY(
  '{SPANNER_CONNECTION_ID}',
  '''SELECT complaint_id, customer_id, product_id, complaint_date, issue_category, description, severity, status FROM CustomerComplaints'''
);

-- 4. Federated View for Spanner Products Catalog Table
CREATE OR REPLACE VIEW `{DATASET_ID}.v_spanner_products` AS
SELECT * FROM EXTERNAL_QUERY(
  '{SPANNER_CONNECTION_ID}',
  '''SELECT product_id, product_name, category, unit_price FROM Products'''
);
