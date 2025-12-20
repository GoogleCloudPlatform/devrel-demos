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
from google.adk.models.lite_llm import LiteLlm
from dotenv import load_dotenv
# from PIL import Image

# --- Agent Definition ---
from aida.agent import root_agent

load_dotenv()
# --- End Agent Definition ---

# --- Services and Runner Setup ---
APP_NAME = "aida"

session_service = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=session_service)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events."""
    print("AIDA AGENT READY.")
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
    random_image = random.choice(images)
    return FileResponse(f"assets/{random_image}")


# --- Web Interface (HTML) ---
@app.get("/", response_class=HTMLResponse)
async def get_chat_ui():
    """Serves the simple HTML chat interface."""
    return FileResponse("templates/index.html")


# --- API Endpoint for Chat Logic ---
@app.get("/config/model")
async def get_model():
    current_model = root_agent.model
    model_id = "gemini" # Default
    
    print(f"DEBUG: get_model current_model type: {type(current_model)}, value: {current_model}")
    if hasattr(current_model, "model_name"):
         print(f"DEBUG: current_model.model_name: {current_model.model_name}")

    if isinstance(current_model, str):
        if "gemini" in current_model:
            model_id = "gemini"
    elif hasattr(current_model, "model_name"):
        if "gemini" in current_model.model_name:
             model_id = "gemini"
        elif "qwen" in current_model.model_name:
            model_id = "qwen"
        elif "gpt-oss" in current_model.model_name:
            model_id = "gpt-oss"
            
    return {"model_id": model_id}


@app.post("/config/model")
async def set_model(request: Request):
    body = await request.json()
    model_id = body.get("model_id")

    if model_id == "gemini":
        root_agent.model = "gemini-2.5-flash"
    elif model_id == "qwen":
        root_agent.model = LiteLlm(model="ollama_chat/qwen2.5")
    elif model_id == "gptoss" or model_id == "gpt-oss":
        root_agent.model = LiteLlm(model="ollama_chat/gpt-oss")
    else:
        return {"error": "Invalid model ID. Use 'gemini', 'qwen' or 'gpt-oss'."}

    print(f"--- MODEL SWITCHED TO: {root_agent.model} ---")
    return {"status": "ok", "current_model": str(root_agent.model)}


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
        # Assume it's LiteLlm/Ollama Qwen 2.5 or GPT-OSS
        usage["max_tokens"] = 32768

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

    print(f"Processing request with model: {root_agent.model}")

    # Ensure a session exists
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if not session:
        session = await session_service.create_session(
            app_name=APP_NAME, user_id=user_id, session_id=session_id
        )

    async def stream_generator():
        """Streams JSON-formatted events for logs and text."""
        full_response = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=Content(role="user", parts=[Part.from_text(text=query)]),
        ):
            # Try to capture tool calls from the event
            if event.content and event.content.parts:
                for part in event.content.parts:
                    # Check for function calls (standard Gemini/Gemma structure)
                    if hasattr(part, "function_call") and part.function_call:
                        fc = part.function_call
                        # Format args nicely
                        args_str = ", ".join(f"{k}='{v}'" for k, v in fc.args.items())
                        log_msg = f"EXECUTING: {fc.name}({args_str})"
                        yield json.dumps({"type": "log", "content": log_msg}) + "\n"
                    
                    # Check for function responses (tool output)
                    if hasattr(part, "function_response") and part.function_response:
                        fr = part.function_response
                        # Extract result if possible, otherwise use whole response
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
                        chunk = new_text[len(full_response) :]
                        if chunk:
                            yield json.dumps({"type": "text", "content": chunk}) + "\n"
                            full_response = new_text

    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")


# To run this file:
# 1. Make sure you have fastapi and uvicorn installed: pip install fastapi uvicorn
# 2. Save the code as main.py
# 3. Run from your terminal: uvicorn main:app --reload
# 4. Open your browser to http://127.0.0.1:8000
