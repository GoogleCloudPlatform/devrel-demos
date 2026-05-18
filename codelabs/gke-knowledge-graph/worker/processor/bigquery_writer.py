# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import json
from google.cloud import bigquery

DATASET_ID = os.environ.get("BQ_DATASET", "petverse_kg")
NODES_TABLE = "Nodes"
EDGES_TABLE = "Edges"

def write_graph_to_bq(nodes, edges):
    client = bigquery.Client()

    dataset_ref = client.dataset(DATASET_ID)

    if nodes:
        try:
            nodes_table = client.get_table(dataset_ref.table(NODES_TABLE))
            # De-duplication check
            target_ids = list(set(node.get('entity_id') for node in nodes if node.get('entity_id')))
            existing_ids = set()
            if target_ids:
                query = f"SELECT entity_id FROM `{client.project}.{DATASET_ID}.{NODES_TABLE}` WHERE entity_id IN UNNEST(@ids)"
                job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", target_ids)])
                rows_iter = client.query(query, job_config=job_config).result()
                existing_ids = {row.entity_id for row in rows_iter}

            rows = []
            for node in nodes:
                if node.get('entity_id') in existing_ids:
                    continue
                props_dict = node.get('properties', {})
                if isinstance(props_dict, str):
                    try:
                        props_dict = json.loads(props_dict)
                    except Exception:
                        props_dict = {}

                # Resolve name from various possible locations
                name_val = node.get('name')
                if not name_val:
                    name_val = props_dict.get('name') or props_dict.get('pet_name')
                if not name_val and node.get('entity_type') == 'Pet':
                    eid = node.get('entity_id')
                    if eid and not (eid.startswith('pet_') or eid.startswith('cat_') or eid.startswith('dog_') or eid.startswith('node_')):
                        name_val = eid

                # Combine targeted strings into single unified bio column to satisfy BigQuery single-embedding restriction
                hobby_val = str(props_dict.get('hobby', '')) if props_dict.get('hobby') else ""
                food_val = str(props_dict.get('favorite_food', '')) if props_dict.get('favorite_food') else ""
                bio_combined = f"Hobby: {hobby_val}. Favorite Food: {food_val}." if (hobby_val or food_val) else None

                rows.append({
                    'entity_id': node.get('entity_id'),
                    'entity_type': node.get('entity_type'),
                    'name': name_val,
                    'pet_bio': node.get('pet_bio') or bio_combined,
                    'properties': json.dumps(props_dict)
                })

            if not rows:
                print("✅ All nodes already exist in BigQuery. Skipping node insert.")
            else:
                errors = client.insert_rows_json(nodes_table, rows)
                if errors:
                    print("❌ BigQuery Node insertion errors:", errors)
                else:
                    print(f"✅ Successfully inserted {len(rows)} new nodes into BigQuery.")
        except Exception as e:
            print("❌ Error accessing Nodes table:", e)

    if edges:
        try:
            edges_table = client.get_table(dataset_ref.table(EDGES_TABLE))
            # De-duplication check for edges using stable composite key logic
            check_keys = list(set(f"{e.get('source_id')}|||{e.get('target_id')}|||{e.get('relationship')}" for e in edges))
            existing_keys = set()

            if check_keys:
                query = f"SELECT source_id, target_id, relationship FROM `{client.project}.{DATASET_ID}.{EDGES_TABLE}` WHERE CONCAT(source_id, '|||', target_id, '|||', relationship) IN UNNEST(@keys)"
                job_config = bigquery.QueryJobConfig(query_parameters=[bigquery.ArrayQueryParameter("keys", "STRING", check_keys)])
                rows_iter = client.query(query, job_config=job_config).result()
                existing_keys = {f"{row.source_id}|||{row.target_id}|||{row.relationship}" for row in rows_iter}

            rows = []
            for edge in edges:
                key = f"{edge.get('source_id')}|||{edge.get('target_id')}|||{edge.get('relationship')}"
                if key in existing_keys:
                    continue
                rows.append({
                    'source_id': edge.get('source_id'),
                    'target_id': edge.get('target_id'),
                    'relationship': edge.get('relationship'),
                    'properties': edge.get('properties') if isinstance(edge.get('properties'), str) else json.dumps(edge.get('properties'))
                })
            if not rows:
                print("✅ All edges already exist in BigQuery. Skipping edge insert.")
            else:
                errors = client.insert_rows_json(edges_table, rows)
                if errors:
                    print("❌ BigQuery Edge insertion errors:", errors)
                else:
                    print(f"✅ Successfully inserted {len(rows)} new edges into BigQuery.")
        except Exception as e:
            print("❌ Error accessing Edges table:", e)
