---
name: auditing-data-models
description: Analyzes legacy ORM models (Mongoose, Sequelize) to extract schemas, validations, and relationships. Use when reverse-engineering a legacy data layer for a modern rewrite.
---

# Auditing Data Models

Analyze the legacy data layer to extract schemas, validation rules, and entity relationships. Produce a blueprint for a modern, type-safe data access layer (e.g., Zod + Native MongoDB).

## Objective
Reverse-engineer the legacy application's database models to ensure data integrity and structural parity in the modernized system.

## Instructions for the Audit Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Locate the Models
- [ ] Step 2: Analyze Entity Schemas
- [ ] Step 3: Map Relationships & Hooks
- [ ] Step 4: Generate Data_Models.md
```

### Step 1. Locate the Models
Search the legacy codebase for database model definitions (e.g., `app/models/`, `db/models/`). Identify the Primary Entities and their corresponding source files.

### Step 2. Analyze Entity Schemas
For each database model, extract:
- **Fields & Types**: Map every field to its legacy data type (e.g., `String`, `ObjectId`, `Date`).
- **Validations**: Document required fields, unique constraints, regex patterns, or enums.
- **Default Values**: Identify any automatically assigned values (e.g., `Date.now`).
- **Legacy Methods/Virtuals**: Note custom methods (e.g., `user.authenticate(password)`) or computed properties that will need to be ported to the utility layer.

### Step 3. Map Relationships & Hooks
- **Relationships**: Identify how entities are connected (One-to-Many, Many-to-Many, Embedded Documents). Use **Mermaid ER diagrams** to visualize these connections in the final report.
- **Hooks**: Search for lifecycle events (e.g., `pre('save')`, `post('remove')`) that perform side-effects like cascading deletes or password hashing.

### Step 4. Generate Data_Models.md & Identify Probes
Compile findings into `docs/legacy-audit/Data_Models.md`. Additionally, **identify specific data-integrity stress-tests** (e.g., "Attempt to load a legacy record missing the `email` field to check if the new Zod schema handles it gracefully"). **Append** these probes to `docs/verification/Verification_Plan.md`.
