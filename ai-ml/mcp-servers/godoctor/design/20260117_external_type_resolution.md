# Proposal: External Type Resolution in `file_read`

## Goal
Provide LLM agents with the necessary context about external dependencies used in a file without requiring them to manually probe other packages. This "Smart Read" capability significantly reduces the "blind exploration" phase of coding tasks.

## Design

### 1. Data Source
The feature will leverage the existing `golang.org/x/tools/go/packages` integration in `checkAnalysis`. By requesting `packages.NeedTypesInfo`, we gain access to the `Uses` map, which links every identifier in the AST to its corresponding type object.

### 2. Extraction Logic
When performing a **Full Read** of a Go file:
1.  Walk the AST of the file.
2.  For every identifier, look up its definition in `pkg.TypesInfo.Uses`.
3.  Filter for symbols where `obj.Pkg() != nil` and `obj.Pkg() != currentPkg`.
4.  Optionally filter out standard library symbols (e.g., `fmt.Println`) unless they are complex, to keep the output concise.
5.  Collect the `obj.Name()`, `obj.Pkg().Path()`, and the formatted type string (`obj.Type().String()`).

### 3. Output Format
Append a new section to the `file_read` response:

```markdown
## External Context
The following external symbols are referenced in this file:

| Symbol | Package | Signature/Type |
| :--- | :--- | :--- |
| `User` | `github.com/org/repo/internal/models` | `type User struct { ... }` |
| `GetAuth` | `github.com/org/repo/internal/auth` | `func GetAuth(ctx context.Context) (*Session, error)` |
```

## Benefits
*   **Reduced Latency:** The agent understands API signatures immediately upon reading the file.
*   **Token Efficiency:** Avoids multiple rounds of `go_docs` or `symbol_inspect`.
*   **Accuracy:** Prevents agents from hallucinating method names or argument types for external dependencies.

## Challenges
*   **Verbosity:** Large files with many dependencies could produce a very long table. We may need to deduplicate and potentially cap the number of symbols shown.
*   **Standard Library Noise:** We should likely exclude `fmt`, `errors`, `context`, etc., by default to focus on project-specific logic.
