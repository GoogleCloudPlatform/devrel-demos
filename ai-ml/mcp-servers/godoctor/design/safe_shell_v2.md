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
        "description": "The binary to run. No shell metacharacters."
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
      "stdout_file": {
        "type": "string",
        "description": "Path to write stdout to. Required for background tasks."
      },
      "stderr_file": {
        "type": "string",
        "description": "Path to write stderr to. If not provided, stderr is merged into stdout_file. To discard stderr, use '/dev/null'."
      },
      "background": {
        "type": "boolean",
        "description": "If true, starts the process and returns immediately (PID returned). You must use stdout_file/stderr_file to capture output. (Default: false)"
      },
      "keep_alive": {
        "type": "integer",
        "description": "Duration in seconds. Blocking mode: process is Killed (SIGKILL) after this time. Background mode: acts as a timeout signal (SIGKILL) if process exceeds duration. Default: 5s."
      }
    },
    "required": ["command"]
  }
}
```

### 2. Output Logic

| Mode | `background` | `stdout_file` | `stderr_file` | Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Interactive** | `false` | (Optional) | (Optional) | Run, feed `input`, wait. Output captured in memory (merged if no stderr_file) + written to files if provided. |
| **Daemon (Explicit)** | `true` | `/tmp/out.log` | `/tmp/err.log` | Start & Detach. Stdout -> out.log, Stderr -> err.log. |
| **Daemon (Merged)** | `true` | `/tmp/all.log` | (Omitted) | Start & Detach. Stdout & Stderr -> all.log. |
| **Daemon (Discard)** | `true` | `/tmp/out.log` | `/dev/null` | Start & Detach. Stdout -> out.log, Stderr -> discarded. |

### 3. Background Output Strategy
When `background=true`, the tool returns immediately. The output content in the tool result will be a JSON object pointing to the logs.

*   **Return Format**:
    ```json
    {
      "pid": 12345,
      "stdout_path": "/path/to/stdout.log",
      "stderr_path": "/path/to/stderr.log"
    }
    ```

## Migration Plan
1.  **Refactor**: Update `cmd/run/run.go` to rename `output_file` to `stdout_file` and handle the new `Params` struct.
2.  **Logic**: Implement `handleBlocking` and `handleBackground` logic branches.
3.  **Logs**: Ensure the temp directory exists and is writable.
