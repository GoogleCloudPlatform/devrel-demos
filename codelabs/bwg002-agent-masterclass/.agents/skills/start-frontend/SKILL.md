---
name: start-frontend
description: Checks if port 8080 is available, terminates any processes occupying port 8080, and starts the Pitch Generator web server on port 8080 as a background daemon process. Use when asked to run, start, restart, or test the Pitch Generator web frontend or server.
---

# Pitch Generator Start Frontend Skill

The **start-frontend** skill provides standardized instructions and utilities for managing the Pitch Generator web application server on port `8080`.

It enforces a safe lifecycle:
1. **Check**: Verify if port `8080` is free.
2. **Clean**: Terminate any lingering or rogue processes occupying port `8080`.
3. **Launch**: Start the web application server (`pitch_generator/fast_api_app.py`) on port `8080` as a background daemon process.
4. **Verify**: Confirm the server is listening and healthy, then deliver the local URL to the user.

---

## Quick Execution

Agents should use the included helper script to handle port checking, cleanup, and server startup in a single idempotent step:

```bash
# Launch the server (automatically frees port 8080 if occupied):
bash .agents/skills/start-frontend/scripts/start_server.sh
```

When executing via the `run_command` tool in Antigravity:
- Set `IsDaemon: true` so the server runs continuously in the background.
- Set `WaitMsBeforeAsync: 3000` to allow the process to initialize and output its startup banner before going asynchronous.

---

## Step-by-Step Procedure

### 1. Pre-Flight Port Check
Before launching the server, inspect whether port `8080` is occupied:

```bash
# Check if port 8080 is in use:
lsof -ti :8080
```
- If this returns empty, port 8080 is free. Proceed to Step 3.
- If this returns one or more PIDs, proceed to Step 2.

Alternatively, run:
```bash
bash .agents/skills/start-frontend/scripts/start_server.sh --check-only
```

### 2. Stop Processes Occupying Port 8080
If port `8080` is in use, terminate the occupying process(es):

```bash
# Graceful termination first:
lsof -ti :8080 | xargs kill 2>/dev/null || true

# Force kill if still lingering:
lsof -ti :8080 | xargs kill -9 2>/dev/null || true
```

Or invoke the helper script stop action:
```bash
bash .agents/skills/start-frontend/scripts/start_server.sh --stop-only
```

Verify port is released:
```bash
lsof -i :8080 || echo "Port 8080 is free"
```

### 3. Launch the Web Server
Launch the server with `PORT=8080`:

```bash
PORT=8080 python3 pitch_generator/fast_api_app.py
```
*(or invoke `bash .agents/skills/start-frontend/scripts/start_server.sh`)*

#### Antigravity Tool Call Parameters:
```json
{
  "CommandLine": "PORT=8080 python3 pitch_generator/fast_api_app.py",
  "Cwd": "/Users/jamesoreilly/Repos/pitch-generator",
  "IsDaemon": true,
  "WaitMsBeforeAsync": 3000,
  "toolAction": "Starting Pitch Generator web server",
  "toolSummary": "Start web server on 8080"
}
```

### 4. Verify Server Health
1. Verify the process is listening on port `8080`:
   ```bash
   lsof -i :8080
   ```
2. Inspect the server task logs (e.g. using `manage_task(Action='status', TaskId=...)` or viewing the log file directly) to confirm the startup message:
   ```text
   ==================================================
   Agentic Pitch Generator Web App Running Locally
   Open in browser: http://127.0.0.1:8080
   ==================================================
   ```
3. Report the URL to the user:
   - **Local Browser URL**: `http://127.0.0.1:8080` (or `http://localhost:8080`)
   - **Endpoints Available**:
     - Frontend UI: `/`
     - Health Check: `/api/health`
     - Public Config: `/api/config`
     - Campaign Pitch Generation: `POST /api/pitch`
     - HITL Concept Approval: `POST /api/approve`
     - Hybrid Router Preview: `POST /api/route`
     - A2A Agent Card: `/.well-known/agent-card.json`
