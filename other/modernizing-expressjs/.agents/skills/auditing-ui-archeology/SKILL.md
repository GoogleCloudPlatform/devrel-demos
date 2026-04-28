---
name: auditing-ui-archeology
description: Analyzes legacy UI templates (Pug, EJS, HTML) to extract a comprehensive inventory of components, layouts, and conditional logic. Use when reverse-engineering a legacy frontend for a modern rewrite.
---

# Intent-Based UI Archeology

Analyze legacy template files (Pug, EJS, HTML) to extract "UI Intent" and structural patterns. Produce a blueprint for a modern, component-driven design system (e.g., ShadCN + Tailwind).

## Objective
Reverse-engineer the legacy frontend by mapping out the explicit **Route & Page Topology** alongside identifying **Recurring Component Patterns** and **Layout Hierarchies**. This ensures no pages are left behind during modernization.

## Instructions for the Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Map Route & Page Topology
- [ ] Step 2: Map Layout Hierarchies
- [ ] Step 3: Catalog Interaction Patterns
- [ ] Step 4: Document Component-Level Intent
- [ ] Step 5: Extract Design Tokens
- [ ] Step 6: Generate UI_Component_Inventory.md
```

### Step 1. Map Route & Page Topology
Explicitly list every route/URL requested and rendered by the legacy views.
- Create a matrix mapping the **Legacy Endpoint** (e.g., `GET /articles`) to the intended **Next.js App Router path** (e.g., `src/app/articles/page.tsx`).
- For each route, briefly list the high-level components it relies on.

### Step 2. Map Layout Hierarchies
Identify the "Shell" of the application. Locate parent templates (e.g., `layout.pug`, `base.html`) and child blocks.
- **Global Regions**: Identify Navbar, Sidebar, Footer, and Content areas.
- **Nested Layouts**: Check if specific modules (e.g., "Account Settings" or "Dashboard") have their own sub-layouts.

### Step 3. Catalog Interaction Patterns
Group UI elements into functional **Patterns**:
- **Navigation Patterns**: Top-level menus, breadcrumbs, pagination.
- **Form Patterns**: Input fields, validation error displays, submission buttons.
- **Data Display Patterns**: Lists/Feeds, Cards, Detail Views, Tables.
- **Feedback Patterns**: Toasts/Messages, Loading states, Empty states.

### Step 4. Document Component-Level Intent
For each unique pattern or shared fragment, document:
- **UI Intent**: What is the purpose of this element? (e.g., "The Primary Navbar provides global navigation and session-aware actions.")
- **Logic & State**: Conditional rendering (e.g., "Show 'Edit' button only if `resource.owner_id === current_user.id`").
- **Abstracted Props**: What data is required from the backend to render this? (e.g., `user`, `items[]`, `isOwner`).

### Step 5. Extract Design Tokens
Identify the underlying "Style Intent" found in legacy CSS or inline classes (e.g., Bootstrap `bg-primary`, `text-muted`):
- **Typography Hierarchy**: H1/H2 sizes, font weights.
- **Color Palette**: Primary, secondary, danger (error), success (toasts).
- **Spacing Patterns**: Common padding, margins between items in a list.

### Step 6. Generate UI_Component_Inventory.md & Identify Interaction Targets
Compile findings into a single, highly detailed artifact at `docs/legacy-audit/UI_Component_Inventory.md`, making sure the Route & Page Topology table is prominent. Additionally, **identify specific interaction-parity targets** (e.g., "The user profile must correctly display a fallback avatar if the image link is broken"). **Append** these interaction-specific test cases to `docs/verification/Verification_Plan.md`.
