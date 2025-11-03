-- ============================================================
-- 1. Finance Mart Data Loading
-- ============================================================

-- Table A: fin_monthly_closing_internal (CFO View)
INSERT INTO `finance_mart.fin_monthly_closing_internal` (closing_date, revenue_amt, cost_amt, profit_amt, status)
VALUES
  ('2024-01-31', 1500000.00, 900000.00, 600000.00, 'FINALIZED'),
  ('2024-02-29', 1450000.00, 850000.00, 600000.00, 'FINALIZED'),
  ('2024-03-31', 1600000.00, 950000.00, 650000.00, 'FINALIZED');

-- Table B: fin_quarterly_public_report (Public PR View)
INSERT INTO `finance_mart.fin_quarterly_public_report` (quarter_name, public_revenue, public_operating_income, disclosure_date)
VALUES
  ('2024-Q1', 4550000.00, 1850000.00, '2024-04-15');

-- ============================================================
-- 2. Marketing Data Loading
-- ============================================================

-- Table C: mkt_realtime_campaign_performance (Marketer View)
INSERT INTO `marketing_prod.mkt_realtime_campaign_performance` (event_time, campaign_id, estimated_revenue)
VALUES
  (TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE), 'CMP_SUMMER_EARLY', 120.50),
  (TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE), 'CMP_SUMMER_EARLY', 350.00),
  (CURRENT_TIMESTAMP(), 'CMP_BRAND_AWARENESS', 50.00);

-- ============================================================
-- 3. Sandbox Data Loading (The Trap)
-- ============================================================

-- Table D: tmp_data_dump_v2_final_real (Bad Data)
INSERT INTO `analyst_sandbox.tmp_data_dump_v2_final_real` (col1, val)
VALUES
  ('2024-01 data maybe?', 1500000),
  ('2024-01 data maybe?', 1500000), -- Intentional duplicate
  ('test_row', 99999999);
