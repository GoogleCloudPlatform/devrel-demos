---
name: breaking-news-lab
description: Slip into the Breaking News Lab agent harness — combines an investigative reporter persona (OCeaN), traffic-light permissions, graph memory with dreaming, local reporting skills, and three deterministic referees (Truth, Safety, and Reading grade).
---

# Breaking News Lab Harness (`news-lab-harness`)

## Overview
Use this skill whenever the user asks you to **"slip into the Breaking News Lab harness"**, investigate a breaking news story, fact-check a draft, or run the `news-lab` grading loop.

## Mandatory Turn-by-Turn Harness Loop

1. **Step 1 — Equip Identity & Permissions:**
   Read [`identity/persona.md`](./identity/persona.md), [`identity/job.md`](./identity/job.md), [`identity/style.md`](./identity/style.md), and [`permissions.md`](./permissions.md).
2. **Step 2 — Consult Memory Graph:**
   Check [`memory/memory_graph.json`](./memory/memory_graph.json) (`./tools/news-lab memory`) so you never repeat debunked rumors or forget verified primary sources.
3. **Step 3 — Execute Local Skills:**
   - Use [`skills/verify-sources/SKILL.md`](./skills/verify-sources/SKILL.md) to triangulate facts.
   - Use [`skills/write-bulletin/SKILL.md`](./skills/write-bulletin/SKILL.md) to write the bulletin.
4. **Step 4 — Run the Referee Scoreboard (Hard Gate):**
   Run the harness grader on your draft:
   ```bash
   ./tools/news-lab grade path/to/draft.md
   ```
   If **Truth Grade**, **Safety Grade**, or **Reading Grade** is below `80/100` (or exits non-zero), fix every listed violation and re-run until all three grades pass.
5. **Step 5 — Dream (Memory Consolidation):**
   After completing a story, run:
   ```bash
   ./tools/news-lab dream
   ```
   to promote verified scratchpad facts into the permanent memory graph and discard unverified noise.
