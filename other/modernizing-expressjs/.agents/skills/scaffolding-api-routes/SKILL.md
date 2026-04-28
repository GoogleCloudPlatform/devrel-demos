---
name: scaffolding-api-routes
description: Reads API_Contracts.md artifacts and rebuilds the legacy Express routes as modern Next.js Route Handlers or Server Actions. Use when following a legacy audit artifact to scaffold out a new Express API routes.
---

# Scaffolding Modern API Routes

Translate legacy Express route definitions and middleware chains into modern **Next.js Route Handlers** with built-in validation and unified session management.

## Objective
Rebuild the documented API surface to ensure 1:1 functional parity with the legacy system, focusing on mapping **Express Middlewares** to **Next.js Route Guards**.

## Instructions for the Scaffold Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Analyze API Contracts
- [ ] Step 2: Establish Route Architecture
- [ ] Step 3: Map Middleware to Guards
- [ ] Step 4: Implement Zod-Backed Request Validation
- [ ] Step 5: Implement Resource Handlers
```

### Step 1. Analyze API Contracts
Locate and read `docs/legacy-audit/API_Contracts.md`. Identify:
- **Primary Routes & Sub-routes**: Map these to the Next.js App Router (e.g., `/api/[resource]/[sub-resource]/route.ts`).
- **Legacy Middleware Requirements**: Identify routes protected by Passport, custom "owner-only" checks, or roles.

### Step 2. Establish Route Architecture
Create the folder structure in `src/app/api/` representing the resources. Ensure that:
- **Dynamic Segments** (e.g., `[id]`) are used for resource-specific operations (GET single, PUT, DELETE).
- **Index Segments** (e.g., `/api/posts/route.ts`) are used for collection operations (GET list, POST new).

### Step 3. Map Middleware to Guards
Translate legacy Express middleware chains into **Modular Route Guards**:
- **Authentication**: Map `requiresLogin` to a `getServerSession(authOptions)` check.
- **Authorization (Ownership)**: Map `resourceAuth.hasAuthorization` to a "Resource Ownership Guard" (e.g., `if (resource.user_id !== session.user.id) throw Unauthorized`).
- **Authorization (Roles)**: Map role-specific middleware to logic that checks `session.user.role`.

### Step 4. Implement Zod-Backed Request Validation
For every incoming request (POST, PUT, PATCH):
- Use the **Zod Schemas** defined in `src/lib/models/schema.ts` (from Step 3) to validate `req.json()`.
- Ensure the API returns a standard `422 Unprocessable Entity` or `400 Bad Request` with a detailed error payload if validation fails.

### Step 5. Implement Resource Handlers
Write the `GET`, `POST`, `PUT`, `PATCH`, and `DELETE` functions.
- **Strict Response Envelopes**: Match the **Common Response Envelope** identified in the audit (e.g., whether to return a raw object or a wrapped `{ data: ... }`).
- **Pagination & Sorting**: Implement `skip`, `limit`, and `sort` parameters to mirror the legacy behavior precisely.
- **Status Code Parity**: Match the exact success and error status codes documented in `API_Contracts.md`.
