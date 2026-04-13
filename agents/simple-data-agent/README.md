# Gemma 4 Data Agent

This agent demonstrates how to create a data agent using [Agent Development Kit (ADK)](https://adk.dev/) and [Google Gemma 4](https://ai.google.dev/gemma) open model. The agent can answer questions about data in BigQuery.

It features a custom web client with:
- **Real-time streaming** of thoughts and responses using SSE.
- **Syntax highlighting** for code blocks and JSON.
- **Robust auto-scrolling** behavior.

## How to run

1. Deploy a Google Gemma 4 31B-it endpoint in Cloud Run as described in [Run inference of Gemma 4 model on Cloud Run with RTX 6000 Pro GPU with vLLM](https://codelabs.developers.google.com/codelabs/cloud-run/cloud-run-gpu-rtx-pro-6000-gemma4-vllm).

2. Create a Python virtual environment and install Google ADK:

    ```bash
    uv pip install google-adk[extensions]
    ```

3. Install node.js and npm.

    You can install them via uv as well:

    ```bash
    uv pip install nodejs-wheel
    ```

4. Copy `.env.sample` as `.env`, and specify configuration values:
    * `API_BASE` – the URL of the deployed Cloud Run service with Gemma 4 vLLM server running.
    * `MODEL_NAME` – the model name, which is `google/gemma-4-31b-it`.
    * `GOOGLE_CLOUD_PROJECT` – the Google Cloud project ID. This is necessary to run BigQuery tools.
    * `SERVER_BASE_URL` – (Optional) The URL of the ADK API server for the web client to proxy to (defaults to `http://localhost:8000`).
    * `AGENT_NAME` – (Optional) The name of the agent to use. If not set, the server will auto-detect it from the available agents.

5. Run the application using the provided script:

    ```bash
    ./run.sh
    ```

    This script will start both the ADK API server (port 8000) and the custom web client (port 8080).

6. Open your browser and navigate to `http://localhost:8080` to interact with the agent.
