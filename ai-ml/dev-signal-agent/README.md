# Dev Signal Agent

**Dev Signal** is an autonomous multi-agent system designed to monitor technical trends, research solutions, and generate content. It demonstrates the power of the **Google Agent Development Kit (ADK)**, **Vertex AI**, and the **Model Context Protocol (MCP)**.

## 🚀 Capabilities

1.  **Trend Spotting**: Monitors Reddit (via MCP) for high-engagement technical questions (e.g., Cloud Run, AI Agents).
2.  **Deep Research**: "Triangulates" answers using:
    *   **Official Docs**: Via Google's Developer Knowledge MCP.
    *   **Community Sentiment**: Via Reddit MCP.
    *   **Web Context**: Via Google Search Tool.
3.  **Content Creation**: Drafts professional technical blog posts based on the research.
4.  **Visual Generation**: Generates custom infographic headers using a local **Nano Banana** MCP tool (powered by Gemini).
5.  **Long-Term Memory**: Remembers user preferences (e.g., writing style, topics) across sessions using Vertex AI Agent Engine.

## 📂 Project Structure

```text
dev-signal/
├── dev_signal_agent/      # Main application package
│   ├── agent.py           # Core agent logic & orchestration
│   ├── fast_api_app.py    # FastAPI server for Cloud Run
│   ├── tools/
│   │   ├── mcp_config.py  # MCP Client configuration
│   │   └── nano_banana_mcp/ # Local Image Generation MCP
│   └── app_utils/         # Telemetry & Config
├── deployment/
│   └── terraform/         # Infrastructure as Code (Cloud Run, IAM, Secrets)
├── blog_part_1_building.md   # Tutorial: Building the Agent
├── blog_part_2_deployment.md # Tutorial: Deploying to Cloud Run
├── blog_part_3_memory.md     # Tutorial: Adding Memory
├── Makefile               # Shortcuts for dev & deploy
└── test_memory_local.py   # Script to test long-term memory
```

## 🛠️ Prerequisites

*   **Python 3.12+** (Managed via `uv`)
*   **Google Cloud Project** with Vertex AI enabled.
*   **API Keys**:
    *   Reddit App Credentials (Client ID/Secret)
    *   Developer Knowledge API Key

## ⚡ Quick Start

1.  **Install Dependencies**:
    ```bash
    make install
    ```

2.  **Configure Environment**:
    Copy `.env.example` to `.env` and fill in your keys:
    ```bash
    cp .env.example .env
    ```

3.  **Run the Playground**:
    Interact with the agent in a local web UI.
    ```bash
    make playground
    ```
    Visit: `http://localhost:8501`

4.  **Test Memory**:
    Verify persistent memory with the local test script.
    ```bash
    python test_memory_local.py
    ```

## ☁️ Deployment

We use **Terraform** for infrastructure and **Cloud Build** for the container.

1.  **Provision Infrastructure**:
    ```bash
    cd deployment/terraform
    terraform init
    terraform apply
    ```

2.  **Deploy Application**:
    ```bash
    make docker-deploy
    ```

## 📚 Learn More

Check out the detailed tutorial series included in this repo:

*   [Part 1: Architecture & Building](blog_part_1_building.md)
*   [Part 2: Production Deployment](blog_part_2_deployment.md)
*   [Part 3: Long-Term Memory](blog_part_3_memory.md)