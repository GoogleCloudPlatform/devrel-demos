# GoDoctor Profiles & Tool Availability

This document lists the tools available in each of the GoDoctor server profiles, generated using the `--list-tools` flag.

## 1. Standard Profile (`--profile=standard`)
*The default profile. Balanced for general coding tasks.*

**Count:** 10 Tools

| Tool | Description |
| :--- | :--- |
| **`ask_specialist`** | Autonomous investigator for complex queries. |
| **`code_outline`** | Returns file skeleton (declarations only). |
| **`edit_code`** | (Fallback) Basic fuzzy edit. |
| **`go_build`** | Runs `go build`. |
| **`go_test`** | Runs `go test`. |
| **`inspect_symbol`** | Deep semantic inspection of symbols. |
| **`list_files`** | Recursively lists project files. |
| **`read_code`** | Reads full file content with symbol extraction. |
| **`read_docs`** | High-level module documentation map. |
| **`smart_edit`** | Advanced "Senior Dev" editor with pre-verification. |

---

## 2. Full Profile (`--profile=full`)
*Enables all experimental and legacy features. The "Kitchen Sink".*

**Count:** 19 Tools

**Includes all Standard tools plus:**
| Tool | Description |
| :--- | :--- |
| **`analyze_dependency_updates`** | Checks for API breaking changes. |
| **`analyze_project`** | (Placeholder) Project mental mapping. |
| **`ask_the_master_gopher`** | Dynamic tool unlocking agent. |
| **`go_install`** | Runs `go install`. |
| **`modernize`** | Auto-upgrades old Go patterns. |
| **`open`** | "Satellite View" (lightweight read). |
| **`rename_symbol`** | Safe refactoring via `gopls`. |
| **`review_code`** | AI-powered code review. |
| **`write`** | Creates NEW files (distinct from edit). |

---

## 3. Oracle Profile (`--profile=oracle`)
*Forced Agentic Flow. The user sees only one tool.*

**Count:** 1 Tool

| Tool | Description |
| :--- | :--- |
| **`ask_specialist`** | The specialist autonomously decides which hidden tools to use to solve the problem. |

---

## 4. Dynamic Profile (`--profile=dynamic`)
*The "Master Gopher" Flow. Starts minimal, unlocks tools on demand.*

**Count:** 1 Tool

| Tool | Description |
| :--- | :--- |
| **`ask_the_master_gopher`** | The Master Gopher reviews the request and dynamically **unlocks** the appropriate subset of tools for the session. |

## 5. Tool Availability Matrix

| Tool | Title | Description | Standard | Full | Oracle | Dynamic |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| `analyze_dependency_updates` | Analyze Dependency Updates | Checks for breaking changes in your Go packages or dependencies. Wrapper around 'apidiff'. useful before upgrading dependencies or releasing new versions. | - | ✅ | - | - |
| `analyze_project` | Analyze Project | Use this first when joining a new project to get a mental map. | - | ✅ | - | - |
| `ask_specialist` | Ask Specialist | Ask a complex question. The specialist will autonomously use other tools (read docs, inspect code, run tests) to investigate and answer. | ✅ | ✅ | ✅ | - |
| `ask_the_master_gopher` | Ask The Master Gopher | Consult the Master Gopher for guidance. Use this when you are unsure which tool to use or how to solve a problem. The Master will review your request, unlock appropriate capabilities in the server, and give you wise instructions. | - | ✅ | - | ✅ |
| `code_outline` | Code Outline | Returns the skeleton of a Go file (declarations without function bodies) and a summary of external imports. | ✅ | ✅ | - | - |
| `edit_code` | Edit Code | Smartly edits a Go file (*.go) with fuzzy matching and safety checks. | ✅ | ✅ | - | - |
| `go_build` | Go Build | Runs 'go build' to compile packages and generate binaries. | ✅ | ✅ | - | - |
| `go_install` | Go Install | Runs 'go install' to install packages. | - | ✅ | - | - |
| `go_test` | Go Test | Runs 'go test' on specified packages/tests. Use this to verify your changes. | ✅ | ✅ | - | - |
| `inspect_symbol` | Inspect Symbol | Returns detailed information about a symbol (signature, documentation, source code, references). Prioritizes local source code over external documentation. | ✅ | ✅ | - | - |
| `list_files` | List Files | Lists files in a directory recursively. Useful for exploring project structure. Supports max depth and ignore patterns. | ✅ | ✅ | - | - |
| `modernize` | Modernize Go Code | Runs the 'modernize' analyzer to suggest and apply updates for newer Go versions (e.g. replacing s[i:len(s)] with s[i:], using min/max/slices/maps packages). | - | ✅ | - | - |
| `open` | Open File (Satellite View) | Entry Point. Returns a lightweight skeleton of a Go file (imports and signatures only). Use this for 'Satellite View' exploration to save tokens and avoid context noise compared to reading the full file. | - | ✅ | - | - |
| `read_code` | Read Code | Reads a Go file (*.go) and extracts a symbol table (functions, types, variables). | ✅ | ✅ | - | - |
| `read_docs` | Read Documentation | The high-level map builder. Lists all sub-packages and exported symbols in a module. Use this FIRST to visualize the codebase structure without flooding your context window. Supports Markdown (default) and JSON. | ✅ | ✅ | - | - |
| `rename_symbol` | Rename Symbol | Renames a symbol refactoring-style using 'gopls'. Updates all references safely. | - | ✅ | - | - |
| `review_code` | Review Go Code | Reviews Go code for correctness, style, and idiomatic usage. | - | ✅ | - | - |
| `smart_edit` | Smart Edit (Fuzzy Patch) | The 'Senior Dev' editor. Uses fuzzy-matching to patch specific code blocks. It auto-formats, updates imports, and PRE-COMPILES your change to catch errors before saving. Use this to safely modify large files. | ✅ | ✅ | - | - |
| `write` | Write New Go File | The context-aware builder. Use this to create NEW Go files. It automatically handles import validation against the current project context. For existing files, use 'edit' instead. | - | ✅ | - | - |
