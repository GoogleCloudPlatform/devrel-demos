// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

window.WALKTHROUGH_DATA = {
  repo: "ykdojo/repo-walkthrough",
  subpath: "",
  diffRange: "5984e02..1c3c31b",
  branch: "main",
  title: "Diff Walkthrough: 5984e02..HEAD",
  subtitle: "12 files changed (+545 / -167) since baseline release 5984e02 · Phrase-Anchored Cues, Transformation Narrative & Diff Mode",
  layers: [
    { id: "entry",        name: "Skill & Schema Spec",   color: "#4285F4", accent: "#8AB4F8", bg: "rgba(66, 133, 244, 0.08)" },
    { id: "engine",       name: "Diff & Build Engine",   color: "#FBBC04", accent: "#FDD663", bg: "rgba(251, 188, 4, 0.08)" },
    { id: "agents",       name: "Player & Diff UI",      color: "#FF8A65", accent: "#FFAB91", bg: "rgba(255, 138, 101, 0.08)" },
    { id: "flows",        name: "Cymbal Autos v2 Flow",  color: "#34A853", accent: "#81C995", bg: "rgba(52, 168, 83, 0.08)" },
    { id: "capabilities", name: "Automated Test Suite",  color: "#A142F4", accent: "#C58AF9", bg: "rgba(161, 66, 244, 0.08)" }
  ],
  nodes: [
    // Row 0: Skill & Schema Spec (y = 26)
    {
      id: "skill_md",
      label: "SKILL.md",
      sub: "Transformation & Diff Rules",
      path: "skills/repo-walkthrough/SKILL.md",
      layer: "entry",
      lines: 108,
      diff: { status: "modified", added: 15, deleted: 7 },
      x: 260, y: 26, w: 240, h: 58,
      role: "Updates the agent instructions to prioritize data transformations and downstream usage over raw syntax, mandate phrase-anchored cue timing, and support `--diff <rev-range>` walkthroughs.",
      snippet: "@@ -52,6 +52,12 @@\n+# Git diff walkthrough (e.g. changes between two commits)\n+python3 ~/projects/repo-walkthrough/scripts/fetch_repo.py <local-repo-path> \\\n+  --diff <base-rev>..<head-rev> \\\n+  --json /tmp/diff-analysis.json\n@@ -77,6 +83,7 @@\n+- **Explain transformations, not syntax**: Explain what input each file takes,\n+  what transformation it performs, and how its output is used down the line.\n+- Anchor each cue with `phrase: \"<exact words in narration>\"`"
    },
    {
      id: "schema_md",
      label: "data-schema.md",
      sub: "Phrase Cue & Diff Schema",
      path: "skills/repo-walkthrough/references/data-schema.md",
      layer: "entry",
      lines: 96,
      diff: { status: "modified", added: 21, deleted: 15 },
      x: 640, y: 26, w: 240, h: 58,
      role: "Extends the `window.WALKTHROUGH_DATA` specification with `diffRange`, per-node `diff: { status, added, deleted }` metadata, and `cues[].phrase` substrings.",
      snippet: "@@ -25,4 +25,5 @@\n window.WALKTHROUGH_DATA = {\n   repo: \"owner/repo\",\n+  diffRange: \"\", // optional git diff range (e.g. \"5984e02..HEAD\")\n@@ -42,3 +43,4 @@\n+  diff: { status: \"modified\", added: 18, deleted: 4 },\n@@ -68,3 +70,3 @@\n-  { at: 0.00, nodes: [\"init\"], focus: \"init\" }\n+  { at: 0.00, phrase: \"At the entry layer, init.py\", nodes: [\"init\"], focus: \"init\" }"
    },

    // Row 1: Diff & Build Engine (y = 150)
    {
      id: "fetch_py",
      label: "fetch_repo.py",
      sub: "Git Diff Range Analyzer",
      path: "scripts/fetch_repo.py",
      layer: "engine",
      lines: 689,
      diff: { status: "modified", added: 152, deleted: 7 },
      x: 260, y: 150, w: 240, h: 58,
      role: "Adds `--diff <rev-range>` and `fetch_git_diff()`, running `git diff --numstat`, `--name-status`, and `-U2` to rank modified files and extract unified diff previews.",
      snippet: "@@ -415,6 +415,24 @@\n+def fetch_git_diff(\n+    local_path: pathlib.Path,\n+    diff_range: str,\n+    max_files: int = 24,\n+) -> dict[str, Any]:\n+  numstat_out = subprocess.check_output(\n+      [\"git\", \"-C\", str(local_path), \"diff\", \"--relative\", \"--numstat\", diff_range, \"--\", \".\"],\n+      text=True,\n+  )\n+  patch_raw = subprocess.check_output(\n+      [\"git\", \"-C\", str(local_path), \"diff\", \"--relative\", \"-U2\", diff_range, \"--\", rel_p],\n+      text=True,\n+  )"
    },
    {
      id: "build_mjs",
      label: "build_walkthrough.mjs",
      sub: "Spoken Offset & Cue Validator",
      path: "scripts/build_walkthrough.mjs",
      layer: "engine",
      lines: 337,
      diff: { status: "modified", added: 58, deleted: 1 },
      x: 640, y: 150, w: 240, h: 58,
      role: "Adds `spokenWeight()` and `computeSpokenOffset(narration, phrase)` (weighting sentence pauses `+26` and clause commas `+12`) and rejects cues whose `at` drifts by `> 0.08`.",
      snippet: "@@ -80,4 +80,26 @@\n+export function spokenWeight(text = \"\") {\n+  let w = 0;\n+  for (let i = 0; i < text.length; i++) {\n+    const ch = text[i], next = text[i + 1] || \"\";\n+    if ((ch === \".\" || ch === \"!\" || ch === \"?\" || ch === \";\" || ch === \":\") && /\\s/.test(next)) w += 26;\n+    else if ((ch === \",\" || ch === \"-\") && /\\s/.test(next)) w += 12;\n+    else if (/\\s/.test(ch)) w += 0.3;\n+    else w += 1.0;\n+  }\n+  return w;\n+}\n+export function computeSpokenOffset(narration = \"\", phrase = \"\") {"
    },

    // Row 2: Player & Diff UI (y = 274)
    {
      id: "web_html",
      label: "web/index.html",
      sub: "Diff Badges & Cue Sync UI",
      path: "web/index.html",
      layer: "agents",
      lines: 1477,
      diff: { status: "modified", added: 92, deleted: 5 },
      x: 260, y: 274, w: 240, h: 58,
      role: "Computes `computeSpokenOffset()` at runtime in `resolveCue()`, renders `+added -deleted` SVG badges on node cards, and highlights `+` / `-` / `@@` diff lines in the inspector.",
      snippet: "@@ -658,4 +658,5 @@\n-      if (progress01 >= (c.at || 0)) chosen = c;\n+      const cueAt = typeof c.at === \"number\" ? c.at : computeSpokenOffset(st.narration, c.phrase);\n+      if (progress01 >= cueAt) chosen = c;\n@@ -811,6 +812,12 @@\n+      if (n.diff && (typeof n.diff.added === \"number\" || typeof n.diff.deleted === \"number\")) {\n+        const dEl = svgEl(\"text\", { x: n.x + n.w - 8, y: n.y + 23, \"text-anchor\": \"end\", class: \"node-diff\" }, g);\n+      }\n@@ -902,4 +912,8 @@\n+      if (line.startsWith(\"+\") && !line.startsWith(\"+++\")) return `<span class=\"diff-line-add\">${safe}</span>`;\n+      if (line.startsWith(\"-\") && !line.startsWith(\"---\")) return `<span class=\"diff-line-del\">${safe}</span>`;"
    },
    {
      id: "example_html",
      label: "cymbal.../index.html",
      sub: "Bundled Cymbal Autos Viewer",
      path: "examples/cymbal-autos-multimodal/index.html",
      layer: "agents",
      lines: 1410,
      diff: { status: "modified", added: 22, deleted: 1 },
      x: 640, y: 274, w: 240, h: 58,
      role: "Updates the standalone Cymbal Autos viewer with `spokenWeight()` and `computeSpokenOffset()` so both interactive playback and video rendering switch highlights on exact phrases.",
      snippet: "@@ -638,4 +638,21 @@\n+  function spokenWeight(text = \"\") {\n+    let w = 0;\n+    for (let i = 0; i < text.length; i++) {\n+      const ch = text[i], next = text[i + 1] || \"\";\n+      if ((ch === \".\" || ch === \"!\" || ch === \"?\") && /\\s/.test(next)) w += 26;\n+      else if ((ch === \",\" || ch === \"-\") && /\\s/.test(next)) w += 12;\n+      else w += /\\s/.test(ch) ? 0.3 : 1.0;\n+    }\n+    return w;\n+  }"
    },

    // Row 3: Cymbal Autos v2 Flow (y = 398)
    {
      id: "cymbal_data",
      label: "cymbal.../data.js",
      sub: "Transformation Narrative v2",
      path: "examples/cymbal-autos-multimodal/data.js",
      layer: "flows",
      lines: 418,
      diff: { status: "modified", added: 107, deleted: 100 },
      x: 260, y: 398, w: 240, h: 58,
      role: "Replaces syntax/table-name enumeration in `cymbal-autos-multimodal/data.js` with file-by-file data transformation narratives and anchors all 33 cues to exact spoken phrases.",
      snippet: "@@ -365,9 +372,9 @@\n-        { at: 0.00, nodes: [\"deal_sql\"], focus: \"deal_sql\" },\n-        { at: 0.50, nodes: [\"export_py\"], focus: \"export_py\" },\n-        { at: 0.85, nodes: [\"listings_json\", \"export_py\"], focus: \"listings_json\" }\n+        { phrase: \"Step 6 brings the previous AI signals together\", nodes: [\"deal_sql\"], focus: \"deal_sql\" },\n+        { phrase: \"Once the scored table is ready, 08 export frontend data.py\", nodes: [\"export_py\"], focus: \"export_py\" },\n+        { phrase: \"into listings.json\", nodes: [\"listings_json\", \"export_py\"], focus: \"listings_json\" }"
    },
    {
      id: "cymbal_manifest",
      label: "audio/manifest.json",
      sub: "Regenerated Despina WAV Map",
      path: "examples/cymbal-autos-multimodal/audio/manifest.json",
      layer: "flows",
      lines: 72,
      diff: { status: "modified", added: 28, deleted: 28 },
      x: 640, y: 398, w: 240, h: 58,
      role: "Records the new SHA-256 content hashes and synthesized `Despina` WAV audio mappings (`step-1.wav` .. `step-7.wav`, 360.6s total) for the v2 transformation-first narration.",
      snippet: "@@ -6,7 +6,7 @@\n     {\n       \"step\": 1,\n-      \"title\": \"Architecture Overview: Multimodal Auto Marketplace\",\n-      \"hash\": \"a469eb3338ef3eb1\",\n+      \"title\": \"End-to-End Flow: Raw Auction Data to Buyer Marketplace\",\n+      \"hash\": \"39386fcbca8a5d81\",\n       \"file\": \"audio/step-1.wav\""
    },

    // Row 4: Automated Test Suite (y = 522)
    {
      id: "test_fetch",
      label: "test_fetch_repo.py",
      sub: "Git Diff Extractor Tests",
      path: "tests/test_fetch_repo.py",
      layer: "capabilities",
      lines: 175,
      diff: { status: "modified", added: 27, deleted: 0 },
      x: 200, y: 522, w: 188, h: 58,
      role: "Verifies `_extract_diff_preview()` unified hunk trimming and `fetch_git_diff()` numstat/status extraction against real commits.",
      snippet: "@@ -146,3 +146,16 @@\n+  def test_fetch_git_diff_and_preview(self) -> None:\n+    preview = fetch_repo._extract_diff_preview(raw_patch)\n+    self.assertIn(\"@@ -1,3 +1,4 @@\", preview)\n+    info = fetch_repo.fetch_git_diff(repo_dir, \"5984e02..e9868a3\", max_files=12)\n+    report = fetch_repo.build_analysis_report(info)\n+    self.assertEqual(report[\"diffRange\"], \"5984e02..e9868a3\")"
    },
    {
      id: "test_pipe",
      label: "test_pipeline.mjs",
      sub: "Cue Drift Validator Tests",
      path: "tests/test_pipeline.mjs",
      layer: "capabilities",
      lines: 284,
      diff: { status: "modified", added: 20, deleted: 1 },
      x: 410, y: 522, w: 188, h: 58,
      role: "Tests `computeSpokenOffset()` punctuation-weighted timing and asserts that `validateWalkthroughData()` rejects missing or drifted cue phrases.",
      snippet: "@@ -109,4 +109,15 @@\n+  const offset = computeSpokenOffset(\n+    \"First we stage files in init.py. Next, runner.py executes the workflow.\",\n+    \"Next, runner.py\"\n+  );\n+  assert.ok(offset > 0.35 && offset < 0.65);\n+  assert.throws(() => validateWalkthroughData(badCueDrift), /drifts from spoken phrase/);"
    },
    {
      id: "test_e2e",
      label: "test_ui_e2e.mjs",
      sub: "Chromium E2E Inspector Test",
      path: "tests/test_ui_e2e.mjs",
      layer: "capabilities",
      lines: 700,
      diff: { status: "modified", added: 1, deleted: 1 },
      x: 620, y: 522, w: 188, h: 58,
      role: "Updates the Chromium E2E inspector link check to verify that Step 1's new initial focus (`00_copy_data.sh`) resolves with `DATA.subpath`.",
      snippet: "@@ -215,5 +215,5 @@\n       if (pagePath.includes(\"cymbal-autos-multimodal\")) {\n         assert.equal(\n           report.inspHref,\n-          \"https://github.com/.../cymbal-autos-multimodal/app/src/app/page.tsx\",\n+          \"https://github.com/.../cymbal-autos-multimodal/scripts/setup/00_copy_data.sh\"\n         );"
    },
    {
      id: "testing_md",
      label: "TESTING.md",
      sub: "Test Suite Documentation",
      path: "TESTING.md",
      layer: "capabilities",
      lines: 84,
      diff: { status: "modified", added: 2, deleted: 1 },
      x: 830, y: 522, w: 188, h: 58,
      role: "Documents the new unit and E2E test coverage for phrase-anchored cue timing and git diff analysis.",
      snippet: "@@ -36,3 +36,4 @@\n-- Schema & zero-overlap validator (`validateWalkthroughData`)\n+- Schema, zero-overlap, and phrase-anchored cue timing validator\n+  (`validateWalkthroughData`, `computeSpokenOffset`)"
    }
  ],
  edges: [
    {
      id: "skill_md>schema_md",
      from: "skill_md",
      to: "schema_md",
      label: "codifies rules in",
      detail: "`SKILL.md` defines transformation-first narrative rules, phrase-anchored cues, and `--diff` mode, which `data-schema.md` formalizes in the `window.WALKTHROUGH_DATA` schema."
    },
    {
      id: "skill_md>fetch_py",
      from: "skill_md",
      to: "fetch_py",
      label: "invokes --diff",
      detail: "Step 1 of `SKILL.md` invokes `fetch_repo.py --diff <base>..<head>` to extract changed files, `+added / -deleted` line counts, and unified diff previews."
    },
    {
      id: "schema_md>build_mjs",
      from: "schema_md",
      to: "build_mjs",
      label: "enforced by",
      detail: "`build_walkthrough.mjs` enforces the `cues[].phrase` synchronization rules defined in `data-schema.md` via `computeSpokenOffset()`."
    },
    {
      id: "fetch_py>web_html",
      from: "fetch_py",
      to: "web_html",
      label: "supplies node.diff",
      detail: "The `diff: { status, added, deleted, patchPreview }` metadata extracted by `fetch_repo.py` is rendered as `+added -deleted` badges and colored diff hunks in `web/index.html`."
    },
    {
      id: "build_mjs>web_html",
      from: "build_mjs",
      to: "web_html",
      label: "shares spokenWeight",
      detail: "`build_walkthrough.mjs` and `web/index.html` use the identical `spokenWeight()` and `computeSpokenOffset()` algorithm so build validation matches browser playback."
    },
    {
      id: "web_html>example_html",
      from: "web_html",
      to: "example_html",
      label: "bundles into",
      detail: "`build_walkthrough.mjs` copies `web/index.html` into `examples/cymbal-autos-multimodal/index.html` when building the standalone Cymbal Autos walkthrough."
    },
    {
      id: "build_mjs>cymbal_data",
      from: "build_mjs",
      to: "cymbal_data",
      label: "validates cues in",
      detail: "`build_walkthrough.mjs` validates all 33 `phrase`-anchored cues in `examples/cymbal-autos-multimodal/data.js` before synthesizing TTS audio."
    },
    {
      id: "cymbal_data>cymbal_manifest",
      from: "cymbal_data",
      to: "cymbal_manifest",
      label: "synthesizes WAVs",
      detail: "The rewritten v2 narration in `cymbal-autos-multimodal/data.js` produces new SHA-256 hashes and 7 `Despina` WAV files recorded in `audio/manifest.json`."
    },
    {
      id: "fetch_py>test_fetch",
      from: "fetch_py",
      to: "test_fetch",
      label: "tested by",
      detail: "`tests/test_fetch_repo.py` unit-tests `fetch_git_diff()` and `_extract_diff_preview()` in `scripts/fetch_repo.py`."
    },
    {
      id: "build_mjs>test_pipe",
      from: "build_mjs",
      to: "test_pipe",
      label: "tested by",
      detail: "`tests/test_pipeline.mjs` unit-tests `computeSpokenOffset()` and cue drift rejection in `scripts/build_walkthrough.mjs`."
    },
    {
      id: "cymbal_data>test_e2e",
      from: "cymbal_data",
      to: "test_e2e",
      label: "verified in Chromium by",
      detail: "`tests/test_ui_e2e.mjs` loads `examples/cymbal-autos-multimodal/index.html` in headless Chromium and verifies zero overflows and the updated `00_copy_data.sh` inspector link."
    },
    {
      id: "test_pipe>testing_md",
      from: "test_pipe",
      to: "testing_md",
      label: "documented in",
      detail: "`TESTING.md` documents the unit, pipeline, and E2E verification commands covering the diff."
    }
  ],
  walkthrough: [
    {
      step: 1,
      title: "Overview of Diff `5984e02..HEAD` (+545 / -167 across 12 Files)",
      focusNode: "skill_md",
      activeNodes: [
        "skill_md", "schema_md", "fetch_py", "build_mjs",
        "web_html", "example_html", "cymbal_data", "cymbal_manifest",
        "test_fetch", "test_pipe", "test_e2e", "testing_md"
      ],
      activeEdges: [
        "skill_md>schema_md", "skill_md>fetch_py", "schema_md>build_mjs",
        "fetch_py>web_html", "build_mjs>web_html", "web_html>example_html",
        "build_mjs>cymbal_data", "cymbal_data>cymbal_manifest",
        "fetch_py>test_fetch", "build_mjs>test_pipe", "cymbal_data>test_e2e", "test_pipe>testing_md"
      ],
      cues: [
        { at: 0.0, phrase: "Since the baseline release at commit 5984e02, this diff", nodes: ["skill_md", "schema_md"], focus: "skill_md" },
        { at: 0.27, phrase: "and data schema.md", nodes: ["schema_md", "skill_md"], focus: "schema_md" },
        { at: 0.45, phrase: "fetch repo.py", nodes: ["fetch_py", "build_mjs"], focus: "fetch_py" },
        { at: 0.47, phrase: "and build walkthrough.mjs", nodes: ["build_mjs", "fetch_py"], focus: "build_mjs" },
        { at: 0.59, phrase: "web/index.html renders", nodes: ["web_html", "example_html"], focus: "web_html" },
        { at: 0.81, phrase: "in data.js", nodes: ["cymbal_data", "cymbal_manifest"], focus: "cymbal_data" },
        { at: 0.82, phrase: "and audio/manifest.json", nodes: ["cymbal_manifest", "cymbal_data"], focus: "cymbal_manifest" },
        { at: 0.89, phrase: "test fetch repo.py", nodes: ["test_fetch", "test_pipe", "test_e2e", "testing_md"], focus: "test_fetch" },
        { at: 0.91, phrase: "test pipeline.mjs", nodes: ["test_pipe", "test_fetch", "test_e2e", "testing_md"], focus: "test_pipe" },
        { at: 0.94, phrase: "and test ui e2e.mjs", nodes: ["test_e2e", "test_fetch", "test_pipe", "testing_md"], focus: "test_e2e" }
      ],
      audio: "audio/step-1.wav",
      summary: "Since the baseline release (`5984e02`), **12 files changed (`+545 / -167`)** to solve three goals: (1) shift walkthrough narratives from raw code syntax to **file-by-file data transformations**, (2) synchronize node highlights to exact spoken phrases via `computeSpokenOffset()`, and (3) add first-class **Git Diff Walkthrough (`--diff`)** support.",
      narration: "Since the baseline release at commit 5984e02, this diff modifies twelve files across five layers to make walkthroughs clearer, tightly synchronized with speech, and capable of visualizing git diffs. At the top layer, SKILL.md and data schema.md update the authoring rules so walkthroughs explain what transformations happen in each file and how outputs flow downstream, rather than reciting code syntax. In the engine layer, fetch repo.py and build walkthrough.mjs add git diff extraction and punctuation-weighted spoken phrase timing. In the player layer, web/index.html renders plus and minus diff badges on node cards, highlights unified diff hunks in the inspector, and switches highlights on exact spoken phrases. Those engine upgrades power the v2 Cymbal Autos walkthrough in data.js and audio/manifest.json. Finally, the automated test suite in test fetch repo.py, test pipeline.mjs, and test ui e2e.mjs locks in every new behavior."
    },
    {
      step: 2,
      title: "Skill & Schema Evolution (`SKILL.md` & `data-schema.md`)",
      focusNode: "skill_md",
      activeNodes: ["skill_md", "schema_md"],
      activeEdges: ["skill_md>schema_md"],
      cues: [
        { at: 0.0, phrase: "In Step 2, SKILL.md", nodes: ["skill_md"], focus: "skill_md" },
        { at: 0.76, phrase: "in data schema.md", nodes: ["schema_md", "skill_md"], focus: "schema_md" }
      ],
      audio: "audio/step-2.wav",
      summary: "`SKILL.md` (`+15 / -7`) and `references/data-schema.md` (`+21 / -15`) codify the reviewer feedback into permanent skill rules: focus narration on transformations and downstream usage, anchor every cue with `phrase: \"...\"`, and support `--diff <rev-range>`.",
      narration: "In Step 2, SKILL.md is updated so future walkthroughs automatically apply the reviewer feedback. Instead of listing internal table names or model identifiers, the skill now instructs the author to explain what input each file takes, what transformation it performs, and how its output is consumed downstream, while also documenting the new dash-dash-diff CLI flag. Those authoring rules are formalized in data schema.md, which replaces hand-guessed cue fractions with phrase substrings and adds optional diff metadata fields to each node."
    },
    {
      step: 3,
      title: "Phrase-Anchored Cue Timing Engine (`build_walkthrough.mjs` & `web/index.html`)",
      focusNode: "build_mjs",
      activeNodes: ["schema_md", "build_mjs", "web_html", "example_html"],
      activeEdges: ["schema_md>build_mjs", "build_mjs>web_html", "web_html>example_html"],
      cues: [
        { at: 0.0, phrase: "Step 3 solves the highlight synchronization problem in build walkthrough.mjs", nodes: ["build_mjs"], focus: "build_mjs" },
        { at: 0.73, phrase: "added to web/index.html", nodes: ["web_html", "build_mjs"], focus: "web_html" },
        { at: 0.81, phrase: "into examples/cymbal autos multimodal/index.html", nodes: ["example_html", "web_html"], focus: "example_html" }
      ],
      audio: "audio/step-3.wav",
      summary: "`scripts/build_walkthrough.mjs` (`+58 / -1`) and `web/index.html` (`+92 / -5`) introduce `spokenWeight()` and `computeSpokenOffset(narration, phrase)`, modeling TTS sentence and comma pauses so highlights switch within `~1%` of actual acoustic WAV boundaries.",
      narration: "Step 3 solves the highlight synchronization problem in build walkthrough.mjs. Previously, cue switch points were hand-estimated numbers between zero and one, which drifted by up to thirty-four percent when early sentences contained more clauses or punctuation pauses. The new spokenWeight and computeSpokenOffset functions model how the TTS voice pauses at sentence endings and commas, computing the exact fraction of audio elapsed before a target phrase is spoken and rejecting any cue that drifts by more than eight percent. The same spokenWeight and computeSpokenOffset functions are added to web/index.html inside resolveCue, and mirrored into examples/cymbal autos multimodal/index.html, so both live browser playback and video rendering switch highlights right as each file is named."
    },
    {
      step: 4,
      title: "Git Diff Extraction & Visual Diff Inspector (`fetch_repo.py` & `web/index.html`)",
      focusNode: "fetch_py",
      activeNodes: ["skill_md", "fetch_py", "web_html"],
      activeEdges: ["skill_md>fetch_py", "fetch_py>web_html"],
      cues: [
        { at: 0.0, phrase: "Step 4 adds first-class git diff walkthrough support starting in fetch repo.py", nodes: ["fetch_py"], focus: "fetch_py" },
        { at: 0.61, phrase: "web/index.html consumes", nodes: ["web_html", "fetch_py"], focus: "web_html" }
      ],
      audio: "audio/step-4.wav",
      summary: "`scripts/fetch_repo.py` (`+152 / -7`) adds `--diff <rev-range>` (`fetch_git_diff` + `_extract_diff_preview`), and `web/index.html` (`+92 / -5`) renders `+added -deleted` badges on SVG node cards plus green/red unified diff hunks in the right-hand inspector.",
      narration: "Step 4 adds first-class git diff walkthrough support starting in fetch repo.py. When invoked with dash-dash-diff and a revision range, fetch git diff runs git diff numstat, name-status, and unified diff commands to filter out binary media, rank modified source files by change size, and extract compact unified diff hunks. Downstream, web/index.html consumes that diff metadata to render green plus-added and red minus-deleted badges in the top-right corner of each node card, while formatting plus, minus, and hunk header lines with syntax highlighting in the right-hand code inspector."
    },
    {
      step: 5,
      title: "Cymbal Autos v2 Narrative & Audio (`data.js` & `audio/manifest.json`)",
      focusNode: "cymbal_data",
      activeNodes: ["build_mjs", "cymbal_data", "cymbal_manifest", "test_fetch", "test_pipe", "test_e2e", "testing_md"],
      activeEdges: ["build_mjs>cymbal_data", "cymbal_data>cymbal_manifest", "fetch_py>test_fetch", "build_mjs>test_pipe", "cymbal_data>test_e2e", "test_pipe>testing_md"],
      cues: [
        { at: 0.0, phrase: "In Step 5, examples/cymbal autos multimodal/data.js", nodes: ["cymbal_data"], focus: "cymbal_data" },
        { at: 0.5, phrase: "updates audio/manifest.json", nodes: ["cymbal_manifest", "cymbal_data"], focus: "cymbal_manifest" },
        { at: 0.67, phrase: "test fetch repo.py", nodes: ["test_fetch", "test_pipe", "test_e2e", "testing_md"], focus: "test_fetch" },
        { at: 0.71, phrase: "test pipeline.mjs", nodes: ["test_pipe", "test_fetch", "test_e2e", "testing_md"], focus: "test_pipe" },
        { at: 0.76, phrase: "test ui e2e.mjs", nodes: ["test_e2e", "test_fetch", "test_pipe", "testing_md"], focus: "test_e2e" },
        { at: 0.81, phrase: "and TESTING.md", nodes: ["testing_md", "test_fetch", "test_pipe", "test_e2e"], focus: "testing_md" }
      ],
      audio: "audio/step-5.wav",
      summary: "`examples/cymbal-autos-multimodal/data.js` (`+107 / -100`) and `audio/manifest.json` (`+28 / -28`) apply the transformation-first narrative and phrase-anchored cues across all 7 steps, verified by `test_fetch_repo.py`, `test_pipeline.mjs`, and `test_ui_e2e.mjs`.",
      narration: "In Step 5, examples/cymbal autos multimodal/data.js rewrites all sixteen node summaries and seven walkthrough steps around data transformations and downstream impact, anchoring all thirty-three cues to exact spoken phrases and eliminating the thirty-four percent highlight lag in Step 6. Regenerating the voice narration updates audio/manifest.json with seven new Despina WAV files totaling six minutes of narration. Finally, test fetch repo.py, test pipeline.mjs, test ui e2e.mjs, and TESTING.md add automated unit and Chromium E2E tests covering git diff extraction, spoken offset calculation, and inspector links."
    }
  ]
};
