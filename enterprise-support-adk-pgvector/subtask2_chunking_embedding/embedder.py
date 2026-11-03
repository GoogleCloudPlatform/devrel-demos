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
