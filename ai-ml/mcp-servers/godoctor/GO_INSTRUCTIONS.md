# Go Coding Instructions for LLMs

When generating Go code, strictly adhere to the following principles to ensure the output is idiomatic, maintainable, testable, and efficient.

## 1. Core Philosophy
- **Clear is better than clever.** Avoid complex abstractions or "magic" code (like heavy reliance on reflection) unless absolutely necessary.
- **Errors are values.** Handle them explicitly. Do not ignore errors.
- **Concurrency is not parallelism.** Use channels for orchestration and signaling; use mutexes for shared state.
- **Simplicity wins.** Prefer understandable code over highly optimized but unreadable code (unless specific performance requirements are stated).

## 2. Project Layout & Structure
Follow standard Go module layouts:
- **`cmd/`**: Main applications (e.g., `cmd/server/main.go`). The `main` package should be thin, primarily handling configuration and signal trapping.
- **`internal/`**: Private application and library code. This enforces boundaries and prevents external import of your core logic.
- **`pkg/`**: Public library code (only if explicitly designing a reusable library for other projects).
- **`api/`**: OpenAPI/Swagger specs, JSON schemas, protocol definitions.
- **Domain-Driven Design (Light):** Group code by domain/feature rather than technical layer (e.g., prefer `user/handler.go` and `user/service.go` over `handlers/user.go` and `services/user.go`).

## 3. Naming Conventions
- **Package Names:** Short, lowercase, singular, and descriptive (e.g., `transport` not `transport_layer`). Avoid `util`, `common`, `base`.
- **Variables:**
    - Short names (`ctx`, `i`, `r`) for small scopes.
    - Descriptive names (`cust`, `param`) for larger scopes.
    - `mixedCaps` for multi-word names.
- **Interfaces:**
    - Method name + `er` (e.g., `Reader`, `Writer`, `Formatter`) for single-method interfaces.
    - Defined where *used* (consumer-defined), not where implemented.
- **Getters:** `Owner` (not `GetOwner`).
- **Setters:** `SetOwner`.

## 4. Coding Style & Formatting
- **Formatting:** Always assume `gofmt` style.
- **Imports:** Group imports into standard library, third-party, and internal.
- **Variable Declaration:**
    - Use `var t []string` (nil slice) over `t := []string{}` when declaring empty slices.
    - Use `:=` for initialization inside functions.
- **Struct Initialization:** Use field names explicitly (`User{Name: "Alice"}` not `User{"Alice"}`).

## 5. Functions & Methods
- **Returns:**
    - Return concrete types (structs), accept interfaces.
    - Use named return parameters only for documentation or complex naked returns (use naked returns sparingly).
- **Context:**
    - Pass `context.Context` as the first argument to functions that involve I/O or long-running operations.
    - Never store `Context` in a struct.
- **Defer:** Use `defer` for cleanup (files, locks, connections) immediately after resource acquisition.

## 6. Error Handling
- **Check Errors:** Always check errors. `if err != nil { return err }`.
- **Wrap Errors:** Use `fmt.Errorf("doing action: %w", err)` to add context while preserving the underlying error.
- **Custom Errors:** Create custom error types only when the caller needs to distinguish them programmatically (use `errors.Is` / `errors.As`).
- **Panic/Recover:** Avoid `panic` for control flow. Only panic on unrecoverable startup errors. Use `recover` only in top-level goroutines or middleware to prevent crashes.

## 7. Concurrency
- **Signaling:** Use channels to signal ownership transfer or completion.
- **State:** Use `sync.Mutex` or `sync.RWMutex` to protect shared state.
- **Goroutines:**
    - Start goroutines only when you know how they will stop.
    - Use `errgroup` or `sync.WaitGroup` to manage groups of goroutines.
    - Avoid exposing channels in public APIs; provide synchronous APIs and let the caller decide to use concurrency.

## 8. HTTP Services (Modern Patterns)
- **Handlers:** Return `error` from handlers and use a middleware to write the HTTP response/log the error.
- **Dependencies:** Inject dependencies (logger, database, config) via a struct (e.g., `Server` struct).
- **Encoding:** Use a helper function `decode(r *http.Request, v any) error` and `encode(w http.ResponseWriter, status int, v any) error`.
- **Routes:** Centralize routing logic in a `routes.go` file.

## 9. Testing
- **Table-Driven Tests:** Use table-driven tests for almost all logic tests.
    ```go
    func TestAdd(t *testing.T) {
        tests := []struct {
            name string
            a, b int
            want int
        }{
            {"positive", 1, 2, 3},
            {"negative", -1, -1, -2},
        }
        for _, tt := range tests {
            t.Run(tt.name, func(t *testing.T) {
                if got := Add(tt.a, tt.b); got != tt.want {
                    t.Errorf("Add() = %v, want %v", got, tt.want)
                }
            })
        }
    }
    ```
- **Subtests:** Use `t.Run()` for subtests.
- **Helpers:** Use `t.Helper()` in helper functions to report errors at the call site.
- **Parallelism:** call `t.Parallel()` for independent tests.
- **External Tests:** Use `package foo_test` for integration tests to treat the package as a black box.

## 10. Dependencies
- Use standard library modules whenever possible (`net/http`, `encoding/json`, `log/slog`).
- Avoid heavy frameworks. Go libraries should be small and composable.
