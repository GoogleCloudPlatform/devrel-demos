---
name: generating-api-tests
description: Reads API_Contracts.md and generates failing Vitest integration tests for the expected Next.js Route Handlers. Use when generating API tests for TDD.
---

## Objective
Implement Test-Driven Development (TDD) by writing strict tests asserting the exact behaviors, payloads, and JSON responses defined in the legacy Express APIs.

## Instructions for the Scaffold Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Read the API Contracts
- [ ] Step 2: Generate Auth/User Tests
- [ ] Step 3: Generate Article/Comment Tests
```

### Step 1.  **Read the Specs:** 
Locate and read `docs/legacy-audit/API_Contracts.md` and `docs/legacy-audit/Business_Logic_Rules.md`.

### Step 2. **Generate Test Suites:**
Create a `tests/api` folder. For each distinct domain in the contracts (e.g., `users.test.ts`, `articles.test.ts`), write a Vitest suite.

### Step 3. **Mocking:**
Use `node-mocks-http` to construct the `Request` and capture the Next.js `NextResponse` JSON output. Assert that the required HTTP status codes (200, 201, 401, 404, 422) and JSON body structures match the original Express requirements.

*Crucial Note: These tests WILL FAIL initially. That is the point of TDD. They will be executed repeatedly during the Data and API scaffolding phases until they pass.*
