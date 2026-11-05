# Breaking News Lab (`news-lab-harness`)

An interactive **Agent Harness** sample built for Antigravity, Claude Code, and Codex.

Instead of relying on a single role prompt that forgets rules as the chat grows, **Breaking News Lab** wraps an AI model in a complete harness suit with **Persona (`OCeaN`)**, **Traffic-Light Permissions**, **Graph Memory + Dreaming**, **Local Skills**, and **Three Built-in Referee Grades (Truth, Safety, and Reading)**.

---

## Download Only This Demo

Per the [`devrel-demos` README](../../README.md), you can pull just this folder without cloning the entire repository using [giget](https://github.com/unjs/giget):

```bash
npx -y giget@latest gh+git:GoogleCloudPlatform/devrel-demos/agents/news-lab-harness news-lab-harness
cd news-lab-harness
```

---

## Directory Structure

```text
news-lab-harness/
├── AGENTS.md                  # Entry point: loads the harness on every turn
├── SKILL.md                   # On-demand doorway ("slip into Breaking News Lab")
├── permissions.md             # Permission slip (Green / Yellow / Red light)
├── hooks.json                 # Lifecycle Stop hook (runs all 3 grades automatically)
├── identity/
│   ├── persona.md             # Big Five (OCeaN) Investigative Hound traits
│   ├── job.md                 # Job description & editorial mandate
│   └── style.md               # 5th-grade clarity & anti-slop style rules
├── memory/
│   ├── memory_graph.json      # Living graph of verified facts, sources & rumor mills
│   └── dream.py               # Dreaming routine: promotes verified facts & prunes rumors
├── skills/
│   ├── verify-sources/
│   │   └── SKILL.md           # Local skill: 3-step source triangulation
│   └── write-bulletin/
│       └── SKILL.md           # Local skill: 4-beat breaking news bulletin
├── grades/
│   ├── check_truth.py         # Truth Grade: verifies [Source: ...] receipts & blocks rumor mills
│   ├── check_safety.py        # Safety Grade: blocks prompt injections, spoofed waivers & secret leaks
│   ├── check_reading.py       # Reading Grade: enforces <= 6.5 Flesch-Kincaid grade & zero AI slop
│   └── run_all_grades.py      # Master scoreboard & Stop-hook handler
├── tools/
│   ├── news-lab               # Unified CLI (`grade`, `dream`, `memory`)
│   └── save_to_gdocs.sh       # Safe Google Docs wrapper locked to approved Doc/Tab ID
├── examples/
│   ├── sample_bad_draft.md    # Example draft that FAILS all 3 grades
│   └── sample_good_draft.md   # Example draft that PASSES all 3 grades (100/100)
└── tests/
    └── test_harness.py        # Automated test suite
```

---

## Quick Start (30-Second Demo)

### 1. Grade a Bad Draft (Watch the Referee Block It)
```bash
./tools/news-lab grade examples/sample_bad_draft.md
```
Catches anonymous rumors, `AnonTechLeaks` rumor-mill citations, leaked secret tokens, spoofed `#KOVE-SEC-8821` waivers, prompt injection (`IGNORE PREVIOUS INSTRUCTIONS`), and corporate AI slop (`game-changer`, `synergy`, `paradigm shift`).

### 2. Grade a Verified Bulletin (`100/100` Pass)
```bash
./tools/news-lab grade examples/sample_good_draft.md
```
Verifies primary `[Source: ...]` tags, `0` safety threats, and a **Grade 4.2** reading level.

### 3. Run the Memory Dreaming Loop
```bash
./tools/news-lab dream --dry-run
```
Promotes verified scratchpad notes into `memory/memory_graph.json` and prunes unverified rumors from `AnonTechLeaks`.

### 4. Slip Into the Harness Inside Antigravity, Claude Code, or Codex
Open this folder in your agent workspace or prompt your agent:
> *"Slip into `news-lab-harness` and write a breaking news bulletin on how agent harnesses work."*

### 5. Run the Test Suite
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
