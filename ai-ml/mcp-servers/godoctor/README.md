# GoDoctor

**GoDoctor** is an intelligent, AI-powered Model Context Protocol (MCP) server designed to assist Go developers. It provides a comprehensive suite of tools for navigating, editing, analyzing, and modernizing Go codebases.

## Features

GoDoctor organizes its capabilities into domain-specific tools to streamline development workflows.

### 🔍 Navigation & Discovery
*   **`file_list`**: Explore the project hierarchy recursively to understand the architecture.
*   **`file_outline`**: View file structure (imports, types, signatures) with minimal token usage.
*   **`file_read`**: Read source code with added context about external symbols (signatures and docs).
*   **`symbol_inspect`**: Retrieve "Ground Truth" for any symbol—its definition, source code, and related types.

### ✏️ Smart Editing
*   **`file_create`**: Initialize a new source file with proper boilerplate and import organization.
*   **`file_edit`**: Perform targeted code modifications using fuzzy-matching. Automatically handles formatting and verifies compilation before finalizing.
*   **`symbol_rename`**: Safely execute semantic renames of identifiers across the entire project.

### 🛠️ Go Toolchain Integration
*   **`go_build`**: Compile the project to verify changes.
*   **`go_test`**: Execute tests with support for regex filtering.
*   **`go_get`**: Manage module dependencies and update `go.mod`.
*   **`go_docs`**: Query documentation for any package or symbol in the Go ecosystem.
*   **`go_modernize`**: Automatically upgrade legacy Go patterns to modern standards.
*   **`go_diff`**: Detect breaking API changes between versions.

### 🤖 Expert Assistance & Safety
*   **`code_review`**: Submit code for expert AI analysis focusing on correctness and idiomatic style.
*   **`safe_shell`**: Execute CLI commands safely with output capping and timeout management.

## Installation

### Prerequisites
*   Go 1.24 or later
*   Make

### Quick Install

```bash
make install
# Installs to $GOPATH/bin/godoctor
```

### Build from Source

```bash
git clone https://github.com/danicat/godoctor.git
cd godoctor
make build
# Binary will be in bin/godoctor
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
