---
name: repo-walkthrough
description: >-
  Generate an interactive codebase architecture graph website and optional
  voice-narrated MP4 walkthrough video for any local, public GitHub, or
  private GitHub repository. Use when the user asks to visualize a codebase,
  build an interactive repo walkthrough website, or generate a walkthrough
  video for a repository or git diff.
license: MIT
compatibility: >-
  Website mode requires Python 3 and a browser; optional Node.js 20+ and
  GEMINI_API_KEY for Gemini TTS audio. Website and video mode additionally
  requires Node.js 20+, GEMINI_API_KEY, ffmpeg, and Playwright (Chrome).
metadata:
  author: ykdojo
  version: "1.0.0"
---

# Repo Walkthrough Skill

Turn any repository (local directory, public GitHub repo, private GitHub repo, or git diff) into an interactive architecture graph website and an optional voice-narrated MP4 walkthrough video.

## Output Options

Support two modes (ask the user which they want if not specified, or default to **Website** first and offer **Website + Video**):

1. **Option 1: Website (`--mode website`)**
   - Generates a standalone interactive architecture viewer (`index.html` + `data.js`) where users can explore the layered graph, click any file or connection to inspect its role and code, and play a step-by-step voice-narrated walkthrough.
   - Synthesizes Gemini TTS audio (`audio/step-*.wav`) when `GEMINI_API_KEY` is available, or falls back to browser speech synthesis with `--no-tts`.
2. **Option 2: Website + Video (`--mode video`)**
   - Builds the interactive website first, synthesizes Gemini TTS narration, and renders an animated MP4 walkthrough video (`<slug>-walkthrough.mp4`) that steps through each layer and highlights files as they are discussed.

## Prerequisites

Run `node ~/projects/repo-walkthrough/scripts/build_walkthrough.mjs --check-prereqs` to check the environment.

| Dependency | Website Only (`--mode website`) | Website + Video (`--mode video`) | Purpose |
| :--- | :--- | :--- | :--- |
| **Python 3** | Required | Required | Runs `fetch_repo.py` to analyze local or GitHub repositories. |
| **Node.js 20+** | Required | Required | Runs the build, audio, and video scripts. |
| **`GEMINI_API_KEY`** | Optional (`--no-tts` uses browser speech) | **Required** | Generates Gemini TTS narration and aligns spoken cues. |
| **`ffmpeg`** | Not required | **Required** | Encodes the rendered frames and audio into an MP4 video. |
| **Playwright + Chrome** | Optional | **Required** | Renders walkthrough frames in headless Chrome. |
| **`gh` CLI** | Optional (private repos only) | Optional (private repos only) | Needed only for private GitHub repositories (`--mode gh`). |

## Step-by-Step Workflow

### Step 1: Analyze the Target Repository (or Git Diff Range)

Run [fetch_repo.py](../../scripts/fetch_repo.py) against a local path, `owner/repo`, or GitHub URL (including `/tree/<branch>/<subpath>`), or pass `--diff <rev-range>` to analyze a git diff across commits:

```bash
# Full repository or monorepo subdirectory
python3 ~/projects/repo-walkthrough/scripts/fetch_repo.py <owner/repo-or-local-path> \
  --json /tmp/repo-analysis.json

# Git diff walkthrough (e.g. changes between two commits or branches)
python3 ~/projects/repo-walkthrough/scripts/fetch_repo.py <local-repo-path> \
  --diff <base-rev>..<head-rev> \
  --json /tmp/diff-analysis.json
```

Read `/tmp/repo-analysis.json` (and inspect any additional key files if needed) to understand the codebase's entry points, execution engine, core domain modules, data/event flows, and tools/storage adapters.

### Step 2: Author `data.js` (5 Layers Default, 12-18 Nodes, 6-8 Walkthrough Steps)

Follow the schema and coordinate grid in [data-schema.md](./references/data-schema.md):

1. **Curate 10-18 High-Signal Files Across 5 Horizontal Layers by Default (Flexible: 3-6 Layers)**:
   - **5 layers is the recommended default** for most projects, with **3-4 layers** for smaller utilities/CLIs or **6 layers** for deeper systems (space rows evenly by `~124px` starting at `y = 26`):
     - Row 0 (`entry`, `y = 26`): Entry points, CLI, HTTP server, package exports
     - Row 1 (`engine`, `y = 150`): Orchestrators, runners, workflow engines
     - Row 2 (`agents`, `y = 274`): Core domain abstractions, agents, controllers
     - Row 3 (`flows`, `y = 398`): Pipelines, request/response flows, event handling
     - Row 4 (`capabilities`, `y = 522`): Tools, model adapters, persistence, evaluation
     - *(Optional Row 5, `y = 646`: Infrastructure or external storage when 6 layers are needed)*
2. **Enforce Zero-Overlap Geometry**:
   - Keep `x: 14..190` clear for left section headers; place all node boxes at `x >= 200` (at most 4 nodes per row) and wire edges between adjacent layers so arrows do not cross.
3. **Write 6-8 Narrative Steps Focused on Transformations & Downstream Flow**:
   - **Explain transformations, not syntax**: Explain what input each file takes, what transformation or logic it performs, and how its output is used downstream. Avoid reciting raw code syntax, internal table names, or model endpoint strings in `narration`.
   - Show exact original filenames (`__init__.py`, `_workflow.py`, `cli_tools_click.py`) in `label`, `title`, and `summary`; in `narration`, use natural spoken filenames (`init.py`, `workflow.py`, `cli tools click.py`) and skip any *"Welcome to..."* intro.
   - **Synchronize `cues` with spoken narration**:
     - List `cues` in the exact chronological order files are discussed in `narration`, and only include nodes that are discussed in that step.
     - Anchor each cue's `phrase` directly to the exact spoken target filename (e.g. `"03 vision extraction.sql"`, `"in route.ts"`) so the highlight switches right when the file is mentioned.

### Step 3: Validate & Build (Website or Website + Video)

Use [build_walkthrough.mjs](../../scripts/build_walkthrough.mjs) to validate `data.js` and build the output:

```bash
# Option 1: Website only
node ~/projects/repo-walkthrough/scripts/build_walkthrough.mjs \
  --data <out-dir>/data.js \
  --out-dir <out-dir> \
  --mode website \
  --open

# Option 2: Website + MP4 Video
node ~/projects/repo-walkthrough/scripts/build_walkthrough.mjs \
  --data <out-dir>/data.js \
  --out-dir <out-dir> \
  --mode video \
  --open
```
