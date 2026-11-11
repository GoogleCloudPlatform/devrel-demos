# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Vectorization using Vertex AI text-embedding-005.
"""

from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

class VertexVectorService:
    def __init__(self, project_id: str, location: str = "us-central1"):
        # TODO(production): For production, connect over Private Service Connect instead of a public endpoint.
        # Verify that calls to aiplatform.googleapis.com resolve via Private Google Access
        # or a dedicated Private Service Connect (PSC) forwarder rule to stay inside the VPC.
        aiplatform.init(project=project_id, location=location)
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-005")

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generates dense 768-dimensional embeddings in batches.
        """
        embeddings = self.model.get_embeddings(texts)
        return [e.values for e in embeddings]
