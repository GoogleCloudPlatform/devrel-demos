# Dev Signal -  Multi-Agent System for Expert Content with Google ADK, MCP and Cloud Run

Welcome to **Dev Signal**, an intelligent monitoring agent designed to filter noise and create value. This project demonstrates how to build, deploy, and train a sophisticated multi-agent system using the Google Agent Development Kit (ADK), Google Cloud Run, MCP, and Vertex AI memory bank.

## 🚀 What is Dev Signal?

Dev Signal is a multi-agent system that operates in a continuous loop to monitor technical trends and generate high-quality content. Its workflow includes:

1.  **Discovery (Reddit Scanner):** Scouts Reddit for high-engagement technical questions and trending topics (e.g., "AI agents on Cloud Run").
2.  **Grounding (GCP Expert):** Researches answers using official Google Cloud documentation via the Developer Knowledge MCP to ensure accuracy.
3.  **Creation (Blog Drafter):** Drafts professional technical blog posts based on the research.
4.  **Multimodal Generation:** Generates custom infographic-style header images for posts using the "Nano Banana" local image generation tool (Gemini 3 Pro).
5.  **Long-Term Memory:** Uses Vertex AI memory bank to remember user preferences (e.g., "I prefer rap-style blogs") across different sessions.

## 🏗️ Architecture

The system is built on a modular multi-agent architecture:

*   **Root Orchestrator:** The strategist that manages the specialist agents and handles memory retrieval/persistence.
*   **Specialist Agents:**
    *   `reddit_scanner`: Finds trending questions using the Reddit MCP tool.
    *   `gcp_expert`: Provides grounded technical answers using the Google Cloud Docs MCP tool.
    *   `blog_drafter`: Synthesizes findings into blog posts and generates visuals.
*   **Tools (MCP):**
    *   **Reddit MCP:** Connects to Reddit API for discovery.
    *   **Developer Knowledge MCP:** Connects to Google Cloud documentation for grounding.
    *   **Nano Banana MCP:** A custom local tool for image generation using Gemini 3 Pro.

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

### 0. Setup environment variables
Paste this code in  deployment/terraform/terraform.tfvars and update it with your project details and secrets.

```project_id = "your-project-id"
region     = "us-central1"
service_name      = "dev-signal"
ai_assets_bucket  = "your-bucket-name"
secrets = {
  REDDIT_CLIENT_ID     = "your_client_id"
  REDDIT_CLIENT_SECRET = "your_client_secret"
  REDDIT_USER_AGENT    = "your_user_agent"
  DK_API_KEY           = "your_dk_api_key"
}
```

### 1. Provision Infrastructure
Initialize and apply the Terraform configuration to set up Cloud Run, Secret Manager, and permissions.

```bash
cd deployment/terraform
terraform init
terraform apply
```
*Create a `terraform.tfvars` file or enter values when prompted.*

### 2. Build & Deploy
Use the provided `Makefile` to build the Docker container and deploy it to Cloud Run.

```bash
# Return to project root
cd ../..

# Deploy
make docker-deploy
```

### 3. Accessing the Agent
The Cloud Run service is deployed privately by default. To access it:

1.  **Grant Permission:**
    ```bash
    gcloud run services add-iam-policy-binding dev-signal-agent \
      --member="user:your-email@example.com" \
      --role="roles/run.invoker" \
      --region=us-central1 \
      --project=your-project-id
    ```

2.  **Proxy via Localhost:**
    ```bash
    gcloud run services proxy dev-signal-agent \
      --region us-central1 \
      --project your-project-id
    ```

3.  **Chat:** Visit `http://localhost:8080` to interact with your production agent.

## 📂 Project Structure

```
dev-signal/
├── dev_signal_agent/
│   ├── agent.py            # The Brain: Agent logic & orchestration
│   ├── fast_api_app.py     # The Body: Application server
│   ├── app_utils/          # The Nervous System: Config & Telemetry
│   └── tools/              # The Hands: External capabilities (MCP)
│       ├── mcp_config.py
│       └── nano_banana_mcp/# Custom local image generation tool
├── deployment/
│   └── terraform/          # Infrastructure as Code
├── .env                    # Local secrets (not committed)
├── Makefile                # Build/Deploy shortcuts
├── Dockerfile              # Container definition
└── pyproject.toml          # Dependencies
```
