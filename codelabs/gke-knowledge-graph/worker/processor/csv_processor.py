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

import pandas as pd
import json

def process_csv(csv_file):
    """Processes a CSV file to extract knowledge graph nodes and edges.

    Reads pet data from a CSV, creating unique nodes for Pets, Hobbies, Foods,
    and Toys, while mapping their relationships (LIKES, OWNS, DOES) as edges.

    Args:
        csv_file: A file-like object containing the CSV data.

    Returns:
        A tuple of (nodes, edges) where nodes is a list of node dictionaries
        and edges is a list of edge dictionaries.
    """
    df = pd.read_csv(csv_file)
    nodes_dict = {}
    edges = []

    for _, row in df.iterrows():
        name = row.get('Name')
        if pd.isna(name):
            continue

        # Create Pet Node
        properties = {
            'species': row.get('Species'),
            'breed': row.get('Breed'),
            'nationality': row.get('Nationality'),
            'nicknames': row.get('Nicknames'),
            'hobby': row.get('Hobby'),
            'adoption_story': row.get('AdoptionStory'),
            'favorite_food': row.get('FavoriteFood'),
            'favorite_toy': row.get('FavoriteToy')
        }
        # Clean up None properties
        properties = {k: v for k, v in properties.items() if pd.notna(v)}

        nodes_dict[name] = {
            'entity_id': name,
            'entity_type': 'Pet',
            'name': name,
            'properties': json.dumps(properties)
        }

        # Create Food Node and Edge
        food = row.get('FavoriteFood')
        if pd.notna(food):
            if food not in nodes_dict:
                nodes_dict[food] = {
                    'entity_id': food,
                    'entity_type': 'Food',
                    'name': food,
                    'properties': json.dumps({})
                }
            edges.append({
                'source_id': name,
                'target_id': food,
                'relationship': 'LIKES',
                'properties': json.dumps({})
            })

        # Create Toy Node and Edge
        toy = row.get('FavoriteToy')
        if pd.notna(toy):
            if toy not in nodes_dict:
                nodes_dict[toy] = {
                    'entity_id': toy,
                    'entity_type': 'Toy',
                    'name': toy,
                    'properties': json.dumps({})
                }
            edges.append({
                'source_id': name,
                'target_id': toy,
                'relationship': 'OWNS',
                'properties': json.dumps({})
            })

        # Create Hobby Node and Edge
        hobby = row.get('Hobby')
        if pd.notna(hobby):
            if hobby not in nodes_dict:
                nodes_dict[hobby] = {
                    'entity_id': hobby,
                    'entity_type': 'Hobby',
                    'name': hobby,
                    'properties': json.dumps({})
                }
            edges.append({
                'source_id': name,
                'target_id': hobby,
                'relationship': 'DOES',
                'properties': json.dumps({})
            })

    return list(nodes_dict.values()), edges
