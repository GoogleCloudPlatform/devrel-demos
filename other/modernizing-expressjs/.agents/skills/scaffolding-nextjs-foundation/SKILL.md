---
name: scaffolding-nextjs-foundation
description: Generates a new Next.js application with Tailwind, TypeScript, and modern dependencies based on audit specifications. Use when beginning the scaffolding phase of a greenfield codebase rewrite.
---

## Objective
Establish the baseline directory structure and dependencies for the modern rewrite of the legacy application.

## Instructions for the Scaffold Subagents

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Initialize Next.js
- [ ] Step 2: Initialize UI
- [ ] Step 3: Install Core Dependencies
- [ ] Step 4: Clean the Scaffold
- [ ] Step 5: Verification
```

### Step 1. Initialize Next.js
Execute the `create-next-app` command in the designated modernization directory (usually the root of the new repo).
    *   **Command:** `npx -y create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"`
    *   *Note: Ensure you are running this in the correct output directory (e.g., `modern-app/`) and not inside the legacy `legacy-app/` folder.*

### Step 2. Initialize UI
Run `npx shadcn@latest init` to set up Tailwind CSS and the components directory.

### Step 3. Install Core Dependencies
Evaluate the `Business_Logic_Rules.md` artifact (found in `docs/legacy-audit/`). Based on those rules, install the necessary modern replacements explicitly using the `@latest` tag so the 10-year old versions are avoided.
    *   **MongoDB & Auth Connection:** If connecting to legacy MongoDB, install `mongodb@latest`.
    *   **Connection Secret**: Plan for the `.env.local` initialization.
        *   **CRITICAL**: When the `modern-app` runs on the host (e.g., `npm run dev`), it cannot resolve internal Docker hostnames like `mongo`. **You MUST use `localhost`** (e.g., `mongodb://localhost:27017/db_name`) to bridge onto the exposed container port.
    *   **Auth Strategy Selection:**
        *   If `mongodb@7+` is used: **Do NOT** install `@auth/mongodb-adapter` (it currently has peer conflicts with v7). Instead, use a **JWT strategy** (`next-auth@latest`) and the native driver for manual account/user lookups in the `authorize` callback.
        *   If `mongodb@^6` is acceptable: Install `mongodb@^6` and `@auth/mongodb-adapter@latest`.
    *   **Additional Packages:**
        *   For payload validation, install `zod@latest`.
        *   For legacy Mongoose methods like password hashing, install `bcrypt@latest` and `-D @types/bcrypt@latest`.
    *   **Command Example (MongoDB 7 / JWT):** `npm install next-auth@latest mongodb@latest zod@latest bcrypt@latest && npm install -D @types/bcrypt@latest`

### Step 4. Clean the Scaffold
Remove default boilerplate from `src/app/page.tsx` and `src/app/globals.css` to create a blank canvas for the next subagents.

### Step 5. Verification
Ensure `npm run build` succeeds on the empty foundation.
