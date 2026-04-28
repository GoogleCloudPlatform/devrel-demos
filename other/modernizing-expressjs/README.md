# Modernizing ExpressJS with AI Agents

This repository contains an Agentic Orchestrator Skill Pack, a suite of specialized AI agent instructions designed to automate the modernization of legacy Express.js monoliths into modern Next.js architectures. These skills leverage agentic design patterns to reverse-engineer "ground truth" logic and rebuild it with 1:1 functional parity.

## Architecture Mapping
The skill pack is pre-configured to migrate legacy stacks to a modern, type-safe target:

| Component | Legacy Stack (Source) | Modern Replacement (Target) | Rationale |
| :--- | :--- | :--- | :--- |
| **Architecture** | Express.js Monolith | Next.js App Router | Optimized rendering via Server Components. |
| **Data Logic** | Mongoose (ODM) | MongoDB + Zod | Type-safe schemas and raw driver performance. |
| **Language** | JavaScript (CommonJS) | TypeScript (ESM) | Enforcing compile-time safety. |
| **Frontend** | Pug/EJS | ShadCN UI + Tailwind | Composable, utility-first design system. |
| **Auth** | Passport.js | Auth.js (NextAuth) | Modern session management for Edge. |
| **Validation** | Manual Middleware | Zod (Strict Validation) | Single source of truth for data integrity. |

## The 5-Phase Workflow
The orchestrator guides a "small army" of subagents through the following stages:

*   Phase 1: The AI Audit (Reverse Engineering)
*   Phase 2: Test-Driven Development (TDD)
*   Phase 3: Greenfield App Scaffolding
*   Phase 4: UI Generation
*   Phase 5: Parity Verification

## Project Structure
We recommend a "Modernization Hub" monorepo structure to isolate legacy code from the greenfield target:

To install, copy this folder and use as your project's root workspace folder.

```text
/modernizing-expressjs/
├── .agents/                # Skill metadata and instructions
│   └── skills/
│       └── skill-name/
│           ├── reference/  # Technical rules/standards
│           └── SKILL.md    # The agent's execution checklist
├── docs/                   # Reverse-engineered markdown artifacts
├── legacy-app/             # The `node-express-mongoose-demo` root
├── modern-app/             # The greenfield target repository
├── GEMINI.md               # Project-specific agent instructions
└── README.md               # This file
```

## Getting Started
1.  **Environment Setup:** Clone this repo and copy/move the `other/modernizing-expressjs` to a location of your choice. Alternatively you can use [giget](https://github.com/unjs/giget). This is faster and more efficient for getting just this folder.
    ```bash
    npx -y giget@latest gh+git:GoogleCloudPlatform/devrel-demos/other/modernizing-expressjs modernizing-expressjs
    ```
2.  **Clone the Source Repo:** Clone `node-express-mongoose-demo` into `modernizing-expressjs/legacy-app`.
    ```bash
    cd modernizing-expressjs
    git clone https://github.com/madhums/node-express-mongoose-demo.git legacy-app
    ```
3.  **Trigger the Orchestrator:** In the Google Antigravity chat interface, run:
    ```bash
    /orchestrating-greenfield-migration
    ```
    The agent will then load the workflow checklist and begin Phase 1.
