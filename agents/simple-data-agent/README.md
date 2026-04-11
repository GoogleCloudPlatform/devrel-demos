# Gemma 4 Data Agent

This agent demonstrates how to create a data agent using [Aget Development Kit (ADK)](https://adk.dev/) and [Google Gemma 4](https://ai.google.dev/gemma) open model. The agent can answer questions about data in BigQuery.

## How to run

1. Deploy a Google Gemma 4 31B-it endpoint in Cloud Run as described in [Run inference of Gemma 4 model on Cloud Run with RTX 6000 Pro GPU with vLLM](https://codelabs.developers.google.com/codelabs/cloud-run/cloud-run-gpu-rtx-pro-6000-gemma4-vllm).

2. Create a Python virtual environment and install Google ADK:

    ```bash
    uv pip install google-adk[extensions]
    ```

3. Install node.js and npm.

    You can install them via uv as well:

    ```bash
    uv pip install npm-wheel
    ```

4. Copy `.env.sample` as `.env`, and specify configuration values:
    * `API_BASE` – the URL of the deployed Cloud Run service with Gemma 4 vLLM server running.
    * `MODEL_NAME` – the model name, which is `google/gemma-4-31b-it`.
    * `GOOGLE_CLOUD_PROJECT` – the Google Cloud project ID. This is necessary to run BigQuery tools.

5. Run `adk web` to interact with the agent:

    ```bash
    adk web agents/simple-data-agent
    ```

