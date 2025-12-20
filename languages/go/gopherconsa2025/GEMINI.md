# Go Development Guidelines
All code contributed to this project must adhere to the following principles.

### 1. Formatting
All Go code **must** be formatted with `gofmt` before being submitted.

### 2. Naming Conventions
- **Packages:** Use short, concise, all-lowercase names.
- **Variables, Functions, and Methods:** Use `camelCase` for unexported identifiers and `PascalCase` for exported identifiers.
- **Interfaces:** Name interfaces for what they do (e.g., `io.Reader`), not with a prefix like `I`.

### 3. Error Handling
- Errors are values. Do not discard them.
- Handle errors explicitly using the `if err != nil` pattern.
- Provide context to errors using `fmt.Errorf("context: %w", err)`.

### 4. Simplicity and Clarity
- "Clear is better than clever." Write code that is easy to understand.
- Avoid unnecessary complexity and abstractions.
- Prefer returning concrete types, not interfaces.

### 5. Documentation
- All exported identifiers (`PascalCase`) **must** have a doc comment.
- Comments should explain the *why*, not the *what*.

# Agent Guidelines
- **Reading URLs:** ALWAYS read URLs provided by the user. They are not optional.
