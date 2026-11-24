# Workshop Prompts: Express → Next.js Modernization with `/swarm`

Copy and paste each prompt in order during the workshop. Every `/swarm` worker automatically loads `GEMINI.md` (target stack & swarm rules) and is protected by `.agents/hooks.json` (`guardrails.mjs`).

> **Note:** Agent reads of root `README.md` and this `docs/prompts.md` file are blocked by `guardrails.mjs` (and edits require your approval) so the Coordinator and workers genuinely reverse-engineer `legacy-app/` instead of reading ahead.

---

## Setup

1. Select **`Orchestrator (Neon)`** (or **`Orchestrator (Carbon)`**) in Model Selection.
   - The Coordinator plans and reviews checkpoints on **Neon/Carbon**, then switches to **Hydrogen** when spawning workers—so parallel workers automatically run on **Hydrogen** with no extra configuration.
2. Make sure Docker MongoDB (`localhost:27017`) is running with `legacy-app` data.

---

## Prompt 1 — Wave 1: Parallel Read-Only Audit

```text
/swarm Audit legacy-app to prepare a greenfield Next.js rewrite in modern-app using the existing MongoDB on localhost:27017. Spawn two read-only workers writing to separate files:
- @audit-backend -> docs/Backend_Contract.md: Document all models, Mongoose hooks, and indexes; inspect live documents in MongoDB (localhost:27017) for missing or blank fields (recommending lenient Read schemas vs. strict Write schemas, plus partial unique indexes where OAuth fields can be empty); include a [ ] endpoint checklist with exact status-code order (404 vs. 401 vs. 403) and who is allowed to edit or delete each resource; call out legacy bugs or security flaws we should fix intentionally rather than copy 1:1; and end with a [ ] checklist of app-specific parity and security test cases for Wave 4.
- @audit-frontend -> docs/UI_Topology.md: Start with a complete Legacy URL -> Next.js page.tsx table (auth guards, client actions, and any unused templates to skip), then document shared layouts, logged-in vs. logged-out UI states, form validation/error behavior, fallbacks for empty lists or deleted authors, and a closing [ ] checklist of browser interaction and mobile edge-case tests for Wave 4.
When both finish, keep @audit-backend waiting on standby for questions, retire @audit-frontend, and pause to summarize both docs—highlighting the legacy flaws you recommend fixing and your proposed 2–4 feature slices—before writing any code.
```

### Checkpoint 1 (Human Review)
Inspect `docs/Backend_Contract.md` and `docs/UI_Topology.md`. Confirm which legacy bugs or security flaws you want fixed vs. preserved, and approve (or adjust) the proposed feature breakdown before moving on.

---

## Prompt 2 — Wave 2: Shared Foundation (`@foundation`)

```text
Approved. Spawn a single @foundation worker to scaffold modern-app/ and build only the shared foundation based on docs/Backend_Contract.md and docs/UI_Topology.md (leaving feature routes and pages for Wave 3):
- Set up the project, MongoDB connection/indexes, Zod read/write models (returning plain strings with secrets stripped), Auth.js config, next.config.ts security headers, and global App Shell (layout, Navbar, Footer, not-found, error).
- Confirm npx tsc --noEmit and npm run build pass, list the required modern-app/.env.local variable names if the file is missing (do not read or write .env* files), and pause to report the shared modules/types created.
```

---

## Prompt 3 — Wave 3: Parallel Feature Slices + `@slice-verifier`

```text
Spawn the approved 2–4 feature workers (@slice-<domain>) in parallel, plus one read-only @slice-verifier:
- Each @slice-<domain> only edits files in its own folders (src/app/api/<domain>/**, src/app/<domain>/**, src/components/<domain>/**, tests/api/<domain>.test.ts). Send any shared-foundation change requests to @foundation, share component prop types on the board, and ask @audit-backend if any legacy behavior is unclear. Write Vitest API tests first, build the API routes, client forms, and pages, and verify with npx vitest run tests/api/<domain>.test.ts and npx tsc --noEmit (do NOT run npm run build inside feature workers), then notify @slice-verifier.
- @slice-verifier waits for all feature workers to finish, verifies every endpoint and page in docs/Backend_Contract.md and docs/UI_Topology.md is implemented, and is the only worker that runs the full npm test, npx tsc --noEmit, npm run lint, and npm run build—sending any failures back to the owning @slice-* worker until everything passes. Retire @audit-backend and all @slice-<domain> workers once Wave 3 is green (keep only @foundation and @slice-verifier on standby for Wave 4).
```

### Checkpoint 2 (Secrets & Servers)
Run this in your terminal to create `modern-app/.env.local` for the shared MongoDB and Auth.js session secret:

```bash
SECRET=$(openssl rand -base64 32)
cat <<EOF > modern-app/.env.local
MONGODB_URI=mongodb://localhost:27017/noobjs_dev
AUTH_SECRET=$SECRET
NEXTAUTH_SECRET=$SECRET
AUTH_URL=http://localhost:3001
NEXTAUTH_URL=http://localhost:3001
EOF
```

Confirm both MongoDB (`localhost:27017`) and `legacy-app` (`http://localhost:3000`) are running before running Prompt 4.

---

## Prompt 4 — Wave 4: Live Side-by-Side Parity & Security Verification (`verify-modernization-parity` skill)

```text
MongoDB (:27017) and legacy-app (:3000) are running—execute Wave 4 verification and close-out using /verify-modernization-parity.
```

---

## Optional Finale — Save What the Swarm Learned (`/learn`)

```text
/learn Summarize any framework, database, or security lessons solved on the swarm board during this migration and add them as concise rules to GEMINI.md.
```
