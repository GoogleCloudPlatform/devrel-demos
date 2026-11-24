# Modernizing ExpressJS with Antigravity `/swarm`

This repository contains a streamlined **Swarm Modernization Pack** for Google Antigravity, engineered to migrate legacy Express.js monoliths (`Express` + `Mongoose` + `Passport` + `Pug`) into modern **Next.js App Router** applications with verified 1:1 functional and security parity.

Background on the original greenfield methodology:
- Article: [Automating modernization: Migrating legacy Express to Next.js with Google Antigravity & AI Agents](https://medium.com/@jamesor/f48b4c206a8e)
- Codelab: [Automating Modernization with Antigravity](https://codelabs.developers.google.com/automating-modernization-with-antigravity)

---

## Architecture Mapping

| Component | Legacy Stack (Source) | Modern Replacement (Target) | Rationale |
| :--- | :--- | :--- | :--- |
| **Architecture** | Express.js Monolith (`:3000`) | Next.js App Router (`:3001`) | Server Components + Web Fetch Route Handlers. |
| **Data Layer** | Mongoose (ODM) | Native `mongodb@7+` + Zod | Split tolerant-read / strict-write schemas over live legacy data. |
| **Language** | JavaScript (CommonJS) | TypeScript (ESM) | End-to-end compile-time and runtime type safety. |
| **Frontend** | Pug / Bootstrap | ShadCN UI + Tailwind CSS | Accessible `@base-ui/react` primitives & utility styling. |
| **Auth** | Passport.js | Auth.js (`next-auth` JWT) | Compatible with legacy `bcrypt` hashes + DB session revalidation. |
| **Testing** | Mocha / Supertest | Vitest + Web `Request` | Fast route-handler TDD without legacy Express mock shims. |

---

## How the v2 `/swarm` Pack Works

Instead of micro-managing 14 sequential phase-step skills, this pack pairs **Gemini Orchestrator + `/swarm`** with a 3-layer customization design:

1. **Always-On Hierarchical Rules (`GEMINI.md` & `modern-app/AGENTS.md`)**: Automatically equips every fresh swarm worker with the target stack choices and distilled framework guardrails (BSON-to-RSC serialization, Base UI `<Link />` element rendering, client form interceptors, Zod error flattening).
2. **Deterministic Safety Gate (`.agents/hooks.json`)**: A `PreToolUse` hook (`guardrails.mjs`) blocks every agent in the swarm from reading/writing `.env*` secrets or accidentally mutating `legacy-app/` source files.
3. **One Verification Skill (`.agents/skills/`)**:
   - **`verify-modernization-parity`**: Independent runtime rubric for fresh Wave 4 verifiers running the side-by-side **Two-Tab Test** (Chrome DevTools MCP + `curl`) and **Adversarial Security & Dirty-Data Probes** directly on the swarm message board (`@verifier <-> @slice-*`).

### The 4-Wave Swarm Topology

```text
Wave 1: Parallel Audit (Read-Only)
  ├── @audit-backend  ──► docs/Backend_Contract.md (models, hooks, live DB dirty-data, APIs, auth)
  └── @audit-frontend ──► docs/UI_Topology.md      (layouts, forms, complete URL -> page.tsx matrix)
  [Gate 1: Human Spec & Safe Intentional-Drift Sign-Off]

Wave 2: Shared Spine (Single Author — Zero File Collisions)
  └── @foundation     ──► Next.js + ShadCN + Vitest + Mongo singleton + Zod schemas + Auth.js + Shell

Wave 3: Parallel Vertical Feature Slices + Continuous Verification (Autonomous from Wave 2)
  ├── @slice-users         ──► Auth/Users Vitest suite + /api/users/* + login/signup/profile pages
  ├── @slice-articles      ──► Articles Vitest suite + /api/articles/* + feed/detail/editor pages
  ├── @slice-comments-tags ──► Comments/Tags Vitest suite + /api/... + UI components
  └── @slice-verifier      ──► Route/endpoint completeness check + full `npm test` & `npm run build`
  [Gate 2: User Creates modern-app/.env.local (Enforced by .agents/hooks.json)]

Wave 4: Live Two-Tab & Adversarial Swarm Loop (:3000 vs :3001 on Unified :27017 MongoDB)
  ├── @parity-verifier ◄──► @slice-* authors (curl API/SSR/bcrypt parity on the swarm board)
  ├── browser-verifier ───► Coordinator MCP subagent (Chrome DevTools Two-Tab sweep)
  └── @sec-adversary   ◄──► @slice-* authors (IDOR, open-redirect, secret projection & dirty-data probes)
```

---

## Project Structure

```text
/modernizing-expressjs/
├── .agents/
│   ├── scripts/
│   │   └── guardrails.mjs                     # Deterministic guardrail script
│   ├── skills/
│   │   └── verify-modernization-parity/
│   │       └── SKILL.md                       # Independent Two-Tab parity & adversarial verification
│   └── hooks.json                             # PreToolUse safety gate (.env* & legacy-app/ protection)
├── docs/                                      # Canonical swarm contracts & Parity_Adversarial_Report.md
│   └── prompts.md                             # Step-by-step prompting guide for this workshop
├── legacy-app/                                # Cloned Express monolith (Read-Only, :3000)
├── modern-app/                                # Greenfield Next.js App Router target (:3001)
├── GEMINI.md                                  # Immutable stack rules & distilled engineering guardrails
└── README.md
```

---

## Getting Started

1. **Clone the Legacy Source App** (if not already present):
   ```bash
   git clone https://github.com/madhums/node-express-mongoose-demo.git legacy-app
   ```
2. **Launch the Modernization Swarm** in Google Antigravity:
   Follow the prompt guide in `docs/prompts.md`.
