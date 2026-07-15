---
name: creating-a-game
description: Guides the creation of a new game and is the high-level orchestrator skill that MUST be invoked first. Use when tasked with creating a new game.
---

# Creating a Game

Follow these steps FIRST when creating a new game:

1. **Setup Workspace:**
   Copy the contents of the `game-template` directory recursively to a subfolder in the workspace with the name of the game as a folder-friendly name (e.g., `my-game`).
   Since `node_modules` are installed globally, you do not need to install dependencies.
   Use the `run_command` tool to copy the template:
   ```bash
   cp -r /workspace/game-template /workspace/<game-name>
   ```

2. **Develop the Game:**
   Attempt to make the game using this newly copied folder as the base. Start modifying the source files to fulfill the user's game request.

   * [ ] Read the game files before starting to understand the setup
   * [ ] Use each of these agent skills when creating or modifying a game
      - `messaging-game-over`
      - `ensuring-arcade-visuals`
      - `handling-user-input`
      - `improving-game-quality`
      - `adding-easter-egg`
      - If a "platformer" game use `building-platformer-games`

3. **Validation Loop:**
   After **every** code edit you make, you MUST run the build command to ensure the game compiles successfully.
   Use the `run_command` tool to run the build:
   ```bash
   cd /workspace/<game-name> && npm run build
   ```
   Do not proceed to the next step or notify the user until compilation succeeds. Fix any compilation errors you encounter.

4. **Play Testing:**
   Once the user has made changes and wants to test them, execute the `playing-the-game` skill to start the server and launch the browser.
