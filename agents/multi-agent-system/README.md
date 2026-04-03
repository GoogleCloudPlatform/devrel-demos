# Multi-Agent Course Creator with Self-Hosted LLM on GPU

A multi-agent system built with Google's Agent Development Kit (ADK) and Agent-to-Agent (A2A) protocol. It features a team of microservice agents that research, judge, and build content, orchestrated to deliver high-quality results.

The **Content Builder** agent is powered by a **self-hosted Gemma model** running on **Google Cloud Run with GPU** via Ollama, demonstrating how to integrate self-hosted LLMs into a multi-agent system.

## Architecture

This project uses a distributed microservices architecture where each agent runs in its own container and communicates via A2A. **6 Cloud Run services total:**

*   **Ollama Backend (`ollama-gemma-gpu`):** Self-hosted Gemma LLM running on Cloud Run with NVIDIA L4 GPU. Serves the model via Ollama's HTTP API.
*   **Orchestrator Service (`orchestrator`):** The main entry point. Manages the workflow using `LoopAgent` and `SequentialAgent`, connects to agents via `RemoteA2aAgent`.
*   **Researcher Service (`researcher`):** Gathers information using Google Search. Uses Gemini 2.5 Pro.
*   **Judge Service (`judge`):** Evaluates research quality with structured output. Uses Gemini 2.5 Pro.
*   **Content Builder Service (`content_builder`):** Compiles the final course using the **self-hosted Gemma model** via LiteLlm.
*   **Agent App (`app`):** Web application that queries the Orchestrator, displays progress and results.

## Project Structure

```
next-demo-multi-agent/
├── ollama-backend/          # Self-hosted Gemma LLM (Cloud Run + GPU)
│   └── Dockerfile
├── agents/
│   ├── orchestrator/        # Main Orchestrator agent, ADK API Service
│   ├── researcher/          # Researcher agent, A2A microservice (Gemini)
│   ├── judge/               # Judge agent, A2A microservice (Gemini)
│   └── content_builder/     # Content Builder agent, A2A microservice (Gemma via Ollama)
├── app/                     # Web App service application
│   └── frontend/            # Frontend application
├── shared/                  # Files used by all agents
├── deploy.sh                # Full deployment script (all 6 services)
├── run_local.sh             # Local development launcher
└── ...
```

### Shared files

Files in `shared/` are linked into agent subdirectories as [symlinks](https://en.wikipedia.org/wiki/Symbolic_link):

* `a2a_utils.py` - Rewrites agent URLs in A2A AgentCard for Cloud Run.
* `adk_app.py` - ADK API Service implementation with A2A functionality.
* `authenticated_httpx.py` - httpx client for [service-to-service auth](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).

## Requirements

*   **uv**: Python package manager (required for local development).
*   **Google Cloud SDK**: For GCP services and authentication.
*   **Ollama** (for local development): Install from [ollama.com](https://ollama.com).

## Quick Start (Local)

1.  **Install Dependencies:**
    ```bash
    uv sync
    ```

2.  **Set up credentials:**
    ```bash
    gcloud auth application-default login
    ```

3.  **Start Ollama locally (for Content Builder):**
    ```bash
    ollama serve
    ollama pull gemma3:270m
    ```

4.  **Run all agents:**
    ```bash
    ./run_local.sh
    ```
    This starts Ollama detection, 4 agents, and the web app.

5.  **Access the App:**
    Open **http://localhost:8000** in your browser.

## Deployment to Cloud Run

The deployment script (`deploy.sh`) handles all 6 services. The key difference from the original repo is the Ollama GPU backend.

### Prerequisites

```bash
# Set your project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com

# Ensure GPU quota is available in your target region
# GPU-supported regions: us-central1, us-east1, europe-west1, asia-southeast1, etc.
```

### Deploy Everything

```bash
./deploy.sh
```

The script deploys in this order:
1. **Ollama Backend (GPU)** - deployed first, URL captured for content-builder
2. **Researcher** - uses Gemini 2.5 Pro via Vertex AI
3. **Content Builder** - uses self-hosted Gemma via Ollama URL
4. **Judge** - uses Gemini 2.5 Pro via Vertex AI
5. **Orchestrator** - connects to all 3 agents via A2A
6. **Frontend App** - public-facing, connects to orchestrator

### Key Deployment Differences (vs. original prai-roadshow)

| Aspect | Original | This Demo |
|--------|----------|-----------|
| Services | 5 | **6** (+ Ollama GPU backend) |
| Content Builder LLM | Gemini 2.5 Pro (Vertex AI) | **Gemma 270M (self-hosted Ollama)** |
| GPU | None | **NVIDIA L4 GPU** for Ollama |
| New env vars | N/A | `OLLAMA_API_BASE`, `GEMMA_MODEL_NAME` |
| Memory (Ollama) | N/A | **16Gi** (for Gemma 270M model) |
| Auth (Ollama) | N/A | Unauthenticated (Ollama has no built-in auth) |

### Ollama Backend Details

The Ollama service runs on Cloud Run with:
- **GPU**: 1x NVIDIA L4
- **CPU**: 8 vCPU
- **Memory**: 16Gi
- **Concurrency**: 4 requests per instance
- **Model**: Gemma3 270M (pre-baked into container image)
- **Timeout**: 600s (10 min for longer generations)

To use a different model, set `GEMMA_MODEL_NAME` before deploying:
```bash
export GEMMA_MODEL_NAME="gemma3:12b"  # Requires more GPU memory
./deploy.sh
```

### GPU Region Override

If your main region doesn't support GPUs, deploy the Ollama backend to a different region:
```bash
export OLLAMA_REGION="us-central1"
./deploy.sh
```

### Environment Variables

| Variable | Service | Description |
|----------|---------|-------------|
| `OLLAMA_API_BASE` | content-builder | URL of the Ollama GPU backend |
| `GEMMA_MODEL_NAME` | content-builder, ollama-backend | Model tag (default: `gemma3:270m`) |
| `OLLAMA_REGION` | deploy.sh | Region for GPU service (optional override) |
| `GOOGLE_CLOUD_PROJECT` | all | GCP project ID |
| `GOOGLE_GENAI_USE_VERTEXAI` | researcher, judge, orchestrator | Use Vertex AI for Gemini |
