---
name: scaffolding-data-layer
description: Reads Data_Models.md artifacts and generates the equivalent modern ORM schema or native MongoDB/Zod layer. Use when following a legacy audit artifact to scaffold out the data access layer for a Next.js app.
---

# Scaffolding the Modern Data Layer

Translate legacy data models (Mongoose, Sequelize, etc.) into a modern, type-safe data access layer using **TypeScript** and **Zod**.

## Objective
Recreate the legacy data structures in a way that provides runtime validation and full TypeScript support, while accounting for **Schema Evolution** and potential "Dirty Data" in the legacy system.

## Instructions for the Scaffold Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Analyze Audit Specs
- [ ] Step 2: Perform Data Integrity Audit (Draft)
- [ ] Step 3: Initialize Database Connection
- [ ] Step 4: Define Zod Schemas & TypeScript Types
- [ ] Step 5: Implement Data Access Utilities
```

### Step 1. Analyze Audit Specs
Locate and read `docs/legacy-audit/Data_Models.md`. Identify:
- **Primary Entities** and their relationships (One-to-Many, Many-to-Many).
- **Validation Rules**: Required fields, regex patterns, min/max values.
- **Middleware Hooks**: Legacy `pre-save` or `post-remove` logic that needs to be manually ported to the service layer.

### Step 2. Perform Data Integrity Audit
Before writing code, you MUST ensure the modern schemas are compatible with the existing legacy data.
- **Strategy**: Run the new Zod validation schemas against *actual* records in the legacy database.
- **Outcome**: Identify "Dirty Data" gaps (e.g., missing required fields in old records, inconsistent types) and use `z.optional()` or `.nullable()` to maintain compatibility with legacy data patterns.

### Step 3. Connect to Legacy Database
Create `src/lib/db/mongodb.ts` (or the appropriate client).
- **Configuration**: Ensure the connection string (usually via `MONGODB_URI` in `.env.local`) points to the **legacy-app's database**.
- **Pattern**: Export a cached client promise (Singleton pattern) to avoid opening too many connections during HMR (Hot Module Replacement) in Next.js development.
```typescript
// Example: src/lib/db/mongodb.ts
import { MongoClient } from "mongodb";

if (!process.env.MONGODB_URI) {
  throw new Error('Invalid/Missing environment variable: "MONGODB_URI"');
}

const uri = process.env.MONGODB_URI;
// ... (Rest of singleton implementation)
```

### Step 4. Define Zod Schemas & TypeScript Types
Create `src/lib/models/schema.ts` (Zod) and `src/lib/models/types.ts` (TypeScript).
- **Zod First**: Define the schema using Zod for runtime validation.
- **Type Inference**: Use `z.infer<typeof Schema>` to generate your TypeScript types automatically.
- **Relationship Mapping**: Convert legacy ORM relationships (e.g., Mongoose `Refs`) into manual link logic using `ObjectId` from the native driver.

### Step 5. Implement Data Access Utilities
Create `src/lib/models/utils.ts` for logic that was previously buried in the ORM (e.g., password hashing, complex queries, virtual field calculation).
- **Static Utilities**: Native drivers lack "Model Methods." All logic must be extracted into pure functions that take the data object as an argument.
