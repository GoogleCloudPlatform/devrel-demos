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

import pytest
import json
from io import StringIO
from processor.csv_processor import process_csv

def test_process_csv_creates_pets_nodes():
    # Arrange
    csv_data = """Id,Name,Species,Breed,Nationality,Nicknames,Hobby,AdoptionStory,FavoriteFood,FavoriteToy
1,Yoda,cat,Faux Burmese,Argentinian,"Yodito, Yodote",Cuddles with mom,Found in internet ad,chicken,Mouse
"""
    mock_csv_file = StringIO(csv_data)

    # Act
    nodes, edges = process_csv(mock_csv_file)

    # Assert
    assert len(nodes) == 4

    # Find Yoda node
    yoda_node = next((n for n in nodes if n['entity_id'] == 'Yoda'), None)
    assert yoda_node is not None
    assert yoda_node['entity_type'] == 'Pet'

    properties = json.loads(yoda_node['properties'])
    assert properties['species'] == 'cat'
    assert properties['breed'] == 'Faux Burmese'

def test_process_csv_creates_relationships():
    # Arrange
    csv_data = """Id,Name,Species,Breed,Nationality,Nicknames,Hobby,AdoptionStory,FavoriteFood,FavoriteToy
1,Yoda,cat,Faux Burmese,Argentinian,"Yodito, Yodote",Cuddles with mom,Found in internet ad,chicken,Mouse
"""
    mock_csv_file = StringIO(csv_data)

    # Act
    nodes, edges = process_csv(mock_csv_file)

    # Assert
    # Yoda -> LIKES -> chicken
    # Yoda -> OWNS -> Mouse
    # Yoda -> DOES -> Cuddles with mom
    assert len(edges) == 3

    food_edge = next((e for e in edges if e['relationship'] == 'LIKES'), None)
    assert food_edge is not None
    assert food_edge['source_id'] == 'Yoda'
    assert food_edge['target_id'] == 'chicken'

    toy_edge = next((e for e in edges if e['relationship'] == 'OWNS'), None)
    assert toy_edge is not None
    assert toy_edge['source_id'] == 'Yoda'
    assert toy_edge['target_id'] == 'Mouse'

    hobby_edge = next((e for e in edges if e['relationship'] == 'DOES'), None)
    assert hobby_edge is not None
    assert hobby_edge['source_id'] == 'Yoda'
    assert hobby_edge['target_id'] == 'Cuddles with mom'
