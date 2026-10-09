# `window.WALKTHROUGH_DATA` Schema & 5-Layer Geometry Reference

Use this reference when authoring `data.js` for a target repository.

## 1. Coordinate Grid (Default: 5 Layers, Flexible: 3-6 Layers)

- **Default Layer Count**: **5 layers** is the recommended default for most repositories, with flexibility to use **3-4 layers** for smaller utilities/CLIs or **6 layers** for deeper full-stack systems (`index.html` automatically computes the full-graph `viewBox` height from `DATA.nodes`).
- **Left Section Headers (`x: 14..190`)**: Reserved exclusively for the horizontal layer labels (`x = 26`).
- **Node Placement (`x >= 200`, `h = 58`)**: Every node must have `x >= 200` so node borders never collide with left layer headers.
- **Recommended Row Y-Coordinates (spaced by `124px`)**:
  - **Row 0 (`entry`)**: `y = 26`, `h = 58`
  - **Row 1 (`engine`)**: `y = 150`, `h = 58`
  - **Row 2 (`agents`)**: `y = 274`, `h = 58`
  - **Row 3 (`flows`)**: `y = 398`, `h = 58`
  - **Row 4 (`capabilities`)**: `y = 522`, `h = 58`
  - *(Optional Row 5 for 6-layer repos: `y = 646`, `h = 58`)*
- **Recommended X-Column Slots per Row**:
  - **3 nodes in a row** (`w = 215`): `x = 205`, `x = 495`, `x = 785`
  - **4 nodes in a row** (`w = 188`): `x = 200`, `x = 410`, `x = 620`, `x = 830`
  - **2 nodes in a row** (`w = 240`): `x = 260`, `x = 640`

## 2. Complete `data.js` Template

```javascript
window.WALKTHROUGH_DATA = {
  repo: "owner/repo", // or local directory name
  subpath: "",        // optional monorepo subdirectory (e.g. "data-analytics/cymbal-autos-multimodal")
  diffRange: "",      // optional git diff range (e.g. "5984e02..HEAD") for diff walkthroughs
  branch: "main",
  title: "owner/repo",
  subtitle: "Short description · Interactive Architecture Walkthrough",
  layers: [
    { id: "entry",        name: "Entry & CLI",           color: "#4285F4", accent: "#8AB4F8", bg: "rgba(66, 133, 244, 0.08)" },
    { id: "engine",       name: "Execution Engine",      color: "#FBBC04", accent: "#FDD663", bg: "rgba(251, 188, 4, 0.08)" },
    { id: "agents",       name: "Core Domain",           color: "#FF8A65", accent: "#FFAB91", bg: "rgba(255, 138, 101, 0.08)" },
    { id: "flows",        name: "Flows & Events",        color: "#34A853", accent: "#81C995", bg: "rgba(52, 168, 83, 0.08)" },
    { id: "capabilities", name: "Tools, Models & State", color: "#A142F4", accent: "#C58AF9", bg: "rgba(161, 66, 244, 0.08)" }
  ],
  nodes: [
    {
      id: "init",
      label: "__init__.py",          // Exact original filename (shown in UI)
      sub: "Core Package Exports",   // Short 2-4 word subtitle
      path: "src/pkg/__init__.py",   // Relative path in repository
      layer: "entry",                // Must match one of layers[].id
      lines: 42,
      diff: { status: "modified", added: 18, deleted: 4 }, // optional (for diff walkthroughs; renders +18 -4 badge)
      x: 205, y: 26, w: 215, h: 58,
      role: "Concise 1-2 sentence explanation of what this file does and how it connects to neighbors.",
      snippet: "Representative 5-10 line code excerpt (or unified diff hunk with +/-/@@ lines for diff walkthroughs)."
    }
  ],
  edges: [
    {
      id: "init>runner",
      from: "init",
      to: "runner",
      label: "exports Runner",
      detail: "1-sentence description of the call, import, or data flow between these two files."
    }
  ],
  walkthrough: [
    {
      step: 1,
      title: "The Front Door: `__init__.py`",
      focusNode: "init",
      activeNodes: ["init", "runner", "agent"],
      activeEdges: ["init>runner"],
      cues: [
        { at: 0.00, phrase: "At the entry layer, init.py", nodes: ["init"], focus: "init" },
        { at: 0.42, phrase: "delegates execution to runner.py", nodes: ["runner"], focus: "runner" },
        { at: 0.76, phrase: "which coordinates agent.py", nodes: ["agent"], focus: "agent" }
      ],
      audio: "audio/step-1.wav",
      summary: "UI text with `code` backticks and exact filenames like `__init__.py` explaining what transforms here and where it flows next.",
      narration: "At the entry layer, init.py exposes the public package interface and delegates execution to runner.py, which coordinates agent.py to process each turn."
    }
  ]
};
```

## 3. Step, Narration & Cue Synchronization Rules

1. **Transformation & Downstream Impact Over Code Syntax**:
   - Write `role`, `summary`, and `narration` for a reader/listener who is new to the codebase: explain **what transformation happens in each file** and **how its output gets used down the line**, organized file by file.
   - Avoid reciting raw SQL/code syntax, full internal table identifiers, or model endpoint strings in `narration` (keep exact code details in `snippet` where the viewer can inspect them visually).
2. **Step 1 (`step: 1`) Full Overview & Steps 2..N Focused Clusters**:
   - Step 1 automatically uses the full 5-layer camera (`FULL_VB`) so all left section headers and the entire graph are visible.
   - For Steps 2..N, keep `activeNodes` to the 2-5 connected nodes actually discussed in that step's narration so `computeStepCamera` frames them cleanly.
3. **Exact Narration-to-Cue Synchronization**:
   - Order `cues` in the exact chronological sequence files are spoken in `narration`.
   - Include `phrase: "<exact substring in narration>"` on each cue so `build_walkthrough.mjs` can compute or verify `at` using punctuation-weighted spoken character offsets (`computeSpokenOffset(narration, phrase)`).
   - Never highlight a node that is not mentioned in `narration`, and never add a trailing wrap-up cue (`at: 0.90+`) that jumps focus back to an earlier node while the narrator is still finishing the final sentence.
4. **UI vs. TTS Filename Formatting**:
   - In `nodes[].label`, `walkthrough[].title`, and `walkthrough[].summary`, always write the **exact filename** (e.g., `__init__.py`, `_workflow.py`, `cli_tools_click.py`).
   - In `walkthrough[].narration`, write natural spoken filenames (`init.py`, `workflow.py`, `cli tools click.py`) and skip any *"Welcome to..."* intro.
