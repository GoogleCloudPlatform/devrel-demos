---
name: scaffolding-ui-and-pages
description: Translates a UI_Component_Inventory.md artifact into modern ShadCN + Tailwind components AND fully scaffolded Next.js pages. Use when building the frontend design system and routing infrastructure.
---

# UI & Pages Scaffolding Specialist
Locate and read all artifacts in `docs/legacy-audit/` directory.

## Objective
Implement high-fidelity, modern React components using ShadCN and Tailwind, AND wire them together into fully functional Next.js pages (`src/app/**/page.tsx`) based on the requirements and Route Topology extracted from legacy Pug templates.

## Instructions for the Scaffold Subagent

Copy this checklist and track your progress:
```
Task Progress:
- [ ] Step 1: Initialize ShadCN
- [ ] Step 2: Build Shared Layout Components (src/components/layout/)
- [ ] Step 3: Scaffold Domain Components (src/components/articles/, etc.)
- [ ] Step 4: Extract Route & Page Topology
- [ ] Step 5: Scaffold Pages (src/app/**/page.tsx)
- [ ] Step 6: Verification (Visual smoke-test)
```

1.  **Initialize Design System:** Install the core ShadCN CLI using `npx shadcn@latest init` and configure the Tailwind theme (colors, fonts).
2.  **Build Shared Layouts:** Create the `Navbar`, `Footer`, and `MobileMenu`.
    *   **Logic:** Replicate the conditional logic (e.g., Auth-links) from the legacy metadata using Next.js `getServerSession`.
    *   **Modernize Features:** Use premium ShadCN primitives (e.g., `NavigationMenu`, `Avatar`, `Button`, `Card`) instead of raw Bootstrap/CSS classes.
3.  **Component Scaffolding:** Build specific logic-heavy components like `CommentList` and `ArticleCard` using the legacy field mapping.
4.  **Route & Page Topology Check:** Go to the `docs/legacy-audit/UI_Component_Inventory.md` and explicitly extract the list of intended pages and URLs.
5.  **Page Scaffolding:** For every single mapped route, create its routing wrapper in `src/app/[path]/page.tsx` (e.g. `/articles` needs `src/app/articles/page.tsx`). Hook up all business logic, server actions, UX intent, and data fetching components required.
6.  **Verification (Visual smoke-test):** Verify that the UI is visually appealing and functional.


**Output Result:** Ensure all components are exported from `src/components/` and all pages are functionally implemented in `src/app/`.

## Base UI & asChild Best Practices
If the design system uses `@base-ui/react` primitives (standard in ShadCN v4+), you MUST follow these patterns for `asChild` support:

1.  **Implicit Slot Pattern**: Use the `render` prop on Base UI primitives to implement `asChild`.
2.  **Button Semantics**: When a `Button` or `MenuItem` acts as a `Link` (via `asChild`), you MUST set `nativeButton={false}` on the primitive to suppress semantics warnings and avoid invalid nested interactive elements.
    *   **Example**: `<ButtonPrimitive nativeButton={false} render={(props) => <Link {...props} />}>`
3.  **Prop Merging**: Use `React.cloneElement` or direct Prop spreading into the `render` callback to ensure `ref`, `className`, and event handlers are correctly merged onto the child.
