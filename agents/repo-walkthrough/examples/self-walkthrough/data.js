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

// Clean, zero-crossing 5-layer architectural graph and 6-step self-walkthrough for repo-walkthrough

window.WALKTHROUGH_DATA = {
  repo: "ykdojo/repo-walkthrough",
  branch: "main",
  title: "repo-walkthrough",
  subtitle: "Universal Codebase Graph Website & Video Skill · Self-Walkthrough",
  layers: [
    { id: "entry",        name: "Skill & Plugin Entry",    color: "#4285F4", accent: "#8AB4F8", bg: "rgba(66, 133, 244, 0.08)" },
    { id: "engine",       name: "Analysis & CLI Builder",  color: "#FBBC04", accent: "#FDD663", bg: "rgba(251, 188, 4, 0.08)" },
    { id: "agents",       name: "Schema & Graph Model",    color: "#FF8A65", accent: "#FFAB91", bg: "rgba(255, 138, 101, 0.08)" },
    { id: "flows",        name: "Viewer, TTS & Renderer",  color: "#34A853", accent: "#81C995", bg: "rgba(52, 168, 83, 0.08)" },
    { id: "capabilities", name: "Audio Cache & MP4 Video", color: "#A142F4", accent: "#C58AF9", bg: "rgba(161, 66, 244, 0.08)" }
  ],
  nodes: [
    // ROW 0: SKILL & PLUGIN ENTRY (y = 26, x >= 200)
    {
      id: "skill_md",
      label: "SKILL.md",
      sub: "Agent Skill Spec",
      path: "skills/repo-walkthrough/SKILL.md",
      layer: "entry",
      lines: 98,
      x: 205, y: 26, w: 280, h: 58,
      role: "Defines the Agent Skill workflow for analyzing a repository and generating an interactive architecture website or walkthrough video.",
      snippet: `---
name: repo-walkthrough
description: >-
  Generate an interactive codebase architecture graph website and
  optional voice-narrated MP4 walkthrough video for any repository.
---`
    },
    {
      id: "plugin_json",
      label: "plugin.json",
      sub: "Plugin Manifest",
      path: "plugin.json",
      layer: "entry",
      lines: 3,
      x: 615, y: 26, w: 280, h: 58,
      role: "Plugin manifest that registers `repo-walkthrough` as an installable skill package.",
      snippet: `{
  "name": "repo-walkthrough"
}`
    },

    // ROW 1: ANALYSIS & CLI BUILDER (y = 150, x >= 200)
    {
      id: "fetch_repo",
      label: "fetch_repo.py",
      sub: "Repo & Diff Analyzer",
      path: "scripts/fetch_repo.py",
      layer: "engine",
      lines: 447,
      x: 205, y: 150, w: 215, h: 58,
      role: "Analyzes local repositories, GitHub repositories, or git diffs (`--diff`) and ranks key files across architectural layers.",
      snippet: `def score_file_path(path: str, size_bytes: int = 0) -> float:
  """Heuristic score ranking files by architectural centrality across the 5 layers."""`
    },
    {
      id: "build_walk",
      label: "build_walkthrough.mjs",
      sub: "Validator & Builder",
      path: "scripts/build_walkthrough.mjs",
      layer: "engine",
      lines: 260,
      x: 495, y: 150, w: 215, h: 58,
      role: "Validates the graph layout and walkthrough steps, then builds the interactive website (`--mode website`) and optional MP4 video (`--mode video`).",
      snippet: `validateWalkthroughData(data, path.basename(dataFile));
// Copies index.html + data.js, runs generate_live_audio.mjs, and optionally render_video.mjs`
    },
    {
      id: "render_sh",
      label: "render_video.sh",
      sub: "Video CLI Wrapper",
      path: "scripts/render_video.sh",
      layer: "engine",
      lines: 6,
      x: 785, y: 150, w: 215, h: 58,
      role: "Shell wrapper that resolves the repository root and runs `scripts/render_video.mjs`.",
      snippet: `REPO_ROOT="$(cd "$(dirname "\${BASH_SOURCE[0]}")/.." && pwd)"
exec node "$REPO_ROOT/scripts/render_video.mjs" "$@"`
    },

    // ROW 2: SCHEMA & GRAPH MODEL (y = 274, x >= 200)
    {
      id: "data_schema",
      label: "data-schema.md",
      sub: "Graph & Cue Schema",
      path: "skills/repo-walkthrough/references/data-schema.md",
      layer: "agents",
      lines: 87,
      x: 205, y: 274, w: 280, h: 58,
      role: "Reference specification for the layered coordinate grid, node/edge schema, and narration cue rules.",
      snippet: `// Row 0 (entry): y = 26 | Row 1 (engine): y = 150 | Row 2 (agents): y = 274
// Row 3 (flows): y = 398 | Row 4 (capabilities): y = 522`
    },
    {
      id: "data_js",
      label: "data.js",
      sub: "Walkthrough Data",
      path: "web/data-adk.js",
      layer: "agents",
      lines: 456,
      x: 615, y: 274, w: 280, h: 58,
      role: "Repository-specific graph data containing `layers`, `nodes`, `edges`, and step-by-step `walkthrough` narration.",
      snippet: `window.WALKTHROUGH_DATA = {
  repo: "ykdojo/repo-walkthrough",
  layers: [...], nodes: [...], edges: [...], walkthrough: [...]
};`
    },

    // ROW 3: VIEWER, TTS & RENDERER (y = 398, x >= 200)
    {
      id: "gen_audio",
      label: "generate_live_audio.mjs",
      sub: "Gemini TTS Audio",
      path: "scripts/generate_live_audio.mjs",
      layer: "flows",
      lines: 270,
      x: 205, y: 398, w: 215, h: 58,
      role: "Generates spoken narration audio for each walkthrough step using Gemini TTS and caches WAV files so unchanged steps are reused.",
      snippet: `function sanitizeForTts(rawText = "") {
  return rawText.replace(/\\b__([a-zA-Z0-9_]+)__/g, "$1").replace(/_/g, " ");
}`
    },
    {
      id: "index_html",
      label: "index.html",
      sub: "Interactive Web Viewer",
      path: "web/index.html",
      layer: "flows",
      lines: 1127,
      x: 495, y: 398, w: 215, h: 58,
      role: "Interactive web viewer that renders the layered architecture graph, file inspector sidebar, and voice-narrated walkthrough.",
      snippet: `if (params.has("video")) document.body.classList.add("video-mode");
window.renderWalkthroughFrame = ({ stepIndex, camTransition, stepProgress, timelinePct }) => { ... };`
    },
    {
      id: "render_video",
      label: "render_video.mjs",
      sub: "MP4 Video Renderer",
      path: "scripts/render_video.mjs",
      layer: "flows",
      lines: 293,
      x: 785, y: 398, w: 215, h: 58,
      role: "Renders the animated walkthrough in headless Chrome and combines the frames with step audio into an MP4 video via `ffmpeg`.",
      snippet: `await page.evaluate((state) => window.renderWalkthroughFrame(state), frameState);
const { data } = await cdp.send("Page.captureScreenshot", { format: "jpeg", quality: 90 });`
    },

    // ROW 4: AUDIO CACHE & MP4 VIDEO (y = 522, x >= 200)
    {
      id: "audio_cache",
      label: "audio/manifest.json",
      sub: "Audio Manifest & Cache",
      path: "web/audio/manifest.json",
      layer: "capabilities",
      lines: 82,
      x: 205, y: 522, w: 280, h: 58,
      role: "Stores step audio durations, aligned cue timings, and cached WAV references.",
      snippet: `{
  "step": 1, "hash": "cc22524683f9a897", "voice": "Despina",
  "file": "audio/step-1.wav", "durationSec": 24.04
}`
    },
    {
      id: "mp4_out",
      label: "walkthrough.mp4",
      sub: "Walkthrough Video",
      path: "web/adk-walkthrough.mp4",
      layer: "capabilities",
      lines: 1,
      x: 615, y: 522, w: 280, h: 58,
      role: "Exported MP4 walkthrough video combining animated graph transitions with voice narration.",
      snippet: `ffmpeg -f image2pipe -vcodec mjpeg -i - -i full-audio.wav \\
  -c:v libx264 -pix_fmt yuv420p -c:a aac -movflags +faststart walkthrough.mp4`
    }
  ],
  edges: [
    // Row 0 -> Row 1 (strictly non-crossing)
    { id: "skill_md>fetch_repo",      from: "skill_md",      to: "fetch_repo",   label: "Step 1: analyze",       detail: "`SKILL.md` runs `fetch_repo.py` first to analyze the repository and rank candidate files." },
    { id: "skill_md>build_walk",      from: "skill_md",      to: "build_walk",   label: "Step 3: build",         detail: "`SKILL.md` runs `build_walkthrough.mjs` to build the website or video." },
    { id: "plugin_json>build_walk",   from: "plugin_json",   to: "build_walk",   label: "exposes skill",         detail: "`plugin.json` registers the skill package." },

    // Row 1 -> Row 2 (strictly non-crossing)
    { id: "fetch_repo>data_schema",   from: "fetch_repo",    to: "data_schema",  label: "layer buckets",         detail: "`fetch_repo.py` groups candidate files into architectural layers." },
    { id: "build_walk>data_schema",   from: "build_walk",    to: "data_schema",  label: "checks geometry",       detail: "`build_walkthrough.mjs` validates layout and cue rules from `data-schema.md`." },
    { id: "build_walk>data_js",       from: "build_walk",    to: "data_js",      label: "validates & copies",    detail: "`build_walkthrough.mjs` validates `data.js` and copies it into the output directory." },
    { id: "render_sh>data_js",        from: "render_sh",     to: "data_js",      label: "passes --data",         detail: "`render_video.sh` forwards CLI flags to `render_video.mjs`." },

    // Row 2 -> Row 3 & Row 3 horizontal (strictly non-crossing)
    { id: "data_schema>gen_audio",    from: "data_schema",   to: "gen_audio",    label: "TTS text rules",        detail: "`data-schema.md` defines spoken filename rules for `generate_live_audio.mjs`." },
    { id: "data_schema>index_html",   from: "data_schema",   to: "index_html",   label: "layered layout",        detail: "`index.html` renders the layered architecture layout defined in `data-schema.md`." },
    { id: "data_js>index_html",       from: "data_js",       to: "index_html",   label: "WALKTHROUGH_DATA",      detail: "`index.html` loads `window.WALKTHROUGH_DATA` from `data.js`." },
    { id: "data_js>render_video",     from: "data_js",       to: "render_video", label: "step cues",             detail: "`render_video.mjs` steps through the walkthrough cues defined in `data.js`." },
    { id: "gen_audio>index_html",     from: "gen_audio",     to: "index_html",   label: "step-*.wav",            detail: "`generate_live_audio.mjs` provides the step audio files played in the viewer." },
    { id: "index_html>render_video",  from: "index_html",    to: "render_video", label: "video frames",          detail: "`render_video.mjs` renders each walkthrough frame from `index.html`." },

    // Row 3 -> Row 4 & Row 4 horizontal (strictly non-crossing)
    { id: "gen_audio>audio_cache",    from: "gen_audio",     to: "audio_cache",  label: "caches WAVs",           detail: "`generate_live_audio.mjs` caches WAV clips and writes `audio/manifest.json`." },
    { id: "index_html>audio_cache",   from: "index_html",    to: "audio_cache",  label: "streams audio",         detail: "`index.html` plays `audio/step-*.wav` and syncs node highlights to the narration." },
    { id: "index_html>mp4_out",       from: "index_html",    to: "mp4_out",      label: "full-width graph",      detail: "In video mode, `index.html` uses a full-width graph layout for the MP4 export." },
    { id: "render_video>mp4_out",     from: "render_video",  to: "mp4_out",      label: "encodes MP4",           detail: "`render_video.mjs` pipes rendered frames and step audio into `ffmpeg` to produce the MP4." },
    { id: "audio_cache>mp4_out",      from: "audio_cache",   to: "mp4_out",      label: "step timings & WAVs",   detail: "`manifest.json` durations and cached WAV files drive the video timeline and audio track." }
  ],
  walkthrough: [
    {
      step: 1,
      title: "Skill & Plugin Packaging: `SKILL.md` & `plugin.json`",
      focusNode: "skill_md",
      activeNodes: ["skill_md", "plugin_json", "build_walk", "index_html", "mp4_out"],
      activeEdges: ["skill_md>build_walk", "plugin_json>build_walk", "build_walk>data_js", "data_js>index_html", "index_html>mp4_out"],
      cues: [
        { at: 0.00, nodes: ["skill_md"], focus: "skill_md" },
        { at: 0.25, nodes: ["plugin_json"], focus: "plugin_json" },
        { at: 0.50, nodes: ["build_walk"], focus: "build_walk" },
        { at: 0.72, nodes: ["index_html", "mp4_out"], focus: "index_html" },
        { at: 0.88, nodes: ["skill_md", "plugin_json", "build_walk", "index_html", "mp4_out"], focus: "skill_md" }
      ],
      audio: "audio/step-1.wav",
      summary: "At the top layer, `SKILL.md` defines the agent workflow and `plugin.json` packages the skill, supporting two output modes via `build_walkthrough.mjs`: **Website** (`index.html`) and **Website + Video** (`walkthrough.mp4`).",
      narration: "At the top layer, SKILL.md follows the open Agent Skills specification, while plugin.json registers the skill in Antigravity. It supports two output modes through build walkthrough.mjs: an interactive website in index.html, or both the website and an animated video in walkthrough.mp4."
    },
    {
      step: 2,
      title: "Repository Analysis: `fetch_repo.py`",
      focusNode: "fetch_repo",
      activeNodes: ["skill_md", "fetch_repo", "data_schema"],
      activeEdges: ["skill_md>fetch_repo", "fetch_repo>data_schema"],
      cues: [
        { at: 0.00, node: "fetch_repo" },
        { at: 0.62, node: "data_schema" }
      ],
      audio: "audio/step-2.wav",
      summary: "`fetch_repo.py` inspects a local folder, public GitHub repo, private GitHub repo, or git diff (`--diff`), ranking key files into the architectural layers defined in `data-schema.md`.",
      narration: "Step one of the workflow runs fetch repo.py, which analyzes any local folder, public GitHub repo over HTTPS without needing the gh CLI, or private repo via gh api. It scores files by architectural centrality and buckets them into the five layers defined in data-schema.md."
    },
    {
      step: 3,
      title: "Graph Schema & Validation: `data-schema.md`, `data.js` & `build_walkthrough.mjs`",
      focusNode: "build_walk",
      activeNodes: ["build_walk", "data_schema", "data_js"],
      activeEdges: ["build_walk>data_schema", "build_walk>data_js"],
      cues: [
        { at: 0.00, node: "data_schema" },
        { at: 0.42, node: "data_js" },
        { at: 0.72, node: "build_walk" }
      ],
      audio: "audio/step-3.wav",
      summary: "Following `data-schema.md`, the agent curates key files into `data.js`. Then `build_walkthrough.mjs` validates that all nodes, edges, and narration cues are well-formed with zero overlaps.",
      narration: "Using data-schema.md as a blueprint, the agent curates twelve to eighteen key files into data.js. Then build walkthrough.mjs validates the five-layer geometry, ensuring every node sits to the right of the left section headers with zero overlaps and valid step cues."
    },
    {
      step: 4,
      title: "Interactive Website & Video Layout: `index.html`",
      focusNode: "index_html",
      activeNodes: ["data_js", "index_html", "render_video"],
      activeEdges: ["data_js>index_html", "index_html>render_video"],
      cues: [
        { at: 0.00, node: "index_html" },
        { at: 0.65, node: "render_video" }
      ],
      audio: "audio/step-4.wav",
      summary: "In website mode, `index.html` pairs the layered architecture graph with a file inspector sidebar. In video mode, it switches to a full-width graph layout so `render_video.mjs` can zoom smoothly across each step.",
      narration: "In interactive mode, index.html pairs the five-layer SVG graph with a right-hand code inspector, drag-to-pan, and scroll-to-zoom. When render video.mjs opens index.html with video equals 1, it hides the right sidebar so the graph fills the entire frame, showing the full five-layer overview on Step 1 before zooming into each cluster."
    },
    {
      step: 5,
      title: "Voice Narration: `generate_live_audio.mjs` & `audio/manifest.json`",
      focusNode: "gen_audio",
      activeNodes: ["gen_audio", "audio_cache", "index_html"],
      activeEdges: ["gen_audio>audio_cache", "gen_audio>index_html", "index_html>audio_cache"],
      cues: [
        { at: 0.00, node: "gen_audio" },
        { at: 0.52, node: "audio_cache" },
        { at: 0.80, node: "index_html" }
      ],
      audio: "audio/step-5.wav",
      summary: "`generate_live_audio.mjs` synthesizes spoken narration for each step with Gemini TTS and stores cached WAV files and timings in `audio/manifest.json`.",
      narration: "For voice narration, generate live audio.mjs resolves your Gemini API key from the environment, macOS Keychain, or dot env. It sanitizes filenames for natural speech, synthesizes 24 kilohertz Despina audio with gemini-3.1-flash-tts-preview, and caches each WAV by SHA-256 hash alongside audio/manifest.json."
    },
    {
      step: 6,
      title: "MP4 Video Export: `render_video.mjs` -> `walkthrough.mp4`",
      focusNode: "render_video",
      activeNodes: ["render_sh", "render_video", "audio_cache", "mp4_out"],
      activeEdges: ["index_html>render_video", "render_video>mp4_out", "audio_cache>mp4_out"],
      cues: [
        { at: 0.00, node: "render_video" },
        { at: 0.45, node: "audio_cache" },
        { at: 0.72, node: "mp4_out" }
      ],
      audio: "audio/step-6.wav",
      summary: "Finally, `render_video.mjs` combines the step audio from `audio/manifest.json` with animated graph frames from headless Chrome and encodes `walkthrough.mp4` via `ffmpeg`.",
      narration: "Finally, render video.mjs concatenates the step WAVs from manifest.json with short pauses, steps renderWalkthroughFrame deterministically in headless Chrome to animate camera transitions, light-blue cue highlights, and the bottom timeline bar, and pipes the frames into ffmpeg to output walkthrough.mp4."
    }
  ]
};
