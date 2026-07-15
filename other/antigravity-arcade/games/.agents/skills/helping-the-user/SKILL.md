---
name: helping-the-user
description: Helps the user make or modify a game. Use when the user wants to create a new game or modify an existing one.
---

# Helping the User with Game Development

**Purpose**: To guide the user through the process of creating or modifying games in the workspace, providing tailored suggestions based on context.

**Trade-offs**: Prioritizes interactive guidance and context inference over immediate execution, which might feel slower to experienced users but ensures better alignment with their goals.

**Decisions**:
*   Infers context from chat history to maintain continuity.
*   Provides a structured flow for new chats (list games -> suggest edits).
*   Delegates new game creation to the `creating-a-game` skill.

## Workflow

### Step 1. Infer Context
*   **Action**: Review the current chat session to see if a game is already being discussed or developed.
*   **Logic**:
    *   If a game name (e.g., `gravity-runner`, `icy-hockey`, `space-shooter`, `survivor-arcade`) is mentioned in recent turns, assume development is underway for that game.
    *   Proceed to **Step 2: Continue Development**.
    *   If the chat is new or no specific game is identified, proceed to **Step 3: Brand New Chat**.

### Step 2. Continue Development
*   **Action**: Use the `ask_question` tool to continue to help the user with the identified game.
*   **Quesion**: Ask the user what they want to do next with the game (e.g., "We are working on `gravity-runner`. What would you like to do next?").
*   **Options**: Provide suggestions relevant to game development (e.g., modifying physics, adding assets, fixing bugs).

### Step 3. Brand New Chat
*   **Action**: Use the `ask_question` tool to prompt the user to select an existing game to modify or create a new one.
*   **Question**: Which game would you like to modify?
*   **Options**: [`gravity-runner`, `icy-hockey`, `space-shooter`, `survivor-arcade`]

### Step 4. Process User Choice

#### If the user chooses "Create a new game":
*   **Action**: Execute the `creating-a-game` skill.
*   **Reference**: See [.agent/skills/creating-a-game/SKILL.md](../creating-a-game/SKILL.md).

#### If the user chooses an existing game:
*   **Action**: Use the `ask_question` tool to provide a list of possible simple edits with short prompts.
*   **Question**: Which modification would you like to make?
*   **Options**:
    *   *Example Edits*:
        *   "Change player speed"
        *   "Add a new enemy type"
        *   "Change background color/music"
        *   "Add a score multiplier"
    *   Also allow the user to type in their own custom modification.
    *   **Testing**: Once the user has made changes and wants to test them, execute the `playing-the-game` skill to start the server and launch the Chome browser. Avoid using the broswer subagent.

## References
*   [creating-a-game](../creating-a-game/SKILL.md) - Skill for creating a new game.
*   [playing-the-game](../playing-the-game/SKILL.md) - Skill for running the game and launching the browser.
