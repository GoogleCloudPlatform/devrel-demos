# Verification Strategy: The Two-Tab Test

This document outlines the standard procedure for verifying a modernized Next.js application against its legacy Express counterpart.

## The Objective
A successful modernization must provide **perfect functional parity** for external consumers (API clients) and **intentional interaction parity** for end users, while adopting a superior design system.

---

### Step 1: Environment Preparation
To perform a runtime audit, both systems must be locally accessible:

| Application | Command | Port |
| :--- | :--- | :--- |
| **Legacy (Express)** | `npm start` | `3000` |
| **Modern (Next.js)** | `npm run dev` | `3001` |

> [!IMPORTANT]
> **Unified Data State**: It is highly recommended to point both applications to the **same MongoDB instance** (or a recently mirrored snapshot). This ensures that resource IDs, search results, and authentication sessions are consistent during side-by-side testing.

---

### Step 2: The Functional Parity Audit (`auditing-functional-parity`)
Dispatch an agent to perform the following checks across both `/api` surfaces:

1.  **Response Envelope Check**: Compare a `GET` request to both endpoints.
    - *Example*: Does both return `{ "id": 1, "title": "..." }` or is one wrapped in `{ "data": ... }`?
2.  **Error Object Consistency**: Intentional parity is required for error fields.
    - *Check*: If validation fails, does the legacy app return `errors: { field: "msg" }`? The new app must mirror this key structure.
3.  **Status Code Verification**: Ensure a `404` in the old app is correctly mapped to a `404` in the new app (and not a `500` due to unhandled exceptions).

---

### Step 3: The Adversarial Probe (`adversarial-verification`)
Scrutinize the security and resiliency of the new Next.js routes:

1.  **Identity & Ownership**:
    - Log into the modern app as **User A**.
    - Attempt a `DELETE` or `PUT` request to a resource owned by **User B**.
    - **Expected Outcome**: Rejection with `404 Not Found` or `401 Unauthorized`.
2.  **Schema Stress-Testing**:
    - Submit an empty JSON object `{}` to a `POST` handler that requires specific fields.
    - **Expected Outcome**: Graceful `422 Unprocessable Entity` with Zod-driven error messages.
3.  **Dirty Data Grace**:
    - Manually remove a "required" field (defined in your new Zod schema) from a record in the database.
    - **Expected Outcome**: The UI should handle the missing data (e.g., using a default value) without a runtime crash.

---

### Step 4: Final Certification
After all implementation fixes have been verified, generate the **`Parity_Adversarial_Report.md`**.

- **Certification Level**: 
    - 🟢 **Full Parity**: Identical behavior and security.
    - 🟡 **Partial Parity**: Minor UI/UX drift with documented reasoning.
    - 🔴 **Significant Drift**: Core business logic differs from the original specification.
