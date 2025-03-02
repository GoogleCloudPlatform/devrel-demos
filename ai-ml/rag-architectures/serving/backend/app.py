import os
from typing import List, Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google import genai
from google.genai.types import HttpOptions
from google.genai.types import EmbedContentConfig


from google.cloud import aiplatform
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Quantum Chatbot Backend")

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
        # GCP Project settings
        self.project_id = os.environ.get("PROJECT_ID")
        self.location = os.environ.get("GCP_REGION", "us-central1")

        logger.info(
            f"Initializing with project_id: {self.project_id}, location: {self.location}"
        )

        # Vertex AI Vector Search settings
        self.index_endpoint_id = os.environ.get("VECTOR_SEARCH_INDEX_ENDPOINT_NAME")
        self.index_id = os.environ.get("VECTOR_SEARCH_INDEX_ID")
        self.deployed_index_id = os.environ.get("VECTOR_SEARCH_DEPLOYED_INDEX_ID")

        logger.info(
            f"Vector Search settings - endpoint: {self.index_endpoint_id}, index: {self.index_id}, deployed: {self.deployed_index_id}"
        )

        # Gemini API settings
        self.model_name = os.environ.get("GEMINI_MODEL_NAME", "gemini-flash-2.0")
        self.embedding_model = os.environ.get("EMBEDDING_MODEL", "text-embedding-005")

        # RAG settings
        self.num_neighbors = int(os.environ.get("NUM_NEIGHBORS", "5"))
        self.max_context_length = int(os.environ.get("MAX_CONTEXT_LENGTH", "8000"))

        # Initialize clients
        self.initialize_clients()

    def initialize_clients(self):
        """Initialize Google Cloud clients"""
        try:
            # Initialize Vertex AI for Vector Search
            aiplatform.init(project=self.project_id, location=self.location)

            # Initialize Vector Search Index and Endpoint
            self.index = aiplatform.MatchingEngineIndex(self.index_id)
            logger.info(f"Successfully initialized index: {self.index_id}")

            self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
                index_endpoint_name=self.index_endpoint_id
            )
            logger.info(
                f"Successfully initialized index endpoint: {self.index_endpoint_id}"
            )

            # Initialize Vertex AI for Gemini
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
            os.environ["GOOGLE_CLOUD_LOCATION"] = self.location
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

            self.genai_client = genai.Client()
            logger.info("Successfully initialized Gemini client")

        except Exception as e:
            logger.error(f"Error initializing clients: {str(e)}")
            raise


# Global config instance
def get_config():
    return app.state.config


# Request/Response models
class PromptRequest(BaseModel):
    prompt: str
    num_neighbors: Optional[int] = None
    use_context: Optional[bool] = True


class PromptResponse(BaseModel):
    response: str
    context_used: bool
    neighbors_found: int


@app.on_event("startup")
async def startup_event():
    """Initialize app state on startup"""
    logger.info("Initializing app state...")
    try:
        app.state.config = AppConfig()
        logger.info("App state initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize app state: {str(e)}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Quantum Chatbot Backend"}


@app.post("/prompt", response_model=PromptResponse)
async def process_prompt(
    request: PromptRequest, config: AppConfig = Depends(get_config)
):
    """
    Process a user prompt through the RAG pipeline:
    1. Retrieve context from Vector Search
    2. Augment the prompt with retrieved context
    3. Generate a response using Gemini 2.0 Flash
    """
    try:
        logger.info(f"Processing prompt: {request.prompt[:50]}...")

        # Determine number of neighbors to retrieve
        num_neighbors = request.num_neighbors or config.num_neighbors

        # 1. Retrieve context from Vector Search, 2. Augment prompt with context
        if request.use_context:
            logger.info("✅ Use Context was True - Retrieving context")
            neighbors = prompt_vector_search(request.prompt, num_neighbors, config)

            # 2. Augment prompt with context
            augmented_prompt = create_augmented_prompt(request.prompt, neighbors)
        else:
            logger.info("❌ Use Context was False - Skipping context retrieval")
            augmented_prompt = request.prompt
            neighbors = []

        # 3. Generate response with Gemini
        response = prompt_gemini(augmented_prompt, config)
        logger.info("Generated response from Gemini")

        return PromptResponse(
            response=response,
            context_used=len(neighbors) > 0,
            neighbors_found=len(neighbors),
        )

    except Exception as e:
        logger.error(f"Error processing prompt: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error processing prompt: {str(e)}"
        )


def extract_id_and_text(neighbor):
    """
    Extract ID and text from a Vertex AI Vector Search "MatchNeighbor" object
    """
    id_value = neighbor.id
    text_value = None
    if hasattr(neighbor, "restricts") and neighbor.restricts:
        for restrict in neighbor.restricts:
            if hasattr(restrict, "name") and restrict.name == "text":
                if hasattr(restrict, "allow_tokens") and restrict.allow_tokens:
                    text_value = restrict.allow_tokens[0]
                    break

    return {"id": id_value, "text": text_value}


def prompt_vector_search(
    prompt: str, num_neighbors: int, config: AppConfig
) -> List[Dict[str, Any]]:
    """Prompt Vector Search to find relevant documents"""
    try:
        logger.info("Creating embeddings for query")
        # Convert prompt to embeddings
        response = config.genai_client.models.embed_content(
            model=config.embedding_model,
            contents=[prompt],
            config=EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )
        query_embedding = response.embeddings[0].values
        logger.info("Query embeddings: " + str(query_embedding[:10]) + "...")

        # Get nearest neighbors from Vector Search
        logger.info(
            f"❓ Querying Vector Search with deployed_index_id: {config.deployed_index_id}"
        )
        neighbors = config.index_endpoint.find_neighbors(
            deployed_index_id=config.deployed_index_id,
            queries=[query_embedding],
            num_neighbors=num_neighbors,
            return_full_datapoint=True,  # Make sure this is True
        )

        logger.info(f"Vector Search returned {len(neighbors[0])} matches")
        return neighbors[0]
    except Exception as e:
        logger.error(f"Error querying Vector Search: {str(e)}")
        raise


def extract_id_and_text(neighbor):
    """
    Extract ID and text from a Vertex AI Vector Search "MatchNeighbor" object
    """
    id_value = neighbor.id
    text_value = None
    if hasattr(neighbor, "restricts") and neighbor.restricts:
        for restrict in neighbor.restricts:
            if hasattr(restrict, "name") and restrict.name == "text":
                if hasattr(restrict, "allow_tokens") and restrict.allow_tokens:
                    text_value = restrict.allow_tokens[0]
                    break

    return {"id": id_value, "text": text_value}


def create_augmented_prompt(prompt: str, neighbors: list) -> str:
    """Create a prompt augmented with retrieved context"""
    if not neighbors or len(neighbors) == 0:
        return prompt

    print("Got # neighbors: " + str(len(neighbors)))
    augment = []
    for n in neighbors:
        result = extract_id_and_text(n)
        print(f"ID: {result['id']}")
        print(f"Text: {result['text']}")
        augment.append(result["text"])
    context = "\n".join(augment)

    final_prompt = f"""You are an expert chatbot in quantum computing. Use the provided up-to-date information to answer the user's question. Only respond on topics related to quantum computing. Answer in 3 sentences or less!  

    Context:
    {context}

    User Prompt: {prompt}
    """
    print("⭐ Augmented Prompt: ", final_prompt)
    return final_prompt


def prompt_gemini(prompt: str, config: AppConfig) -> str:
    """Prompt Gemini model with the augmented prompt
    https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-v2#google-gen
    """
    try:
        logger.info(f"Calling Gemini with model: {config.model_name}")
        client = genai.Client(http_options=HttpOptions(api_version="v1"))
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",  # Using hardcoded model name for consistency
            contents=[prompt],
        )
        return response.text
    except Exception as e:
        logger.error(f"Error prompting Gemini: {str(e)}")
        raise


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
