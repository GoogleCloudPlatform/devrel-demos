# GoDoctor

**GoDoctor** is an intelligent, AI-powered Model Context Protocol (MCP) server designed to assist Go developers. It provides a comprehensive suite of tools for navigating, editing, analyzing, and modernizing Go codebases.

## Features

GoDoctor organizes its capabilities into domain-specific tools to streamline development workflows.

### 🔍 Navigation & Discovery
*   **`list_files`**: Explore the project hierarchy recursively to understand the architecture.
*   **`smart_read`**: **The Universal Reader.** Inspects file content, structure (outline), or specific snippets. Includes documentation for imported packages.

### ✏️ Smart Editing
*   **`file_create`**: Initialize a new source file with proper boilerplate and import organization.
*   **`smart_edit`**: Perform targeted code modifications using Levenshtein distance matching. Automatically handles formatting and checks syntax before finalizing.

### 🛠️ Go Toolchain Integration
*   **`smart_build`**: **The Universal Quality Gate.** Compiles the project, runs tests, and checks for linting issues in a single atomic step. Automatically runs `go mod tidy` and `gofmt`.
*   **`add_dependency`**: Manage module dependencies and immediately fetch documentation for the new package.
*   **`read_docs`**: Query documentation for any package or symbol in the Go ecosystem.
*   **`modernize_code`**: Automatically upgrade legacy Go patterns to modern standards.
*   **`check_api`**: Detect breaking API changes between versions.


### 🤖 Expert Assistance
*   **`code_review`**: Submit code for expert AI analysis focusing on correctness and idiomatic style.


## Installation

### For Gemini CLI Users (Recommended)

If you use the [Gemini CLI](https://github.com/google/gemini-cli), you can install GoDoctor as an extension. This is the easiest way for most Go developers to use it.

1.  **Install the binary:**
    ```bash
    go install github.com/danicat/godoctor@latest
    ```
2.  **Install the extension:**
    ```bash
    gemini extensions install https://github.com/danicat/godoctor
    ```

### For GoDoctor Developers

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/danicat/godoctor.git
    cd godoctor
    ```
2.  **Build the project:**
    ```bash
    make build
    ```
3.  **Run the server (Stdio mode):**
    ```bash
    ./bin/godoctor
    ```


## Configuration

### 1. Authentication

GoDoctor requires access to Google's Generative AI models.

**Option 1: Gemini API (Personal)**
Set the `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) environment variable.

```bash
export GEMINI_API_KEY="your-api-key"
```

**Option 2: Vertex AI (Enterprise)**
Set the following environment variables:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

### 2. Command-Line Flags

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--model` | Default Gemini model to use for AI tasks. | `gemini-2.5-pro` |
| `--allow` | Comma-separated list of tools to explicitly **enable** (whitelist mode). | `""` |
| `--disable` | Comma-separated list of tools to explicitly **disable**. | `""` |
| `--listen` | Address to listen on for HTTP transport (e.g., `:8080`). | `""` (Stdio) |
| `--list-tools`| List all available tools and their descriptions, then exit. | `false` |
| `--agents` | Print LLM agent instructions and exit. | `false` |
| `--version` | Print version and exit. | `false` |

## Agent Integration

To get the optimal system prompt for your AI agent:

```bash
godoctor --agents
```

To see which tools are currently active:

```bash
godoctor --list-tools
```

## License

Apache 2.0

## Cloud Deployment

GoDoctor can be deployed as a containerized service on **Google Cloud Run**. This allows you to host your own MCP server instance securely.

### Prerequisites

1.  **Google Cloud Project**: You need an active GCP project.
2.  **gcloud CLI**: Installed and authenticated (`gcloud auth login`).
3.  **Permissions**:
    *   `Artifact Registry Administrator`
    *   `Cloud Run Admin`
    *   `Secret Manager Admin` (if using Gemini API keys)
    *   `Vertex AI User` (if using Vertex AI)

### 1. Setup Infrastructure

Run the setup script once to enable required APIs (Cloud Run, Artifact Registry, Secret Manager) and create the Docker repository.

```bash
# Optional: Set region (defaults to us-central1)
export GOOGLE_CLOUD_LOCATION="europe-west1"

./deploy/setup.sh
```


### 2. Deploy to Cloud Run

The deployment script handles building the container, pushing it to the registry, and deploying the service. It supports three modes:

#### Option A: Standard Mode (No AI)
Deploys the server with basic file and Go tools. The `code_review` tool will be **disabled**.

```bash
./deploy/deploy.sh
```

#### Option B: With Gemini API (Secret Manager)
For secure API key management, store your key in Secret Manager first:

```bash
echo -n "YOUR_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=-
```

Then deploy with the Gemini flag. The script will securely mount the secret as an environment variable.

```bash
./deploy/deploy.sh --with-gemini
```

#### Option C: With Vertex AI
Uses your project's default Vertex AI quota.

```bash
./deploy/deploy.sh --with-vertex
```

### 3. Usage

After deployment, the script outputs the **Service URL**. You can connect your MCP client to this URL (e.g., using Streamable HTTP transport).

```bash
MCP Endpoint (Streamable HTTP): https://godoctor-xyz.a.run.app
```


