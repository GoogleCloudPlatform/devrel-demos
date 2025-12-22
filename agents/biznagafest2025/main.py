import os
import asyncio
import random
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from dotenv import load_dotenv
import vertexai
# from PIL import Image

# --- Agent Definition ---
from v4.agent import root_agent

load_dotenv()

# Initialize Vertex AI
project_id = os.getenv("PROJECT_ID")
location = os.getenv("LOCATION")
vertexai.init(project=project_id, location=location)
# --- End Agent Definition ---


# --- Services and Runner Setup ---
session_service = InMemorySessionService()
runner = Runner(
    app_name="agents", agent=root_agent, session_service=session_service
)
app = FastAPI()

# --- Static assets ---
@app.get("/idle")
async def idle():
    return FileResponse("assets/idle.png")

@app.get("/talk")
async def talk():
    return FileResponse("assets/talk.png")

@app.get("/think")
async def think():
    return FileResponse("assets/think.png")

@app.get("/random_image")
async def random_image():
    images = os.listdir("assets")
    random_image = random.choice(images)
    return FileResponse(f"assets/{random_image}")


# --- Web Interface (HTML) ---
@app.get("/", response_class=HTMLResponse)
async def get_chat_ui():
    """Serves the simple HTML chat interface."""
    return r"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Emergency Diagnostic Agent</title>
        <style>
            body { 
                font-family: 'Courier New', Courier, monospace; 
                background-color: #1e1e1e;
                color: #d4d4d4;
                display: flex; 
                justify-content: center; 
                align-items: flex-start;
                padding-top: 50px;
            }
            #main-container {
                display: flex;
                gap: 20px;
            }
            #chat-container { 
                width: 600px; 
                border: 2px solid #888; 
                padding: 20px; 
                background-color: #2d2d2d;
                box-shadow: 0 0 10px rgba(0,0,0,0.5);
            }
            #header {
                text-align: center;
                font-size: 24px;
                margin-bottom: 20px;
                color: #0f0;
                text-shadow: 0 0 5px #0f0;
            }
            #messages { 
                height: 400px; 
                overflow-y: scroll; 
                border: 1px solid #444; 
                padding: 10px; 
                margin-bottom: 10px; 
                background-color: #111;
            }
            #user-input { display: flex; }
            #user-input input { 
                flex-grow: 1; 
                padding: 8px; 
                background-color: #333;
                border: 1px solid #555;
                color: #d4d4d4;
            }
            #user-input button { 
                padding: 8px 12px; 
                background-color: #0a0;
                color: #fff;
                border: none;
                cursor: pointer;
            }
            .user-message { text-align: right; color: #0ff; }
            .agent-message { color: #0f0; }
            #avatar-container {
                width: 200px;
                text-align: center;
            }
            #avatar-window {
                width: 150px;
                height: 150px;
                border: 2px solid #888;
                background-color: #111;
                margin: 0 auto 10px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            #avatar-window img {
                max-width: 100%;
                max-height: 100%;
            }
            #avatar-label {
                color: #0f0;
                text-shadow: 0 0 5px #0f0;
            }
        </style>
    </head>
    <body>
        <div id="main-container">
            <div id="chat-container">
                <div id="header">-- EMERGENCY DIAGNOSTIC AGENT --</div>
                <div id="messages"></div>
                <form id="user-input" onsubmit="sendMessage(event)">
                    <input type="text" id="message-text" autocomplete="off" placeholder="> Type your command..."/>
                    <button type="submit">SEND</button>
                </form>
            </div>
            <div id="avatar-container">
                <div id="avatar-window">
                    <img src="/idle" alt="Agent Avatar" id="avatar-img">
                </div>
                <div id="avatar-label">AIDA</div>
            </div>
        </div>
        <script>
            const messagesDiv = document.getElementById('messages');
            const messageText = document.getElementById('message-text');
            const avatarImg = document.getElementById('avatar-img');

            async function sendMessage(event) {
                event.preventDefault();
                const query = messageText.value;
                if (!query) return;

                // Display user message
                const userMsgDiv = document.createElement('div');
                userMsgDiv.className = 'user-message';
                userMsgDiv.textContent = `USER: ${query}`;
                messagesDiv.appendChild(userMsgDiv);
                messageText.value = '';

                // Create a container for the agent's response
                const agentMsgDiv = document.createElement('div');
                agentMsgDiv.className = 'agent-message';
                agentMsgDiv.textContent = 'AIDA: ';
                messagesDiv.appendChild(agentMsgDiv);

                avatarImg.src = '/think'; // Set to thinking pose

                // Stream agent response
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let wordQueue = [];
                let isStreaming = true;

                // Asynchronously read from the stream and populate the word queue
                (async () => {
                    while (true) {
                        const { value, done } = await reader.read();
                        if (done) {
                            isStreaming = false;
                            break;
                        }
                        const chunk = decoder.decode(value, { stream: true });
                        wordQueue.push(...chunk.split(/(\s+)/));
                    }
                })();

                let animationInterval = null;

                function startAnimation() {
                    if (animationInterval) return; // Animation is already running
                    let toggle = false;
                    avatarImg.src = '/talk';
                    animationInterval = setInterval(() => {
                        toggle = !toggle;
                        avatarImg.src = toggle ? '/talk' : '/idle';
                    }, 200); // Faster animation speed
                }

                function stopAnimation() {
                    clearInterval(animationInterval);
                    animationInterval = null;
                    avatarImg.src = '/idle';
                }

                function render() {
                    if (wordQueue.length > 0) {
                        startAnimation(); // Start or continue animation
                        
                        const word = wordQueue.shift();
                        agentMsgDiv.textContent += word;
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                        
                        setTimeout(render, 50); // Faster typing speed
                    } else if (isStreaming) {
                        // Word queue is empty, but more words might be coming.
                        // Do nothing to the animation, let it stay in 'thinking' mode.
                        setTimeout(render, 100);
                    } else {
                        // No more words and the stream is done
                        stopAnimation(); // Ensure animation is stopped
                    }
                }

                render(); // Start the rendering loop
            }
        </script>
    </body>
    </html>
    """


# --- API Endpoint for Chat Logic ---
@app.post("/chat")
async def chat_handler(request: Request):
    """Handles the chat logic, streaming the agent's response."""
    body = await request.json()
    query = body.get("query")
    user_id = "web_user"
    session_id = "web_session" # In a real app, you'd manage sessions per user

    # Ensure a session exists
    session = await session_service.get_session(app_name="agents", user_id=user_id, session_id=session_id)
    if not session:
        session = await session_service.create_session(app_name="agents", user_id=user_id, session_id=session_id)

    async def stream_generator():
        """Streams the agent's final text response chunks."""
        full_response = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=Content(role="user", parts=[Part.from_text(text=query)]),
        ):
            if event.is_final_response() and event.content and event.content.parts[0].text:
                new_text = event.content.parts[0].text
                # Yield only the new part of the text
                yield new_text[len(full_response):]
                full_response = new_text

    return StreamingResponse(stream_generator(), media_type="text/plain")

# To run this file:
# 1. Make sure you have fastapi and uvicorn installed: pip install fastapi uvicorn
# 2. Save the code as main.py
# 3. Run from your terminal: uvicorn main:app --reload
# 4. Open your browser to http://127.0.0.1:8000