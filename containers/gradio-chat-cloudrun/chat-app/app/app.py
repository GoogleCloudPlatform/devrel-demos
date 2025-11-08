# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import logging
import os

import google.api_core.exceptions
import google.auth
import google.auth.transport.requests
import google.cloud
import google.oauth2.id_token
import gradio as gr
import requests
import themes
from google import genai

from google.cloud import firestore
from google.genai import types

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

## Do one-time initialization things

## grab the project id from google auth
_, project = google.auth.default()
logger.info(f"Project: {project}")

# initialize vertex for interacting with Gemini
client = genai.Client(
    vertexai=True,
    project=project,
    location="global",
)

# Initialize Firestore client
db = firestore.Client(database="chat-app-db")


# Construct the request, send it to Gemma, return the model's response
# aggregated_message = current user message + history
def call_gemma_model(
    aggregated_message, model_temperature, top_p, max_tokens, config
):
    json_message = {
        "model": config["model_name"],
        "prompt": aggregated_message,
        "stream": False,
        "options": {
            "temperature": model_temperature,
            "top_p": top_p,
            "num_predict": max_tokens,
            "stop": ["User's Turn:"],
        },
    }

    # Log what will be sent to the LLM
    logger.info(f"*** JSON request: {json_message}")

    # Send the constructed json with the user prompt to the model and put the model's response in the json_data variable
    json_data = post_request(json_message, config)

    # Ollama response format
    output = json_data.get("response", "")

    # The model sometimes continues the conversation and includes the next user's turn.
    # The 'stop' parameter is a good hint, but we parse the output as a safeguard.
    stop_marker = "User's Turn:"
    stop_pos = output.lower().find(stop_marker.lower())
    if stop_pos != -1:
        output = output[:stop_pos]

    return output.strip()


# Send a request to Gemini via the VertexAI API. Return the model's response
# contents = list of types.Content objects
def call_gemini_model(contents, model_temperature, top_p, max_tokens, config):
    response = client.models.generate_content(
        model=config["model_name"],
        contents=contents,
        config={
            "temperature": model_temperature,
            "max_output_tokens": max_tokens,
            "top_p": top_p,
        },
    )
    output = response.text  # Extract the generated text
    # Consider handling additional response attributes (safety, usage, etc.)
    return output


def process_message_gemini(message, history):
    contents = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])])
        )

    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=message)])
    )
    return contents


# This function takes a user's message and the conversation history as input.
#   Its job is to format these elements into a single,
#   structured prompt that can be understood by the language model (LLM).
#   This structured format helps the LLM maintain context and generate more relevant responses.
def process_message_gemma(message, history):
    user_prompt_format = "User's Turn:\n>>> {prompt}\n"
    assistant_prompt_format = "Assistant's Turn:\n>>> {prompt}\n"

    history_message = ""
    for turn in history:
        if turn["role"] == "user":
            history_message += user_prompt_format.format(prompt=turn["content"])
        else:
            history_message += assistant_prompt_format.format(prompt=turn["content"])

    # Format the new user message
    new_user_message = user_prompt_format.format(prompt=message)
    # Create a new aggregated message to be used as a single flat string in a json object sent to the LLM
    aggregated_message = (
        history_message + new_user_message + "Assistant's Turn:\n>>> "
    )
    return aggregated_message


# Function to save chat history to Firestore
def save_chat_history(interaction, doc_ref):
    # Use UTC timestamp in ISO 8601 format
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Save the chat history, merging with existing data
    doc_ref.update({timestamp_str: interaction})

    logger.info("Chat history saved successfully!")


# Send the json message to the model and return the model's response. This is used for Gemma but not Gemini. It could also be used for other models.
def post_request(json_message, config):
    logger.info(f"*** Request: {json_message}")

    host = config["host"]
    endpoint = config["endpoint"]

    headers = {}
    # If connecting to another Cloud Run service, we need to authenticate.
    if "run.app" in host:
        auth_req = google.auth.transport.requests.Request()
        id_token = google.oauth2.id_token.fetch_id_token(auth_req, host)
        headers["Authorization"] = f"Bearer {id_token}"

    url = f"{host.rstrip('/')}{endpoint}"
    logger.info(f"*** Posting to: {url}")

    # Set a timeout and check for HTTP errors. This will raise an exception on a bad status code (4xx or 5xx).
    response = requests.post(url, json=json_message, headers=headers, timeout=60)
    response.raise_for_status()
    json_data = response.json()
    logger.info(f"*** Output: {json_data}")
    return json_data


# Configuration for supported models
MODEL_CONFIG = {
    "Gemma": {
        "process_fn": process_message_gemma,
        "call_fn": call_gemma_model,
        "config": {
            "host": os.environ.get("GEMMA_HOST"),
            "endpoint": os.environ.get("GEMMA_ENDPOINT", "/api/generate"),
            "model_name": os.environ.get("GEMMA_MODEL", "gemma3:4b"),
        },
    },
    "Gemini": {
        "process_fn": process_message_gemini,
        "call_fn": call_gemini_model,
        "config": {
            "model_name": os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        },
    },
}

# Dynamically remove models if their required environment variables are missing
if not MODEL_CONFIG["Gemma"]["config"]["host"]:
    del MODEL_CONFIG["Gemma"]
    logger.warning("GEMMA_HOST not set. Gemma model will be unavailable.")


# This is the primary chat function. Every time a user sends a message, gradio calls this function,
# which sends the user's input to the appropriate AI (as indicated on the user interface), updates
# the chat history for future use during this session, and records the chat history in Firestore.
def inference_interface(
    message,
    history,
    model_name,
    model_temperature,
    top_p,
    max_tokens,
    request: gr.Request,
):

    # set history to empty array
    if history is None:
        history = []

    # Get or create a chronologically ordered session document ID
    session_hash = request.session_hash
    mapping_ref = db.collection("session_mappings").document(session_hash)
    mapping_doc = mapping_ref.get()

    if mapping_doc.exists:
        doc_id = mapping_doc.get("doc_id")
    else:
        # Create new chronological ID: session-YYYYMMDD-HHMMSS-hash
        # Use UTC for consistency
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        timestamp = now_utc.strftime("%Y%m%d-%H%M%S")
        doc_id = f"session-{timestamp}-{session_hash}"
        # Save the mapping so future messages in this session use the same ID
        mapping_ref.set({"doc_id": doc_id, "created_at": now_utc})

    doc_ref = db.collection("chat_sessions").document(doc_id)

    # Create the session document if it doesn't exist
    if not doc_ref.get().exists:
        doc_ref.set(
            {"Session start": datetime.datetime.now(datetime.timezone.utc)}
        )

    # Log info
    logger.info(f"Model: {model_name}")
    logger.info(f"* History: {history}")

    # Use the model configuration to process and call the appropriate model
    if model_name in MODEL_CONFIG:
        config = MODEL_CONFIG[model_name]
        try:
            # 1. Process the message history into the format the model expects
            processed_input = config["process_fn"](message, history)
            # 2. Call the model with the processed input and parameters
            output = config["call_fn"](
                processed_input,
                model_temperature,
                top_p,
                max_tokens,
                config["config"],
            )
        except (
            requests.exceptions.RequestException,
            google.api_core.exceptions.GoogleAPICallError,
        ) as e:
            logger.error(f"Error calling {model_name}: {e}", exc_info=True)
            output = f"An error occurred while communicating with {model_name}."
        except Exception as e:
            # Keep a generic catch-all for other unexpected errors (e.g., bugs in process_fn)
            # to prevent crashing the Gradio worker entirely, but log it as an error.
            logger.error(f"Unexpected error in {model_name} inference: {e}", exc_info=True)
            output = "An unexpected error occurred."
    else:
        # Handle the case where no valid model is selected
        output = "Error: Invalid model selected."

    interaction = {"user": message, model_name: output}

    # Log the updated chat history
    logger.info(f"* History: {history} {interaction}")

    # Save the updated history to Firestore
    save_chat_history(interaction, doc_ref)

    return output


# custom css to hide default footer
css = """
footer {display: none !important;} .gradio-container {min-height: 0px !important;}
"""

# Determine available models and default
model_choices = list(MODEL_CONFIG.keys())
default_model = "Gemma" if "Gemma" in model_choices else model_choices[0]

# Add a dropdown to select the model to chat with
model_dropdown = gr.Dropdown(
    choices=model_choices,
    label="Model",
    info="Select the model you would like to chat with.",
    value=default_model,
)

# Make the model temperature, top_p, and max tokents modifiable via sliders in the GUI
model_temperature = gr.Slider(
    minimum=0.1, maximum=1.0, value=0.9, label="Temperature", render=False
)
top_p = gr.Slider(minimum=0.1, maximum=1.0, value=0.95, label="Top_p", render=False)
max_tokens = gr.Slider(
    minimum=1, maximum=4096, value=1024, label="Max Tokens", render=False
)

# Call gradio to create the chat interface
app = gr.ChatInterface(
    inference_interface,
    additional_inputs=[model_dropdown, model_temperature, top_p, max_tokens],
    theme=themes.google_theme(),
    css=css,
    title="Chat with AI",
    type="messages",
)

server_port = int(os.environ.get("PORT", 7860))
app.launch(server_name="0.0.0.0", server_port=server_port, allowed_paths=["images"])