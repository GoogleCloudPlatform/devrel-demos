# Comprehensive Go Coding Instructions for LLMs

This document provides a comprehensive set of instructions for Large Language Models (LLMs) on how to write idiomatic, maintainable, testable, and easy-to-read Go code. It synthesizes best practices from official Go documentation, style guides, and community wisdom.

## 1. Guiding Principles & Philosophy

These are the core tenets of Go development.

*   **Simplicity is Key**: "Clear is better than clever." Write simple, straightforward code. Avoid unnecessary complexity and clever tricks. Reflection, for instance, is powerful but often obscures the code's intent ("Reflection is never clear").
*   **Communicate by Sharing Memory**: "Don't communicate by sharing memory, share memory by communicating." Use channels to manage concurrency and data exchange between goroutines. Mutexes are for serializing access, while channels are for orchestration.
*   **Concurrency is not Parallelism**: Understand the distinction. Concurrency is about dealing with lots of things at once. Parallelism is about doing lots of things at once.
*   **Embrace the Zero Value**: "Make the zero value useful." Design your types so that their zero value is meaningful and ready to use without explicit initialization.
*   **A Little Copying is Better than a Little Dependency**: Avoid unnecessary dependencies. Sometimes, copying a small amount of code is better than introducing a new dependency.
*   **Don't Panic**: Use `panic` only for truly unrecoverable errors that should halt the program, such as during initialization. For all other error handling, use Go's `error` return values.

## 2. Project & Package Organization

A well-organized project is easier to navigate and maintain.

### Project Structure

Follow the standard Go module layout conventions.

*   **`cmd/`**: Contains the `main` packages for the executables in your project. Each subdirectory within `cmd/` should correspond to a single executable.
*   **`internal/`**: For packages that are internal to your project. The Go compiler enforces that these packages cannot be imported by external modules. This is the ideal place for your application-specific business logic.

### Package Design ("Package Oriented Design")

*   **Package Names**: Should be short, concise, lowercase, and single-word. Avoid generic names like `util`, `common`, or `helpers`. The package name is part of the identifier, so `chubby.File` is better than `chubby.ChubbyFile`.
*   **Package Cohesion**: A package should have a clear purpose. Group related functionality together.
*   **Dependencies**:
    *   Packages in `internal/` should not import each other if they are at the same level. If one needs to import another, consider restructuring.
    *   Packages in `internal/platform` (for foundational code like database access) should not import packages from the rest of `internal/`.
*   **Policy**: Foundational packages (like in a `kit/` project or `internal/platform`) should not set application-level policy. They should not log directly but can provide hooks for logging. Configuration should be decoupled.

## 3. Formatting & Naming Conventions

Consistency in formatting and naming is crucial for readability.

*   **`gofmt` is Law**: Always format your code with `gofmt` or `goimports`. This is non-negotiable.
*   **Variable Names**:
    *   Short variable names are idiomatic, especially for local variables with a limited scope (e.g., `i` for a loop index, `r` for a reader).
    *   The further a variable is from its declaration, the more descriptive its name should be.
    *   Method receiver names should be short (one or two letters) and consistent across all methods for a given type (e.g., `c` or `cl` for `Client`). Do not use `this`, `self`, or `me`.
*   **Initialisms**: Words that are initialisms or acronyms (like URL, NATO, ID) should have a consistent case. Write `URL` or `url`, not `Url`. For example, `ServeHTTP`, `appID`.
*   **MixedCaps**: Use `MixedCaps` or `mixedCaps` for multi-word names. Unexported constants should be `maxLength`, not `MaxLength` or `MAX_LENGTH`.
*   **Line Length**: There is no strict line length limit. Let `gofmt` handle it. If a line is too long, it's often a sign that your names are too long or your logic is too nested.

## 4. API Design & Interfaces

Design clean and intuitive APIs.

*   **Interfaces**:
    *   "The bigger the interface, the weaker the abstraction." Prefer small, single-method interfaces. Name them with the `-er` suffix (e.g., `Reader`, `Writer`).
    *   Interfaces belong in the package that *uses* them, not the package that *implements* them. This allows for decoupling and easier testing.
    *   Do not define interfaces "for mocking" on the implementor side. The consumer should define the interface it needs.
*   **Function Signatures**:
    *   **Return Values**: Use multiple return values to return a result and an error.
    *   **Named Result Parameters**: Use them sparingly. They can be useful if the meaning of a result isn't clear from the context, but don't use them just to avoid declaring a variable inside the function. Naked returns are acceptable only in very short functions.
    *   **Passing Pointers**: Don't pass pointers to save a few bytes. Pass values unless you need to modify the original value. This does not apply to large structs.
*   **Receiver Type (Value vs. Pointer)**:
    *   If the method needs to modify the receiver, it *must* be a pointer.
    *   If the receiver is a struct with a `sync.Mutex` or similar, it *must* be a pointer to avoid copying the lock.
    *   If the receiver is a large struct or array, a pointer is more efficient.
    *   If the receiver is a map, func, or chan, do not use a pointer to it.
    *   Be consistent. If some methods have pointer receivers, all methods for that type should have pointer receivers.
    *   When in doubt, use a pointer receiver.

## 5. Error Handling

Robust error handling is a hallmark of good Go code.

*   **Errors are Values**: Treat errors as regular values.
*   **Handle Errors Gracefully**: "Don't just check errors, handle them gracefully." Do not discard errors using `_`. If a function returns an error, check it. Handle it, return it, or, in truly exceptional cases, panic.
*   **Error Strings**: Should not be capitalized or end with punctuation. They are often part of a larger context.
*   **Wrapping Errors**: When returning an error from a lower level, add context using `fmt.Errorf` with the `%w` verb (available since Go 1.13) or a similar library. This preserves the original error for inspection.
*   **Indent Error Flow**: Handle errors first, then continue with the normal code path. This keeps the "happy path" at a minimal indentation level and improves readability.

```go
// Good
x, err := f()
if err != nil {
    // handle error
    return
}
// use x

// Bad
if err != nil {
    // handle error
} else {
    // normal code
}
```

## 6. Concurrency

Go's concurrency features are powerful but require care.

*   **Goroutine Lifetimes**: When you start a goroutine, know when it will end. Leaked goroutines can cause serious problems.
*   **Channels**: Use channels for communication and synchronization between goroutines.
*   **Contexts**: Use `context.Context` to manage deadlines, cancellation signals, and other request-scoped values across API boundaries.
    *   Accept a `Context` as the first argument to a function.
    *   Do not store a `Context` inside a struct. Pass it explicitly to methods.
*   **Synchronous Functions**: Prefer synchronous functions over asynchronous ones. They are easier to reason about and test. The caller can always add concurrency by running the function in a goroutine.

## 7. HTTP Services

Specific patterns for building robust HTTP services.

*   **`main` calls `run`**: Keep `func main()` minimal. It should call a `run` function that takes dependencies like `os.Args`, `os.Stdout`, etc. This makes the application easier to test.
*   **NewServer Constructor**: Create a constructor function (e.g., `NewServer`) that takes all dependencies as arguments and returns the main `http.Handler`. This is where you set up routing, middleware, etc.
*   **Centralized Routing**: Define all your API routes in one place (e.g., a `routes.go` file or a `routes()` method on your server struct).
*   **Graceful Shutdown**: Use `context` to signal shutdown to your server and other long-running processes.
*   **Helper Functions**: Use helper functions for common tasks like JSON encoding/decoding and validation.
*   **Middleware**: Use the adapter pattern for middleware: a function that takes an `http.Handler` and returns a new `http.Handler`.

## 8. Testing

Write tests to ensure your code is correct and maintainable.

*   **Useful Test Failures**: Test failures should be informative. State what was wrong, the inputs, the actual result, and the expected result.
*   **Table-Driven Tests**: Use table-driven tests to cover multiple cases concisely.
*   **Test Helpers**: When using test helpers, ensure they produce useful error messages.
*   **Focus**:
    *   In foundational packages (`kit/`, `internal/platform/`), focus on unit tests.
    *   In `cmd/`, focus on integration tests.

## 9. Comments & Documentation

Good documentation is essential for maintainability.

*   **Doc Comments**: All top-level, exported names should have doc comments.
*   **Comment Sentences**: Doc comments should be full sentences, starting with the name of the thing being described and ending with a period.
*   **Package Comments**: Every package should have a package comment, a block comment preceding the `package` clause.

## 10. Security

*   **Use `crypto/rand`**: For generating keys or any other security-sensitive random data, always use `crypto/rand`, not `math/rand`.

## 11. Tooling

*   **`goimports`**: Use `goimports` to automatically format your code and manage imports. It's a superset of `gofmt`.
