---
name: write-bulletin
description: Local Breaking News Lab skill for structuring a 4-part breaking news bulletin that passes Truth, Safety, and Reading grades on the first try.
---

# Local Skill: Write Breaking Bulletin (`skills/write-bulletin`)

Follow this 4-beat recipe card whenever you draft a Breaking News Lab story:

1. **Beat 1 — The Headline & 1-Sentence Lead (Under 20 words):**
   Start with a sharp `# Headline` and a 1-sentence lead that states exactly what happened today.
2. **Beat 2 — The Hard Receipts (With `[Source: ...]` Tags):**
   In 2–3 short paragraphs, share the concrete numbers (cost, speed, date, or headcount) and tag each claim with `[Source: <Verified Source>]`.
3. **Beat 3 — The 5th-Grade Breakdown:**
   Explain *how* it works and *why* regular builders should care using a simple physical metaphor (no unexplained jargon, no paragraphs over 75 words).
4. **Beat 4 — What Happens Next:**
   End with 1–2 crisp sentences on what to watch next, then run `./tools/news-lab grade <draft.md>` to verify all three grades pass (`100/100`).
