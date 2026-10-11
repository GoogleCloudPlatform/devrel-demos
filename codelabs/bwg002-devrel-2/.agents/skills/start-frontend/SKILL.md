---
name: start-frontend
description: Manages local server ports and starts the Pitch Generator web server (port 8080) and optional standalone Visual Director A2A service (port 8801) as background daemon processes. Use when asked to run, start, restart, or test the Pitch Generator app or Visual Director service in a browser.
---

# Pitch Generator Start Frontend Skill

The **start-frontend** skill provides standardized instructions and utilities for managing the local Pitch Generator web application server (`8080`) and the standalone Visual Director A2A microservice (`8801`). Users do not need to specify port numbers in their prompts—this skill automatically applies the canonical ports.

It enforces a safe lifecycle:
1. **Check**: Verify if port `8080` (and port `8801` when launching the Visual Director service) is free.
2. **Clean**: Terminate any lingering processes occupying the target port(s).
3. **Launch**: Start the web application server (`pitch_generator/fast_api_app.py`) on port `8080` (and optionally the Visual Director A2A service on port `8801`) as a background process.
4. **Verify**: Confirm the server is listening and healthy, then deliver the local URL(s) to the user.

---

## Quick Execution

### 1. Start the Pitch Generator App Only (Baseline & Module 1 Steps 1a–1d)
When the user asks to start or test the Pitch Generator app in a browser:

```bash
bash .agents/skills/start-frontend/scripts/start_server.sh
```

### 2. Start Both the Visual Director Service and Pitch Generator App (Module 1 Step 1e+)
When the user asks to start the Visual Director service and the Pitch Generator app (e.g., *"Start the Visual Director service and the Pitch Generator app so I can test in a browser"*):

```bash
bash .agents/skills/start-frontend/scripts/start_server.sh --with-visual-director
```

This automatically:
- Frees port `8801` and starts the standalone Visual Director A2A microservice (`SERVICE_ROLE=visual-director`) at `http://localhost:8801` (serving `/.well-known/agent-card.json` and `/a2a/visual_director`).
- Frees port `8080` and starts the Pitch Generator app (`SERVICE_ROLE=pitch-generator`) at `http://localhost:8080` with `VISUAL_DIRECTOR_URL=http://127.0.0.1:8801`.

---

## Step-by-Step Procedure

### 1. Pre-Flight Port Check
```bash
bash .agents/skills/start-frontend/scripts/start_server.sh --check-only
```

### 2. Stop Occupied Ports
```bash
bash .agents/skills/start-frontend/scripts/start_server.sh --stop-only
# Or stop both 8080 and 8801:
bash .agents/skills/start-frontend/scripts/start_server.sh --with-visual-director --stop-only
```

### 3. Verify Server Health
1. Verify the server is listening and responding to `/healthz` on port `8080` (and `8801` if `--with-visual-director` was used):
   ```bash
   curl -s http://127.0.0.1:8080/healthz
   ```
2. Report the URL(s) to the user:
   - **Pitch Generator Web UI**: `http://localhost:8080`
   - **Visual Director A2A Agent Card** (when `--with-visual-director` is active): `http://localhost:8801/.well-known/agent-card.json`
