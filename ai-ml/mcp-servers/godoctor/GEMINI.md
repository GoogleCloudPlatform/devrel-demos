# GoDoctor Context

## Project Overview
**GoDoctor** is an intelligent, AI-powered Model Context Protocol (MCP) server designed to assist Go developers. It integrates with AI-powered IDEs to provide context-aware code reviews and on-demand documentation.

*   **Version:** 0.7.1
*   **Language:** Go 1.24+
*   **License:** Apache 2.0 (implied by headers)

## Key Features & Tools
The server exposes the following MCP tools:

1.  **`review_code`**
    *   **Purpose:** Analyzes Go code for style, correctness, and idioms.
    *   **Input:** `file_content` (string), `model_name` (optional), `hint` (optional).
    *   **Output:** Structured JSON suggestions (line number, severity, finding, comment).
    *   **Backend:** Uses Google's `gemini-2.5-pro` (default) via `google.golang.org/genai`.

2.  **`read_docs`**
    *   **Purpose:** Retrieves documentation for Go packages or symbols in Markdown format.
    *   **Input:** `package_path` (string), `symbol_name` (optional).
    *   **Mechanism:** Uses native `go/doc` and `go/parser` parsing. Supports merging examples from `_test.go` files and fuzzy matching for symbols and packages. Includes fallback to download missing packages.

3.  **`edit_code`**
    *   **Purpose:** Smartly edits Go code with fuzzy matching and safety checks.
    *   **Input:** `file_path`, `search_context`, `new_content`, `strategy` ("replace_block", "replace_all", "overwrite_file", or "append").
    *   **Mechanism:** Uses Levenshtein distance for fuzzy matching, runs `goimports` for auto-formatting, and performs syntax validation before saving.

4.  **`read_code`** (Experimental)
    *   **Purpose:** Reads a Go file and extracts a symbol table (functions, types, variables).
    *   **Input:** `file_path`.
    *   **Output:** File content + Markdown symbol table.

## Architecture & Structure
*   **`cmd/godoctor/`**: Main entry point. Handles signal processing and server startup.
*   **`internal/server/`**: Core server logic. Registers tools and prompts. Handles transport (Stdio/HTTP).
*   **`internal/config/`**: Configuration loading (flags and defaults).
*   **`internal/tools/`**:
    *   `codereview/`: Implementation of the AI code review tool.
    *   `read_docs/`: Implementation of the documentation retrieval tool.
    *   `edit_code/`: Implementation of the smart editing tool.
    *   `read_code/`: Implementation of the file reading and symbol extraction tool.

## Build & Development
*   **Build:** `make build` (creates binary in `bin/godoctor`)
*   **Install:** `make install` (installs to `$GOPATH/bin`)
*   **Test:** `make test` (runs `go test ./...`)
*   **Test Coverage:** `make test-cov`

## Configuration & Authentication
The server supports two authentication modes for the AI features:

1.  **Gemini API (Personal):**
    *   Requires `GOOGLE_API_KEY` or `GEMINI_API_KEY` environment variable.

2.  **Vertex AI (Enterprise):**
    *   Requires `GOOGLE_GENAI_USE_VERTEXAI=true`.
    *   Requires `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`.
    *   Uses Application Default Credentials (ADC).

**Command-Line Flags:**
*   `--listen <addr>`: Start HTTP server on specified address (e.g., `:8080`). Default is Stdio.
*   `--model <name>`: Override default Gemini model (default: `gemini-2.5-pro`).

## Conventions
*   **Style:** Standard Go project layout.
*   **Testing:** Table-driven tests. Mocking used for external AI calls (`ContentGenerator` interface).
*   **MCP:** Follows Model Context Protocol specifications (2025-06-18).
