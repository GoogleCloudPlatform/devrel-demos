# Gemma 4 Coding Agent

This agent demonstrates how to create a coding agent using [Aget Development Kit (ADK)](https://adk.dev/) and [Google Gemma 4](https://ai.google.dev/gemma) open model. The agent can generate and execute Python code in an isolated WebAssembly environment (Pyodide).

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

5. Run `adk web` to interact with the agent:

    ```bash
    adk web agents/simple-coding-agent
    ```

## DISCLAIMER

Pyodide is only recommended for local experiments. For production or pretty much as serious code execution work, consider using a proper Sandbox Environment, such as [Cloud Run Sandbox](https://github.com/GoogleCloudPlatform/cloud-run-sandbox), [GKE Sandbox](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods), or [Vertex AI Agent Engine Code Execution](https://docs.cloud.google.com/agent-builder/agent-engine/code-execution/overview).

You may also take a look at [BentoRun](https://github.com/vladkol/bentorun).
