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

import google.auth
import google.cloud
import gradio as gr
import requests
import themes
from google import genai

from google.cloud import firestore
from google.genai import types

## Do one-time initialization things

## grab the project id from google auth
_, project = google.auth.default()
print(f"Project: {project}")

# Set initial values for model
llm_engine = "vllm"
host = "http://gemma-service:8000"
context_path = "/generate"

# initialize vertex for interacting with Gemini
client = genai.Client(
    vertexai=True,
    project=project,
    location="global",
)

# Initialize Firestore client
db = firestore.Client(database="chat-app-db")

# Send a request to Gemini via the VertexAI API. Return the model's response
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
    # TODO: Implement inference workflow

# Construct the request, send it to Gemma, return the model's response
# aggregated_message = current user message + history
def call_gemma_model(aggregated_message, model_temperature, top_p, max_tokens):
    # TODO: Implement call to gke-hosted gemma endpoint

# Send a request to Gemini via the VertexAI API. Return the model's response
# contents = list of types.Content objects
def call_gemini_model(contents, model_temperature, top_p, max_tokens):
    # TODO: Implement call to VertexAI-hosted Gemini endpoint

def process_message_gemini(message, history):
    # TODO: Implement structured message processing for Gemini
    pass

# This function takes a user's message and the conversation history as input.
#   Its job is to format these elements into a single,
#   structured prompt that can be understood by the language model (LLM).
#   This structured format helps the LLM maintain context and generate more relevant responses.
def process_message_gemma(message, history):
    # TODO: Implement processing of multi-turn chatbot conversation for input to LLM and for saving to history in Firestore.

# Function to save chat history to Firestore
def save_chat_history(interaction, doc_ref):
    timestamp_str = str(datetime.datetime.now())

    # Save the chat history, merging with existing data
    doc_ref.update({timestamp_str: interaction})

    print("Chat history saved successfully!")  # Optional: Log success

# Send the json message to the model and return the model's response. This is used for Gemma but not Gemini. It could also be used for other models.
def post_request(json_message):
    print("*** Request" + str(json_message), flush=True)
    # Set a timeout and check for HTTP errors. This will raise an exception on a bad status code (4xx or 5xx).
    response = requests.post(host + context_path, json=json_message, timeout=60)
    response.raise_for_status()
    json_data = response.json()
    print("*** Output: " + str(json_data), flush=True)
    return json_data

# custom css to hide default footer
css = """
footer {display: none !important;} .gradio-container {min-height: 0px !important;}
"""

# Add a dropdown to select the model to chat with
model_dropdown = gr.Dropdown(
    ["Gemma3 12b it", "Gemini"],
    label="Model",
    info="Select the model you would like to chat with.",
    value="Gemma3 12b it",
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
)

app.launch(server_name="0.0.0.0", allowed_paths=["images"])
