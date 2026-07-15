---
name: playing-the-game
description: Starts the local Vite server for the game and loads the game into a Chrome browser so the user can play it. Use when the user wants to test changes or play the game.
---

# Playing the Game

**Purpose**: To automate the process of starting the local Vite server and launching the game in a browser for testing.

**Trade-offs**: Automatically stopping existing Vite servers ensures the correct game is loaded but may disrupt other running servers if they were intentionally started.

**Decisions**:
*   Uses `npm run dev -- --port 5173 --strictPort` to start the Vite server on a consistent port.
*   Launches Chrome pointing to `http://localhost:5173`.
*   Avoids restarting the server if it is already running the same game, to preserve the HMR connection.

## Workflow

### 1. Identify Game Directory
*   Determine which game the user wants to play (e.g., `icy-hockey`, `gravity-runner`).
*   Locate the directory for that game (e.g., `<workspace>/icy-hockey`).

### 2. Check for Existing Vite Server
*   Check if a Vite server is already running.
*   If it is running for a **different game**, or on the target port (5173) but for a different game, stop it.
*   If it is running for the **same game**, do **NOT** stop it. This preserves the HMR connection and avoids opening duplicate tabs.
*   *Rule*: Only restart the server if switching games or if the server is unresponsive.

### 3. Start Vite Server (If Needed)
*   If a server is not already running for the same game, run `npm run dev -- --port 5173 --strictPort` in the game's directory using `run_command`.
*   *Why*: The `--port` flag forces the port, and `--strictPort` ensures it fails if the port is taken, rather than picking a random one.
*   This ensures a consistent URL of `http://localhost:5173`.
*   If the command fails because the port is in use, proceed to find and kill the process on that port (Step 2) and try again.
*   Do not block on this command if it runs continuously; send it to the background if needed or use a persistent terminal.

### 4. Launch Browser
*   If a new server was started, or if the user explicitly asks to open the browser:
    *   Use `run_command` to launch Chrome: `google-chrome http://localhost:5173`.
*   If the server was already running, do not automatically launch Chrome to avoid opening duplicate tabs. Instead, inform the user that the server is running and provide the URL `http://localhost:5173`.
*   *Note*: The agent cannot reliably determine if the user has closed the browser tab, so providing the URL and asking is the best approach if the server was already running.

### 5. Explain Controls to the User
After launching the game or providing the URL, print the following exact control explanation in the chat to guide the user:

```markdown
🎮 **Cabinet Control Mapping Reference**

Because of the custom hardware wiring on our physical cabinet, the keys are mapped as follows:

| Cabinet Button | Keyboard Key | Gamepad Button | Purpose (Standard) |
| :--- | :--- | :--- | :--- |
| **A** | `X` | Button 1 (`pad.B`) | Action / Select / Fire |
| **B** | `Z` | Button 0 (`pad.A`) | Cancel / Back |
| **X** | `V` | Button 3 (`pad.Y`) | Action |
| **Y** | `C` | Button 2 (`pad.X`) | Action |
| **Home** | `H` | Button 8 | Exit / Go Home |
| **Restart** | `R` | Button 9 | Restart Game / Reload |

**Movement:**
* Use the **Arrow Keys** (`↑`, `↓`, `←`, `→`) to move around.
```
