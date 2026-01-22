import os
import random
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from dotenv import load_dotenv

# --- Agent Definition ---
import aida_v1.agent
import aida_v2.agent
import aida_v3.agent
import aida_v4.agent
import aida_v5.agent

# --- Global State ---
# This variable holds the currently active root agent instance.
root_agent = aida_v5.agent.root_agent

load_dotenv()
# --- End Agent Definition ---

# --- Services and Runner Setup ---
APP_NAME = "aida"

session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    print("AIDA AGENT (v4) READY.")
    yield
    print("--- AIDA SHUTDOWN SEQUENCE ---")


app = FastAPI(lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- Static assets ---
@app.get("/idle")
async def idle():
    return FileResponse("assets/idle.png")


@app.get("/blink")
async def blink():
    return FileResponse("assets/blink.png")


@app.get("/talk")
async def talk():
    return FileResponse("assets/talk.png")


@app.get("/think")
async def think():
    return FileResponse("assets/think.png")


@app.get("/think_blink")
async def think_blink():
    return FileResponse("assets/think_blink.png")


@app.get("/teehee")
async def teehee():
    return FileResponse("assets/teehee.png")


@app.get("/error")
async def error():
    return FileResponse("assets/error.png")


@app.get("/random_image")
async def random_image():
    images = os.listdir("assets")
    # Filter only png files in assets root
    images = [img for img in images if img.endswith(".png")]
    if not images:
        return FileResponse("assets/idle.png")
    random_img = random.choice(images)
    return FileResponse(f"assets/{random_img}")


# --- Web Interface (HTML) ---
@app.get("/", response_class=HTMLResponse)
async def get_chat_ui():
    """Serves the simple HTML chat interface."""
    return FileResponse("templates/index.html")


# --- API Endpoint for Chat Logic ---
def get_current_models_dict():
    """Helper to get the MODELS registry from the currently active agent module."""
    import sys
    # Find which aida_vX module the root_agent belongs to
    for module_name, module in sys.modules.items():
        if module_name.startswith("aida_v") and hasattr(module, "agent") and module.agent.root_agent == root_agent:
            return getattr(module.agent, "MODELS", {})
    return {}


def update_agent_model(agent, model):
    """Recursively update the model for an agent and all its sub-agents."""
    agent.model = model
    if hasattr(agent, "sub_agents") and agent.sub_agents:
        for sub in agent.sub_agents:
            update_agent_model(sub, model)


@app.get("/config/model")
async def get_model():
    current_model = root_agent.model
    model_id = "gemini3" # Default

    models_registry = get_current_models_dict()

    for mid, m_obj in models_registry.items():
        if m_obj == current_model:
            model_id = mid
            break
        if isinstance(current_model, str) and current_model == m_obj:
            model_id = mid
            break
        if hasattr(m_obj, "model_name") and hasattr(current_model, "model_name"):
            if m_obj.model_name == current_model.model_name:
                model_id = mid
                break

    return {"model_id": model_id}


@app.post("/config/model")
async def set_model(request: Request):
    body = await request.json()
    model_id = body.get("model_id")

    models_registry = get_current_models_dict()

    if model_id in models_registry:
        target_model = models_registry[model_id]
        # Update the entire tree
        update_agent_model(root_agent, target_model)
        print(f"SWITCHED ALL AGENTS TO MODEL: {target_model}")
    else:
        return {
            "error": f"Invalid model ID. Available: {', '.join(models_registry.keys())}"
        }

    return {"status": "ok", "current_model": str(root_agent.model)}


@app.get("/config/version")
async def get_version():
    """Helper to determine current version based on module name."""
    import sys
    for module_name, module in sys.modules.items():
        if module_name.startswith("aida_v") and hasattr(module, "agent") and module.agent.root_agent == root_agent:
            return {"version": module_name.split(".")[0].replace("aida_", "")}
    return {"version": "unknown"}


@app.post("/config/version")
async def set_version(request: Request):
    body = await request.json()
    version = body.get("version")

    global root_agent
    
    if version == "v1":
        root_agent = aida_v1.agent.root_agent
    elif version == "v2":
        root_agent = aida_v2.agent.root_agent
    elif version == "v3":
        root_agent = aida_v3.agent.root_agent
    elif version == "v4":
        root_agent = aida_v4.agent.root_agent
    elif version == "v5":
        root_agent = aida_v5.agent.root_agent
    else:
        return {"error": f"Invalid version: {version}"}

    # Update the runner with the new agent
    runner.agent = root_agent
    
    print(f"SWITCHED TO AGENT VERSION: {version}")
    return {"status": "ok", "current_version": version}


@app.get("/session/usage")
async def get_session_usage():
    user_id = "web_user"
    session_id = "web_session"
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "max_tokens": 1000000,
    }

    # Determine max tokens based on current model
    current_model = root_agent.model
    is_gemini = False
    if isinstance(current_model, str) and "gemini" in current_model:
        is_gemini = True
    elif hasattr(current_model, "model_name") and "gemini" in current_model.model_name:
        is_gemini = True
        
    if is_gemini:
        usage["max_tokens"] = 1000000
    else:
        usage["max_tokens"] = 32768 # Ollama/Local default

    if session and session.events:
        # Find the last event with usage metadata
        for event in reversed(session.events):
            if event.usage_metadata:
                meta = event.usage_metadata
                try:
                    usage["prompt_tokens"] = getattr(meta, "prompt_token_count", 0)
                    usage["completion_tokens"] = getattr(
                        meta, "candidates_token_count", 0
                    )
                    usage["total_tokens"] = getattr(meta, "total_token_count", 0)
                    break
                except Exception as e:
                    print(f"Error accessing usage metadata: {e}")

    return usage


@app.post("/session/clear")
async def clear_session():
    user_id = "web_user"
    session_id = "web_session"
    await session_service.delete_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    print(f"--- SESSION CLEARED: {session_id} ---")
    return {"status": "ok", "message": "Session history cleared."}


@app.post("/chat")
async def chat_handler(request: Request):
    """Handles the chat logic, streaming the agent's response."""
    body = await request.json()
    query = body.get("query")
    user_id = "web_user"
    session_id = "web_session"

    # Ensure a session exists
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session:
        print(f"DEBUG: Session State: {session.state}")
    
    if not session:
        import platform
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id,
            state={"app:host_os": platform.system().lower()}
        )
    elif "app:host_os" not in session.state:
        import platform
        # Use an event to update state correctly as per ADK docs
        from google.adk.events import Event, EventActions
        import time
        await session_service.append_event(session, Event(
            invocation_id="init_os",
            author="system",
            actions=EventActions(state_delta={"app:host_os": platform.system().lower()}),
            timestamp=time.time()
        ))

    async def stream_generator():
        """Streams JSON-formatted events for logs and text."""
        full_response = ""
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=Content(role="user", parts=[Part.from_text(text=query)]),
            ):
                # print(f"DEBUG EVENT: {event}") # Uncomment for deeper debugging

                # Handle Delegate events (SequentialAgent)
                if hasattr(event, "delegate") and event.delegate:
                     # Log the delegation
                    log_msg = f"DELEGATING TO: {event.delegate.target_agent}"
                    yield json.dumps({"type": "log", "content": log_msg}) + "\n"
                    yield json.dumps({"type": "task_switch", "task": event.delegate.target_agent.upper()}) + "\n"
                
                # Try to capture tool calls from the event
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Check for function calls
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            args_str = ", ".join(f"{k}='{v}'" for k, v in fc.args.items())
                            log_msg = f"EXECUTING: {fc.name}({args_str})"
                            yield json.dumps({"type": "log", "content": log_msg}) + "\n"
                        
                        # Check for function responses
                        if hasattr(part, "function_response") and part.function_response:
                            fr = part.function_response
                            if isinstance(fr.response, dict) and 'result' in fr.response:
                                output_str = str(fr.response['result'])
                            else:
                                output_str = str(fr.response)
                            
                            yield json.dumps({"type": "tool_output", "content": output_str}) + "\n"

                # Capture final text response
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            new_text = part.text
                            # For SequentialAgent, we might get multiple final responses from sub-agents
                            if new_text.startswith(full_response):
                                chunk = new_text[len(full_response) :]
                            else:
                                chunk = new_text 
                                full_response = "" # Reset if the text doesn't extend the previous
                            
                            if chunk:
                                # Determine if this is a "speaking" agent or a "thinking" agent
                                author = getattr(event, "author", "unknown")

                                # Only the root agent (aida) and the pipeline summarizer should "speak" (show in chat bubble)
                                # The reporter's output is now internal, consumed by AIDA for summarization.
                                speaking_agents = ["aida", "summarizer"]
                                
                                if author in speaking_agents:
                                    yield json.dumps({"type": "text", "content": chunk}) + "\n"
                                else:
                                    # Other agents (incident_commander, forensic_investigator) output is treated as internal text (debug/log)
                                    yield json.dumps({"type": "internal_text", "author": author, "content": chunk}) + "\n"
                                
                                full_response = new_text
        except Exception as e:
            print(f"ERROR during streaming: {e}")
            yield json.dumps({"type": "log", "content": f"ERROR: {str(e)}"}) + "\n"
            # Re-raise or handle gracefully? For now, let the client know something went wrong.

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


# To run this file:
# uv run python main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
