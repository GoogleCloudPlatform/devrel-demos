---
name: auditing-parity
description: Compares a modernized Next.js application against its legacy Express counterpart using runtime side-by-side verification. Use when ensuring functional and business logic parity between two systems.
---

# Side-by-Side Parity Audit

Verify the modernization by performing a side-by-side architectural and interaction audit between the legacy and modern applications.

## Objective
Ensure 1:1 functional parity by systematically comparing the live behavior and internal logic of both applications. The goal is to prove the new code is a perfect functional replacement.

## Prerequisites
1.  **Legacy App**: Running on `http://localhost:3000`.
2.  **Modern App**: Running on `http://localhost:3001`.
3.  **Unified State (MongoDB)**: Both applications must target the same database instance to ensure data consistency during side-by-side testing.

## Pre-Audit Environment Setup
Before performing the audit, you MUST ensure a stable MongoDB environment:

1.  **Detect Port Conflicts**: Run `docker ps --format "table {{.ID}}\t{{.Names}}\t{{.Ports}}"` and look for any container binding to `0.0.0.0:27017`.
2.  **Stop Conflicting Instances**: If a container is binding to `27017` but is not the intended database for this audit session, stop it immediately (`docker stop <ID>`).
3.  **Fresh Lifecycle**: To ensure a clean state, run `docker compose down` in both `modern-app/` and `legacy-app/` before starting the "Unified" database instance (`docker compose up -d mongodb` in `modern-app/`).
4.  **Verify Unified Port**: Ensure only **one** MongoDB container is reporting a bound host port in `docker ps`.
5.  **Connectivity Check**: Verify both applications connect to `localhost:27017` (or the unified instance) without error.

## Instructions for the Audit Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 0: Validate Database & Container State
- [ ] Step 1: Execute Side-by-Side Interactions
- [ ] Step 2: Compare Network Payloads
- [ ] Step 3: Verify Complex Authorization
- [ ] Step 4: Validate Edge Cases & Error Responses
- [ ] Step 5: Final Parity Report
- [ ] Step 6: Rinse and Repeat
```

### Step 1. Execute Side-by-Side Interactions
Open both apps in the browser. Perform the following actions in tandem:
- **Navigation**: Click through all primary and sub-resource routes. Do the URL structures match or have a clear mapping?
- **Data Entry**: Submit the same data into both legacy and modern forms. Ensure both succeed or fail in the same way.
- **Empty States**: Compare views when no data is present.

### Step 2. Compare Network Payloads
Use the browser developer tools (or server logs) to intercept API requests:
- **Request Bodies**: Ensure the new frontend sends the exact same field names and types expected by the legacy API contract.
- **Response Envelopes**: Verify that the JSON response structure is identical (Check for wrapped vs. unwrapped payloads).
- **Status Codes**: Confirm that success (200/201) and failure (400/404/422/500) codes are shared between both versions.

### Step 3. Verify Complex Authorization
Test "Owner-Only" and "Role-Only" logic by attempting unauthorized actions in both:
- **Unauthorized Access**: If the legacy app redirects to `/login` for a specific route, does the modern app do the same?
- **Horizontal Privilege Checks**: If a user cannot delete another's resource in the legacy app, confirm the same failure occurs in the modern app.

### Step 4. Validate Edge Cases & Error Responses
Input malformed data (invalid IDs, excessively long strings) and compare the error messages returned. While the UI can be modern, the **API logic must remain functionally equivalent** to prevent breaking downstream consumers.

### Step 5. Final Parity Report
Compile findings into a `docs/verification/Functional_Parity_Report.md`. Categorize every finding as **Confirmed Parity**, **Functional Gap** (missing logic), or **Intentional Drift** (modernized logic with a documented reason).

### Step 6: Rinse and Repeat
If there are any gaps or errors during testing, go back to the modern app and fix them. Then, repeat these steps from the beginning until the modern app is a perfect functional replacement for the legacy app.
