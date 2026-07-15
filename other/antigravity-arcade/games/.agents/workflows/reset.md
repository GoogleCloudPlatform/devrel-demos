---
description: Reset the workspace after a session. Use when the user prompts to "reset workspace" or when the workflow is called directly via `/reset` command.
---

# Workflow: Resetting the Workspace

To reset the workspace or a specific game to its initial state, follow these steps.

## Step 1: Ask the User Which Game to Reset

When initiated, first ask the user which game they would like to reset. Present the following options:
- All games
- space-shooter
- gravity-runner
- survivor-arcade
- icy-hockey

## Step 2: Run the Reset Script

Once the user selects an option, run the reset script from the workspace root, passing the selected game name as an argument. If the user selects "All games" (or specifies no game), run the script without arguments:

```bash
# For a specific game (e.g., space-shooter)
./utils/reset.sh space-shooter

# For All games
./utils/reset.sh
```

This will restore the specified game folder (or all game folders) to their original state while preserving system folders like `node_modules` and `utils`.

## Response Template
After completing the reset, reply to the user with this exact message (updating the text if only a specific game was reset):

> **Workspace Reset Successful**
> The workspace has been restored to its default state. All modifications to game folders have been reverted, and new files have been removed. Your environment is ready for a new session.
