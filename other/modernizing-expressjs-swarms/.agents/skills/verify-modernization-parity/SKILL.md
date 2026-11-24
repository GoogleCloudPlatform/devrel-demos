---
name: verify-modernization-parity
description: >-
  Executes independent side-by-side runtime parity (Two-Tab Test) and adversarial security/dirty-data
  verification between a legacy Express app (:3000) and a modernized Next.js app (:3001) backed by a
  unified MongoDB instance (:27017). Use for Wave 4 swarm verifiers or standalone migration certification.
---

# Runtime Parity & Adversarial Verification

Verify `modern-app` (`http://localhost:3001`) against `legacy-app` (`http://localhost:3000`) over shared MongoDB (`localhost:27017`), covering every Wave 4 `[ ]` test case in `docs/Backend_Contract.md` and `docs/UI_Topology.md`.
- **Pre-Flight**: Start `modern-app` (`:3001`) in the background if not already running; confirm `docker ps` shows a single MongoDB bound to `:27017` and both `:3000` and `:3001` return `200 OK` against the same database.
- **Verifier Roles & Fixture Isolation**: Run three read-only verifiers with separate test-data prefixes (`parity-`, `browser-`, `adv-`):
  1. `@parity-verifier` (`/swarm` worker) — Track A Part 1.
  2. `browser-verifier` (Coordinator subagent via `define_subagent({ EnableMCPTools: true, EnableWriteTools: false })` in a clean `isolatedContext`) — Track A Part 2.
  3. `@sec-adversary` (`/swarm` worker) — Track B.
- **Role Boundary & Defect Loop**: Verifiers must never edit `modern-app/` or `legacy-app/`. Report defects on the board to `@foundation` (for shared or small targeted fixes) or `@coordinator` (to spawn a fresh targeted `@fix-<domain>` worker if a larger slice defect is found—assuming Wave 3 `@slice-*` workers were retired once Wave 3 passed) with exact `curl`/browser repro + expected vs. actual to fix, **add a regression test**, rebuild cleanly (`@slice-verifier`, after stopping `:3001`), and re-verify live after `[done]`. Avoid literal `@worker-name` mentions in briefs or summaries when not intentionally waking a worker. Delete all temporary (`parity-`, `browser-`, `adv-`) DB fixtures before finishing.

---

## Track A: Functional Parity (`@parity-verifier` + `browser-verifier`)

### Part 1: CLI API & SSR Parity (`@parity-verifier` via `curl`)
- **Envelopes, Pagination & URLs**: Verify JSON shapes, sort order, page sizes, boundary queries (`?page=0`, `-1`, `abc`, out-of-range), and malformed/encoded path params (e.g., `%E0%A4%A` -> `400`, never `500 URIError`).
- **Status Precedence**: Verify `400` (invalid JSON), `401` (unauthenticated mutation), `403` (non-owner), `404` (missing or malformed `ObjectId`), and `422` (flattened `fieldErrors`).
- **Cross-App Interop (`:3000` <-> `:3001`)**: Confirm accounts created on `:3001` authenticate on `:3000` (`bcrypt` parity) and records written by either app render cleanly in the other.

### Part 2: Two-Tab Browser Sweep (`browser-verifier` via `chrome-devtools-plugin_chrome-devtools`)
- **MCP Setup & Hygiene**: Read lazy schemas in `<appDataDir>/mcp/chrome-devtools-plugin_chrome-devtools/` before `call_mcp_tool`. Open pages in a clean `isolatedContext` (avoiding stale session cookies), **clear** inputs before typing, and use `handle_dialog` for `window.confirm` prompts.
- **Sweep & Round-Trip**: Visit every route in `docs/UI_Topology.md` (including mobile `<768px` viewport and `404`s) confirming zero hydration, RSC, Base UI, CSP, or 5xx errors. Execute full signup -> create -> edit -> sub-resource -> delete -> logout across `:3001` and `:3000` (including dirty legacy records created on `:3000`), and report any remaining `browser-` user IDs for DB cleanup.

---

## Track B: Adversarial Security & Dirty Data (`@sec-adversary`)

1. **Auth, Redirects & Headers**: Verify login anti-enumeration (unknown user vs. wrong password vs. passwordless OAuth account), deleted-user stale JWT rejection (`401` / redirect), CSRF enforcement, security headers (`X-Content-Type-Options`, `X-Frame-Options`/CSP `frame-ancestors`, no `X-Powered-By`), and open-redirect neutralization across raw and single/double percent-encoded payloads (`https://evil.com`, `//evil.com`, `\`, `/%5cevil.com`, `/%2fevil.com`, `/%255cevil.com`).
2. **IDOR & Compound Ownership**: Attempt cross-user `edit`/`PUT`/`DELETE` (`403`, zero DB mutation) and test every multi-actor authorization matrix documented in `docs/Backend_Contract.md`.
3. **Mass Assignment, Secret Leaks & Boundaries**: Inject privileged keys (`_id`, `provider`, `role`, `hashed_password`, tokens) on writes; scan both JSON APIs and SSR HTML payloads for leaked hashes, tokens, OAuth blobs, or private emails; confirm neutralized legacy `GET` quirks cause zero mutations; fuzz empty/whitespace/over-length/wrong-type/operator inputs.
4. **Dirty-Data & Partial-Index Resilience**: Temporarily insert (and clean up) `adv-` MongoDB docs with omitted keys, multiple empty-string OAuth fields (testing partial unique indexes against `E11000`), dangling `ObjectId` refs, and malformed embedded fields—verifying `200` UI fallbacks and `403` (never `500`) auth guards.

---

## Close-Out & Certification (`docs/Parity_Adversarial_Report.md`)
1. Once live verification is clean, have `@foundation` delete any remaining temporary (`parity-`, `browser-`, `adv-`) DB fixtures and verify baseline DB restoration.
2. Stop `:3001` and have `@slice-verifier` run the final `npm test`, `npx tsc --noEmit`, `npm run lint`, and `npm run build`.
3. Have `@parity-verifier` write `docs/Parity_Adversarial_Report.md` recording the overall parity level—🟢 **Full Parity**, 🟡 **Partial Parity** (documented safe intentional drift / unconfigured optional OAuth), or 🔴 **Significant Drift**—with the stream summary matrix, remediated defects, final `npm test` / `tsc` / `lint` / `npm run build` status, and baseline DB restoration proof.
4. Retire all swarm workers and post a final `[done]` summary (without `@mentions`) to close the swarm.
