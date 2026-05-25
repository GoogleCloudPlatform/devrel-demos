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

-- Visualize
GRAPH finance_ds.BankGraph_Complaints
MATCH p = (c:Customer)-[own:OWNS]->(src:Account)
RETURN
TO_JSON(p) AS res;


GRAPH finance_ds.BankGraph_Complaints
MATCH (cust:Customer)-[:FILED]->(comp:Complaint),
      (cust)-[:OWNS]->(acct:Account)
WHERE ML.DISTANCE(
        comp.text_embedding.result,
        ( AI.EMBED(
            'Angry customer',
            model => 'embeddinggemma-300m')
        ).result,
        'COSINE'
      ) < 0.5 -- Adjust based on tolerance for semantic distance
RETURN
    cust.name AS customer_name,
    comp.complaint_text,
    acct.balance AS balance;
