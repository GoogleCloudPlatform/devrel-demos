import os
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import google.cloud.aiplatform as aiplatform
from google.cloud.aiplatform.matching_engine import MatchingEngineIndexEndpoint
import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession, Content

# Initialize FastAPI app
app = FastAPI(title="RAG App Serving Backend with FastAPI")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Configuration model
class AppConfig:
    def __init__(self):
        # Google Cloud project settings
        self.project_id = os.environ.get("GCP_PROJECT_ID")
        self.location = os.environ.get("GCP_LOCATION", "us-central1")

        # Vector Search settings
        self.index_endpoint_id = os.environ.get("VECTOR_SEARCH_ENDPOINT_ID")
        self.index_id = os.environ.get("VECTOR_SEARCH_INDEX_ID")
        self.deployed_index_id = os.environ.get("VECTOR_SEARCH_DEPLOYED_INDEX_ID")

        # Gemini settings
        self.model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-flash-2.0")

        # RAG settings
        self.num_neighbors = int(os.environ.get("NUM_NEIGHBORS", "5"))
        self.max_context_length = int(os.environ.get("MAX_CONTEXT_LENGTH", "8000"))

        # Initialize clients
        self.initialize_clients()

    def initialize_clients(self):
        """Initialize Google Cloud clients"""
        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        vertexai.init(project=self.project_id, location=self.location)

        # Initialize Vector Search endpoint
        self.index_endpoint = MatchingEngineIndexEndpoint(
            index_endpoint_name=self.index_endpoint_id
        )

        # Initialize Gemini model
        self.gemini_model = GenerativeModel(self.model_name)


# Global config instance
def get_config():
    return app.state.config


# Request/Response models
class QueryRequest(BaseModel):
    query: str
    num_neighbors: Optional[int] = None


class QueryResponse(BaseModel):
    response: str
    context_used: bool
    neighbors_found: int


@app.on_event("startup")
async def startup_event():
    """Initialize app state on startup"""
    app.state.config = AppConfig()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "RAG API"}


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest, config: AppConfig = Depends(get_config)):
    """
    Process a user query through the RAG pipeline:
    1. Retrieve context from Vector Search
    2. Augment the query with retrieved context
    3. Generate a response using Gemini
    """
    try:
        # Determine number of neighbors to retrieve
        num_neighbors = request.num_neighbors or config.num_neighbors

        # 1. Retrieve context from Vector Search
        neighbors = query_vector_search(request.query, num_neighbors, config)

        # 2. Augment query with context
        context = extract_context_from_neighbors(neighbors)
        augmented_prompt = create_augmented_prompt(request.query, context)

        # 3. Generate response with Gemini
        response = query_gemini(augmented_prompt, config)

        return QueryResponse(
            response=response,
            context_used=len(neighbors) > 0,
            neighbors_found=len(neighbors),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


def query_vector_search(
    query: str, num_neighbors: int, config: AppConfig
) -> List[Dict[str, Any]]:
    """Query Vector Search to find relevant documents"""
    try:
        # Get nearest neighbors from Vector Search
        response = config.index_endpoint.match(
            deployed_index_id=config.deployed_index_id,
            queries=[query],
            num_neighbors=num_neighbors,
        )

        # Extract neighbor data
        neighbors = []
        for match in response[0]:
            # Only include the 'text' field from the neighbor data
            if hasattr(match, "neighbor") and hasattr(match.neighbor, "restricts"):
                for restrict in match.neighbor.restricts:
                    if restrict.namespace == "allow" and restrict.string_val == "text":
                        neighbors.append(
                            {
                                "id": match.neighbor.corpus_document_id,
                                "distance": match.distance,
                                "text": restrict.string_val,
                            }
                        )

        return neighbors

    except Exception as e:
        print(f"Error querying Vector Search: {str(e)}")
        return []


def extract_context_from_neighbors(neighbors: List[Dict[str, Any]]) -> str:
    """Extract and format context from retrieved neighbors"""
    if not neighbors:
        return ""

    context_pieces = []
    for idx, neighbor in enumerate(neighbors):
        if "text" in neighbor:
            context_pieces.append(f"Document {idx+1}:\n{neighbor['text']}")

    return "\n\n".join(context_pieces)


def create_augmented_prompt(query: str, context: str) -> str:
    """Create a prompt augmented with retrieved context"""
    if not context:
        return query

    return f"""Answer the following query based on the provided context. If the context doesn't contain relevant information, respond based on your knowledge but clearly indicate when you're doing so.

Context:
{context}

Query: {query}
"""


def query_gemini(prompt: str, config: AppConfig) -> str:
    """Query Gemini model with the augmented prompt"""
    try:
        # Create a chat session
        chat = config.gemini_model.start_chat()

        # Send the prompt and get a response
        response = chat.send_message(prompt)

        return response.text
    except Exception as e:
        print(f"Error querying Gemini: {str(e)}")
        raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
