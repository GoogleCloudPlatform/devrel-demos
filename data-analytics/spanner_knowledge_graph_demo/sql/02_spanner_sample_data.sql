-- ============================================================================
-- Spanner DML: Initial Sample Data Population
-- Insert statements for Customers, Products, Purchase Orders, and Customer Complaints
-- ============================================================================

-- 1. Insert Products
INSERT INTO Products (product_id, product_name, category, unit_price, created_at) VALUES
('P001', 'Arctic Swirl 5000', 'Commercial Freezers', 12500.00, CURRENT_TIMESTAMP()),
('P002', 'Arctic Swirl Pro 7000', 'Commercial Freezers', 18900.00, CURRENT_TIMESTAMP()),
('P003', 'FroYoFlow Elite 7000', 'Dispensing Systems', 14200.00, CURRENT_TIMESTAMP()),
('P004', 'ChillBliss Nova 8000', 'Cryogenic Chillers', 24500.00, CURRENT_TIMESTAMP()),
('P005', 'SwirlSense 8000', 'Monitoring Systems', 8300.00, CURRENT_TIMESTAMP());

-- 2. Insert Customers
INSERT INTO Customers (customer_id, company, email, annual_support_allowance, city, country, created_at) VALUES
('C001', 'Royal Soft Serve Inc.', 'support@royalsoftserve.com', 50000.00, 'Seattle', 'USA', CURRENT_TIMESTAMP()),
('C002', 'Frosty Treats Chains', 'ops@frostytreats.com', 75000.00, 'Chicago', 'USA', CURRENT_TIMESTAMP()),
('C003', 'Glacier Ice Cream Co.', 'procurement@glacierice.com', 30000.00, 'Denver', 'USA', CURRENT_TIMESTAMP()),
('C004', 'Alpine Desserts Ltd.', 'tech@alpinedesserts.ca', 45000.00, 'Vancouver', 'Canada', CURRENT_TIMESTAMP());

-- 3. Insert Purchase Orders
INSERT INTO PurchaseOrders (order_id, customer_id, product_id, order_date, quantity, total_amount, status) VALUES
('ORD-1001', 'C001', 'P001', TIMESTAMP('2026-01-15T09:30:00Z'), 3, 37500.00, 'COMPLETED'),
('ORD-1002', 'C001', 'P002', TIMESTAMP('2026-02-10T14:15:00Z'), 2, 37800.00, 'COMPLETED'),
('ORD-1003', 'C002', 'P003', TIMESTAMP('2026-03-01T11:00:00Z'), 5, 71000.00, 'COMPLETED'),
('ORD-1004', 'C003', 'P001', TIMESTAMP('2026-03-20T16:45:00Z'), 2, 25000.00, 'COMPLETED'),
('ORD-1005', 'C004', 'P004', TIMESTAMP('2026-04-05T10:20:00Z'), 1, 24500.00, 'COMPLETED'),
('ORD-1006', 'C002', 'P005', TIMESTAMP('2026-04-18T13:00:00Z'), 4, 33200.00, 'SHIPPED');

-- 4. Insert Customer Complaints
INSERT INTO CustomerComplaints (complaint_id, customer_id, product_id, complaint_date, issue_category, description, severity, status) VALUES
('CMP-501', 'C001', 'P001', TIMESTAMP('2026-05-01T08:00:00Z'), 'Overheating & Texture Failure', 'Arctic Swirl 5000 dispensing unit experiencing rapid heating and inconsistent texture output under high ambient temperature.', 'HIGH', 'OPEN'),
('CMP-502', 'C002', 'P003', TIMESTAMP('2026-05-04T10:30:00Z'), 'Auger Noise & Vibration', 'FroYoFlow Elite 7000 unit producing loud grinding noise from mixing auger assembly.', 'MEDIUM', 'INVESTIGATING'),
('CMP-503', 'C003', 'P001', TIMESTAMP('2026-05-10T15:00:00Z'), 'Cooling Line Leak', 'Fluid leaks observed around pump seals in Arctic Swirl 5000.', 'HIGH', 'OPEN');
