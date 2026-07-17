---
description: Deploy your game.
---

# Workflow: Deploying a Game

To deploy a game, follow these steps to ensure the correct game is selected and deployed.

## Step 1: Determine the Game to Deploy

The agent (or user) must identify which game folder to deploy.

1. **Infer from Context**: Check the recent conversation history. If a specific game was recently mentioned, created, edited, or tested, assume that is the game to deploy.
2. **List and Prompt**: If the game cannot be inferred from context:
   - List the directories in the root of the workspace.
   - Filter out non-game directories (e.g., `.agent`, `.git`, `node_modules`, `utils` and `game-template`).
   - Present the list of available games to the user and ask them to select one.

## Step 2: Run the Deploy Command

Once the game folder name is known, run the appropriate compiled deployment binary from the root of the workspace based on the operating system, setting a workspace-local temporary directory:

**For Linux:**
```bash
TMPDIR=./tmp ./utils/deploy_linux -game <game-folder-name>
```

**For macOS:**
```bash
TMPDIR=./tmp ./utils/deploy_osx -game <game-folder-name>
```

Replace `<game-folder-name>` with the actual folder name of the game (e.g., `space-shooter`).

### Example (Linux)
```bash
TMPDIR=./tmp ./utils/deploy_linux -game space-shooter
```

### Example (macOS)
```bash
TMPDIR=./tmp ./utils/deploy_osx -game space-shooter
```


This script will:
1. Verify the game folder exists and is valid.
2. Build the game using Vite.
3. Zip the build output.
4. Fetch a short-lived Signed URL from the backend.
5. Upload the zip to GCS.
6. Poll the server for the final Game ID.

## Step 3: Communicate with the User

The agent must provide clear and secure feedback to the user during and after the deployment process. Use the following templates for consistency:

### 1. During Upload
Use this message when starting the build and upload process:
> I am starting the build and upload process for the game `<game-folder-name>`. This might take a few moments...

### 2. During Polling
Use this message when the file is uploaded and you are waiting for processing:
> Upload complete! I am now waiting for the server to process the build and generate the Game ID. This usually takes a few seconds, up to 30 seconds...

### 3. On Success
Use this template when the Game ID is successfully retrieved:
> 🚀 **Deployment Successful!**
>
> *   **Game ID**: `<game-id>`
> *   **Title**: `<game-title>`
>
> You can now view your game in the arcade catalog.

### 4. On Failure
Use this template if the process fails (do **NOT** leak raw error messages, tokens, or URLs):
> ❌ **Deployment Failed**
>
> The deployment encountered an error during processing.
> Please share the following Build ID with a moderator or developer to investigate the logs:
> *   **Build ID**: `<build-id>`
