# GoDoctor

## Project Overview

**GoDoctor** is an intelligent, AI-powered Model Context Protocol (MCP) server designed to assist Go developers. It provides a comprehensive suite of tools for navigating, editing, analyzing, and modernizing Go codebases, all integrated via the MCP standard for use with AI agents and IDEs.

The project is architected with a separation between **Internal Tool Logic** and **External Tool Presentation**, allowing for dynamic renaming and A/B testing of prompts without code changes.

### Key Concepts

*   **Tool Registry:** A centralized definition file (`internal/toolnames/registry.go`) that maps stable internal logic to agent-facing descriptions and instructions.
*   **Safe Editing:** The editor (`file_edit`) uses fuzzy matching and pre-verification (syntax checks, `goimports`) to ensure safe code modifications.

## Building and Running

**Prerequisites:**
*   Go 1.24 or later

**Key Commands:**

*   **Build the server:**
    ```bash
    go build -o godoctor cmd/godoctor/main.go
    ```

*   **Run the server (Stdio mode):**
    ```bash
    go run cmd/godoctor/main.go
    ```

*   **List all available tools:**
    ```bash
    go run cmd/godoctor/main.go --list-tools
    ```

*   **Run tests:**
    ```bash
    go test ./...
    ```

## Development Conventions

### Project Structure

The project follows a domain-driven package layout for tools:

*   **`cmd/godoctor/`**: Main entry point.
*   **`internal/server/`**: MCP server implementation and tool wiring.
*   **`internal/toolnames/`**: **CRITICAL**. Contains `registry.go`, which defines the Name, Title, Description, and Instructions for *all* tools. Modify this file to change how agents perceive tools.
*   **`internal/tools/`**: Tool implementations grouped by domain.
    *   `file/` (`create`, `edit`, `read`, `list`, `outline`)
    *   `symbol/` (`inspect`, `rename`)
    *   `go/` (`build`, `test`, `get`, `modernize`, `diff`, `docs`)
    *   `agent/` (`review`)

### Adding a New Tool

1.  **Implement:** Create a new package in `internal/tools/<domain>/<toolname>/`.
2.  **Define:** Add the tool definition to `internal/toolnames/registry.go`.
3.  **Register:** Add the registration logic to `internal/server/server.go`.

### Tool Naming Convention

Tools follow a `domain_verb` naming convention (e.g., `file_create`, `go_build`). These names are stable and used by the agent to invoke functionality.

### Documentation

*   **`EVOLUTION.md`**: History of tool changes and architectural shifts.
