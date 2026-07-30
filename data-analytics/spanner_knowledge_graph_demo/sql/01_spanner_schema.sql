-- ============================================================================
-- Spanner DDL: Transactional Database Schema
-- Table definitions for Customers, Products, Purchase Orders, Complaints, and Reverse ETL Insights
-- ============================================================================

-- 1. Customers Table (Transactional Master Data)
CREATE TABLE Customers (
    customer_id STRING(36) NOT NULL,
    company STRING(100) NOT NULL,
    email STRING(100),
    annual_support_allowance NUMERIC,
    city STRING(50),
    country STRING(50),
    created_at TIMESTAMP
) KEY(customer_id);

-- 2. Products Table (Transactional Catalog)
CREATE TABLE Products (
    product_id STRING(36) NOT NULL,
    product_name STRING(100) NOT NULL,
    category STRING(50),
    unit_price NUMERIC,
    created_at TIMESTAMP
) KEY(product_id);

-- 3. PurchaseOrders Table (Transactional Operations)
CREATE TABLE PurchaseOrders (
    order_id STRING(36) NOT NULL,
    customer_id STRING(36) NOT NULL,
    product_id STRING(36) NOT NULL,
    order_date TIMESTAMP,
    quantity INT64,
    total_amount NUMERIC,
    status STRING(20),
    FOREIGN KEY (customer_id) REFERENCES Customers (customer_id),
    FOREIGN KEY (product_id) REFERENCES Products (product_id)
) KEY(order_id);

-- 4. CustomerComplaints Table (Operational Customer Support Data)
CREATE TABLE CustomerComplaints (
    complaint_id STRING(36) NOT NULL,
    customer_id STRING(36) NOT NULL,
    product_id STRING(36) NOT NULL,
    complaint_date TIMESTAMP,
    issue_category STRING(50),
    description STRING(MAX),
    severity STRING(20),
    status STRING(20),
    FOREIGN KEY (customer_id) REFERENCES Customers (customer_id),
    FOREIGN KEY (product_id) REFERENCES Products (product_id)
) KEY(complaint_id);

-- 5. ReverseEtlEnrichedInsights Table (Receives Reverse ETL Analytical Insights from BigQuery)
CREATE TABLE ReverseEtlEnrichedInsights (
    insight_id STRING(36) NOT NULL,
    customer_id STRING(36) NOT NULL,
    product_id STRING(36) NOT NULL,
    suspected_material STRING(100),
    extracted_part_name STRING(100),
    risk_score NUMERIC,
    recommended_action STRING(MAX),
    last_updated TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES Customers (customer_id),
    FOREIGN KEY (product_id) REFERENCES Products (product_id)
) KEY(insight_id);
