---
name: auditing-api-contracts
description: Analyzes Express route definitions and controller logic to document API endpoints, payloads, and response structures. Use when reverse-engineering an existing Express application's API surface.
---

# Auditing API Contracts

Analyze the surface area of a legacy application's API to precisely document its behavior for recreation in a modern framework (e.g., Next.js Route Handlers).

## Objective
Reverse-engineer the legacy API's routes, payloads, and response structures, categorizing them by **Primary Resources** and **Sub-resources**.

## Instructions for the Audit Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Locate the Routes & Controllers
- [ ] Step 2: Categorize Resources
- [ ] Step 3: Identify Common Patterns
- [ ] Step 4: Analyze Each Endpoint
- [ ] Step 5: Generate API_Contracts.md
```

### Step 1. Locate the Routes & Controllers
Search the legacy codebase (e.g., `../ExpressModernization-Old/`) for where endpoints are defined (usually `config/routes.js`, `routes/`, or directly in `app.js`/`server.js`). Trace each route to its corresponding controller function.

### Step 2. Categorize Resources
Divide the API surface into:
- **Primary Resources**: High-level entities (e.g., `Users`, `Products`, `Posts`).
- **Sub-resources**: Dependent entities linked to a primary resource (e.g., `Comments` belonging to a `Post`, `Reviews` for a `Product`).

### Step 3. Identify Common Patterns
Look for a **Common Response Envelope**. Is the API consistent in how it returns data?
- *Example 1 (Wrapped):* `{ success: true, data: [...], meta: { total: 100 } }`
- *Example 2 (Unwrapped):* Returns the object/array directly.
Identify common status codes for success, validation failure (400/422), and authorization failure (401/403).

### Step 4. Analyze Each Endpoint
For every endpoint, document:
- **Method & Path**: e.g., `GET /resource/:id/sub-resource`
- **Middleware Analysis**: List middleware functions (e.g., `requiresLogin`, `hasAuthorization`). Document what they implicitly check (Session, Ownership, Roles).
- **Inbound Data**: Examine `req.body`, `req.query`, and `req.params`. Identify required vs. optional fields and their data types.
- **Outbound Structure**: Document the exact shape of the returned JSON or the redirect target.
- **Error States**: How does the controller handle failures (Mongoose errors, empty results, invalid IDs)?

### Step 5. Generate API_Contracts.md & Identify Probes
Compile findings into a single, highly detailed artifact at `docs/legacy-audit/API_Contracts.md`. 
**Critical:** Ensure that all of the endpoints are listed in a **checklist** within the artifact. The agent will use this checklist during the later scaffolding phase of the modernization workflow to ensure nothing is missed. Also, identify any necessary route redirects (e.g., `/articles` -> `/` if an endpoint isn't actually implemented but routing behavior is expected).
Additionally, **identify specific parity probes** (e.g., "The search API must be queried with an empty string to ensure it returns the same default sort as legacy"). **Append** these specific test cases to `docs/verification/Verification_Plan.md`.
