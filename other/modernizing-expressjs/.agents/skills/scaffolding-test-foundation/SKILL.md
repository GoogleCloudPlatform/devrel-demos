---
name: scaffolding-test-foundation
description: Installs and configures Vitest for a modern Next.js Application. Use this for setting up the environment to run Vitest.
---

## Objective
Establish a rapid Test-Driven Development (TDD) harness using Vitest for Next.js Route Handlers and Utilities.

## Instructions for the Scaffold Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Install Dependencies
- [ ] Step 2: Configure Vitest
- [ ] Step 3: Update package.json
```

### Step 1. Install Dependencies
Install `vitest`, `@vitejs/plugin-react`, `node-mocks-http`, and `@testing-library/react` as devDependencies using the `@latest` tag to ensure modern AI environments do not lock to outdated versions.
    *   **Command:** `npm install -D vitest@latest @vitejs/plugin-react@latest node-mocks-http@latest @testing-library/react@latest`

### Step 2. Configure Vitest
Create a `vitest.config.ts` file in the root directory that is configured to handle Next.js path aliases (e.g., `resolve.alias` pointing `@/` to `./src/`).

### Step 3. Update package.json
Add a `"test": "vitest run"` script.
