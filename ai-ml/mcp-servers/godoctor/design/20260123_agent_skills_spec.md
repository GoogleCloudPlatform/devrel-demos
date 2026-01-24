# Godoctor Agent Skills Specification

**Date:** 2026-01-23
**Status:** Updated

## Objective
To define a set of "Agent Skills" for the `godoctor` extension. These skills encapsulate specialized knowledge about Go software development, allowing the agent to switch context and become an expert in specific phases of the SDLC.

## Sources & Philosophy
The skills are derived from:
- **Project Layout:** Standard Go Project Layout & Ardan Labs (Package Oriented Design).
- **HTTP Services:** Grafana's "Writing HTTP Services after 13 years".
- **Code Quality:** Effective Go, Go Code Review Comments, Google Style Guide.
- **Testing:** Standard library best practices (Mitchell Hashimoto & Mat Ryer).
- **Hallucination Prevention:** Strict "Documentation First" approach for dependencies.

---

## 1. Skill: `go-architect`
**Focus:** Project Scaffolding, Layout, and Dependency Management.
**Triggers:** "Create a new project", "Structure this app", "Where should I put this file?"

### Specialist Knowledge
- **Layout:** Enforce the standard layout (`cmd/`, `internal/`).
- **Domain-Driven:** Group by feature/domain rather than technical layer.
- **Dependency Injection:** Explicitly pass dependencies to constructors; avoid globals.
- **Initialization:** Use a `run()` function pattern in `main` that takes `ctx`, `args`, and `env`.
- **Dependency Safety:** ALWAYS fetch documentation for new packages before using them. Prefer `go_get` for its auto-doc feature.
- **ADR Methodology:** Mandate the creation of Architecture Decision Records (ADRs) for significant changes. Use a standard format (Status, Context, Options, Decision, Consequences) to prevent "short memory".

### Relevant Tools
- `file_create`, `safe_shell`, `go_get`, `go_docs`.

---

## 2. Skill: `go-backend-dev`
**Focus:** Implementing HTTP Servers, APIs, and Business Logic.
**Triggers:** "Add an endpoint", "Create a handler", "Write an API".

### Specialist Knowledge (Grafana & Modern Patterns)
- **Handler Signature:** Handlers should return `error` and use wrappers for HTTP response logic.
- **Encoding/Decoding:** Use generic helpers for JSON interaction.
- **Routing:** Centralize in a `routes.go` file.
- **Context Propagation:** Always respect `r.Context()`.
- **Hallucination Mitigation:** Never guess APIs. When adding a library, read `go_docs` first to verify method names and signatures.
- **Definition of Done:** Mandatory: Compile -> Test -> Lint (`go vet`) -> Verify Binary -> **Update Docs** (README/Context).

### Relevant Tools
- `file_edit` (Append Mode), `file_read`, `go_get`, `go_docs`.

---

## 3. Skill: `go-test-expert`
**Focus:** Unit Testing, Integration Testing, and Benchmarking.
**Triggers:** "Write a test", "Fix this bug", "Why is this failing?", "Benchmark this".

### Specialist Knowledge
- **Table-Driven Tests:** MANDATORY for logical functions.
- **HTTP Testing:** Test handlers directly with `httptest.NewRequest` and `httptest.NewRecorder`.
- **Quality Gates:** Enforce `go vet`, binary verification, and regression testing (run all tests).
- **Advanced Patterns (MitchellH):**
    - **Golden Files:** For complex outputs.
    - **Test Helpers:** Pass `*testing.T` and return cleanup closures.
    - **Real Connections:** Use loopback listeners instead of `net.Conn` mocks.
    - **Subprocesses:** Use the `GO_WANT_HELPER_PROCESS` pattern.

### Relevant Tools
- `go_test`, `file_edit`, `file_create`.

---

## 4. Skill: `go-reviewer`
**Focus:** Code Quality, Refactoring, and Idiomatic correctness.
**Triggers:** "Review my code", "Is this idiomatic?", "Refactor this".

### Specialist Knowledge (CodeReviewComments & Proverbs)
- **Interfaces:** Define where used. Return concrete types.
- **Concurrency:** "Share memory by communicating." Check for goroutine leaks.
- **Errors:** Errors are values. lowercase error strings without punctuation.
- **Naming:** Short names for short scopes. `MixedCaps`. Acronym preservation.
- **Complexity:** "Clear is better than clever."

### Relevant Tools
- `code_review`, `go_modernize`, `symbol_inspect`, `go_diff`.

---

## Implementation Strategy
We will create a `skills/` directory in the extension root with a folder for each skill containing a `SKILL.md`.

Example Path: `skills/go-architect/SKILL.md`