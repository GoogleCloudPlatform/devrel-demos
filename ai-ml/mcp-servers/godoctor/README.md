# GoDoctor

**GoDoctor** is an intelligent, AI-powered Model Context Protocol (MCP) server designed to assist Go developers. It integrates seamlessly with AI-powered IDEs and agents to provide context-aware code reviews, on-demand documentation, and smart code editing capabilities.

## Features

*   **🤖 AI Code Review:** Analyze your code for bugs, race conditions, and idiomatic Go style using Google's Gemini models.
*   **📚 Documentation Retrieval:** Instantly fetch documentation for standard library and third-party packages without leaving your editor.
*   **🔍 Deep Inspection:** Analyze file dependencies and external symbol usage to understand code context.
*   **✨ Smart Editing:** Safely modify code with fuzzy matching, auto-formatting (`goimports`), and syntax validation.

## Installation

### Prerequisites
*   Go 1.24 or later
*   Make

### Build from Source

```bash
git clone https://github.com/danicat/godoctor.git
cd godoctor
make build
# Binary will be in bin/godoctor
```

### Install

```bash
make install
# Installs to $GOPATH/bin/godoctor
```

## Configuration

GoDoctor requires access to Google's Generative AI models. You can use either the Gemini API (personal) or Vertex AI (enterprise).

### Authentication

**Option 1: Gemini API (Simplest)**
Set the `GOOGLE_API_KEY` (or `GEMINI_API_KEY`) environment variable.

```bash
export GOOGLE_API_KEY="your-api-key"
```

**Option 2: Vertex AI**
Set the following environment variables:

```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

### Command-Line Flags

| Flag | Description | Default |
| :--- | :--- | :--- |
| `--listen` | Address to listen on for HTTP transport (e.g., `:8080`). If empty, uses Stdio. | `""` (Stdio) |
| `--model` | Default Gemini model to use for code reviews. | `gemini-2.5-pro` |
| `--version` | Print version and exit. | `false` |
| `--agents` | Print LLM agent instructions and exit. | `false` |

## Tools Usage

GoDoctor exposes the following tools via the Model Context Protocol:

### 1. `review_code`
Reviews Go code for correctness, style, and best practices.

*   **file_content**: The raw content of the Go file.
*   **model_name**: (Optional) Override the default model.
*   **hint**: (Optional) Focus the review on a specific aspect (e.g., "security", "performance").

### 2. `read_godoc`
Retrieves documentation for packages and symbols.

*   **package_path**: The import path (e.g., `fmt`, `encoding/json`).
*   **symbol_name**: (Optional) Specific symbol to look up (e.g., `Println`, `Decoder`).

### 3. `inspect_file`
Analyzes a file to understand its structure and dependencies.

*   **file_path**: Absolute path to the file.

### 4. `edit_code`
Intelligently edits a file.

*   **file_path**: Path to the file.
*   **search_context**: Code block to replace (3+ lines recommended for uniqueness).
*   **new_content**: The new code to insert.
*   **strategy**: `single_match` (default), `replace_all`, or `overwrite_file`.
*   **autofix**: (Optional) Attempt to fix minor typos in search context.

## Development

### Running Tests
```bash
make test
```

### Agent Configuration
To generate instructions for configuring an LLM agent to use GoDoctor:

```bash
./bin/godoctor -agents
```

## License

Apache 2.0