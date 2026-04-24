# Gemma 4 Data Agent

This agent demonstrates how to create a data agent using [Agent Development Kit (ADK)](https://adk.dev/) and [Google Gemma 4](https://ai.google.dev/gemma) open model. The agent can answer questions about data in BigQuery.

## How to run

0. Deploy a Google Gemma 4 31B-it endpoint in Cloud Run as described in [Run inference of Gemma 4 model on Cloud Run with RTX 6000 Pro GPU with vLLM](https://codelabs.developers.google.com/codelabs/cloud-run/cloud-run-gpu-rtx-pro-6000-gemma4-vllm).

2. Enable BigQuery API and MCP Server.

    ```bash
    gcloud services enable bigquery.googleapis.com
    gcloud services mcp enable bigquery.googleapis.com
    ```

3. Create an OAuth Client for the agent:

    > This **optional** steps allows the agent and its web client to use tools that require user authentication with OAuth 2.0.
    If you skip this step, the agent will always use
    [Application Default Credentials](https://docs.cloud.google.com/docs/authentication/application-default-credentials).

    In the Google Cloud console, go to Google Auth Platform > Clients > [Create client](https://console.cloud.google.com/auth/clients/create).

    * Use **Web Application** as application type.
    * **Authorized JavaScript origins** and **Authorized redirect URIs** depend on where you run your Agent Web Client:
        * Local ADK Web UI:
            - Authorized JavaScript origins: `http://localhost:8000`
            - Authorized redirect URIs: `http://localhost:8000/dev-ui/`
        * Cloud Shell with ADK Web:
            - For "Authorized JavaScript origins" value use output of this command: `echo "https://8000-$WEB_HOST"`
            - For "Authorized redirect URIs" value use output of this command: `echo "https://8000-$WEB_HOST/dev-ui/"`
        * [Custom ADK Client](../adk-client) running on your machine:
            - Authorized JavaScript origins: `http://localhost:8080`
            - Authorized Redirect URIs: `http://localhost:8080/auth_callback.html`
        * [Custom ADK Client](../adk-client) running in Cloud Shell:
            - For "Authorized JavaScript origins" value use output of this command: `echo "https://8080-$WEB_HOST"`
            - For "Authorized Redirect URIs" value use output of this command: `echo "https://8080-$WEB_HOST/auth_callback.html"`
        * [Custom ADK Client](../adk-client) running in Cloud Run with a public URL:
            - In the **Authorized JavaScript origins** field, add a URL with your Cloud Run service URL:
            ```
            https://<your-cloud-run-service-url>
            ```
            - In the **Authorized redirect URIs** field, add a URL with your Cloud Run service URL followed by `/auth_callback.html` path:
            ```
            https://<your-cloud-run-service-url>/auth_callback.html
            ```
    Once an OAuth client is created, it will display a **Client ID** and a **Client Secret**. Copy these values to use in the next step.

4. Copy `.env.sample` as `.env`, and specify configuration values:
    * `API_BASE` – the URL of the deployed Cloud Run service with Gemma 4 vLLM server running.
    * `MODEL_NAME` – the model name, which is `google/gemma-4-31b-it`.
    * `GOOGLE_CLOUD_PROJECT` – the Google Cloud project ID. This is necessary to run BigQuery tools.
    * `OAUTH_CLIENT_ID` – Agent's OAuth Client ID (optional).
    * `OAUTH_CLIENT_SECRET` – Agent's OAuth Client Secret (optional).

### Run locally

0. Switch to the agent's directory:

    ```bash
    cd agents/simple-data-agent
    ```

1. Create a Python virtual environment and install Google ADK:

    ```bash
    uv pip install google-adk[extensions]
    ```

2. Run the application using the provided script:

    ```bash
    ./run.sh
    ```

    This script will start the ADK API server (port 8000).

### Run in Cloud Run

0. Switch to the agent's directory:

    ```bash
    cd agents/simple-data-agent
    ```

1. Execute the following command:

    ```bash
    source .env
    gcloud run deploy simple-data-agent \
        --source . \
        --project $GOOGLE_CLOUD_PROJECT \
        --region $GOOGLE_CLOUD_REGION \
        --cpu 4 \
        --memory 4Gi \
        --session-affinity \
        --no-allow-unauthenticated \
        --set-env-vars GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
        --set-env-vars GOOGLE_CLOUD_REGION="${GOOGLE_CLOUD_REGION}" \
        --set-env-vars API_BASE="${API_BASE}" \
        --set-env-vars MODEL_NAME="${MODEL_NAME}" \
        --set-env-vars OAUTH_CLIENT_ID="${OAUTH_CLIENT_ID}" \
        --set-env-vars OAUTH_CLIENT_SECRET="${OAUTH_CLIENT_SECRET}"
    ```

## How to use

You can use **Custom ADK Client** (located in [adk-client](../adk-client) to interact with the agent.

In a separate terminal, run:

```bash
export SERVER_BASE_URL="http://localhost:8000"
agents/adk-client/local_run.sh
```

If you deployed the agent to Cloud Run, set `SERVER_BASE_URL` to the public URL of the deployed service:

```bash
export SERVER_BASE_URL="https://your-cloud-run-service-url"
agents/adk-client/local_run.sh
```
