# Holistic Project Assessment: GoDoctor v0.10.0+

**Date:** 2026-01-23
**Status:** Review

## 1. The Core Value Proposition
`godoctor` aims to be a **"Senior Go Engineer in a Box"** for LLMs.
It moves beyond simple file I/O to provide *language-aware* capabilities (Symbol Intelligence, Test Reporting, Auto-Formatting).

## 2. The Trinity Analysis (Tools, Skills, Prompts)

### A. Tools (11) - The "Hands"
**State:** Strong, transitioning to "Intent-Driven".
*   **Strengths:** `smart_edit` (Levenshtein) and `test_project` (Smart Reporting) are high-value differentiators. They solve specific LLM failure modes (typos, context flooding).
*   **Weakness:** Still reliance on external binaries (`gopls`, `apidiff`) without fully integrated management (yet).
*   **Coverage:** Excellent across the lifecycle (Create -> Edit -> Build -> Test -> Refactor).

### B. Skills (4) - The "Brain"
We have 4 specialized personas:
1.  `go-architect`: Structure & Layout.
2.  `go-backend-dev`: API & Service implementation.
3.  `go-reviewer`: Code quality & Idioms.
4.  `go-test-expert`: Testing patterns.

**Alignment:**
*   `go-test-expert` heavily leverages `verify_tests` (was `go_test`). **Good alignment.**
*   `go-reviewer` aligns with `code_review` (Agent) and `explain_symbol`. **Good alignment.**
*   `go-architect` needs `list_files` and `file_create`. **Good alignment.**
*   **Gap:** `go-backend-dev` relies on generic coding. It could benefit from a prompt/tool that generates *idiomatic* handlers or standard middleware stacks (scaffolding).

### C. Prompts (1) - The "Context"
We have only **1 prompt**: `import_this`.
*   **Function:** Ingests 7 high-value Go philosophy documents (Effective Go, Proverbs, etc.).
*   **Assessment:** This is a **"Nuclear Option"** for context loading. It's powerful but heavy.
*   **Gap:** We lack granular prompts.
    *   *Missing:* `scaffold_service` (Setup standard HTTP service layout).
    *   *Missing:* `explain_error` (Ingest a compiler error and teach the LLM *why* it happened using Go spec).

## 3. Cohesion Check

| Component | Status | Comment |
| :--- | :--- | :--- |
| **Tools** | 🟢 Mature | Renaming to "Intent-Driven" will fix the last UX friction. |
| **Skills** | 🟡 Good | Definitions are solid, but could explicitly *call* specific tools in their instructions. |
| **Prompts** | 🔴 Thin | 1 prompt is not enough for a "suite". We rely too much on the LLM's raw training. |

## 4. Strategic Recommendations

### 1. "Skill-Tool Binding"
Update the `SKILL.md` files to explicitly recommend the new tool names.
*   *Example:* `go-test-expert` should explicitly say: "Always use `test_project(coverage=true)` to establish a baseline."

### 2. Prompt Expansion
Add lightweight prompts to bootstrap common tasks without "reading the internet".
*   `new_http_service`: Generates `main.go`, `handler.go`, `server.go` stubs.
*   `test_table_driven`: Generates a table-driven test template for a selected function.

### 3. "Smart" Evolution
The move to **Intent-Driven** tools (`smart_read`, `smart_edit`) is the right direction. It shifts the burden of "how to use the tool" from the prompt to the code.

## 5. Conclusion
We have a Ferrari engine (Tools) and a professional driver (Skills), but we are missing the GPS (Prompts) to guide them to specific destinations quickly. The platform is solid; the "Application Layer" (Prompts/Templates) needs the next focus.
