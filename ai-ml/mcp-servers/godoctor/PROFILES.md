# GoDoctor Profiles & Tool Availability

This document lists the tools available in each of the GoDoctor server profiles.

## 1. Standard Profile (`--profile=standard`)
*The default profile. Balanced for general coding tasks and iterative development.*

**Count:** 11 Tools

| Tool | Title | Description |
| :--- | :--- | :--- |
| `safe_shell` | Safe Execution | Execute a specific binary with arguments. Blocks until completion or timeout. |
| `file_create` | Initialize File | Create a new source file from scratch. |
| `file_edit` | Patch File | Targeted code modification using fuzzy-matching and pre-verification. |
| `file_list` | Survey Directory | Explore the project hierarchy recursively. |
| `file_read` | Examine Content | Perform a deep read of a file with symbol extraction. |
| `go_build` | Go Build | Compiles the packages named by the import paths. |
| `go_docs` | Consult Docs | Query Go documentation for any package or symbol. |
| `go_get` | Go Get | Downloads and installs packages; updates `go.mod`. |
| `go_lint` | Go Lint | Runs 'golangci-lint' on the project. |
| `go_mod` | Go Mod | Module maintenance operations like `go mod tidy`. |
| `go_test` | Run Tests | Execute the test suite with aggregate coverage reporting. |

---

## 2. Advanced Profile (`--profile=advanced`)
*Enables all features, including specialized symbol navigation and refactoring tools.*

**Count:** 18 Tools

**Includes all Standard tools plus:**
| Tool | Title | Description |
| :--- | :--- | :--- |
| `code_review` | Request Review | Submit code for expert analysis focusing on correctness and style. |
| `file_outline` | Scan Structure | Examine the structural layout of a file (signatures only). |
| `go_diff` | Assess API Risk | Compare the public API of two versions of a package. |
| `go_install` | Go Install | Compiles and installs the package/binary to `$GOPATH/bin`. |
| `go_modernize` | Modernize Code | Automatically upgrade legacy Go patterns to modern standards. |
| `symbol_inspect` | Diagnose Symbol | Deep-dive analysis of a specific symbol (definitions and references). |
| `symbol_rename` | Refactor Symbol | Execute a safe, semantic rename of a Go identifier. |

---

## 3. Tool Availability Matrix

| Tool | Standard | Advanced |
| :--- | :---: | :---: |
| `code_review` | ❌ | ✅ |
| `safe_shell` | ✅ | ✅ |
| `file_create` | ✅ | ✅ |
| `file_edit` | ✅ | ✅ |
| `file_list` | ✅ | ✅ |
| `file_outline` | ❌ | ✅ |
| `file_read` | ✅ | ✅ |
| `go_build` | ✅ | ✅ |
| `go_diff` | ❌ | ✅ |
| `go_docs` | ✅ | ✅ |
| `go_get` | ✅ | ✅ |
| `go_install` | ❌ | ✅ |
| `go_lint` | ✅ | ✅ |
| `go_mod` | ✅ | ✅ |
| `go_modernize` | ❌ | ✅ |
| `go_test` | ✅ | ✅ |
| `symbol_inspect` | ❌ | ✅ |
| `symbol_rename` | ❌ | ✅ |