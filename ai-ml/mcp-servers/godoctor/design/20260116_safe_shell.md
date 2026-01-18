# Godoctor: Safe Shell Tool Proposal

## Problem Statement
Experiments 33 and 34 demonstrated that **unrestricted shell access (`run_shell_command`) is harmful** to agent performance (Success Rate: ~40% vs 63% without it).
- **"The Shell Trap":** Agents attempt complex, one-liner bash scripts involving pipes (`|`), redirects (`>`), and subshells. These are fragile, hard to debug, and prone to hanging (timeouts).
- **Misleading Success:** Commands like `go build` or `echo ... | ./bin` often exit with code 0 but fail to provide semantic verification.
- **Verification Gap:** Removing the shell entirely (`no-core`) prevents the agent from running the compiled binary to verify specification compliance (e.g., "Does it actually speak JSON-RPC?").

## Implementation Status (2026-01-16)
**Verified:**
*   `safe.shell` tool is active and correctly blocks `rm` (absolute paths) and `>`.
*   Nudge mechanism works for `go build` and `go test`.
*   Force flag successfully overrides validation.

**Pending (To Be Implemented):**
*   Nudge mechanism for remaining Go subcommands: `go mod`, `go get`, `go install`, `go doc`.
*   Fix for `mkdir .godoctor` read-only error on some environments.

## Proposed Solution: `safe.shell` (Restricted Execution)
A restricted execution tool designed specifically for testing and verification, not for general-purpose scripting.

### 1. Tool Specification

```json
{
  "name": "safe.shell",
  "description": "Execute a specific binary with arguments. Use this to run compilers, tests, or your compiled program. Blocks until completion or timeout. Stdout and Stderr are merged. Output is capped to prevent context flooding.",
  "parameters": {
    "type": "object",
    "properties": {
      "command": {
        "type": "string",
        "description": "The binary to run. Must be a simple executable name or relative path. No shell metacharacters allowed."
      },
      "args": {
        "type": "array",
        "items": { "type": "string" },
        "description": "List of arguments to pass to the command."
      },
      "input": {
        "type": "string",
        "description": "Optional standard input (stdin) to pass to the process. Use this instead of piping. (Equivalent to `echo '...' | cmd`)"
      },
      "output_mode": {
        "type": "string",
        "enum": ["merged", "stdout", "stderr", "separate"],
        "description": "Control how output is returned. 'merged' (default) combines both. 'separate' returns a JSON object with 'stdout' and 'stderr' fields."
      },
      "force": {
        "type": "boolean",
        "description": "Set to true to override advisory warnings (e.g. running 'grep'). This does NOT override the security Blocklist (e.g. 'git' is always blocked)."
      },
      "timeout_millis": {
        "type": "integer",
        "description": "Timeout in milliseconds (default: 5000, max: 30000)."
      }
    },
    "required": ["command"]
  }
}
```

### 2. Safety & Stability Restrictions
1.  **No Shell Interpretation:** The command should be executed directly (e.g., `exec.Command(name, args...)`), NOT via `bash -c`.
2.  **Allowed Binaries:**
    *   **Allowlist:** `go`, `cargo`, `npm`, `node`, `python`.
    *   **Local Binaries:** Allow `./*` (relative paths) to run generated artifacts.
    *   **Conditional Allow (File Ops):** `rm`, `mv`, `cp`.
        *   **Constraint:** All arguments must be relative paths resolving within the Current Working Directory (CWD). No absolute paths (`/etc/passwd`) or traversal (`../`).
3.  **Merged Output (Default):** Stdout and Stderr are combined.

4.  **Strict Blocklist (Immutable):** The following commands are **ALWAYS BLOCKED**:
    *   `git` (State mutating, complex. Use `go.get` or dedicated git tools).
    *   `sudo`, `su`, `chown`, `chmod` (Privilege escalation).
    *   `bash`, `sh`, `zsh` (Shell inception).
    *   `vi`, `nano` (Interactive editors).

5.  **Output Limits & Automagic Redirection:**
    *   **Buffer Limit:** 16KB hard limit for direct return.
    *   **Strategy:** If output exceeds 16KB, the tool will:
        1.  Stream the full output to a temporary file (via `os.CreateTemp`).
        2.  Return the **first 1KB** and **last 1KB** of the output.
        3.  Return a warning: `"Output truncated (size: X MB). Full log written to /tmp/..."`.
    *   This ensures the agent doesn't crash the context window but still captures the full logs for analysis if needed (via `file.read`).

6.  **Metacharacter Ban:** Reject `command` strings containing `|`, `>`, `<`, `&`, `;`, `$`, `` ` ``. (Structural safety).
7.  **Enforced Timeout:** Hard timeout (default 5s, max 30s) to prevent hanging processes.

### 3. Intelligent Rejection (The "Nudge" Mechanism)
Instead of silently failing or just blocking, the tool will provide *educational feedback* when the agent tries to use suboptimal tools.

**Logic:**
If `command` matches a known pattern, reject the execution and return a specific error message guiding the agent to the semantic alternative.

| Command(s) | Rejection Message | Recommended Tool |
| :--- | :--- | :--- |
| `grep`, `find`, `ack`, `ripgrep` | "Do not use grep/find for code search. It lacks context." | `file.search`, `go.docs`, or `symbol.inspect` |
| `ls`, `dir`, `tree` | "Do not use shell to list files. Use the semantic file tools." | `file.list` or `project.map` |
| `cat`, `less`, `more`, `head` | "Do not read files via shell. Use the file system tools." | `file.read` |
| `vim`, `nano`, `sed`, `awk` | "Do not edit files via shell. Use the file editor." | `file.edit` |
| `git` | "Do not use raw git commands. Use language-specific package tools." | `go.get`, `go.mod` |
| `go build` | "Use the verified 'go.build' tool." | `go.build` |
| `go test` | "Use the verified 'go.test' tool with result parsing." | `go.test` |
| `go mod`, `go get`, `go install` | "Use verified dependency tools." | `go.mod`, `go.get`, `go.install` |
| `go doc`, `go vet`, `go lint` | "Use verified doc/analysis tools." | `go.docs`, `go.lint` |

 **Example Interaction:**
> **Agent:** `safe.shell("git", ["diff"])`
> **Tool Output (Error):** `Error: Use of 'git' is strictly blocked in safe.shell. Please use specific version control tools or diff tools.`

### 4. Implementation Details
*   **External Name:** `safe.shell` (To clearly distinguish it as the "safe" alternative to `run_shell_command`).
*   **Internal Name:** `cmd.run` or `safe.shell` (TBD in Registry).

### 5. Benefits
1.  **Eliminates Syntax Errors:** No more "bash: syntax error near unexpected token".
2.  **Prevents Hanging:** Explicit timeouts and no `sleep` hacks.
3.  **Encourages Verified Tools:** Nudges agents away from `grep` toward `symbol.inspect`.
4.  **Semantic Input:** `input` field makes testing interactive CLIs explicit.
5.  **Context Safety:** Automatic output truncation prevents context explosions.
