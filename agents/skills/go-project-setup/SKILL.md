---
name: go-project-setup
description: >
  Standardized setup for new Go (Golang) projects and services. Activate to ensure clean, idiomatic project structures (Standard Layout) and implement production-ready patterns (graceful shutdown, package separation) from day one.
---

# Go Project Setup

This skill guides the creation of clean, idiomatic Go project structures.

## Core Mandates
1.  **Standard Layout Only**: Use the official Go project layout (`cmd/`, `internal/`).
    *   **NEVER** create a `pkg/` directory. (It is an anti-pattern common in Kubernetes but not idiomatic Go).
2.  **Flat by Default**: Start with a flat structure (all files in root) for simple apps. Only introduce `cmd/` and `internal/` when multiple binaries or private packages are needed.
3.  **Modern Go**: Ensure `go.mod` specifies the latest stable Go version (currently 1.24+).

## Workflow

### 1. Determine Scope
Ask the user: "Is this a simple tool, a library, or a multi-service repo?"

### 2. Select and Use Template
**MANDATORY**: You MUST read and use the templates provided in the `assets/` directory. They establish idiomatic patterns like graceful shutdown, `run` functions, and package separation.

*   **Simple CLI / Tool**: `assets/cli-simple`. Flat structure.
*   **Cobra CLI**: `assets/cli-cobra`. For complex CLI tools.
*   **Library**: `assets/library`. Package in root, `internal/` for hidden logic.
*   **Application / Service**: `assets/webservice`.
    *   `cmd/app-name/main.go`: Entry point using the `run` function pattern.
    *   `internal/`: Private application logic.
*   **MCP Server**: `assets/mcp-server`.
*   **Game**: `assets/game`. Using Ebitengine.

### 3. Initialize
1.  **Create Directory**: `mkdir my-app`
2.  **Init Module**: `go mod init github.com/user/my-app`
3.  **Linting**: (Optional) Initialize `.golangci.yml` if the project requires rigorous style enforcement.
4.  **Apply Template**: Copy and adapt the files from the chosen template in `assets/`. Ensure module names are updated.
5.  **Verify**: Run `go mod tidy` and `go build ./...`.

## References
*   `references/project_layout.md`: Official Go Module Layout guide.
