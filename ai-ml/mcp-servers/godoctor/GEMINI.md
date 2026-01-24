# GoDoctor

## Project Overview

**GoDoctor** is an intelligent, AI-powered Model Context Protocol (MCP) server designed to assist Go developers. It provides a comprehensive suite of tools for navigating, editing, analyzing, and modernizing Go codebases, all integrated via the MCP standard for use with AI agents and IDEs.

The project is architected with a separation between **Internal Tool Logic** and **External Tool Presentation**, allowing for dynamic renaming and A/B testing of prompts without code changes.

### Key Concepts

*   **Tool Registry:** A centralized definition file (`internal/toolnames/registry.go`) that maps stable internal logic to agent-facing descriptions and instructions.
*   **Safe Editing:** The editor (`smart_edit`) uses Levenshtein distance matching and pre-verification (syntax checks, `goimports`) to ensure safe code modifications. Use `start_line` and `end_line` for precise targeting.

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

The project follows a modular package layout:

*   **`cmd/godoctor/`**: Main entry point.
*   **`internal/server/`**: MCP server implementation and tool orchestration.
*   **`internal/toolnames/`**: **CRITICAL**. Centralized tool registry. Modify this file to change tool names, descriptions, or instructions.
*   **`internal/tools/`**: Tool implementations grouped by functional domain (`file/`, `go/`, `agent/`).

### Adding a New Tool

1.  **Implement:** Create a new package in `internal/tools/<domain>/<toolname>/`.
2.  **Define:** Add the tool metadata to `internal/toolnames/registry.go`.
3.  **Register:** Add the registration logic to `internal/server/server.go`.

### Tool Naming Convention

Tools follow an **Intent-Driven** naming convention (e.g., `smart_read`, `smart_edit`, `verify_tests`). These names are chosen to map directly to the LLM's goal, reducing cognitive load and improving selection accuracy.




### Documentation



*   **`EVOLUTION.md`**: History of tool changes and architectural shifts.
