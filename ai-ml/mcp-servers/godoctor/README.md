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
| `--experimental` | Enable new Code-Aware tools and background indexing. | `false` |

## Tools Usage

GoDoctor exposes the following stable tools via the Model Context Protocol:

### 1. `review_code`
Reviews Go code for correctness, style, and best practices.

*   **file_content**: The raw content of the Go file.
*   **model_name**: (Optional) Override the default model.
*   **hint**: (Optional) Focus the review on a specific aspect (e.g., "security", "performance").

### 2. `read_docs`
Retrieves documentation for packages and symbols. (Superseded by `describe` in experimental mode).

*   **package_path**: The import path (e.g., `fmt`, `encoding/json`).
*   **symbol_name**: (Optional) Specific symbol to look up (e.g., `Println`, `Decoder`).

### 3. `read_code`
Reads a file and returns its content along with a symbol table (functions, types, variables).

*   **file_path**: Absolute path to the file.

### 4. `edit_code`
Intelligently edits a file with safety checks and auto-formatting. (Superseded by `edit` in experimental mode).

*   **file_path**: Path to the file.
*   **search_context**: Code block to replace (3+ lines recommended for uniqueness). Required for replace strategies.
*   **new_content**: The new code to insert.
*   **strategy**: `replace_block` (default), `replace_all`, `overwrite_file`, or `append`.
*   **autofix**: (Optional) Attempt to fix minor typos in search context.

## Code-Aware Workflow (Experimental)

Enabled via the `--experimental` flag, this workflow uses a **Semantic Knowledge Graph** to provide compiler-verified context and safety.

### 1. `open`
Loads a file into the context and returns a **Skeleton View** (package, imports, types, function signatures). Use this to explore a file's structure without token bloat.

### 2. `describe`
The deep explorer. Returns full documentation, implementation source code, and usage references for any symbol (local or external).

### 3. `edit`
Modify code with whitespace-agnostic fuzzy matching. Performs post-edit verification and warns about compilation errors or broken references.

### 4. `write`
Creates or appends content to a file with automatic import and symbol validation.

## Development

### Running Tests
```bash
make test
```

### Agent Configuration
To generate instructions for configuring an LLM agent to use GoDoctor (use `--experimental` for the new workflow):

```bash
godoctor --agents --experimental
```

## License

Apache 2.0