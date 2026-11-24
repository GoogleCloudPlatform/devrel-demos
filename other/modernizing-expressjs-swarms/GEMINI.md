# GEMINI Guidelines & Target Stack

This file provides workspace-wide architectural invariants, target stack choices, and `/swarm` rules for the Coordinator and every worker during Express-to-Next.js modernization.

## 🚨 Mandatory Instructions for Every Agent

**BEFORE every code generation attempt, you MUST:**
1. **Follow the Workspace Topology & Target Stack** below.
2. **Swarm & Build Discipline**: Keep `GEMINI.md` **read-only** during active `/swarm` runs so prompt prefix caches stay warm and workers never collide on this file (post newly discovered runtime gotchas to the swarm message board during a run, and persist them afterward using `/learn`). Retire finished workers promptly at wave boundaries (e.g., retire `@audit-backend` and all `@slice-<domain>` workers once Wave 3 is green, keeping only `@foundation` and `@slice-verifier` on standby for Wave 4) and avoid literal `@worker-name` mentions in briefs or summaries unless actively waking that worker, preventing cold cache-TTL wakeups. Run `npm run build` from only one designated worker at a time (after stopping any running `:3001` server) to avoid `.next/lock` contention. Because `/swarm` workers do not inherit MCP tools, delegate Chrome DevTools MCP browser verification to a Coordinator `define_subagent({ EnableMCPTools: true, EnableWriteTools: false })` subagent in an `isolatedContext`. Pause cleanly after each wave summary and wait for explicit USER go-ahead before starting the next wave; at final close-out, retire all workers and post a `[done]` summary without `@mentions`.
3. **🔐 Security & Environment Access Rule**: NEVER read or write a `.env` or `.env.*` file (enforced deterministically by `.agents/hooks.json`). If an environment variable check or edit is needed, ask the USER to perform it.
4. **Network, Package Installs & Sandbox Batching**: The default sandbox has no outbound network, Docker socket, or host `localhost` access. Request `BypassSandbox: true` directly (skipping offline sandbox attempts) for `npm`/`npx` registry fetches, `docker`, and `localhost` probes (`:3000`, `:3001`, `:27017`), while keeping `npm test`, `tsc`, `eslint`, and `npm run build` sandboxed. Write all runtime and dev dependencies into `package.json` first and run **one** batched `npm install` (keep root `.npmrc` fail-fast retry settings); in Wave 4, consolidate live `curl`/`node`/`docker` checks into 1–2 reusable scripts per verifier to minimize approval prompts.

---

## 🏗️ Workspace Topology & Target Stack

| Path / Runtime | Role | Rules |
| :--- | :--- | :--- |
| `legacy-app/` (`http://localhost:3000`) | Read-Only Source (Express + Mongoose + Pug) | Ground-truth baseline. Never modify `legacy-app/app/`, `config/`, `public/`, or `test/`. |
| `modern-app/` (`http://localhost:3001`) | Greenfield Target (Next.js App Router) | TypeScript ESM (`--src-dir`, `--import-alias "@/*"`, `--disable-git`). |
| `localhost:27017` | Unified MongoDB Instance | Expose Docker MongoDB to host `27017:27017`; always connect via `localhost`, never container hostname `mongo`. |
| `docs/` | Canonical Swarm Contracts | `Backend_Contract.md`, `UI_Topology.md`, and `Parity_Adversarial_Report.md`. |

### Opinionated Stack Replacements
- **Framework**: Express Monolith -> **Next.js App Router** (Server Components + Route Handlers; always scaffold with `--disable-git` inside a parent hub repo).
- **Language**: JavaScript (CommonJS) -> **TypeScript (ESM)**.
- **Data Layer**: Mongoose ODM -> **Native `mongodb` Driver** singleton (`src/lib/db/mongodb.ts`) + **Zod** schemas (`src/lib/models/schema.ts`). Do **not** install Mongoose, Prisma, or `@auth/mongodb-adapter`.
- **Authentication**: Passport.js -> **Auth.js (`next-auth`) JWT Strategy** with manual `bcrypt` verification against legacy `hashed_password` and DB user-existence revalidation.
- **UI System**: Pug / Bootstrap -> **ShadCN UI + Tailwind CSS**.
- **Testing**: Mocha / Supertest -> **Vitest** calling Route Handlers directly with standard Web `new Request()`.

