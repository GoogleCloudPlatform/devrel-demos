---
name: ping_pong_pairing
description: Enforces a strict, turn-based TDD ping-pong cycle by defining and orchestrating two specialized subagents (Player One and Player Two).
---

# Ping-Pong Pairing Workflow (Subagent Edition)

Use this skill to orchestrate an automated, turn-based Ping-Pong TDD loop using Antigravity subagents. The main agent acts as the **Coordinator**, while delegating the coding and testing tasks to two specialized subagents: **Player One** and **Player Two**.

## 1. Setup Phase: Defining the Subagents
At the start of the session, the Coordinator MUST define the two subagents using the `define_subagent` tool:

1.  **`tdd_player_one`**:
    *   **Description**: "Acts as Player One in the TDD ping-pong pairing loop, alternating between writing a failing test and writing minimum code to pass a test."
    *   **Write Tools**: Enabled (`enable_write_tools: true`).
    *   **System Prompt**:
        ```
        You are Player One in a Ping-Pong pairing pair.
        Your task is to:
        1. Check which phase of the TDD cycle you are in.
        2. If writing a test: Identify the next smallest, simplest unit of functionality to test, write exactly one new failing unit test, verify it fails, and report back (RED phase).
        3. If implementing code: Write the absolute minimum amount of production code to make the current failing test pass, verify all tests pass, and report back (GREEN phase).
        ```

2.  **`tdd_player_two`**:
    *   **Description**: "Acts as Player Two in the TDD ping-pong pairing loop, alternating between writing a failing test and writing minimum code to pass a test."
    *   **Write Tools**: Enabled (`enable_write_tools: true`).
    *   **System Prompt**:
        ```
        You are Player Two in a Ping-Pong pairing pair.
        Your task is to:
        1. Check which phase of the TDD cycle you are in.
        2. If writing a test: Identify the next smallest, simplest unit of functionality to test, write exactly one new failing unit test, verify it fails, and report back (RED phase).
        3. If implementing code: Write the absolute minimum amount of production code to make the current failing test pass, verify all tests pass, and report back (GREEN phase).
        ```

## 2. The Orchestration Loop
The Coordinator drives the process by invoking the subagents sequentially using `invoke_subagent` and checkpointing their progress in git:

### Turn 1: Player One (Ping)
1.  **Invoke `tdd_player_one`** with the prompt:
    *   *Prompt*: `"Write the next failing unit test for [feature description/checklist item]. Verify it fails, then report back."`
2.  **Wait** for the subagent to finish.
3.  **Verify & Commit**: Run git status, stage any new or modified files (e.g., `git add <file>`), and commit:
    *   `git commit -m "Player One: Add failing test for [feature]"`

### Turn 2: Player Two (Pong)
1.  **Invoke `tdd_player_two`** with the prompt:
    *   *Prompt*: `"Implement the minimum code to pass the current failing test. Run the test suite, verify it passes, then report back."`
2.  **Wait** for the subagent to finish.
3.  **Verify & Commit**: Run git status, stage any new or modified files (e.g., `git add <file>`), and commit:
    *   `git commit -m "Player Two: Implement minimum code for [feature]"`

### Turn 3: Player Two (New Ping)
1.  **Invoke `tdd_player_two`** with the prompt:
    *   *Prompt*: `"Write the next failing unit test for [next checklist item]. Verify it fails, then report back."`
2.  **Wait** for the subagent to finish.
3.  **Verify & Commit**: Run git status, stage any new or modified files (e.g., `git add <file>`), and commit:
    *   `git commit -m "Player Two: Add failing test for [next feature]"`

### Turn 4: Player One (Pong)
1.  **Invoke `tdd_player_one`** with the prompt:
    *   *Prompt*: `"Implement the minimum code to pass the current failing test. Run the test suite, verify it passes, then report back."`
2.  **Wait** for the subagent to finish.
3.  **Verify & Commit**: Run git status, stage any new or modified files (e.g., `git add <file>`), and commit:
    *   `git commit -m "Player One: Implement minimum code for [next feature]"`

*Repeat this loop (alternating roles after every Green implementation) until all features are complete.*

## 3. Refactoring Rules
*   At the start of any turn, the Coordinator can inspect the code and determine if refactoring is needed.
*   Refactoring can ONLY be performed when the test suite is 100% GREEN.
*   If refactoring is needed, the Coordinator can instruct the active subagent to perform the refactor and verify the tests remain green, or perform it directly.
*   Refactor commits MUST be distinct (remember to stage any new files first): `git commit -m "Refactor: [description]"`

## 4. Quality Gates
*   No turn handoff is allowed unless the workspace has **exactly one failing test** (during Red phase) or **zero failing tests** (during Green/Refactor phase).
*   No untested new functionality is allowed to be committed in the green phase.

## 5. Optimizing User Approvals
To minimize repeated permission prompts during the turn-based loop:
*   **Inherit Workspace**: Keep the subagents set to `Workspace: 'inherit'` (default). Avoid using `'branch'` (sandbox mode) because temporary worktree paths bypass project-specific permission rules.
*   **Leverage 'Always Allow'**: When approving the first few subagent commands (e.g., test runs, file modifications), check the **"Always allow for this project"** option to grant persistent permissions for the remainder of the session.
