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
from processor.audio_processor import process_audio

def test_process_audio_returns_nodes_and_edges():
    # Arrange
    with patch('processor.audio_processor.genai.Client') as mock_client:
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "nodes": [{"entity_id": "Pixel", "entity_type": "Pet", "properties": {"trait": "talkative"}}],
            "edges": []
        })
        mock_client.return_value.models.generate_content.return_value = mock_response

        # Act
        nodes, edges = process_audio("gs://dummy/pixel_description.wav")

        # Assert
        assert len(nodes) == 1
        assert nodes[0]['entity_id'] == 'Pixel'
