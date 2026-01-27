# Gopls Integration Strategy (Future Vision)

**Date:** 2026-01-23
**Status:** Strategic Vision

## 1. The Opportunity
`gopls` (the Go Language Server) provides a standardized, robust, and maintained implementation of the "Language Intelligence" features that `godoctor` currently partially re-implements.

By integrating `gopls` as a managed subprocess (LSP Client), we can:
1.  **Reduce Maintenance:** Delete our custom `internal/graph` and `internal/godoc` parsing logic.
2.  **Increase Accuracy:** `gopls` is the gold standard for Go semantics.
3.  **Unlock Features:** Get "Find References", "Rename", "Signature Help", and "Diagnostics" for free.

## 2. Potential Replacements

| Current `godoctor` Tool | `gopls` Capability | Impact |
| :--- | :--- | :--- |
| `symbol_inspect` | `textDocument/definition` + `textDocument/hover` | **Replace.** `gopls` handles jump-to-def and docs perfectly. |
| `file_outline` | `textDocument/documentSymbol` | **Replace.** `gopls` returns a hierarchy of symbols (Structs, Methods) natively. |
| `symbol_rename` | `textDocument/rename` | **Wrap.** We currently wrap the CLI; wrapping the LSP command is faster and safer. |
| `search_code` (Proposed) | `workspace/symbol` | **Enhance.** `gopls` can find symbols by name instantly across the workspace. |
| `verify_build` (Partially) | `textDocument/publishDiagnostics` | **Enhance.** `gopls` pushes compile errors (diagnostics) in real-time without running `go build`. |

## 3. Implementation Strategy

### A. Managed Session
Instead of spawning `gopls` for one-off CLI commands, `godoctor` would start `gopls` as a long-running subprocess and communicate via JSON-RPC 2.0 over Stdio.

### B. Virtual Filesystem
We can use LSP `didChange` notifications to send file edits *before* saving them to disk. This allows `godoctor` to "preview" the impact of an edit (compilation errors) without touching the disk, enabling a true "Sandboxed Edit" mode.

## 4. Risks & Challenges
1.  **State Management:** Keeping the LSP session in sync with disk changes.
2.  **Complexity:** Implementing a full LSP client is non-trivial compared to simple CLI wrapping.
3.  **Startup Latency:** `gopls` takes time to initialize the workspace cache.

## 5. Roadmap
1.  **v0.10.x:** Stick to current implementations.
2.  **v0.11.0:** Experimental `gopls` sidecar for `symbol_inspect`.
3.  **v1.0.0:** Deprecate custom graph; fully rely on `gopls`.
