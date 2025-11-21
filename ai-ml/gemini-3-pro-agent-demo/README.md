ADK Agent with Google Search & Gemini 3

This project demonstrates how to build and run an AI agent using the Google Agent Development Kit (ADK), powered by the Gemini 3 model and equipped with the Google Search Tool.

Prerequisites

1. uv (An extremely fast Python package installer and resolver)

2. A [Google Cloud Project](https://developers.google.com/workspace/guides/create-project?utm_campaign=CDR_0xf9030db1_default_b462529980&utm_medium=external&utm_source=blog) with the Gemini API enabled

3. A valid [GOOGLE_API_KEY](https://aistudio.google.com)

Getting Started

Follow these steps to set up your environment, create the agent, and run the web interface.

1. Initialize the Project

Initialize a new Python project using uv:

`uv init`


2. Install Dependencies

Add the necessary Google libraries for ADK and GenAI:

`uv add google-adk`
`uv add google-genai`


3. Configure Environment

Set your Google API key as an environment variable. Replace "YOUR_API_KEY" with your key.

`export GOOGLE_API_KEY="YOUR_API_KEY"`


4. Activate Virtual Environment

Activate the virtual environment created by uv:

`source .venv/bin/activate`


5. Create the Agent

Use the ADK CLI to generate a new agent scaffold named my_Agent:

`adk create my_Agent`


Note during creation: When prompted, ensure you select Gemini 3 as the model for the root agent to leverage the latest capabilities.

6. Run the Agent

You can run the agent in the terminal to test basic functionality:

`adk run my_agent`


7. Launch Web Interface

To interact with your agent via a web UI, start the web server on port 8000:

`adk web --port 8000`


Open your browser and navigate to http://localhost:8000 to chat with your agent.