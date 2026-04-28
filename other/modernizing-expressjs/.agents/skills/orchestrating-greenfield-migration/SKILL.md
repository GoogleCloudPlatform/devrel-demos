---
name: orchestrating-greenfield-migration
description: Manages the end-to-end modernization of legacy Express monoliths into Next.js architectures. Orchestrates subagents for auditing, scaffolding, and verification. Use when starting or managing a greenfield rewrite project.
---

# Greenfield Migration Orchestrator

This skill manages the transition from legacy Node.js monoliths (Express/Pug/Mongoose) to modern Next.js architectures using a **Greenfield Rewrite** strategy.

## Modernization Hub Structure
The preferred workspace layout is a **"Modernization Hub"** monorepo:
```text
/workspace-root/
├── .agents/        # This Skills Pack
├── docs/           # Centralized Audit & Verification Specs
├── legacy-app/     # The Source (Read-Only)
└── modern-app/     # The Target (The Greenfield Repo)
```

## The Workflow

### Phase 1: The AI Audit (Reverse Engineering)
Dispatch subagents to produce specifications while identifying project-specific test scenarios for the `Verification_Plan.md`.

*   [ ] **Establish Database Strategy**: Decide whether to use the **Existing Legacy DB** or a **Seeded Greenfield DB**. (Default: Legacy Direct).
*   [ ] **Expose Legacy DB to Host**: If using the legacy DB via Docker, modify `legacy-app/docker-compose.yml` to include `ports: ["27017:27017"]` and restart the service.
*   [ ] **Initialize `docs/verification/Verification_Plan.md`**: Create the baseline template using `resources/verification-strategy.md`.
*   [ ] Run `auditing-data-models` -> Append **Data Integrity Stress-Tests**.
*   [ ] Run `auditing-api-contracts` -> Append **API Parity & Edge Case Probes**.
*   [ ] Run `auditing-business-logic` -> Append **Logic & Authorization Stress-Tests**.
*   [ ] Run `auditing-ui-archeology` -> Append **Interaction & Layout Verification Targets**.

### Phase 2: The Greenfield Foundation & TDD
*   [ ] Run `scaffolding-nextjs-foundation` to generate the base App.
*   [ ] Run `scaffolding-test-foundation` to configure Vitest.
*   [ ] Run `generating-api-tests` to convert `API_Contracts.md` into failing integration tests.

### Phase 3: The Greenfield Scaffold (Make Tests Pass)
*   [ ] Run `scaffolding-data-layer` to translate models into Native MongoDB/Zod types.
*   [ ] Run `scaffolding-api-routes` to implement Route Handlers until tests pass.
*   [ ] **Skip or Run** `generating-database-seeder` based on the Strategy decision.

### Phase 4: The UI & Pages Scaffold
*   [ ] Run `scaffolding-ui-and-pages` to translate `UI_Component_Inventory.md` into ShadCN components AND complete Next.js pages.
*   [ ] **Strict Checkpoint**: Verify that every route identified in the "Route & Page Topology" section of the inventory has an associated `page.tsx` implementation.

### Phase 5: Verification & Adversarial Audit
*   [ ] Run `auditing-parity` to perform a side-by-side runtime check.
*   [ ] Run `adversarial-verification` to probe for security and logic flaws.
*   [ ] Finalize `Parity_Adversarial_Report.md`.

## Instructions for Orchestration
1.  **Validate Paths**: Confirm the relative paths to the `legacy-app` and `modern-app`.
2.  **Dispatch Subagents**: Explicitly tell subagents where the source code and documentation folders are located.
3.  **Checkpointing**: Wait for each phase's artifacts (in `docs/`) to be completed before starting the implementation phase.

## Resources
- **`resources/verification-strategy.md`**: The master methodology for side-by-side verification.
