# Gemini Go Coding Style Guide

This document provides a set of guidelines for writing idiomatic, maintainable, testable, and easy-to-read Go code. It is based on a collection of best practices from the Go community, including "Effective Go," "Go Code Review Comments," the Google Go Style Guide, and other resources.

## Core Principles

These are the high-level principles that should guide your Go development. Many of these are captured in the "Go Proverbs."

*   **Simplicity:** "Clear is better than clever." Write code that is easy to understand and maintain. Avoid unnecessary complexity.
*   **Readability:** "Readability is paramount." Code is read more often than it is written. Optimize for the reader.
*   **Concurrency:** "Don't communicate by sharing memory, share memory by communicating." Use channels to manage concurrency.
*   **Interfaces:** "The bigger the interface, the weaker the abstraction." Keep interfaces small and focused.
*   **Error Handling:** "Errors are values." Handle errors explicitly and gracefully. Don't ignore them.
*   **Zero Value:** "Make the zero value useful." The zero value of a type should be a sensible default.

## Formatting and Style

Consistent formatting and style are crucial for readability.

*   **gofmt:** All Go code **must** be formatted with `gofmt`. This is not negotiable. The `goimports` tool is also recommended to automatically manage imports.
*   **Naming Conventions:**
    *   **Packages:** Package names should be short, concise, single-word, and in lowercase.
    *   **Getters:** Getters should be named `Owner()` for a field `owner`, not `GetOwner()`.
    *   **Interfaces:** One-method interfaces are often named by the method name with an "-er" suffix (e.g., `Reader`, `Writer`).
    *   **MixedCaps:** Use `MixedCaps` or `mixedCaps` for multi-word names, not underscores.
    *   **Initialisms:** Words that are initialisms or acronyms (like "URL" or "ID") should have a consistent case, such as `URL` or `id`, but not `Url`.
*   **Comments:**
    *   Document all exported names.
    *   Comments should be full sentences, starting with the name of the thing being described and ending with a period.
    *   Use `//` for comments, not `/* */`.

## Project Structure

A well-organized project is easier to navigate and maintain.

*   **`cmd/`:** Place your `main` packages in a `cmd/` directory. Each subdirectory of `cmd/` should be a separate command.
*   **`internal/`:** Place code that is not meant to be imported by other projects in an `internal/` directory. This is enforced by the Go compiler.
*   **Package-Oriented Design:**
    *   Structure your code around packages, not types. Each package should have a clear and focused purpose.
    *   A package should be a cohesive unit, with its types and functions working together to achieve a single goal.
    *   Avoid creating "utility" packages. Instead, group related functionality into well-defined packages.

## Interfaces

Interfaces are a powerful tool for decoupling code and improving testability.

*   **Implicit Implementation:** Interfaces are implemented implicitly. A type implements an interface by implementing its methods.
*   **Small Interfaces:** Prefer small, focused interfaces. This makes them easier to implement and reuse.
*   **Interface Location:** Interfaces generally belong in the package that uses them, not the package that implements them.

## Error Handling

Robust error handling is a hallmark of good Go code.

*   **Errors are Values:** Errors are just another type of value. Treat them as such.
*   **Explicit Handling:** Handle errors explicitly. Don't ignore them by assigning them to the blank identifier (`_`).
*   **Error Messages:** Error strings should not be capitalized or end with punctuation.
*   **`context.Context`:** Use `context.Context` for request-scoped values, cancellation signals, and deadlines. It should be the first parameter of a function.
*   **Panic:** Avoid using `panic` for normal error handling. `panic` should only be used for unrecoverable errors.

## Concurrency

Go's concurrency model is one of its greatest strengths.

*   **Goroutines:** Use goroutines for concurrent operations. They are lightweight and efficient.
*   **Channels:** Use channels for communication and synchronization between goroutines.
*   **`select`:** Use the `select` statement to manage multiple channels.
*   **Race Detector:** Use the race detector (`go test -race`) to identify data races in your code.

## HTTP Services

When writing HTTP services, follow these patterns for a maintainable and testable application.

*   **`NewServer` Constructor:** Create a `NewServer` constructor function that takes all dependencies as arguments and returns an `http.Handler`.
*   **Handlers as Functions:** Implement handlers as functions that return an `http.Handler`. This allows for a closure environment for each handler to manage its own state or dependencies.
*   **`routes.go`:** Define all your routes in a single `routes.go` file to provide a clear overview of your API surface.
*   **`main` and `run`:** Keep your `main` function minimal. It should call a `run` function that takes dependencies like `context.Context`, `io.Writer`, and `os.Args`. This makes your application easier to test.
*   **Middleware:** Use the adapter pattern for middleware, where a function takes an `http.Handler` and returns a new one.
*   **Testing:** Write end-to-end tests that start the server and interact with it as a real client would.

## Go Toolchain

The Go toolchain provides several essential tools for writing high-quality code.

*   **`gofmt`:** Automatically formats your code. All submitted code must be formatted with `gofmt`.
*   **`go vet`:** A static analysis tool that checks for common errors and suspicious constructs. Run this before committing changes.
*   **`go test`:** The built-in testing tool. Use it to run your tests and check for race conditions (`go test -race`).

## AI Assistant (MCP) Tooling

These tools are specific to the AI-powered development environment and are designed to augment your workflow.

*   **`gopls`:** The Go language server that powers many of the other tools. It provides code completion, navigation, and refactoring capabilities. While you may not use it directly, it's the engine behind the scenes.
*   **`go_workspace`**: Use this to get a high-level overview of the Go modules in the current workspace. This is a good first step to understand the project structure.
*   **`go_package_api`**: Use this to understand the public API of a specific package. This is useful when you need to interact with a package you are not familiar with.
*   **`go_search`**: Use this to find symbols (functions, types, variables) across the workspace. This is helpful for locating where a specific piece of functionality is defined.
*   **`go_file_context`**: Use this to understand the dependencies of a specific file. It helps to see what other parts of the codebase a file interacts with.
*   **`go_symbol_references`**: After finding a symbol with `go_search`, use this tool to find all its references. This is crucial for understanding the impact of a change.
*   **`go-doc`**: Use this to retrieve documentation for a package or a specific symbol within a package. This is useful for understanding how to use a library or function correctly.
*   **`go_diagnostics`**: Before committing any changes, run this tool to check for build and parse errors across the entire workspace. This is a critical step for ensuring code quality.
*   **`code_review`**: Before finalizing your work, use this tool to get an AI-powered code review. It will check for idiomatic Go, style issues, and potential bugs.

## Prioritization Framework

To ensure we work on the most impactful features and improvements, we use a prioritization matrix based on **Technical Certainty vs. Business Value**. This framework helps us make objective decisions about what to work on next.

### The Matrix

We categorize proposed features, improvements, and bug fixes into one of four quadrants:

1.  **Top Priority (Do Now):**
    *   **High Business Value / High Technical Certainty**
    *   These are high-impact items that we are confident we can implement correctly and efficiently. They are the top of our backlog.

2.  **Needs Exploration (Spike):**
    *   **High Business Value / Medium-to-Low Technical Certainty**
    *   These items are valuable, but there are unknowns in the implementation. Before committing to the full feature, a "spike" or research task is created to investigate the technical challenges and increase our certainty.

3.  **Optional (Do Later / Backlog):**
    *   **Low Business Value / High Technical Certainty**
    *   These are "nice-to-have" features or minor improvements that are easy to implement but are not critical. They are kept in the backlog to be worked on when time allows.

4.  **Deprioritized (Ignore):**
    *   **Low Business Value / Medium-to-Low Technical Certainty**
    *   These items provide little value and are technically challenging. They are removed from the active backlog to avoid wasting effort.

### Process

1.  All new work is first documented in the `IMPROVEMENT_REPORT.md` or a similar document.
2.  The work is then assessed and placed into the `PRIORITIZATION_MATRIX.md` file according to the framework.
3.  The development team prioritizes work from the "Top Priority" quadrant first, followed by exploration tasks from the "Needs Exploration" quadrant.

## Putting It All Together

By following these guidelines, you will write Go code that is not only correct but also idiomatic, maintainable, and a pleasure to work with. Remember to always prioritize clarity and simplicity, and to leverage the power of the Go toolchain and your AI assistant to help you along the way.