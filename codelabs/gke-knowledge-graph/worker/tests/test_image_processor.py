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

from unittest.mock import patch, MagicMock
import json
from processor.image_processor import process_image

def test_process_image_returns_nodes_and_edges():
    # Arrange
    with patch('processor.image_processor.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "nodes": [{"entity_id": "Joel", "entity_type": "Pet", "properties": {"color": "tabby"}}],
            "edges": []
        })
        mock_client.return_value.models.generate_content.return_value = mock_response

        # Act
        nodes, edges = process_image("gs://dummy/Joel_Flowers.jpg")

        # Assert
        assert len(nodes) == 1
        assert nodes[0]['entity_id'] == 'Joel'
        assert nodes[0]['entity_type'] == 'Pet'
