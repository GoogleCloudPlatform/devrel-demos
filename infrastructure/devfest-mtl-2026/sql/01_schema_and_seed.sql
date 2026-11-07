-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--      https://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

-- ============================================================================
-- DevFest Montréal 2026 Demo: AlloyDB for PostgreSQL Data Layer & Sample Data
-- Database: support_db
-- ============================================================================

-- 1. Enable vector & AlloyDB AI extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS alloydb_scann;
CREATE EXTENSION IF NOT EXISTS google_ml_integration;

-- 2. Customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    full_name    VARCHAR(120) NOT NULL,
    email       VARCHAR(160) UNIQUE NOT NULL,
    tier        VARCHAR(20) NOT NULL DEFAULT 'STANDARD'
                CHECK (tier IN ('STANDARD', 'PRO', 'ENTERPRISE')),
    city        VARCHAR(80) NOT NULL DEFAULT 'Montréal'
);

-- 3. Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id      VARCHAR(32) PRIMARY KEY,
    customer_id  VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    product_name VARCHAR(160) NOT NULL,
    amount_cad   NUMERIC(10, 2) NOT NULL,
    order_status VARCHAR(24) NOT NULL
                 CHECK (order_status IN ('PROCESSING', 'SHIPPED', 'DELIVERED', 'DELAYED', 'REFUNDED')),
    ordered_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 4. Support tickets table with 768-dim Gemini vector embeddings
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id       SERIAL PRIMARY KEY,
    customer_id     VARCHAR(32) NOT NULL REFERENCES customers(customer_id),
    order_id        VARCHAR(32) REFERENCES orders(order_id),
    priority        VARCHAR(16) NOT NULL DEFAULT 'MEDIUM'
                    CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status          VARCHAR(20) NOT NULL DEFAULT 'OPEN'
                    CHECK (status IN ('OPEN', 'IN_PROGRESS', 'ESCALATED', 'RESOLVED')),
    issue_summary   TEXT NOT NULL,
    resolution_note TEXT,
    embedding       vector(768),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Seed sample customers
INSERT INTO customers (customer_id, full_name, email, tier, city) VALUES
    ('CUST-101', 'Amélie Tremblay', 'amelie.tremblay@example.ca', 'ENTERPRISE', 'Montréal'),
    ('CUST-102', 'Marc-Antoine Roy', 'marc.roy@example.ca', 'PRO', 'Laval'),
    ('CUST-103', 'Chloe Nguyen', 'chloe.nguyen@example.ca', 'STANDARD', 'Quebec City'),
    ('CUST-104', 'David Gagnon', 'david.gagnon@example.ca', 'ENTERPRISE', 'Montréal')
ON CONFLICT (customer_id) DO NOTHING;

-- 6. Seed sample orders
INSERT INTO orders (order_id, customer_id, product_name, amount_cad, order_status, ordered_at) VALUES
    ('ORD-9001', 'CUST-101', 'Cloud Workstation GPU Node x2', 4200.00, 'DELAYED',   NOW() - INTERVAL '6 days'),
    ('ORD-9002', 'CUST-102', 'NVMe Enterprise Dock',           189.00, 'DELIVERED', NOW() - INTERVAL '4 days'),
    ('ORD-9003', 'CUST-103', 'Mechanical Dev Keyboard',        145.00, 'SHIPPED',   NOW() - INTERVAL '2 days'),
    ('ORD-9004', 'CUST-104', 'Rackmount UPS Battery Pack',    1350.00, 'DELAYED',   NOW() - INTERVAL '8 days')
ON CONFLICT (order_id) DO NOTHING;

-- 7. Seed sample support tickets
INSERT INTO support_tickets (customer_id, order_id, priority, status, issue_summary, resolution_note) VALUES
    ('CUST-101', 'ORD-9001', 'CRITICAL', 'OPEN',
     'Shipment stuck at Mirabel hub for 5 days; Enterprise SLA breach imminent.', NULL),
    ('CUST-102', 'ORD-9002', 'MEDIUM', 'OPEN',
     'Thunderbolt port intermittently disconnects when waking macOS from sleep.', NULL),
    ('CUST-103', 'ORD-9003', 'LOW', 'RESOLVED',
     'Requested French-Canadian keycap layout swap prior to delivery.',
     'Included complimentary CSA keycap kit in shipment ORD-9003.'),
    ('CUST-104', 'ORD-9004', 'HIGH', 'OPEN',
     'Carrier tracking frozen in transit for over a week on critical server room UPS.', NULL),
    ('CUST-101', NULL, 'LOW', 'RESOLVED',
     'Firmware update v2.4 fixed dock wake-from-sleep disconnect on macOS.',
     'Sent firmware v2.4 link; customer confirmed disconnect issue resolved.');

-- 8. Optional: Populate Gemini embeddings in-database (requires Vertex AI integration on AlloyDB)
-- Uncomment after granting Vertex AI User role to the AlloyDB service agent:
-- UPDATE support_tickets
-- SET embedding = embedding('text-embedding-005', issue_summary)::vector
-- WHERE embedding IS NULL;
--
-- CREATE INDEX IF NOT EXISTS tickets_scann_idx
-- ON support_tickets USING scann (embedding cosine) WITH (num_leaves = 16);

-- 9. Grant least-privilege table access to your IAM DB user
-- Note: IAM database users cannot be created using standard SQL alone; register the
-- user via Google Cloud Console, gcloud alloydb users create --type=IAM_BASED, or
-- the AlloyDB API first, then grant standard PostgreSQL roles and privileges below:
-- GRANT SELECT, INSERT, UPDATE ON customers, orders, support_tickets TO "adk-agent-sa@devfest-project.iam";
-- GRANT USAGE, SELECT ON SEQUENCE support_tickets_ticket_id_seq TO "adk-agent-sa@devfest-project.iam";
