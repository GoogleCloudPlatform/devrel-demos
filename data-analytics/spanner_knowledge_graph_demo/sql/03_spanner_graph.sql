-- ============================================================================
-- Spanner Graph DDL: Property Graph Definition in Spanner
-- Models Customer, Product, and Complaint operational entities and relationships
-- ============================================================================

CREATE OR REPLACE PROPERTY GRAPH spanner_manufacturing_graph
  NODE TABLES (
    Customers
      KEY (customer_id)
      LABEL Customer
      PROPERTIES (customer_id, company, email, annual_support_allowance, city, country),

    Products
      KEY (product_id)
      LABEL Product
      PROPERTIES (product_id, product_name, category, unit_price),

    CustomerComplaints
      KEY (complaint_id)
      LABEL Complaint
      PROPERTIES (complaint_id, complaint_date, issue_category, severity, status, description)
  )
  EDGE TABLES (
    PurchaseOrders
      KEY (order_id)
      SOURCE KEY (customer_id) REFERENCES Customers(customer_id)
      DESTINATION KEY (product_id) REFERENCES Products(product_id)
      LABEL PURCHASED
      PROPERTIES (order_id, order_date, quantity, total_amount, status),

    CustomerComplaints AS ComplaintCustomerRef
      KEY (complaint_id)
      SOURCE KEY (customer_id) REFERENCES Customers(customer_id)
      DESTINATION KEY (complaint_id) REFERENCES CustomerComplaints(complaint_id)
      LABEL FILED_COMPLAINT,

    CustomerComplaints AS ComplaintProductRef
      KEY (complaint_id)
      SOURCE KEY (complaint_id) REFERENCES CustomerComplaints(complaint_id)
      DESTINATION KEY (product_id) REFERENCES Products(product_id)
      LABEL REGARDING_PRODUCT
  );
