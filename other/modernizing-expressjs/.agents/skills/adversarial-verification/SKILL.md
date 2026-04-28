---
name: adversarial-verification
description: Systematically probe a modernized Next.js application for logic flaws, security vulnerabilities, or missing features. Use this to find bugs or cases where the migration failed to match legacy behavior.
---

# Adversarial Verification

Take the role of an "Adversary" to scrutinize the modernized application. Proactively search for logic flaws, security vulnerabilities, and functional regressions that traditional tests may have missed.

## Objective
Identify where the modernization is "broken" or "insecure." The goal is to maximize the surface area for finding errors by stress-testing authorization, validation, and data integrity.

## Instructions for the Audit Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Authorization & Privilege Probes
- [ ] Step 2: Validation Stress-Testing
- [ ] Step 3: Data Integrity & "Dirty Data" Scrutiny
- [ ] Step 4: UI/UX Edge Case Exploration
- [ ] Step 5: Adversarial Audit Report
```

### Step 1. Authorization & Privilege Probes
Attempt to bypass access controls to prove the new implementation is at least as secure as the legacy model:
- **Unauthenticated Access**: Try to access protected interaction routes (POST/PUT/DELETE) without a valid session.
- **Vertical Privilege Escalation**: Attempt to perform administrative actions from a regular user account.
- **Horizontal Privilege Escalation (IDOR)**: Try to modify or delete a resource (e.g., User, Post, Profile) that belongs to a different user. Ensure the "Ownership Guard" is strictly enforced.

### Step 2. Validation Stress-Testing
Pressure the Zod schemas and Route Handlers with malformed input:
- **Schema Boundaries**: Send empty strings for required fields, exceed character limits, or provide invalid formats (e.g., malformed emails or non-numeric IDs).
- **Malformed Payloads**: Submit invalid JSON, excessively large payloads, or incorrect types (e.g., an array where a string is expected) to Route Handlers.
- **Response Consistency**: Verify that validation failures return a consistent `422 Unprocessable Entity` or `400 Bad Request` as documented in `API_Contracts.md`.

### Step 3. Data Integrity & "Dirty Data" Scrutiny
Investigate how the modernized app handles inconsistent or incomplete legacy data:
- **Null Reference Handling**: Check how the UI and API behave when a referenced entity (e.g., a Comment's Author) is missing from the database.
- **Inconsistent Keys**: Test the app against legacy records that may lack "required" fields introduced in the new Zod schemas. Does the app provide defaults or crash?

### Step 4. UI/UX Edge Case Exploration
Identify regressions in the user experience compared to the legacy intent:
- **Error Feedback**: Trigger validation errors and ensure the user receives clear feedback (e.g., Toasts or Form error messages).
- **Empty States**: Verify that every resource list (index pages, sub-resource feeds) has a clean, helpful empty state (not just a blank screen).
- **Mobile Resiliency**: Ensure the new ShadCN layout remains functional on small/narrow viewports.

### Step 5. Adversarial Audit Report
Generate a `docs/verification/Adversarial_Audit_Report.md`. Categorize findings as:
- **Critical Security Flaws**: Vulnerabilities like IDOR or session leaks.
- **Validation Oversights**: Missing field checks or incorrect Zod rules.
- **Functional Deficiencies**: Features that behave differently than the legacy intent.
- **UI Regressions**: Broken layouts or missing user feedback.
