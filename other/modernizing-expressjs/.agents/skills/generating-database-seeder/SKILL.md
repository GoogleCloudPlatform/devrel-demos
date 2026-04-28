---
name: generating-database-seeder
description: Generates and executes a database seeder script to populate MongoDB with sample data based on modern Zod schemas. Use this to prepare an environment for functional parity testing.
---

# Generating Database Seeder

Establish a clean, reproducible database state for development and verification.

> [!IMPORTANT]
> **DATABASE STRATEGY**: Skip this skill if the modernization strategy is to **use the existing legacy database directly**. This tool is only for cases where you need a fresh dataset to test in isolation.

## Objective
Generate a script that populates the modern database with sample records (Primary and Sub-resources) that satisfy the Zod validation rules and established relational integrity.

## Workflow

1.  **Analyze Schemas**: Read the modern schemas (e.g., `src/lib/models/schema.ts`) to identify required fields, data types, and default values.
2.  **Generate Realistic Samples**: Create a set of sample data that covers:
    - **Primary Resources**: Users, Accounts, or root entities.
    - **Sub-resources**: Related items linked via `ObjectId`.
    - **Edge Cases**: Empty strings, long text, and various tag/category combinations.
3.  **Implement Seeder**: Create the seeder script (e.g., `src/lib/db/seeder.ts`).
    - **Invariants**: The script MUST clear existing collections before insertion to ensure a deterministic state.
    - **Security**: Hash passwords and sanitize inputs using the project's utility functions.
4.  **Execute & Verify**: Run the seeder (e.g., `npm run db:seed`) and confirm the records exist in the database with the correct structure.

## Output
A functional seeding command and a populated database ready for Phase 5 verification.
