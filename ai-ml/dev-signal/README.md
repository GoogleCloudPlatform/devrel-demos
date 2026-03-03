# Dev Signal - Production-Ready AI Agent

Welcome to **Dev Signal**, an intelligent monitoring agent designed to filter noise and create value. This project demonstrates how to build, deploy, and train a sophisticated multi-agent system using the Google Agent Development Kit (ADK), Google Cloud Run, and Vertex AI memory bank.

## 🚀 What is Dev Signal?

Dev Signal is a multi-agent system that operates in a continuous loop to monitor technical trends and generate high-quality content. Its workflow includes:

1.  **Discovery (Reddit Scanner):** Scouts Reddit for high-engagement technical questions and trending topics (e.g., "AI agents on Cloud Run").
2.  **Grounding (GCP Expert):** Researches answers using official Google Cloud documentation (Developer Knowledge MCP) and broader web searches to ensure accuracy and capture community sentiment.
3.  **Creation (Blog Drafter):** Drafts professional technical blog posts based on the research.
4.  **Multimodal Generation:** Generates custom infographic-style header images for posts using the "Nano Banana" local image generation tool (Gemini 3 Pro Image).
5.  **Long-Term Memory:** Uses Vertex AI memory bank to remember user preferences (e.g., "I prefer rap-style blogs") across different sessions.

## 🏗️ Architecture

The system is built on a modular multi-agent architecture:

*   **Root Orchestrator:** The strategist that manages the specialist agents and handles memory retrieval/persistence.
*   **Specialist Agents:**
    *   `reddit_scanner`: Finds trending questions using the Reddit MCP tool.
    *   `gcp_expert`: Provides grounded technical answers by synthesizing official documentation with community insights gathered via web search.
    *   `blog_drafter`: Synthesizes findings into blog posts and generates visuals.
*   **Tools (MCP):**
    *   **Reddit MCP:** Connects to Reddit API for discovery.
    *   **Developer Knowledge MCP:** Connects to Google Cloud documentation for grounding.
    *   **Nano Banana MCP:** A custom local tool for image generation using Gemini 3 Pro Image.

## 📋 Prerequisites

Ensure you have the following installed:

*   **Python 3.12+**
*   **[uv](https://github.com/astral-sh/uv):** Fast Python package manager.
*   **Google Cloud SDK (gcloud):** Installed and authenticated.
*   **Terraform:** For infrastructure as code.
*   **Node.js & npm:** Required for the Reddit MCP tool.

**Google Cloud Requirements:**
*   A Google Cloud Project with billing enabled.
*   **APIs Enabled:** Vertex AI, Cloud Run, Secret Manager, Artifact Registry.

**API Keys:**
*   **Reddit API Credentials:** (Client ID, Secret) from the [Reddit Developer Portal](https://www.reddit.com/prefs/apps).
*   **Developer Knowledge API Key:** For Google Cloud docs search.

## 🛠️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd dev-signal
    ```

2.  **Install dependencies:**
    We use `uv` for fast dependency management.
    ```bash
    uv sync
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the project root:
    ```bash
    touch .env
    ```
    Add the following configuration (replace with your actual values):
    ```ini
    # Google Cloud Configuration
    GOOGLE_CLOUD_PROJECT=your-project-id
    GOOGLE_CLOUD_LOCATION=global
    GOOGLE_CLOUD_REGION=us-central1
    GOOGLE_GENAI_USE_VERTEXAI=True
    AI_ASSETS_BUCKET=your-bucket-name

    # Reddit API Credentials
    REDDIT_CLIENT_ID=your_client_id
    REDDIT_CLIENT_SECRET=your_client_secret
    REDDIT_USER_AGENT=my-agent/0.1

    # Developer Knowledge API Key
    DK_API_KEY=your_api_key
    ```

## 💻 Local Testing

You can test the full agent loop locally, including the connection to the cloud-based Vertex AI Memory Bank.

1.  **Authenticate with Google Cloud:**
    ```bash
    gcloud auth application-default login
    ```

2.  **Run the local test script:**
    ```bash
    uv run test_local.py
    ```

**Test Scenario:**
1.  **Teach:** Tell the agent a preference (e.g., "Write all blogs as a 90s rap song").
2.  **Reset:** Type `new` to start a fresh session (clears local history).
3.  **Verify:** Ask for a new blog post. The agent should recall your preference from the cloud memory bank.

## ☁️ Deployment (Production)

We use **Terraform** for infrastructure and **Cloud Run** for hosting.

### 1. Provision Infrastructure
Initialize and apply the Terraform configuration to set up Cloud Run, Secret Manager, and permissions.

1.  **Initialize Terraform:**
    ```bash
    cd deployment/terraform
    terraform init
    ```

2.  **Create Variables:**
    Create a `terraform.tfvars` file and add your configuration (project ID, region, bucket, and secrets).

3.  **Plan and Apply:**
    ```bash
    terraform plan -out=plan.tfplan
    terraform apply plan.tfplan
    ```

### 2. Build & Deploy
Use the provided `Makefile` to build the Docker container and deploy it to Cloud Run via Google Cloud Build.

1.  **Return to project root:**
    ```bash
    cd ../..
    ```

2.  **Deploy:**
    ```bash
    make docker-deploy
    ```
    *This command builds the image, stores it in Artifact Registry, and updates the Cloud Run service.*

### 3. Accessing the Agent
Production services are private by default. Access them securely via IAM and the Cloud Run proxy.

1.  **Grant Permission:**
    ```bash
    gcloud run services add-iam-policy-binding dev-signal \
      --member="user:$(gcloud config get-value account)" \
      --role="roles/run.invoker" \
      --region=us-central1 \
      --project=$(gcloud config get-value project)
    ```

2.  **Launch Proxy:**
    ```bash
    gcloud run services proxy dev-signal \
      --region us-central1 \
      --project $(gcloud config get-value project)
    ```

3.  **Chat:** Visit `http://localhost:8080` to interact with your production agent.

## 📊 Monitoring & Tracing
Once deployed, you can monitor your agent's reasoning traces in the Google Cloud Console:

1.  Navigate to **Trace Explorer**.
2.  Filter for the `dev-signal` service.
3.  View the "visual waterfall" of agent thoughts, tool calls, and LLM responses.

## 📂 Project Structure

```
dev-signal/
├── dev_signal_agent/
│   ├── __init__.py
│   ├── agent.py           # The brain: Agent logic & orchestration
│   ├── fast_api_app.py    # The body: Application server & memory connection
│   ├── app_utils/         # The nervous system: Env Config
│   │   └── env.py
│   └── tools/             # The hands: External capabilities
│       ├── __init__.py
│       ├── mcp_config.py  # Tool configuration (Reddit, Docs)
│       └── nano_banana_mcp/# Custom local image generation tool
├── deployment/
│   └── terraform/         # Infrastructure as Code
├── .env                   # Local secrets (API keys)
├── .gitignore             # Git ignore patterns
├── Makefile               # Shortcuts for building/deploying
├── Dockerfile             # Container definition
├── pyproject.toml         # Dependencies
├── uv.lock                # Locked dependencies
└── test_local.py          # Local test runner
```
