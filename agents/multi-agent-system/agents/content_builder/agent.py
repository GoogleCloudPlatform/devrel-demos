import os
import litellm
import google.auth.transport.requests
from google.oauth2 import id_token
from google.adk.agents import Agent
from google.adk.models import LiteLlm

# 1. Fetch the token
target_url = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
auth_req = google.auth.transport.requests.Request()
token = id_token.fetch_id_token(auth_req, target_url)

# 2. Inject the token securely into LiteLLM's environment state
# LiteLLM's 'ollama_chat' provider will automatically discover this and 
# inject 'Authorization: Bearer <token>' for every request!
os.environ["OLLAMA_API_KEY"] = token

# 4. Instantiate the model 
# (Note: We use 'ollama/gemma3:270m' to align with ADK's expected prefix)
gemma_model_name = os.environ.get("GEMMA_MODEL_NAME", "gemma3:270m")
model = LiteLlm(
    model=f"ollama_chat/{gemma_model_name}", 
    api_base=target_url
)

# 5. Define the Agent
content_builder = Agent(
    name="content_builder",
    model=model,
    description="Transforms research findings into a structured course.",
    instruction="""
    You are an expert course creator.
    Take the approved 'research_findings' and transform them into a well-structured, engaging course module.

    **Formatting Rules:**
    1. Start with a main title using a single `#` (H1).
    2. Use `##` (H2) for main section headings. These will be used for the Table of Contents.
    3. Use `###` (H3) for sub-sections within main sections.
    4. Use bullet points and clear paragraphs.
    5. Maintain a professional but engaging tone.

    **Structure Requirements:**
    - Begin with a brief Introduction section explaining what the learner will gain.
    - Organize content into 3-5 main sections with clear headings.
    - Include Key Takeaways at the end as a bulleted summary.
    - Keep each section focused and concise.

    Ensure the content directly addresses the user's original request.
    Do not include any preamble or explanation outside the course content itself.
    """,
)

root_agent = content_builder
