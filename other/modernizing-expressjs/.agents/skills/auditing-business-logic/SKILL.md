---
name: auditing-business-logic
description: Analyzes authentication flows, authorization rules, middleware logic, and side-effects. Use when extracting business rules, Passport configurations, or mailer logic from an Express application.
---

# Auditing Business Logic & Side-Effects

Analyze the implicit "rules" and external behaviors of a legacy application to ensure they are accurately replicated in the modern architecture.

## Objective
Reverse-engineer the application's authentication flows, authorization logic (RBAC/ABAC), and any asynchronous side-effects (Mailers, External APIs, File Storage).

## Instructions for the Audit Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Analyze AuthN & AuthZ Flows
- [ ] Step 2: Map Side-Effects (External APIs, Mailers)
- [ ] Step 3: Analyze Global Middleware
- [ ] Step 4: Draft Modernization Advisory
- [ ] Step 5: Generate Business_Logic_Rules.md
```

### Step 1. Analyze AuthN & AuthZ Flows
- **Authentication (AuthN)**: Locate Passport, session, or JWT configurations (e.g., `config/passport.js`). Document the login strategies (Local, OAuth, etc.) and required fields.
- **Authorization (AuthZ)**: Document the logic used for access control. How does the system verify a user's role or ownership of a **Primary Resource**? (e.g., `requiresRole('admin')` or `isOwner(resource_id)`).

### Step 2. Map Side-Effects
Identify actions that occur outside of the primary request/response cycle:
- **External Services**: Check `package.json` and controllers for Stripe (Payments), Twilio (SMS), SendGrid (Email), etc.
- **Mailers**: Audit the `mailer/` or `services/email/` directory. Does creating a resource trigger an automated notification?
- **File Storage**: Locate file upload configurations (e.g., Multer). Determine where assets are stored (Local Disk vs Cloud Storage).

### Step 3. Analyze Global Middleware
Examine `app.js` or `config/express.js`. Document global middlewares such as `helmet`, `cors`, custom loggers, or `csurf`. Determine which remain relevant for a modern Next.js API.

### Step 4. Provide Modernization Advisory
Flag potential pitfalls for the modern stack (e.g., Next-Auth vs Passport). Recommend modern equivalents for legacy side-effects (e.g., moving from local file storage to S3/Uploadthing).

### Step 5. Generate Business_Logic_Rules.md & Identify Probes
Compile findings into `docs/legacy-audit/Business_Logic_Rules.md`. Additionally, **identify specific logic-parity probes** (e.g., "Attempt to submit a form without the required OAuth session to verify the redirect loop matches legacy"). **Append** these logic-specific test cases to `docs/verification/Verification_Plan.md`.
