# Building a "Dev Signal" Agent: Part 3 - Adding Long-Term Memory

In parts 1 and 2, we built the Dev Signal agent and deployed it to the cloud. Now, we will make it truly "smart" by giving it **Long-Term Memory**.

Using **Vertex AI Agent Engine**, our agent will be able to remember user preferences, feedback, and past topics across different sessions.

## How it Works

1.  **Ingestion**: At the end of every turn, we use an `after_agent_callback` to save the session context into the long-term knowledge store.
2.  **Retrieval**: We give the agent the `LoadMemoryTool` so it can perform semantic searches over its past experiences.
3.  **Personalization**: We instruct the agent to check memory at the start of a task to tailor its behavior.

## Step 1: Configure the App Server

We need to tell our FastAPI app to use the **Agent Engine** for memory. Here is the full code for `fast_api_app.py` with the memory updates highlighted.

**File:** `dev_signal_agent/fast_api_app.py`
```python
import os
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as cloud_logging
from vertexai import agent_engines
from dev_signal_agent.app_utils.telemetry import setup_telemetry
from dev_signal_agent.app_utils.typing import Feedback
from dev_signal_agent.app_utils.env import init_environment

setup_telemetry()
PROJECT_ID, MODEL_LOC, SERVICE_LOC = init_environment()
logger = cloud_logging.Client().logger(__name__)

# --- Configuration & Sessions ---
AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUCKET = os.environ.get("LOGS_BUCKET_NAME")
USE_IN_MEMORY = os.environ.get("USE_IN_MEMORY_SESSION", "").lower() in ("true", "1")

def _get_agent_engine_uri():
    if USE_IN_MEMORY: return None, None
    name = os.environ.get("AGENT_ENGINE_SESSION_NAME", "dev_signal_agent")
    existing = list(agent_engines.list(filter=f"display_name={name}"))
    ae = existing[0] if existing else agent_engines.create(display_name=name)
    uri = f"agentengine://{ae.resource_name}"
    print(f"DEBUG: Connecting to Reasoning Engine: {uri} (display_name={name})")
    return uri, uri

SESSION_URI, MEMORY_URI = _get_agent_engine_uri()

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=f"gs://{BUCKET}" if BUCKET else None,
    allow_origins=os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None,
    session_service_uri=SESSION_URI,
    # <--- ADDED: Connect the memory service to the app
    memory_service_uri=MEMORY_URI, 
    otel_to_cloud=True,
)

@app.post("/feedback")
def collect_feedback(feedback: Feedback):
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Step 2: Equip the Agents

Now we update the core logic in `agent.py`. We add the `LoadMemoryTool`, define a callback to save memories, and update the instructions.

**File:** `dev_signal_agent/agent.py`
```python
import logging
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools import google_search, AgentTool, load_memory_tool, preload_memory_tool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from dev_signal_agent.app_utils.env import init_environment
from dev_signal_agent.tools.mcp_config import (
    get_reddit_mcp_toolset, 
    get_dk_mcp_toolset, 
    get_nano_banana_mcp_toolset
)

# --- 1. Infrastructure & Model Setup ---
PROJECT_ID, MODEL_LOC, SERVICE_LOC = init_environment()

shared_model = Gemini(
    model="gemini-3-flash-preview",
    vertexai=True,
    project=PROJECT_ID,
    location=MODEL_LOC,
    retry_options=types.HttpRetryOptions(attempts=3),
)

# <--- ADDED: Logic to persist sessions into memory
# This function runs automatically after every turn.
async def save_session_to_memory_callback(*args, **kwargs) -> None:
    """Defensive callback to persist session history."""
    ctx = kwargs.get("callback_context") or (args[0] if args else None)
    if ctx and hasattr(ctx, "_invocation_context") and ctx._invocation_context.memory_service:
        await ctx._invocation_context.memory_service.add_session_to_memory(ctx._invocation_context.session)

def add_info_to_state(tool_context: ToolContext, key: str, data: str) -> dict:
    tool_context.state[key] = data
    return {"status": "success", "message": f"Saved '{key}' to state."}

# ... (Toolsets definition) ...

# ... (Specialist Agents with LoadMemoryTool added to their tools list) ...

root_agent = Agent(
    name="root_orchestrator",
    model=shared_model,
    instruction="""
    You are a technical content strategist. You manage three specialists:
    ...
    Your responsibilities:
    - **MEMORY CHECK**: At the start of a conversation, use `load_memory` to check if the user has specific **areas of interest**, preferred topics, or past projects. Tailor your suggestions accordingly.
    - **CAPTURE PREFERENCES**: Actively listen for user preferences, interests, or project details. Explicitly acknowledge them to ensure they are captured in the session history for future personalization.
    ...
    """,
    # <--- ADDED: Memory tools and the Auto-Save callback
    tools=[load_memory_tool.LoadMemoryTool(), preload_memory_tool.PreloadMemoryTool()],
    after_agent_callback=save_session_to_memory_callback,
    sub_agents=[reddit_scanner, gcp_expert, blog_drafter]
)

app = App(root_agent=root_agent, name="dev_signal_agent")
```

## Step 3: Re-deploy

Push your changes to Cloud Run (Run this from the project root):
```bash
make docker-deploy
```

## Step 4: Verifying Long-Term Memory

To verify the memory integration locally without deploying every time, we've provided a test script: `test_memory_local.py`.

This script:
1.  Connects to the real **Vertex AI Agent Engine** in the cloud for memory storage.
2.  Uses an in-memory session service for local chat history (so you can wipe it easily).
3.  Runs a chat loop where you can talk to your agent.

**Running the Test:**

First, ensure you have your Application Default Credentials set up:
```bash
gcloud auth application-default login
```

Then run the script:
```bash
python test_memory_local.py
```

**Test Scenario:**

1.  **Teach (Session 1)**: Start the script. Tell the agent: "I want all my blog posts to be written in **rhyming verse** like a poem."
2.  **Reset**: Type `new` to simulate a completely fresh session. This wipes the local chat history, but the Cloud Memory persists.
3.  **Test (Session 2)**: Ask: "Write a blog post about Cloud Run."
4.  **Result**: The agent should retrieve the rhyme preference from the Cloud Memory and write your poem!

## Summary

You have implemented **Long-Term Managed Memory**! 

*   You used **Agent Engine** as a persistent knowledge store.
*   You automated memory ingestion using an **after-agent callback**.
*   You personalized the agent workflow so it adapts to you over time.