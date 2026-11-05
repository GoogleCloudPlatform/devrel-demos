---
name: verify-sources
description: Local Breaking News Lab skill for triangulating incoming news tips against the memory graph and primary sources before drafting.
---

# Local Skill: Verify Sources (`skills/verify-sources`)

Use this step-by-step recipe card whenever a new tip, press release, or claim arrives at the Breaking News Lab desk:

1. **Step 1 — Check the Memory Graph:**
   Look up the company, project, or source in [`memory/memory_graph.json`](../../memory/memory_graph.json).
   - Is the source listed under `verified_sources`?
   - Is the source flagged under `known_rumor_mills`? (If so, reject any claim that relies on it alone.)
2. **Step 2 — Demand Primary Receipts:**
   Every number, benchmark, price, or quote needs at least **one primary source** (an official repo, peer-reviewed paper, public filing, or reproducible lab test).
3. **Step 3 — Tag Every Fact:**
   Attach `[Source: <Name>]` right after every factual or numeric sentence. Never leave `[UNVERIFIED]` or `"sources say"` in a finished draft.
4. **Step 4 — Log New Findings to the Scratchpad:**
   Add newly discovered facts (with `verified: true` or `verified: false`) to the `scratchpad` array in `memory/memory_graph.json` so the **Dreaming** routine (`memory/dream.py`) can consolidate them after your story ships.
