## Gemini AI-powered assistant

This file provides instructions for the Gemini AI-powered assistant on how to work with the `speedgrapher` project.

### Project Overview

Speedgrapher is a local MCP (Model Context Protocol) server written in Go. It's designed to assist writers, especially in the tech industry, by providing a suite of tools to streamline the writing process. It uses the [official Go SDK for MCP](https://github.com/modelcontextprotocol/go-sdk) and communicates over the `stdio` transport layer.

### Development Workflow

The project uses a `Makefile` to manage common development tasks.

*   **Building the project:** To build the server, run the following command:
    ```bash
    make build
    ```
    This will create an executable at `bin/speedgrapher`.

*   **Running tests:** To run the project's tests, use the following command:
    ```bash
    make test
    ```

*   **Cleaning the project:** To remove the `bin` directory and its contents, run:
    ```bash
    make clean
    ```

### Dependencies

The main dependency for this project is the `github.com/modelcontextprotocol/go-sdk`. The project's module path is `github.com/danicat/speedgrapher`.

### Coding Style

The project follows standard Go coding conventions. Please maintain this style when adding or modifying code.

### Prompts

The server's functionality is exposed through a series of prompts. New prompts can be added in the `internal/prompts` directory. Each new prompt requires two functions:

1.  A function that defines the prompt's name, description, and arguments.
2.  A handler function that implements the prompt's logic.

After creating these two functions, you must register the new prompt in the `run` function in `cmd/speedgrapher/main.go`.

**Available Prompts:**

*   **`haiku`**: Creates a haiku about a given topic.
*   **`interview`**: Interviews an author to produce a technical blog post.
*   **`localize`**: Translates an article into a target language.
*   **`readability`**: Analyzes the last generated text for readability and suggests improvements. It uses the `fog` tool.
*   **`reflect`**: Analyzes the current session and proposes improvements to the development process.
*   **`review`**: Reviews an article against the editorial guidelines.

### Tools

The server can also expose tools to the user. New tools can be added in the `internal/tools` directory.

**Available Tools:**

*   **`fog`**: Calculates the Gunning Fog Index for a given text. The implementation uses a heuristic based on vowel groups to count syllables.

### General Development Principles

*   **Prioritize API/SDK Understanding:** Before writing code that uses an external library or SDK, I must first use documentation-lookup tools (`godoc`, `web_search`) to understand the correct API usage. I will prioritize official documentation and user-provided links.
*   **Favor Consistent Heuristics:** When implementing features based on heuristics (e.g., readability formulas), I will propose a simple, robust, and consistent algorithm first. I will explain its trade-offs and seek user approval before attempting more complex, exception-laden solutions.
*   **Trust but Verify:** I must critically evaluate all information, including user-provided test cases and my own generated text. I will use the tools at my disposal to verify data and assumptions before acting on them.
*   **Maintain an Objective Tone:** I will present facts and results objectively and avoid defensive justifications unless explicitly asked for them. My primary goal is to be a helpful, data-driven assistant.
*   **Use the Right Tool for the Job:** Prioritize built-in tools over shell commands. If a specific tool is available for a task (e.g., `gopretty`, `godoc`), use it directly instead of trying to execute it through `run_shell_command`.
*   **Always Read the README:** At the start of every session, read the `README.md` file to ensure you have the latest information about the project, especially the testing procedures.
