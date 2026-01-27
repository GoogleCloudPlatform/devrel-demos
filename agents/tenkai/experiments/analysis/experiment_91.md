# Experiment 91: GoDoctor vs Core Tools

## Overview
This experiment evaluated whether **forcing** the use of GoDoctor tools by disabling standard file editing tools (`write_file`, `replace`, `read_file`) affects agent success rates.

**Hypothesis:** Agents can successfully complete tasks using *only* GoDoctor tools for file manipulation, potentially achieving higher quality results due to the specialized nature of tools like `smart_edit`.

## Alternatives
1.  **`default`**: Gemini 3 Flash + Standard Core Tools (`write_file`, `replace`, `run_shell_command`).
2.  **`godoctor-mcp`**: GoDoctor via MCP + `run_shell_command` ONLY (Core editing tools disabled).
3.  **`godoctor-extension`**: GoDoctor via Extension + `run_shell_command` ONLY (Core editing tools disabled).

## Results

### Performance & Efficiency
| Alternative | Success Rate | Avg Duration (s) | Avg Tokens |
|---|---|---|---|
| **godoctor-mcp** | **47/50 (94%)** | 166.0 | 1.17M |
| **godoctor-extension** | **47/50 (94%)** | **162.7** | **1.19M** |
| **default** | 45/50 (90%) | 183.7 | 1.23M |

### Tool Usage Breakdown
| Alternative | Shell Calls | GoDoctor Calls | Other Calls |
|---|---|---|---|
| **godoctor-mcp** | 59% | 41% | 0% |
| **godoctor-extension** | 57% | 43% | 0% |
| **default** | 63% | 0% | 37% |

### Failure Analysis
A deeper look at the tool failure patterns reveals *why* GoDoctor outperformed the baseline.

| Metric | Default | GoDoctor (MCP/Ext) | Insight |
|---|---|---|---|
| **Test Failure Rate** | **~25%** | **~15%** | Agents using `smart_edit` and `file_create` wrote correct code on the first try significantly more often than those using `replace` and `write_file`. |
| **Command Not Found** | 26 (High) | ~14 (Low) | Most "Command Not Found" errors were for `golangci-lint`, which is not installed in the environment. |

## Key Findings

1.  **Forced Adoption Works:** Disabling core tools successfully forced the agents to use GoDoctor tools (`file_create`, `smart_edit`) without hindering performance. In fact, success rates *increased* slightly (94% vs 90%).
2.  **GoDoctor Tools are Viable Replacements:** The high success rate confirms that `file_create` and `smart_edit` are robust enough to replace `write_file` and `replace` for this class of tasks.
3.  **Efficiency Gains:** The GoDoctor alternatives were faster (~20s) and used fewer tokens than the default approach, likely because `smart_edit` handles context and imports more intelligently than raw string replacement, reducing retry loops (evident in the lower test failure rate).
4.  **Shell Usage Remains High:** Even with GoDoctor, agents rely heavily on `run_shell_command` (57-59%) for tasks like `go mod init`, `go test`, and `mkdir`. This suggests specific gaps in the toolset.

## Feature Proposals for GoDoctor

Based on the high volume of specific shell commands, we propose the following new tools/improvements to further reduce shell reliance and token usage:

1.  **`verify_lint` Tool:**
    *   **Problem:** 68 calls to `golangci-lint` resulted in a ~90% failure rate ("Command Not Found").
    *   **Solution:** A tool that runs the linter if available, or falls back to `go vet` automatically. This eliminates the "hallucinated command" error loop.
    *   **Impact:** Would save ~10 turns per failing run.

2.  **`project_init` Tool:**
    *   **Problem:** 162 calls were for the standard `go mod init` -> `go get` -> `go mod tidy` sequence.
    *   **Solution:** A single tool to initialize the module and optionally add dependencies.
    *   **Impact:** Reduces 3 shell calls to 1 tool call.

3.  **Doc Update: `file_create`:**
    *   **Problem:** 286 calls to `mkdir`. Agents defensively create directories before writing files.
    *   **Solution:** Explicitly state in the `file_create` description: *"Automatically creates parent directories."*
    *   **Impact:** Eliminates ~10% of all tool calls (shell overhead).

4.  **`read_text` Tool:**
    *   **Problem:** 258 calls to `cat`/`read`. Agents use `cat` heavily when `read_file` is disabled because `smart_read` is perceived as code-specific.
    *   **Solution:** Either re-brand `smart_read` or provide a simple `read_text` for config files (`go.mod`, `Makefile`).

## Recommendation
For future Go-specific agent configurations, we should:
1.  **Disable** `write_file`, `replace`, and `read_file`.
2.  **Enable** GoDoctor tools.
3.  **Implement** the proposed `verify_lint` and `project_init` tools in GoDoctor to close the remaining efficiency gaps.