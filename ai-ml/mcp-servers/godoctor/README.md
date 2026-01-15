# GoDoctor

**GoDoctor** is an intelligent, AI-powered Model Context Protocol (MCP) server designed to assist Go developers. It integrates context-aware code analysis, smart editing, and on-demand documentation into AI-powered IDEs and agentic workflows.

## Features

GoDoctor organizes its capabilities into **Profiles** to suit different workflow needs, from safe, standard editing to full-blown autonomous modernization.

### 🚀 Core Capabilities (Standard Profile)

*   **🔍 Smart Navigation**:
    *   `code_outline`: View file structure (imports, types, signatures) with minimal token usage. Supersedes reading entire files.
    *   `inspect_symbol`: Retrieve "Ground Truth" for any symbol—its definition, source code, and related types—to ensure edits feature 100% correct context.
    *   `list_files`: Explore the file system.

*   **✏️ Smart Editing**:
    *   `smart_edit`: The gold standard for code modification. It performs **Pre-Verification** (syntax check + `goimports`) *before* saving to disk, ensuring you never break the build. It also handles fuzzy matching and auto-fixes typos in search blocks.

*   **🛠️ Utilities**:
    *   `go_build`: Compile the project to verify changes.
    *   `go_test`: Run specific tests to validate logic.
    *   `read_docs`: internal documentation retrieval.

### ⚡ Advanced Modernization (Full Profile)

Includes all Standard tools, plus:
*   **♻️ Modernize**:
    *   `modernize`: Automatically upgrades legacy patterns (e.g., `interface{}` → `any`, manual loops → slices).
*   **📦 Dependency Analysis**:
    *   `analyze_dependency_updates`: Assess breaking changes and risks *before* upgrading dependencies.

### 🔮 Specialized Profiles

*   **Oracle**: Exposes *only* `ask_specialist`, a high-level tool that acts as a gateway to other hidden tools, forcing a "Human-in-the-Loop" or "Manager Agent" pattern.
*   **Dynamic**: Exposes *only* `ask_the_master_gopher`, an experimental dynamic agent interface.

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
| `--profile` | Server profile: `standard`, `full`, `oracle`, `dynamic`. | `standard` |
| `--model` | Default Gemini model to use for AI tasks. | `gemini-2.5-pro` |
| `--allow` | Comma-separated list of tools to explicitly **enable** (overrides profile defaults). | `""` |
| `--disable` | Comma-separated list of tools to explicitly **disable**. | `""` |
| `--listen` | Address to listen on for HTTP transport (e.g., `:8080`). If empty, uses Stdio. | `""` (Stdio) |
| `--agents` | Print LLM agent instructions for the current profile and exit. | `false` |
| `--version` | Print version and exit. | `false` |

### Legacy Tools
The following tools are still available for backward compatibility but are superseded by the "Smart" suite:
*   `edit_code` (Superseded by `smart_edit`)
*   `read_code`
*   `review_code`

## Agent Integration

To get the optimal system prompt for your AI agent based on your chosen profile:

```bash
# Get instructions for the standard profile
godoctor --agents --profile=standard

# Get instructions for the full profile with modernization tools
godoctor --agents --profile=full
```

## License

Apache 2.0