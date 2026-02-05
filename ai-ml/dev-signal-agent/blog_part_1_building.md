# Building a "Dev Signal" Agent: Part 1 - Architecture & Local Development

In this tutorial series, we will build **Dev Signal**, an autonomous multi-agent system that monitors Reddit for high-engagement technical questions, researches answers using official Google Cloud documentation, drafts blog posts, and **generates infographic-style header images** for them.

We will use the **Google Agent Development Kit (ADK)** for orchestration and the **Model Context Protocol (MCP)** to connect our agents to external tools, including a custom local tool for image generation.

## Prerequisites

*   **Python 3.12+** (We recommend using `uv` for package management)
*   **Node.js & npm** (for the Reddit MCP server)
*   **Google Cloud Project** with Vertex AI API enabled.
*   **Reddit App Credentials** (Client ID, Client Secret, User Agent).
*   **Developer Knowledge API Key** (for accessing Google Cloud docs).

## Step 1: Project Setup

Create a new directory for your project and initialize it. We'll use `uv`, which is an extremely fast Python package manager.

```bash
mkdir dev-signal && cd dev-signal
uv init
```

### Folder Structure
Our project will follow this structure:
```
dev-signal/
├── dev_signal_agent/
│   ├── __init__.py
│   ├── agent.py            # Main agent logic & orchestration
│   ├── fast_api_app.py     # FastAPI application server
│   ├── app_utils/
│   │   ├── env.py
│   │   ├── telemetry.py
│   │   └── typing.py
│   └── tools/
│       ├── __init__.py
│       ├── mcp_config.py   # MCP tool definitions
│       └── nano_banana_mcp/# Local Image Gen MCP Server
├── deployment/
│   └── terraform/          # Infrastructure as Code
├── .env                    # Secrets and configuration
├── Makefile                # Development shortcuts
└── pyproject.toml          # Project dependencies
```

### Dependencies
Update your `pyproject.toml` with the necessary dependencies. We use `google-adk` for the agent framework and `google-genai` for the model interaction.

```toml
dependencies = [
    "google-adk>=0.1.0",
    "google-genai>=1.0.0",
    "mcp>=1.0.0",
    "python-dotenv>=1.0.0",
    "fastapi>=0.110.0",
    "uvicorn>=0.29.0",
    "google-cloud-logging>=3.0.0",
    "google-cloud-aiplatform>=1.38.0",
]
```

Run `make install` (or `uv sync`) to install them.

---

## Step 2: Defining the MCP Tools

The **Model Context Protocol (MCP)** is a universal standard for connecting AI agents to external data and tools. Instead of writing custom API wrappers, we use standard MCP servers.

We'll define our toolsets in `dev_signal_agent/tools/mcp_config.py`.

### 1. Reddit Search (Discovery Tool)
The **Reddit MCP** server connects to the Reddit API. It allows agents to fetch top posts and analyze engagement.

```python
def get_reddit_mcp_toolset():
    """Reddit MCP for engagement analysis."""
    # We check if 'reddit-mcp' is installed globally, otherwise use npx
    cmd = "reddit-mcp" if shutil.which("reddit-mcp") else "npx"
    args = [] if shutil.which("reddit-mcp") else ["-y", "--quiet", "reddit-mcp"]
    # Ensure environment variables are passed correctly
    env = {**os.environ, "DOTENV_CONFIG_SILENT": "true", "LANG": "en_US.UTF-8"}
    
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command=cmd, args=args, env=env),
            timeout=120.0
        )
    )
```

### 2. Google Cloud Docs (Knowledge Tool)
The **Developer Knowledge** MCP provides **Grounding** by searching official Google Cloud documentation. This is crucial for accurate technical answers.

```python
def get_dk_mcp_toolset():
    """DeveloperKnowledge MCP for official GCP docs."""
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url="https://developerknowledge.googleapis.com/mcp",
            headers={"X-Goog-Api-Key": os.getenv("DK_API_KEY", "")}
        )
    )
```

### 3. Visuals with Nano Banana (Local Utility Tool)
**Nano Banana** is a custom local MCP server that uses Gemini to generate images. It runs as a subprocess.

```python
def get_nano_banana_mcp_toolset():
    """Nano Banana MCP for image generation."""
    path = os.path.join("dev_signal_agent", "tools", "nano_banana_mcp", "main.py")
    bucket = os.getenv("AI_ASSETS_BUCKET") or os.getenv("LOGS_BUCKET_NAME")
    env = {
        **os.environ, 
        "MCP_TRANSPORT": "stdio", 
        "DOTENV_CONFIG_SILENT": "true",
        "AI_ASSETS_BUCKET": bucket
    }
    
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command="uv", args=["run", path], env=env),
            timeout=600.0 # Long timeout for image generation
        )
    )
```

---

## Step 3: Building the Multi-Agent System

Our system uses a "Specialist" pattern where a **Root Orchestrator** delegates tasks to specialized agents. All logic lives in `dev_signal_agent/agent.py`.

### 1. Infrastructure Setup
First, we initialize the environment and the shared Gemini model.

```python
# --- 1. Infrastructure & Model Setup ---
PROJECT_ID, MODEL_LOC, SERVICE_LOC = init_environment()

shared_model = Gemini(
    model="gemini-3-flash-preview",
    vertexai=True,
    project=PROJECT_ID,
    location=MODEL_LOC,
    retry_options=types.HttpRetryOptions(attempts=3),
)
```

### 2. The Specialized Agents

#### Reddit Scanner (Discovery)
**Role**: The Trend Spotter.
**Mechanism**: Identifies high-engagement questions from the last 3 weeks. It explicitly filters for recent, active discussions.
```python
reddit_scanner = Agent(
    name="reddit_scanner",
    model=shared_model,
    instruction="""
    You are a Reddit research specialist. Your goal is to identify high-engagement questions 
    from the last 3 weeks on specific topics of interest, such as AI/agents on Cloud Run.
    
    Follow these steps:
    1. **MEMORY CHECK**: Use `load_memory` to retrieve the user's **past areas of interest** and **preferred topics**. Calibrate your search to align with these interests.
    2. Use the Reddit MCP tools to search for relevant subreddits and posts.
    3. Filter results for posts created within the last 21 days (3 weeks).
    4. Analyze "high-engagement" based on upvote counts and the number of comments.
    5. Recommend the most important and relevant questions for a technical audience.
    6. **CRITICAL**: For each recommended question, provide a direct link to the original thread and a concise summary of the discussion.
    """,
    tools=[reddit_mcp, load_memory_tool.LoadMemoryTool()],
)
```

#### GCP Expert (Researcher)
**Role**: The Technical Authority.
**Mechanism**: Triangulates facts using **DeveloperKnowledge** (Docs), **Reddit** (Sentiment), and **Google Search** (Context). It saves findings to state for the blog drafter.
```python
gcp_expert = Agent(
    name="gcp_expert",
    model=shared_model,
    instruction="""
    You are a Google Cloud Platform (GCP) documentation expert. 
    Your goal is to provide accurate, detailed, and cited answers to technical questions by synthesizing official documentation with community insights.
    
    For EVERY technical question, you MUST perform a comprehensive research sweep using ALL available tools:
    
    1. **Official Docs (Grounding)**: Use DeveloperKnowledge MCP (`search_documents`) to find the definitive technical facts.
    2. **Community Sentiment (Reddit)**: Use Reddit MCP to find real-world user discussions, common pain points, or alternative solutions related to the topic.
    3. **Broader Context (Web/Social)**: Use the `search_agent` tool to find recent technical blogs, social media discussions, or tutorials.
    
    Synthesize your answer:
    - Start with the official answer based on GCP docs.
    - Add "Community Insights" or "Common Issues" sections derived from Reddit and Web Search findings.
    - **CRITICAL**: After providing your answer, you MUST use the `add_info_to_state` tool to save your full technical response under the key: `technical_research_findings`.
    - Cite your sources specifically at the end of your response, providing **direct links** (URLs) to the official documentation, blog posts, and Reddit threads used.
    """,
    tools=[dk_mcp, AgentTool(search_agent), reddit_mcp, add_info_to_state],
)
```

#### Blog Drafter (Creative Synthesizer)
**Role**: The Content Creator.
**Mechanism**: Drafts the blog based on the expert's findings and offers to generate visuals.
```python
blog_drafter = Agent(
    name="blog_drafter",
    model=shared_model,
    instruction="""
    You are a professional technical blogger specializing in Google Cloud Platform. 
    Your goal is to draft high-quality blog posts based on technical research and answers provided in the conversation.
    
    You have access to the research findings from the gcp_expert_agent here:
    {{ technical_research_findings }}
 
    Follow these steps:
    1. **MEMORY CHECK**: Use `load_memory` to retrieve past blog posts, **areas of interest**, and user feedback on writing style. Adopt the user's preferred style and depth.
    2. Review the technical research findings provided above.
    3. Draft a blog post that is engaging, accurate, and helpful for a technical audience.
    ...
    7. **VISUALS**: After presenting the drafted blog post, explicitly ask the user: "Would you like me to generate an infographic-style header image to illustrate these key points?" If they agree, use the `generate_image` tool (Nano Banana).
    """,
    tools=[dk_mcp, load_memory_tool.LoadMemoryTool(), nano_mcp],
)
```

### 3. The Root Orchestrator
**Role**: The Strategist.
**Mechanism**: Orchestrates the workflow and handles user preferences (Memory).
```python
root_agent = Agent(
    name="root_orchestrator",
    model=shared_model,
    instruction="""
    You are a technical content strategist. You manage three specialists:
    ...
    Your responsibilities:
    - **MEMORY CHECK**: At the start of a conversation, use `load_memory` to check if the user has specific **areas of interest**, preferred topics, or past projects. Tailor your suggestions accordingly.
    - **CAPTURE PREFERENCES**: Actively listen for user preferences, interests, or project details. Explicitly acknowledge them to ensure they are captured in the session history for future personalization.
    - If the user wants to find trending topics or questions from Reddit, delegate to reddit_scanner.
    - If the user has a technical question or wants to research a specific theme, delegate to gcp_expert.
    ...
    """,
    tools=[load_memory_tool.LoadMemoryTool(), preload_memory_tool.PreloadMemoryTool()],
    after_agent_callback=save_session_to_memory_callback,
    sub_agents=[reddit_scanner, gcp_expert, blog_drafter]
)
```

---

## Step 4: Local Development

We use `make` commands to simplify the development workflow.

1.  **Configure `.env`**: Copy `.env.example` to `.env` and fill in your keys.
2.  **Start the Playground**:
    ```bash
    make playground
    ```
    This launches the ADK web interface at `http://localhost:8501`. You can chat with your agent, inspect the trace of tool calls, and debug any issues in real-time.

In **Part 2**, we'll show you how to take this local agent and deploy it to **Google Cloud Run** using Terraform!