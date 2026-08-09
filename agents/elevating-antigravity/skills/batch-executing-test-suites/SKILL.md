---
name: batch-executing-test-suites
description: Orchestrates parallel test suite execution across isolated workspace branches by registering a custom test_suite_runner subagent via define_subagent and dispatching parallel workers via invoke_subagent. Use when batch executing test suites and analyzing test failures.
---

# Batch Executing Test Suites

Orchestrates multi-agent parallel test execution across isolated workspace branches using custom subagent definition and concurrent dispatch.

---

## Workflow Steps

### 1. Register Custom Worker Subagent (`define_subagent`)

Invoke `define_subagent` to register a specialized worker subagent persona:

- **name**: `test_suite_runner`
- **description**: "Specialized test runner and diagnostic subagent that executes test suites, parses stack traces, isolates root causes, and generates fix recommendations."
- **system_prompt**: "You are a specialized Test Runner and Diagnostic Subagent. Execute assigned test suites in your workspace branch, parse failure stack traces, inspect affected source files to isolate root causes, and write a structured execution report to `reports/tests/<suite_name>.md`. Return a Markdown summary with pass/fail counts, key stack traces, and actionable root-cause diagnoses."
- **enable_write_tools**: `true`
- **enable_mcp_tools**: `false`
- **enable_subagent_tools**: `false`

---

### 2. Dispatch Parallel Workers (`invoke_subagent`)

Identify target test suites from the user request or project configuration (e.g., Unit, Integration, E2E, API Contract, Security).

Dispatch all workers concurrently in a single `invoke_subagent` call with `"Workspace": "branch"`:

- **TypeName**: `"test_suite_runner"`
- **Role**: `<Suite Name> Runner`
- **Prompt**: Specify the test command to execute, stack trace parsing directives, root-cause inspection rules, and report path (`reports/tests/<suite_name>.md`).
- **Workspace**: `"branch"`

---

### 3. Aggregate & Report Test Results

Upon receiving completion callbacks from all background subagents:

1. Verify execution reports exist under `reports/tests/`.
2. Parse overall pass/fail metrics, execution durations, and root-cause failure stack traces.
3. Present a consolidated test suite matrix to the user with actionable diagnostic summaries and clickable report links.
