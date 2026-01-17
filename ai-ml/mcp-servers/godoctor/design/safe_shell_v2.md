# Safe Shell v2: Background & Web Testing Improvements

## Context
The initial `safe_shell` implementation solved the "EOF Panic" and "Shell Trap" issues by enforcing direct binary execution and a "Keep-Alive" strategy for interactive processes.
However, testing **long-running web services** (e.g., starting a local server to test against) requires the ability to run processes in the background without blocking the agent.

## User Requests
1.  **Rename `timeout` to `keep_alive`**: To better reflect the "run for X seconds then stop" behavior of interactive tests.
2.  **Background Execution**: A `run_in_background` flag (default `false`) to return immediately.
3.  **File Redirection**: Background processes must capture output to files for later inspection.

## Proposed Specification

### 1. Updated Schema

```json
{
  "name": "safe_shell",
  "description": "Execute a specific binary safely. Supports blocking (wait for completion) or background (start and detach) modes.",
  "parameters": {
    "type": "object",
    "properties": {
      "command": {
        "type": "string",
        "description": "The binary to run (e.g., './server', 'go'). No shell metacharacters."
      },
      "args": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Arguments for the command."
      },
      "input": {
        "type": "string",
        "description": "Stdin data to feed to the process."
      },
      "background": {
        "type": "boolean",
        "description": "If true, starts the process and returns immediately. Output is redirected to log files. (Default: false)"
      },
      "keep_alive": {
        "type": "integer",
        "description": "Duration in seconds. For blocking calls: process is killed after this time. For background: acts as a strict time-to-live (optional). Default 5s for blocking."
      }
    },
    "required": ["command"]
  }
}
```

### 2. Output Logic

| Mode | `background` | `keep_alive` | Behavior | Output |
| :--- | :--- | :--- | :--- | :--- |
| **Interactive** | `false` | `> 0` | Run, feed `input`, wait `keep_alive` seconds, then Kill. | Merged Stdout/Stderr (capped). |
| **Batch** | `false` | `0` (or omitted) | Run, feed `input`, wait until Exit. | Merged Stdout/Stderr (capped). |
| **Daemon** | `true` | `any` | Start, detach, redirect output to files. Return PID. | JSON: `{ "pid": 123, "stdout": "/tmp/out.log", "stderr": "/tmp/err.log" }` |

### 3. Background Output Strategy
When `background=true`, we cannot return the output directly because it hasn't happened yet.
*   **Redirect**: Automatically create temporary files:
    *   Stdout: `/tmp/godoctor_<pid>_stdout.log`
    *   Stderr: `/tmp/godoctor_<pid>_stderr.log`
*   **Agent Workflow**:
    1.  `safe_shell(command="./server", background=true)` -> Returns PID and log paths.
    2.  Agent does work (e.g., `run_shell_command("curl localhost:8080")`).
    3.  Agent checks logs: `safe_shell(command="cat", args=["/tmp/..._stderr.log"])` (or `file.read`).
    4.  Agent kills server: `safe_shell(command="kill", args=["<pid>"])` (Wait, `safe.shell` blocks system binaries... we might need a `stop` tool or allow `kill` in `safe.shell`).
        *   *Decision*: Add `kill` to the `safe_shell` allowlist.

## Migration Plan
1.  **Refactor**: Update `cmd/run/run.go` to handle the new `Params` struct.
2.  **Logic**: Split handler into `handleBlocking` and `handleBackground`.
3.  **Logs**: Ensure the temp directory exists and is writable.
