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

-- Sample yse of standard scalar functions
GRAPH finance_ds.BankGraph_Complaints
MATCH (cust:Customer)
WHERE LENGTH(cust.name) > 10
RETURN
    UPPER(cust.name) AS customer_name_upper,
    LENGTH(cust.name) AS name_length;


GRAPH finance_ds.BankGraph_Complaints
MATCH (src:Account)-[t:TRANSFER]->(dst:Account)
RETURN
  t.tid AS transaction_id,
  CONCAT(
    'Transfer of $', CAST(t.amount AS STRING),
    ' from account ', CAST(t.from_aid AS STRING),
    ' to account ', CAST(t.to_aid AS STRING)
  ) AS transaction_description;
