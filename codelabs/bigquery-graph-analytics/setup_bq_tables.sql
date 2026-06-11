-- Lab 3: Logistics Network Baseline Table Initialization

-- 1. Define Node Tables with relaxed Primary Keys (Required for Property Graph logic)
CREATE OR REPLACE TABLE `lost_cargo_dataset.companies` (
  company_id INT64 NOT NULL,
  company_name STRING,
  headquarters_address STRING,
  phone_number STRING,
  PRIMARY KEY (company_id) NOT ENFORCED
);

-- 1b. Define Ports Node Table
CREATE OR REPLACE TABLE `lost_cargo_dataset.ports` (
  port_id STRING NOT NULL,
  port_name STRING,
  latitude FLOAT64,
  longitude FLOAT64,
  country STRING,
  PRIMARY KEY (port_id) NOT ENFORCED
);

-- Populating Ports records
INSERT INTO `lost_cargo_dataset.ports` (port_id, port_name, latitude, longitude, country)
VALUES
  ('P-MEL', 'Port of Melbourne', -37.8409, 144.9454, 'Australia'),
  ('P-MTV', 'Mountain View Terminal', 37.3861, -122.0839, 'United States'),
  ('P-TOK', 'Tokyo Harbor', 35.6122, 139.7764, 'Japan'),
  ('P-RIO', 'Port of Rio de Janeiro', -22.8958, -43.1818, 'Brazil'),
  ('P-LDN', 'Port of London', 51.5033, 0.0512, 'United Kingdom'),
  ('P-FRA', 'Frankfurt River Port', 50.1083, 8.7303, 'Germany'),
  ('P-SIN', 'Port of Singapore', 1.2644, 103.8400, 'Singapore'),
  ('P-SYD', 'Sydney Harbour', -33.8600, 151.2100, 'Australia'),
  ('P-DXB', 'Port of Jebel Ali', 24.9857, 55.0717, 'United Arab Emirates'),
  ('P-NYC', 'Port of New York', 40.7050, -74.0150, 'United States');

-- 2. Define Vessels Node Table
CREATE OR REPLACE TABLE `lost_cargo_dataset.vessels` (
  vessel_id STRING NOT NULL,
  vessel_name STRING,
  company_id INT64,
  destination_port_id STRING,
  PRIMARY KEY (vessel_id) NOT ENFORCED,
  FOREIGN KEY (company_id) REFERENCES `lost_cargo_dataset.companies`(company_id) NOT ENFORCED,
  FOREIGN KEY (destination_port_id) REFERENCES `lost_cargo_dataset.ports`(port_id) NOT ENFORCED
);

-- Populating Vessels records
INSERT INTO `lost_cargo_dataset.vessels` (vessel_id, vessel_name, company_id, destination_port_id)
VALUES
  ('V-DINO-01', 'Dino Voyager', 101, 'P-RIO'),
  ('V-ANDROID-02', 'Android Express', 102, 'P-TOK'),
  ('MV-DOG-002', 'Flying Dutchman', 103, 'P-MTV'),
  ('V-THAMES-04', 'Thames Carrier', 104, 'P-LDN'),
  ('V-RHINE-05', 'Rhine Merchant', 105, 'P-FRA'),
  ('V-MERLION-06', 'Merlion Star', 106, 'P-SIN'),
  ('V-HARBOUR-07', 'Harbour Transit', 107, 'P-SYD'),
  ('V-FALCON-08', 'Desert Falcon', 108, 'P-DXB'),
  ('V-LIBERTY-09', 'Liberty Pioneer', 109, 'P-NYC'),
  ('V-CLOUD-10', 'Cloud Stratus', 103, 'P-SIN'),
  ('V-ANDROID-11', 'Android T-Rex', 102, 'P-MEL'),
  ('V-DINO-12', 'Dino Runner', 101, 'P-RIO'),
  ('V-CLOUD-14', 'Cloud Cumulus', 103, 'P-TOK'),
  ('V-ANDROID-15', 'Android Honeycomb', 102, 'P-SIN'),
  ('V-DINO-16', 'Dino Rex', 101, 'P-RIO');

-- 2c. Define Shipping Manifest Node Table directly
CREATE OR REPLACE TABLE `lost_cargo_dataset.manifests` (
  shipment_id STRING NOT NULL,
  timestamp TIMESTAMP,
  seal_integrity_status INT64,
  custodian_id STRING,
  vessel_id STRING,
  PRIMARY KEY (shipment_id) NOT ENFORCED,
  FOREIGN KEY (vessel_id) REFERENCES `lost_cargo_dataset.vessels`(vessel_id) NOT ENFORCED
)
OPTIONS(
  description="Foundational physical shipment repository. Materialized dataset supporting property graph vertex participation."
);

-- Populating Standalone Records for Manifests
INSERT INTO `lost_cargo_dataset.manifests` 
  (shipment_id, timestamp, seal_integrity_status, custodian_id, vessel_id)
VALUES
  ('NORMAL-001', CURRENT_TIMESTAMP(), 1, 'usr_101_safe', 'V-DINO-01'),
  ('NORMAL-002', CURRENT_TIMESTAMP(), 1, 'usr_102_safe', 'V-ANDROID-02'),
  ('NORMAL-003', CURRENT_TIMESTAMP(), 1, 'usr_101_safe', 'V-DINO-01'),
  ('NORMAL-004', CURRENT_TIMESTAMP(), 1, 'usr_104_safe', 'V-THAMES-04'),
  ('NORMAL-005', CURRENT_TIMESTAMP(), 1, 'usr_105_safe', 'V-RHINE-05'),
  ('NORMAL-006', CURRENT_TIMESTAMP(), 1, 'usr_106_safe', 'V-MERLION-06'),
  ('NORMAL-007', CURRENT_TIMESTAMP(), 1, 'usr_107_safe', 'V-HARBOUR-07'),
  ('NORMAL-008', CURRENT_TIMESTAMP(), 1, 'usr_108_safe', 'V-FALCON-08'),
  ('NORMAL-009', CURRENT_TIMESTAMP(), 1, 'usr_109_safe', 'V-LIBERTY-09'),
  ('NORMAL-010', CURRENT_TIMESTAMP(), 1, 'usr_103_safe', 'MV-DOG-002'),
  ('NORMAL-011', CURRENT_TIMESTAMP(), 1, 'usr_103_safe', 'V-CLOUD-10'),
  ('NORMAL-012', CURRENT_TIMESTAMP(), 1, 'usr_102_safe', 'V-ANDROID-11'),
  ('NORMAL-013', CURRENT_TIMESTAMP(), 1, 'usr_105_safe', 'V-RHINE-05'),
  ('NORMAL-014', CURRENT_TIMESTAMP(), 1, 'usr_103_safe', 'MV-DOG-002'),
  ('NORMAL-015', CURRENT_TIMESTAMP(), 1, 'usr_103_safe', 'MV-DOG-002'),
  ('NORMAL-016', CURRENT_TIMESTAMP(), 1, 'usr_103_safe', 'V-CLOUD-10'),
  ('NORMAL-017', CURRENT_TIMESTAMP(), 1, 'usr_103_safe', 'V-CLOUD-10'),
  ('NORMAL-018', CURRENT_TIMESTAMP(), 1, 'usr_103_safe', 'V-CLOUD-14'),
  ('NORMAL-019', CURRENT_TIMESTAMP(), 1, 'usr_102_safe', 'V-ANDROID-15'),
  ('NORMAL-020', CURRENT_TIMESTAMP(), 1, 'usr_101_safe', 'V-DINO-16'),
  ('NORMAL-021', CURRENT_TIMESTAMP(), 1, 'usr_101_safe', 'V-DINO-16'),
  ('MV-CAPYBARA-003', CURRENT_TIMESTAMP(), 0, 'usr_999_shadow', 'MV-DOG-002');

-- 3. Seed the mandatory clue relationship dataset alongside expanded global entities
-- Core clue: Target shadow shell companies ultimately link to '+1-650-253-0000'.
INSERT INTO `lost_cargo_dataset.companies` (company_id, company_name, headquarters_address, phone_number)
VALUES
  (101, 'Chrome Dino Logistics', 'Hub B, Rio de Janeiro', '+1-555-0101'),
  (102, 'Android Shipping Co', 'Shinjuku City, Tokyo', '+1-555-0102'),
  (103, 'Davy Jones Shipping', 'Mountain View, CA', '+1-650-253-0000'),
  (104, 'Thames Cargo Ltd', 'Canary Wharf, London', '+44-20-7946-0104'),
  (105, 'Rhine-Main Freight', 'Gateway West, Frankfurt', '+49-69-1234-0105'),
  (106, 'Merlion Express', 'Changi Logistics Center, Singapore', '+65-6789-0106'),
  (107, 'Harbour Bridge Transit', 'Darling Park, Sydney', '+61-2-9876-0107'),
  (108, 'Desert Falcon Transport', 'Al Quoz Industrial Area, Dubai', '+971-4-567-0108'),
  (109, 'Liberty Global Transit', 'Hudson Yards, New York', '+1-212-555-0109');

-- 4. Provision the Highly Secure Maritime Security Registry
-- The column containing the clearance code is directly linked to the custodian authorization token
-- and protected by the exact same Dataplex Policy Tag configured in Lab 1.
CREATE OR REPLACE TABLE `lost_cargo_dataset.maritime_security_registry` (
  co_id INT64 NOT NULL,
  lst_sec_chk DATE OPTIONS(description="Timestamp of last safety/security audit."),
  cust_nm STRING OPTIONS(description="Name of authorized container custodian."),
  cust_tok STRING OPTIONS(description="Authorization token assigned to physical custodians."),
  clc_ovr_cd STRING OPTIONS(description="Secure container override passcode.")
);

-- Note: Instructors/Operators attach the Policy Tag 'MaskShippingDetails'
-- directly to the 'clc_ovr_cd' schema column via the BigQuery console to enforce access boundaries.
INSERT INTO `lost_cargo_dataset.maritime_security_registry` (co_id, lst_sec_chk, cust_nm, cust_tok, clc_ovr_cd)
VALUES
  (101, '2026-04-12', 'Custodian Delta', 'usr_101_dino', 'CARNIVAL-GOLD-882'),
  (102, '2026-05-02', 'Custodian Beta', 'usr_102_droid', 'KRAKEN-HARBOR-194'),
  (103, '2026-05-20', 'Custodian Alpha', 'usr_999_shadow', 'SHIVER-ME-TIMBERS-888'),
  (104, '2026-05-18', 'Custodian Gamma', 'usr_104_thames', 'MIND-THE-GAP-777'),
  (105, '2026-05-11', 'Custodian Epsilon', 'usr_105_freight', 'DRAGON-CASTLE-905');
