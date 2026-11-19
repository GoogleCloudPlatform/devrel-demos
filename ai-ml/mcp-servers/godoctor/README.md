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

### For Antigravity Users (Recommended)

If you use [Google Antigravity](https://antigravity.google), register GoDoctor as an MCP server. Antigravity CLI (`agy`) replaced Gemini CLI. See the [migration guide](https://antigravity.google/docs/cli/gcli-migration) for details.

1.  **Install the binary** (from the `devrel-demos` root):
    ```bash
    cd ai-ml/mcp-servers/godoctor && go install ./cmd/godoctor
    ```
2.  **Add the MCP server:**
    ```bash
    agy mcp add godoctor "$(go env GOPATH)/bin/godoctor"
    ```
    Or add it to `~/.gemini/config/mcp_config.json` (global) or `.agents/mcp_config.json` (workspace), using the full binary path if `$(go env GOPATH)/bin` is not on `PATH`:
    ```json
    {
      "mcpServers": {
        "godoctor": {
          "command": "godoctor"
        }
      }
    }
    ```
    GoDoctor's local Go tools work immediately without an API key. To enable `code_review`, pass `-e GEMINI_API_KEY="your-api-key"` before the server name in `agy mcp add` or add an `"env"` block in `~/.gemini/config/mcp_config.json`.

### For GoDoctor Developers
... (rest of the existing installation)


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