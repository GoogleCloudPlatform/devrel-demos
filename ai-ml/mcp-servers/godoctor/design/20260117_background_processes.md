# Specification: Background Processes and Safe PID Tracking

## Goal
Allow agents to start long-running processes (like servers or background workers) and safely terminate them using the `kill` command.

## Architecture

### 1. State Management
The `run` tool package will maintain an in-memory `ProcessRegistry`.
```go
var activeProcesses = make(map[int]*exec.Cmd)
var mu sync.Mutex
```

### 2. `safe_shell` Upgrades
Update `Params` in `internal/tools/cmd/run/run.go`:
*   Add `Background bool`: If true, the tool will `Start()` the process but not `Wait()` for it.
*   **Validation:** If `Background` is true, `OutputFile` becomes **required** to ensure logs are captured even after the MCP call returns.

**Behavior:**
1.  Generate a unique ID (PID).
2.  Start the process.
3.  Add the `*exec.Cmd` to the `activeProcesses` map.
4.  Return immediately with a message: `Background process started with PID: 12345`.

### 3. Safe `kill` Implementation
Remove `kill` from the `commandDenyList`.

**Validation Logic in `validateCommand`:**
1.  Intercept `kill` command.
2.  Extract the target PID from the arguments.
3.  Verify the PID exists in `activeProcesses`.
4.  If verified, allow the execution.
5.  On success, remove the PID from `activeProcesses`.

## Benefits
*   **Self-Service Testing:** Agents can spin up a server, test it with `curl`, and shut it down.
*   **Safety:** The agent cannot kill system processes, other users' processes, or the `godoctor` server itself.
*   **Automation:** Prevents "zombie" processes from being left behind after an agent finishes its task.

## Future Considerations
*   **Auto-Cleanup:** Automatically kill all processes in the `activeProcesses` map when the MCP session ends or the server shuts down.
*   **Status Tool:** Create a `cmd_status` tool to list all currently running background processes and their durations.
