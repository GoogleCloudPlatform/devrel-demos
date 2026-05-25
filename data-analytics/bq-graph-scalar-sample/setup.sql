-- Copyright 2026 Google LLC
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

CREATE SCHEMA IF NOT EXISTS `finance_ds`;

-- Step 1: Create the Table with an Autonomous Embedding Column
CREATE OR REPLACE TABLE `finance_ds.Complaints` (
  id INT64,
  customer_id INT64,
  complaint_text STRING,
  -- The magic: BigQuery manages this column for you
  text_embedding STRUCT<result ARRAY<FLOAT64>, status STRING>
    GENERATED ALWAYS AS (
      AI.EMBED(
        complaint_text,
        -- connection_id => 'us.vertex_connection',
        model => 'embeddinggemma-300m'
      )
    )
    STORED
    OPTIONS(asynchronous = TRUE)
);

-- 2. Create Tables
CREATE TABLE IF NOT EXISTS finance_ds.Customers (cid INT64, name STRING);
CREATE TABLE IF NOT EXISTS finance_ds.Accounts (aid INT64, customer_id INT64, balance FLOAT64);
CREATE TABLE IF NOT EXISTS finance_ds.Transactions (tid INT64, from_aid INT64, to_aid INT64, amount FLOAT64);
CREATE TABLE IF NOT EXISTS finance_ds.Complaints (id INT64, customer_id INT64, text STRING, text_embed ARRAY<FLOAT64>);


-- 1. Insert Customers
INSERT INTO `finance_ds.Customers` (cid, name)
VALUES
  (101, 'Alice Smith'),
  (102, 'Bob Jones'),
  (103, 'Charlie Davis'),
  (104, 'Diana Prince'),
  (105, 'Eve Black'),
  (106, 'Martha Jones');

-- 2. Insert Accounts
-- Some customers have multiple accounts.
INSERT INTO `finance_ds.Accounts` (aid, customer_id, balance)
VALUES
  (201, 101, 4000.00), -- Alice's main account
  (202, 102, 1500.00), -- Bob's main account
  (203, 103, 50.00),   -- Charlie's account A
  (204, 103, 120.00),  -- Charlie's account B
  (205, 104, 8500.00), -- Diana's main account
  (206, 105, 95000.00),-- Eve's offshore/sink account
  (207, 106, 300.00);  -- Martha's account

-- 3. Insert Transactions
-- This creates the edges (TRANSFERS) between accounts.
INSERT INTO `finance_ds.Transactions` (tid, from_aid, to_aid, amount)
VALUES
  (301, 201, 203, 1000.00), -- Alice sends $1000 to Charlie (stuck/scam)
  (302, 202, 207, 250.00),  -- Bob sends $250 to Martha (app crashed during this)
  (303, 205, 204, 5000.00), -- Diana's account sends $5000 to Charlie (unauthorized)
  (304, 203, 206, 1000.00), -- Charlie funnels Alice's $1000 to Eve
  (305, 204, 206, 5000.00); -- Charlie funnels Diana's $5000 to Eve

-- 4. Insert Complaints
-- BigQuery Autonomous Embeddings will automatically vectorize the `complaint_text`.
INSERT INTO `finance_ds.Complaints` (id, customer_id, complaint_text)
VALUES
  (1, 101, 'I am extremely frustrated! My transfer has been stuck for three days.'),
  (2, 102, 'The app crashed while I was sending money to my mother.'),
  (3, 104, 'URGENT: There is an unauthorized transfer of $5000 out of my account! I did not approve this transaction.'),
  (4, 101, 'Is there any update on my missing funds? I think I may have been scammed by a fake contractor.'),
  (5, 106, 'I never received the $250 my son Bob tried to send me for groceries.');

CREATE PROPERTY GRAPH finance_ds.BankGraph_Complaints
NODE TABLES (
  finance_ds.Customers AS Customers
      KEY (cid)
      LABEL Customer,
    finance_ds.Accounts AS Accounts
      KEY (aid)
      LABEL Account,
  finance_ds.Complaints
      KEY (id)
      LABEL Complaint -- Added to allow MATCHing on embedding properties
)
EDGE TABLES (
  finance_ds.Transactions
        KEY (tid)
        SOURCE KEY(from_aid) REFERENCES Accounts(aid)
        DESTINATION KEY(to_aid) REFERENCES Accounts(aid) LABEL TRANSFER,
  finance_ds.Accounts AS AccountEdges
        KEY (aid)
        SOURCE KEY(customer_id) REFERENCES Customers(cid)
        DESTINATION KEY(aid) REFERENCES Accounts(aid) LABEL OWNS,
  -- Optional: Direct edge from Customer to Complaint
  finance_ds.Complaints AS ComplaintEdges
        KEY (id)
        SOURCE KEY(customer_id) REFERENCES Customers(cid)
        DESTINATION KEY(id) REFERENCES Complaints(id) LABEL FILED
);

