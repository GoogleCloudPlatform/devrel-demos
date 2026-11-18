#!/usr/bin/env node
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

/**
 * Unit and integration tests for:
 *   - scripts/build_walkthrough.mjs (schema & geometry validator, flexible 3-6 layers, CLI arg parser, website build)
 *   - scripts/generate_live_audio.mjs (TTS filename sanitizer, SHA-256 content-hash key, WAV RIFF header builder)
 *   - scripts/render_video.mjs (CLI arg & speed bounds validation)
 *   - Skill & plugin manifests (SKILL.md, plugin.json, zero internal or disallowed tool mentions)
 */

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

import {
  computeSpokenOffset,
  detectPythonCmd,
  hasGeminiKey,
  openTarget,
  parseArgs as parseBuildArgs,
  resolveDataFile,
  resolveRepoRoot as resolveBuildRepoRoot,
  resolveTemplatePath,
  validateWalkthroughData,
} from "../skills/repo-walkthrough/scripts/build_walkthrough.mjs";
import {
  computeAcousticCueAt,
  computeContentHash,
  createWavBuffer,
  extractPcmSegments,
  resolveGeminiApiKey,
  resolveRepoRoot as resolveAudioRepoRoot,
  resolveSharedCacheDir,
  sanitizeForTts,
} from "../skills/repo-walkthrough/scripts/generate_live_audio.mjs";
import {
  formatFfmpegConcatEntry,
  getPlaywrightSearchRoots,
  launchChromium,
  loadPlaywright,
  parseArgs as parseVideoArgs,
  resolveRepoRoot as resolveVideoRepoRoot,
} from "../skills/repo-walkthrough/scripts/render_video.mjs";

const REPO_ROOT = path.resolve(import.meta.dirname, "..");
const SKILL_SCRIPTS_DIR = path.join(REPO_ROOT, "skills", "repo-walkthrough", "scripts");
const WEB_TEMPLATE_REL = fs.existsSync(path.join(REPO_ROOT, "web", "index.html"))
  ? "web/index.html"
  : "web/index.tmpl";

function loadDataJs(filePath) {
  const sandbox = { window: {} };
  vm.runInNewContext(fs.readFileSync(filePath, "utf8"), sandbox);
  return sandbox.window.WALKTHROUGH_DATA || sandbox.window.ADK_DATA;
}

function makeSampleData(layerCount = 5) {
  const allLayers = [
    { id: "l0", name: "Layer 0", color: "#4285F4", accent: "#8AB4F8", bg: "rgba(66,133,244,0.08)" },
    { id: "l1", name: "Layer 1", color: "#FBBC04", accent: "#FDD663", bg: "rgba(251,188,4,0.08)" },
    { id: "l2", name: "Layer 2", color: "#FF8A65", accent: "#FFAB91", bg: "rgba(255,138,101,0.08)" },
    { id: "l3", name: "Layer 3", color: "#34A853", accent: "#81C995", bg: "rgba(52,168,83,0.08)" },
    { id: "l4", name: "Layer 4", color: "#A142F4", accent: "#C58AF9", bg: "rgba(161,66,244,0.08)" },
    { id: "l5", name: "Layer 5", color: "#26C6DA", accent: "#80DEEA", bg: "rgba(38,198,218,0.08)" },
  ].slice(0, layerCount);

  const nodes = allLayers.map((l, idx) => ({
    id: `n${idx}`,
    label: `file_${idx}.py`,
    sub: `Module ${idx}`,
    path: `src/file_${idx}.py`,
    layer: l.id,
    lines: 100,
    x: 220,
    y: 26 + idx * 124,
    w: 215,
    h: 58,
    role: `Role for module ${idx}.`,
    snippet: `def fn_${idx}(): pass`,
  }));

  const edges = [];
  for (let i = 0; i < nodes.length - 1; i++) {
    edges.push({
      id: `n${i}>n${i + 1}`,
      from: `n${i}`,
      to: `n${i + 1}`,
      label: "calls",
      detail: `Module ${i} calls module ${i + 1}.`,
    });
  }

  return {
    repo: "test/sample",
    branch: "main",
    title: "test/sample",
    subtitle: "Sample Walkthrough",
    layers: allLayers,
    nodes,
    edges,
    walkthrough: [
      {
        step: 1,
        title: "Overview: `file_0.py`",
        focusNode: "n0",
        activeNodes: nodes.map((n) => n.id),
        activeEdges: edges.map((e) => e.id),
        cues: [
          { at: 0.0, nodes: ["n0"], focus: "n0" },
          { at: 0.5, nodes: ["n1"], focus: "n1" },
        ],
        audio: "audio/step-1.wav",
        summary: "Starts at `file_0.py`.",
        narration: "Starts at file 0.py.",
      },
    ],
  };
}

test("Production walkthrough datasets (ADK, self-walkthrough, cymbal-autos-multimodal, and diff-5984e02-to-head) pass schema & zero-overlap validation", () => {
  const adkData = loadDataJs(path.join(REPO_ROOT, "web", "data-adk.js"));
  const selfData = loadDataJs(
    path.join(REPO_ROOT, "examples", "self-walkthrough", "data.js")
  );
  const cymbalData = loadDataJs(
    path.join(REPO_ROOT, "examples", "cymbal-autos-multimodal", "data.js")
  );
  const diffData = loadDataJs(
    path.join(REPO_ROOT, "examples", "diff-5984e02-to-head", "data.js")
  );
  assert.doesNotThrow(() => validateWalkthroughData(adkData, "data-adk.js"));
  assert.doesNotThrow(() => validateWalkthroughData(selfData, "self-walkthrough/data.js"));
  assert.doesNotThrow(() => validateWalkthroughData(cymbalData, "cymbal-autos-multimodal/data.js"));
  assert.doesNotThrow(() => validateWalkthroughData(diffData, "diff-5984e02-to-head/data.js"));
  assert.equal(cymbalData.subpath, "data-analytics/cymbal-autos-multimodal");
  assert.equal(diffData.diffRange, "5984e02..1c3c31b");
});

test("Flexible layer counts (3, 4, 5, and 6 layers) validate cleanly", () => {
  for (const count of [3, 4, 5, 6]) {
    const sample = makeSampleData(count);
    assert.doesNotThrow(
      () => validateWalkthroughData(sample, `sample-${count}-layers.js`),
      `Expected ${count}-layer configuration to validate`
    );
  }
});

test("Validator rejects overlapping nodes, invalid edge endpoints, invalid step references, and out-of-sync cue phrases", () => {
  // 1. Overlapping nodes
  const overlapping = makeSampleData(5);
  overlapping.nodes[1].x = overlapping.nodes[0].x + 20;
  overlapping.nodes[1].y = overlapping.nodes[0].y + 10;
  assert.throws(
    () => validateWalkthroughData(overlapping, "overlapping.js"),
    /overlap on the SVG canvas/
  );

  // 2. Unknown edge endpoint
  const badEdge = makeSampleData(5);
  badEdge.edges.push({ id: "bad", from: "n0", to: "nonexistent", detail: "bad" });
  assert.throws(
    () => validateWalkthroughData(badEdge, "badEdge.js"),
    /unknown 'to' node 'nonexistent'/
  );

  // 3. Unknown focusNode / cue node
  const badCue = makeSampleData(5);
  badCue.walkthrough[0].cues.push({ at: 0.8, nodes: ["ghost_node"], focus: "ghost_node" });
  assert.throws(
    () => validateWalkthroughData(badCue, "badCue.js"),
    /unknown cue node 'ghost_node'/
  );

  // 4. Cue phrase drift > 0.08 or missing phrase in narration
  const driftedCue = makeSampleData(5);
  driftedCue.walkthrough[0].narration =
    "First, file 0.py ingests raw records and validates schemas. Next, file 1.py transforms those records into embeddings for downstream search.";
  const exactSecondOffset = computeSpokenOffset(
    driftedCue.walkthrough[0].narration,
    "Next, file 1.py"
  );
  assert.ok(exactSecondOffset > 0.35 && exactSecondOffset < 0.65);
  driftedCue.walkthrough[0].cues = [
    { at: 0.0, phrase: "First, file 0.py", nodes: ["n0"], focus: "n0" },
    { at: 0.85, phrase: "Next, file 1.py", nodes: ["n1"], focus: "n1" },
  ];
  assert.throws(
    () => validateWalkthroughData(driftedCue, "driftedCue.js"),
    /drifts from spoken offset/
  );
});

test("TTS filename sanitization and content-hash stability", () => {
  const raw =
    "In `__init__.py` and `_workflow.py`, `cli_tools_click.py` dispatches to `Runner`.";
  const sanitized = sanitizeForTts(raw);
  assert.equal(
    sanitized,
    "In init.py and workflow.py, cli tools click.py dispatches to Runner."
  );
  assert.ok(!sanitized.includes("_"), "Sanitized TTS text must not contain underscores");
  assert.ok(!sanitized.includes("`"), "Sanitized TTS text must not contain backticks");

  const h1 = computeContentHash("gemini-3.1-flash-tts-preview", "Despina", raw);
  const h2 = computeContentHash("gemini-3.1-flash-tts-preview", "Despina", sanitized);
  assert.equal(h1, h2, "Hash of raw and sanitized text should be identical");
  assert.equal(h1.length, 16);
});

test("createWavBuffer, extractPcmSegments, and computeAcousticCueAt align voiced segments accurately", () => {
  const pcm = Buffer.alloc(24000 * 2 * 2); // 2.0 seconds of 24kHz 16-bit mono
  for (let i = Math.floor(0.1 * 24000); i < Math.floor(0.6 * 24000); i++) {
    pcm.writeInt16LE(4000, i * 2);
  }
  for (let i = Math.floor(1.0 * 24000); i < Math.floor(1.8 * 24000); i++) {
    pcm.writeInt16LE(4000, i * 2);
  }
  const wav = createWavBuffer(pcm, 24000, 1, 16);
  assert.equal(wav.length, 44 + pcm.length);
  assert.equal(wav.toString("ascii", 0, 4), "RIFF");
  assert.equal(wav.toString("ascii", 8, 12), "WAVE");
  assert.equal(wav.toString("ascii", 12, 16), "fmt ");
  assert.equal(wav.readUInt32LE(24), 24000);
  assert.equal(wav.readUInt16LE(22), 1);
  assert.equal(wav.readUInt16LE(34), 16);
  assert.equal(wav.toString("ascii", 36, 40), "data");
  assert.equal(wav.readUInt32LE(40), pcm.length);

  const { segments, totalDur } = extractPcmSegments(wav, 10);
  assert.equal(totalDur, 2.0);
  assert.equal(segments.length, 2);
  assert.equal(segments[0].startSec, 0.1);
  assert.equal(segments[1].startSec, 1.0);

  const aligned = [
    { seg: 0, startSec: 18.24, endSec: 20.8, text: "03 vision extraction.sql inspects photos" },
    { seg: 1, startSec: 26.76, endSec: 29.52, text: "while 04 predictive pricing.sql combines traits" },
  ];
  assert.equal(computeAcousticCueAt(aligned, 60.76, "03 vision extraction.sql", 1), 0.3);
  assert.equal(computeAcousticCueAt(aligned, 60.76, "04 predictive pricing.sql", 2), 0.45);
});

test("CLI argument parsers handle --mode, --speed, and reject out-of-range speeds", () => {
  const bOpts = parseBuildArgs([
    "--data",
    "examples/self-walkthrough/data.js",
    "--mode",
    "video",
    "--speed",
    "1.2",
    "--no-tts",
  ]);
  assert.equal(bOpts.mode, "video");
  assert.equal(bOpts.speed, "1.2");
  assert.equal(bOpts.noTts, true);

  const vOpts = parseVideoArgs(["--fps", "12", "--speed", "1.1"]);
  assert.equal(vOpts.fps, 12);
  assert.equal(vOpts.speed, 1.1);

  assert.throws(() => parseVideoArgs(["--speed", "0.2"]), /--speed must be between 0.5 and 2.0/);
  assert.throws(() => parseVideoArgs(["--speed", "2.5"]), /--speed must be between 0.5 and 2.0/);
});

test("build_walkthrough.mjs --mode website --no-tts generates standalone site bundle", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "rw-test-"));
  try {
    const sampleDataPath = path.join(tmpDir, "data.js");
    fs.writeFileSync(
      sampleDataPath,
      `window.WALKTHROUGH_DATA = ${JSON.stringify(makeSampleData(4), null, 2)};\n`,
      "utf8"
    );
    execFileSync(
      process.execPath,
      [
        path.join(SKILL_SCRIPTS_DIR, "build_walkthrough.mjs"),
        "--data",
        sampleDataPath,
        "--out-dir",
        tmpDir,
        "--mode",
        "website",
        "--no-tts",
      ],
      { stdio: "pipe" }
    );
    const builtHtml = fs.readFileSync(path.join(tmpDir, "index.html"), "utf8");
    assert.ok(fs.existsSync(path.join(tmpDir, "index.html")));
    assert.ok(!builtHtml.includes('src="data-adk.js"'), "Standalone build must strip data-adk.js");
    assert.ok(builtHtml.includes('src="data.js"'), "Standalone build must load data.js");
    assert.match(
      builtHtml,
      /<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="data:image\/svg\+xml,[^"]+">/,
      "Standalone build must preserve inline SVG favicon in generated index.html"
    );
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test("Skill manifest is valid and project layout is clean", () => {
  const skillMd = fs.readFileSync(
    path.join(REPO_ROOT, "skills", "repo-walkthrough", "SKILL.md"),
    "utf8"
  );
  assert.match(skillMd, /^---\r?\nname:\s*repo-walkthrough\r?\ndescription:/m);
  assert.ok(!/^license:/m.test(skillMd), "SKILL.md frontmatter should not include license field");
  assert.match(skillMd, /^\s*author:\s*Google\s*$/m, "SKILL.md metadata.author should be Google");
  assert.ok(
    !skillMd.includes("~/projects/"),
    "SKILL.md must not hardcode ~/projects/ paths"
  );
  assert.match(
    skillMd,
    /node\s+<plugin-root>\/skills\/repo-walkthrough\/scripts\/build_walkthrough\.mjs\s+--check-prereqs/
  );
  assert.ok(
    skillMd.includes(
      "python3 <plugin-root>/skills/repo-walkthrough/scripts/fetch_repo.py"
    )
  );
  assert.ok(
    !/^\s*(?:node|python3?)\s+scripts\//m.test(skillMd),
    "SKILL.md must never invoke bare scripts/..."
  );
  assert.ok(
    skillMd.includes("python") && skillMd.includes("$TEMP"),
    "SKILL.md must mention python and $TEMP for Windows portability"
  );

  // Verify skills/repo-walkthrough/scripts is a real directory (not a symlink that turns into a 13-byte stub on Windows git clone)
  const skillScriptsDir = path.join(REPO_ROOT, "skills", "repo-walkthrough", "scripts");
  assert.equal(
    fs.lstatSync(skillScriptsDir).isSymbolicLink(),
    false,
    "skills/repo-walkthrough/scripts must be a real directory for Windows core.symlinks=false compatibility"
  );
  assert.equal(fs.statSync(skillScriptsDir).isDirectory(), true);
  for (const requiredScript of [
    "build_walkthrough.mjs",
    "fetch_repo.py",
    "generate_live_audio.mjs",
    "render_video.mjs",
    "render_video.sh",
  ]) {
    assert.ok(
      fs.existsSync(path.join(skillScriptsDir, requiredScript)),
      `Missing script in skill bundle: ${requiredScript}`
    );
  }
  const rootScriptsDir = path.join(REPO_ROOT, "scripts");
  if (fs.existsSync(rootScriptsDir)) {
    for (const scriptFile of fs.readdirSync(rootScriptsDir)) {
      const srcPath = path.join(rootScriptsDir, scriptFile);
      if (!fs.statSync(srcPath).isFile()) continue;
      const srcText = fs.readFileSync(srcPath, "utf8").replace(/\r\n/g, "\n");
      const dstPath = path.join(skillScriptsDir, scriptFile);
      assert.ok(fs.existsSync(dstPath), `Missing mirrored script in skill bundle: ${scriptFile}`);
      const dstText = fs.readFileSync(dstPath, "utf8").replace(/\r\n/g, "\n");
      assert.equal(dstText, srcText, `Mirrored script ${scriptFile} drifted from scripts/${scriptFile}`);
    }
  }

  const pluginJsonPath = path.join(REPO_ROOT, "plugin.json");
  assert.ok(fs.existsSync(pluginJsonPath), "plugin.json must exist at plugin root");
  const pluginManifest = JSON.parse(fs.readFileSync(pluginJsonPath, "utf8"));
  assert.equal(pluginManifest.name, "repo-walkthrough");
  assert.equal(pluginManifest.displayName, "Repo Walkthrough");
  assert.ok(!/plugin|antigravity|gemini/i.test(pluginManifest.displayName));
  assert.equal(pluginManifest.version, "1.0.0");
  assert.ok(
    pluginManifest.description.length >= 120 && pluginManifest.description.length <= 160,
    `Expected description length 120..160, got ${pluginManifest.description.length}`
  );
  assert.equal(pluginManifest.logo, "assets/logo.svg");
  assert.ok(fs.existsSync(path.join(REPO_ROOT, pluginManifest.logo)), "assets/logo.svg must exist");
  assert.ok(!("license" in pluginManifest), "plugin.json should not include license field");
  assert.match(pluginManifest.homepage || "", /^https:\/\//);
  assert.match(pluginManifest.repository || "", /^https:\/\//);
  assert.equal(pluginManifest.suggestedPrompts?.length, 3);
  assert.ok(Array.isArray(pluginManifest.keywords) && pluginManifest.keywords.length >= 4);

  assert.ok(!fs.existsSync(path.join(REPO_ROOT, "poc")), "poc directory must not exist in shareable repo-walkthrough");
  assert.ok(!fs.existsSync(path.join(REPO_ROOT, ".claude-plugin")), ".claude-plugin directory must not exist");

  const localTermsPath = path.join(REPO_ROOT, "tests", "local_disallowed_terms.json");
  if (fs.existsSync(localTermsPath)) {
    const disallowedTerms = JSON.parse(fs.readFileSync(localTermsPath, "utf8"));
    const forbidden = new RegExp(disallowedTerms.join("|"), "i");
    const checkedRels = [
      ".gitignore",
      "README.md",
      "TESTING.md",
      "plugin.json",
      "assets/logo.svg",
      "skills/repo-walkthrough/SKILL.md",
      "skills/repo-walkthrough/references/data-schema.md",
      "skills/repo-walkthrough/scripts/build_walkthrough.mjs",
      "skills/repo-walkthrough/scripts/fetch_repo.py",
      "skills/repo-walkthrough/scripts/generate_live_audio.mjs",
      "skills/repo-walkthrough/scripts/render_video.mjs",
      "skills/repo-walkthrough/scripts/render_video.sh",
      WEB_TEMPLATE_REL,
      "web/data-adk.js",
      "examples/self-walkthrough/data.js",
      "examples/cymbal-autos-multimodal/data.js",
      "examples/diff-5984e02-to-head/data.js",
      "tests/test_fetch_repo.py",
      "tests/test_pipeline.mjs",
      "tests/test_ui_e2e.mjs",
    ];
    if (fs.existsSync(path.join(REPO_ROOT, "scripts"))) {
      checkedRels.push(
        "scripts/build_walkthrough.mjs",
        "scripts/fetch_repo.py",
        "scripts/generate_live_audio.mjs",
        "scripts/render_video.mjs",
        "scripts/render_video.sh"
      );
    }
    for (const rel of checkedRels) {
      const content = fs.readFileSync(path.join(REPO_ROOT, rel), "utf8");
      assert.ok(!forbidden.test(content), `Forbidden reference found in ${rel}`);
    }
  }
});

test("resolveRepoRoot handles both standard scripts/ and dereferenced skills/repo-walkthrough/scripts/", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-deref-"));
  try {
    fs.mkdirSync(path.join(tmpRoot, "web"), { recursive: true });
    fs.writeFileSync(path.join(tmpRoot, "web", "index.html"), "<html></html>", "utf8");
    const directScripts = path.join(tmpRoot, "scripts");
    const derefScripts = path.join(tmpRoot, "skills", "repo-walkthrough", "scripts");
    fs.mkdirSync(directScripts, { recursive: true });
    fs.mkdirSync(derefScripts, { recursive: true });

    for (const fn of [resolveBuildRepoRoot, resolveAudioRepoRoot, resolveVideoRepoRoot]) {
      assert.equal(fn(directScripts), tmpRoot);
      assert.equal(fn(derefScripts), tmpRoot);
    }
    assert.equal(resolveTemplatePath(tmpRoot), path.join(tmpRoot, "web", "index.html"));

    // Verify web/index.tmpl (plugin template) takes precedence when index.html is absent
    fs.unlinkSync(path.join(tmpRoot, "web", "index.html"));
    fs.writeFileSync(path.join(tmpRoot, "web", "index.tmpl"), "<html>tmpl</html>", "utf8");
    for (const fn of [resolveBuildRepoRoot, resolveAudioRepoRoot, resolveVideoRepoRoot]) {
      assert.equal(fn(directScripts), tmpRoot);
      assert.equal(fn(derefScripts), tmpRoot);
    }
    assert.equal(resolveTemplatePath(tmpRoot), path.join(tmpRoot, "web", "index.tmpl"));

    // Verify resolveDataFile never looks for unpackaged web/data-adk.js when absent, and resolves outDir/data.js
    assert.equal(
      resolveDataFile({ dataFile: null, outDir: path.join(tmpRoot, "no-out") }, tmpRoot, tmpRoot),
      null
    );
    const outDataDir = path.join(tmpRoot, "out-with-data");
    fs.mkdirSync(outDataDir, { recursive: true });
    const outDataJs = path.join(outDataDir, "data.js");
    fs.writeFileSync(outDataJs, "window.WALKTHROUGH_DATA = {};", "utf8");
    assert.equal(
      resolveDataFile({ dataFile: null, outDir: outDataDir }, tmpRoot, tmpRoot),
      outDataJs
    );

    // Invoking via skills/repo-walkthrough/scripts/build_walkthrough.mjs (symlink on POSIX) must execute main()
    const symlinkOrDerefBuild = path.join(
      REPO_ROOT,
      "skills",
      "repo-walkthrough",
      "scripts",
      "build_walkthrough.mjs"
    );
    if (fs.existsSync(symlinkOrDerefBuild)) {
      const prereqOut = execFileSync(process.execPath, [symlinkOrDerefBuild, "--check-prereqs"], {
        encoding: "utf8",
      });
      assert.match(prereqOut, /Prerequisites/);
    }
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test("resolveSharedCacheDir uses PLUGIN_DATA or ~/.cache and falls back to localCacheDir when read-only", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-cache-"));
  try {
    const localCache = path.join(tmpRoot, "local-cache");
    fs.mkdirSync(localCache, { recursive: true });

    // 1. PLUGIN_DATA set
    const pluginDataDir = path.join(tmpRoot, "plugin-data");
    const resolvedPluginCache = resolveSharedCacheDir(localCache, { PLUGIN_DATA: pluginDataDir }, tmpRoot);
    assert.equal(resolvedPluginCache, path.join(pluginDataDir, "audio-cache"));
    assert.ok(fs.existsSync(resolvedPluginCache));

    // 2. Default ~/.cache/repo-walkthrough/audio when PLUGIN_DATA is unset
    const fakeHome = path.join(tmpRoot, "home");
    const resolvedHomeCache = resolveSharedCacheDir(localCache, {}, fakeHome);
    assert.equal(resolvedHomeCache, path.join(fakeHome, ".cache", "repo-walkthrough", "audio"));
    assert.ok(fs.existsSync(resolvedHomeCache));

    // 3. Read-only parent directory falls back cleanly to localCacheDir without throwing
    const roDir = path.join(tmpRoot, "ro-parent");
    fs.mkdirSync(roDir, { recursive: true });
    if (process.platform === "win32") {
      execFileSync("icacls", [roDir, "/deny", "*S-1-1-0:(OI)(CI)(WD,AD,WEA,WA)"]);
    } else {
      fs.chmodSync(roDir, 0o555);
    }
    try {
      const fallbackCache = resolveSharedCacheDir(
        localCache,
        { PLUGIN_DATA: path.join(roDir, "blocked-plugin-data") },
        roDir
      );
      assert.equal(fallbackCache, localCache);
    } finally {
      if (process.platform === "win32") {
        try {
          execFileSync("icacls", [roDir, "/reset"]);
        } catch {}
      } else {
        fs.chmodSync(roDir, 0o755);
      }
    }
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test("Read-only installed plugin directory (chmod -R a-w) builds website and runs cached audio without failing", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-ro-plugin-"));
  const roPluginDir = path.join(tmpRoot, "plugin");
  const outDir = path.join(tmpRoot, "out");
  const pluginDataDir = path.join(tmpRoot, "plugin-data");
  try {
    // Simulate agy plugin install from packaged plugin bundle (web/index.tmpl + dereferenced skills/repo-walkthrough/scripts)
    fs.mkdirSync(path.join(roPluginDir, "web"), { recursive: true });
    fs.copyFileSync(
      resolveTemplatePath(REPO_ROOT),
      path.join(roPluginDir, "web", "index.tmpl")
    );
    const derefScripts = path.join(roPluginDir, "skills", "repo-walkthrough", "scripts");
    fs.mkdirSync(derefScripts, { recursive: true });
    for (const scriptName of ["build_walkthrough.mjs", "generate_live_audio.mjs", "render_video.mjs"]) {
      fs.copyFileSync(
        path.join(SKILL_SCRIPTS_DIR, scriptName),
        path.join(derefScripts, scriptName)
      );
    }

    fs.mkdirSync(outDir, { recursive: true });
    const sample = makeSampleData(4);
    const dataFile = path.join(outDir, "data.js");
    fs.writeFileSync(
      dataFile,
      `window.WALKTHROUGH_DATA = ${JSON.stringify(sample, null, 2)};\n`,
      "utf8"
    );

    // Pre-seed shared cache in PLUGIN_DATA so generate_live_audio.mjs runs offline with read-only plugin dir
    const sharedAudioCache = path.join(pluginDataDir, "audio-cache");
    fs.mkdirSync(sharedAudioCache, { recursive: true });
    const stepHash = computeContentHash(
      "gemini-3.1-flash-tts-preview",
      "Despina",
      sample.walkthrough[0].narration
    );
    const dummyWav = createWavBuffer(Buffer.alloc(24000 * 2), 24000, 1, 16);
    fs.writeFileSync(path.join(sharedAudioCache, `${stepHash}.wav`), dummyWav);

    // Lock down the entire plugin install directory as read-only
    if (process.platform === "win32") {
      execFileSync("attrib", ["+R", path.join(roPluginDir, "*"), "/S", "/D"]);
      execFileSync("icacls", [roPluginDir, "/deny", "*S-1-1-0:(OI)(CI)(WD,AD,WEA,WA)"]);
    } else {
      execFileSync("chmod", ["-R", "a-w", roPluginDir]);
    }

    // 1. Run dereferenced skills/repo-walkthrough/scripts/build_walkthrough.mjs
    execFileSync(
      process.execPath,
      [
        path.join(derefScripts, "build_walkthrough.mjs"),
        "--data",
        dataFile,
        "--out-dir",
        outDir,
        "--mode",
        "website",
        "--no-tts",
      ],
      { env: { ...process.env, PLUGIN_DATA: pluginDataDir }, stdio: "pipe" }
    );
    assert.ok(fs.existsSync(path.join(outDir, "index.html")));

    // 2. Run dereferenced skills/repo-walkthrough/scripts/generate_live_audio.mjs against read-only plugin root
    execFileSync(
      process.execPath,
      [
        path.join(derefScripts, "generate_live_audio.mjs"),
        "--data",
        dataFile,
        "--out-dir",
        path.join(outDir, "audio"),
      ],
      {
        env: { ...process.env, PLUGIN_DATA: pluginDataDir, GEMINI_API_KEY: "" },
        stdio: "pipe",
      }
    );
    assert.ok(fs.existsSync(path.join(outDir, "audio", "step-1.wav")));
    assert.ok(fs.existsSync(path.join(outDir, "audio", "manifest.json")));
  } finally {
    try {
      if (process.platform === "win32") {
        execFileSync("icacls", [roPluginDir, "/reset", "/T"]);
        execFileSync("attrib", ["-R", path.join(roPluginDir, "*"), "/S", "/D"]);
      } else {
        execFileSync("chmod", ["-R", "u+w", roPluginDir]);
      }
    } catch {}
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test("Cross-platform GEMINI_API_KEY resolution (env -> .env files -> OS credential store across macOS/Linux/Windows) and OS-aware errors", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-apikey-"));
  try {
    const cwdDir = path.join(tmpRoot, "cwd");
    const pluginDataDir = path.join(tmpRoot, "plugin-data");
    const appDataDir = path.join(tmpRoot, "appdata");
    const fakeHome = path.join(tmpRoot, "home");
    const fakeRepo = path.join(tmpRoot, "repo");
    fs.mkdirSync(cwdDir, { recursive: true });
    fs.mkdirSync(pluginDataDir, { recursive: true });
    fs.mkdirSync(path.join(appDataDir, "repo-walkthrough"), { recursive: true });
    fs.mkdirSync(path.join(fakeHome, ".config", "repo-walkthrough"), { recursive: true });
    fs.mkdirSync(path.join(fakeHome, ".gemini"), { recursive: true });
    fs.mkdirSync(fakeRepo, { recursive: true });
    const noStore = () => "";

    // 1. Uses GEMINI_API_KEY and ignores GOOGLE_API_KEY
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: { GEMINI_API_KEY: "gem-key-1", GOOGLE_API_KEY: "goog-key-2" },
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "gem-key-1"
    );
    assert.throws(
      () =>
        resolveGeminiApiKey(fakeRepo, {
          env: { GOOGLE_API_KEY: "goog-key-only" },
          platform: "linux",
          cwd: cwdDir,
          homedir: fakeHome,
          runner: noStore,
        }),
      /GEMINI_API_KEY/
    );

    // 2. Fallback chain across .env and key files in reverse priority order
    fs.writeFileSync(path.join(fakeRepo, ".env"), 'GEMINI_API_KEY="from-repo-env"\n', "utf8");
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: {},
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-repo-env"
    );

    fs.writeFileSync(
      path.join(fakeHome, ".gemini", "gemini_api_key"),
      "from-home-gemini-keyfile\n",
      "utf8"
    );
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: {},
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-home-gemini-keyfile"
    );

    fs.writeFileSync(
      path.join(fakeHome, ".gemini", ".env"),
      "GEMINI_API_KEY=from-home-gemini-env\n",
      "utf8"
    );
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: {},
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-home-gemini-env"
    );

    fs.writeFileSync(
      path.join(fakeHome, ".config", "repo-walkthrough", "gemini_api_key"),
      "from-config-rw-keyfile\n",
      "utf8"
    );
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: {},
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-config-rw-keyfile"
    );

    fs.writeFileSync(
      path.join(fakeHome, ".config", "repo-walkthrough", ".env"),
      "GEMINI_API_KEY=from-config-rw-env\n",
      "utf8"
    );
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: {},
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-config-rw-env"
    );

    fs.writeFileSync(
      path.join(appDataDir, "repo-walkthrough", "gemini_api_key"),
      "from-appdata-rw-keyfile\n",
      "utf8"
    );
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: { APPDATA: appDataDir },
        platform: "win32",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-appdata-rw-keyfile"
    );

    fs.writeFileSync(
      path.join(appDataDir, "repo-walkthrough", ".env"),
      "GEMINI_API_KEY=from-appdata-rw-env\n",
      "utf8"
    );
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: { APPDATA: appDataDir },
        platform: "win32",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-appdata-rw-env"
    );

    fs.writeFileSync(
      path.join(pluginDataDir, ".env"),
      "GEMINI_API_KEY=from-plugin-data-env\n",
      "utf8"
    );
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: { PLUGIN_DATA: pluginDataDir, APPDATA: appDataDir },
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-plugin-data-env"
    );

    fs.writeFileSync(path.join(cwdDir, ".env"), "GEMINI_API_KEY=from-cwd-env\n", "utf8");
    assert.equal(
      resolveGeminiApiKey(fakeRepo, {
        env: { PLUGIN_DATA: pluginDataDir },
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      "from-cwd-env"
    );
    assert.equal(
      hasGeminiKey(fakeRepo, {
        env: {},
        platform: "linux",
        cwd: cwdDir,
        homedir: fakeHome,
        runner: noStore,
      }),
      true
    );

    // 3. Native OS credential store lookup across macOS, Linux, and Windows
    const emptyDir = path.join(tmpRoot, "empty");
    fs.mkdirSync(emptyDir, { recursive: true });
    assert.equal(
      resolveGeminiApiKey(emptyDir, {
        env: {},
        platform: "darwin",
        cwd: emptyDir,
        homedir: emptyDir,
        runner: (cmd, args) =>
          cmd === "security" && args.includes("gemini-api-key") ? "from-macos-keychain\n" : "",
      }),
      "from-macos-keychain"
    );
    assert.equal(
      resolveGeminiApiKey(emptyDir, {
        env: {},
        platform: "linux",
        cwd: emptyDir,
        homedir: emptyDir,
        runner: (cmd, args) =>
          cmd === "secret-tool" && args.includes("gemini-api-key") ? "from-linux-secret-tool\n" : "",
      }),
      "from-linux-secret-tool"
    );
    assert.equal(
      resolveGeminiApiKey(emptyDir, {
        env: {},
        platform: "win32",
        cwd: emptyDir,
        homedir: emptyDir,
        runner: (cmd, args) =>
          cmd === "powershell.exe" && args.some((a) => a.includes("gemini-api-key"))
            ? "from-windows-cred\r\n"
            : "",
      }),
      "from-windows-cred"
    );

    // 4. OS-aware error instructions when no key exists
    assert.throws(
      () =>
        resolveGeminiApiKey(emptyDir, {
          env: {},
          platform: "win32",
          cwd: emptyDir,
          homedir: emptyDir,
          runner: noStore,
        }),
      /\$env:GEMINI_API_KEY/
    );
    assert.throws(
      () =>
        resolveGeminiApiKey(emptyDir, {
          env: {},
          platform: "linux",
          cwd: emptyDir,
          homedir: emptyDir,
          runner: noStore,
        }),
      /export GEMINI_API_KEY/
    );
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test("GEMINI_API_KEY lookup never probes unrelated config folders or non-standard keychain services", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-apikey-strict-"));
  try {
    const cwdDir = path.join(tmpRoot, "cwd");
    const appDataDir = path.join(tmpRoot, "appdata");
    const fakeHome = path.join(tmpRoot, "home");
    const fakeRepo = path.join(tmpRoot, "repo");
    fs.mkdirSync(cwdDir, { recursive: true });
    fs.mkdirSync(fakeRepo, { recursive: true });

    // Unrelated sibling tool folders under ~/.config and %APPDATA% must never be read
    const otherConfigDir = path.join(fakeHome, ".config", "unrelated-private-tool");
    const otherAppDataDir = path.join(appDataDir, "unrelated-private-tool");
    fs.mkdirSync(otherConfigDir, { recursive: true });
    fs.mkdirSync(otherAppDataDir, { recursive: true });
    fs.writeFileSync(path.join(otherConfigDir, ".env"), "GEMINI_API_KEY=leaked-config\n", "utf8");
    fs.writeFileSync(path.join(otherConfigDir, "gemini_api_key"), "leaked-keyfile\n", "utf8");
    fs.writeFileSync(path.join(otherAppDataDir, ".env"), "GEMINI_API_KEY=leaked-appdata\n", "utf8");
    fs.writeFileSync(path.join(otherAppDataDir, "gemini_api_key"), "leaked-appdata-key\n", "utf8");

    // On every OS, credential store runner must query strictly "gemini-api-key" once and nothing else
    for (const platform of ["darwin", "linux", "win32"]) {
      const calls = [];
      assert.throws(
        () =>
          resolveGeminiApiKey(fakeRepo, {
            env: { APPDATA: appDataDir },
            platform,
            cwd: cwdDir,
            homedir: fakeHome,
            runner: (cmd, args) => {
              calls.push({ cmd, args });
              return "";
            },
          }),
        /GEMINI_API_KEY/
      );
      assert.equal(calls.length, 1, `Expected strictly 1 credential-store lookup on ${platform}, got ${calls.length}`);
      assert.ok(
        calls[0].args.some((a) => a.includes("gemini-api-key")),
        `Expected credential-store lookup on ${platform} to target gemini-api-key`
      );
    }
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test("Cross-platform helpers: openTarget, detectPythonCmd, formatFfmpegConcatEntry, getPlaywrightSearchRoots, and launchChromium", async () => {
  // 1. openTarget on darwin, win32, linux, and headless Linux ENOENT fallback
  const calls = [];
  const mockRunner = (cmd, args) => {
    calls.push({ cmd, args });
  };
  assert.equal(openTarget("/path/to/index.html", "darwin", mockRunner), true);
  assert.deepEqual(calls.pop(), { cmd: "open", args: ["/path/to/index.html"] });

  assert.equal(openTarget("C:\\out\\index.html", "win32", mockRunner), true);
  assert.deepEqual(calls.pop(), { cmd: "cmd", args: ["/c", "start", "", "C:\\out\\index.html"] });

  assert.equal(openTarget("/path/to/index.html", "linux", mockRunner), true);
  assert.deepEqual(calls.pop(), { cmd: "xdg-open", args: ["/path/to/index.html"] });

  // Headless Linux where xdg-open throws ENOENT must not crash
  assert.doesNotThrow(() => {
    const ok = openTarget("/path/to/index.html", "linux", () => {
      const err = new Error("spawn xdg-open ENOENT");
      err.code = "ENOENT";
      throw err;
    });
    assert.equal(ok, false);
  });

  // 2. detectPythonCmd fallback order: python3 -> python -> py -3 on win32
  assert.deepEqual(
    detectPythonCmd("win32", (cmd, args) => cmd === "py" && args[0] === "-3"),
    { cmd: "py", args: ["-3"] }
  );
  assert.deepEqual(
    detectPythonCmd("win32", (cmd) => cmd === "python"),
    { cmd: "python", args: [] }
  );
  assert.deepEqual(
    detectPythonCmd("linux", (cmd) => cmd === "python3"),
    { cmd: "python3", args: [] }
  );

  // 3. FFmpeg concat path escaping for Windows backslashes and single quotes
  assert.equal(
    formatFfmpegConcatEntry("C:\\Users\\dev\\out\\audio\\step-1.wav"),
    "file 'C:/Users/dev/out/audio/step-1.wav'"
  );
  assert.equal(
    formatFfmpegConcatEntry("C:\\Users\\O'Connor\\audio\\step-1.wav"),
    "file 'C:/Users/O'\\''Connor/audio/step-1.wav'"
  );

  // 4. Playwright search roots on Windows include LOCALAPPDATA and APPDATA _npx
  const roots = getPlaywrightSearchRoots({
    platform: "win32",
    homedir: "C:\\Users\\dev",
    env: {
      LOCALAPPDATA: "C:\\Users\\dev\\AppData\\Local",
      APPDATA: "C:\\Users\\dev\\AppData\\Roaming",
    },
  });
  assert.equal(roots.npmCmd, "npm.cmd");
  assert.ok(roots.npxBases.some((p) => p.includes("Local") && p.includes("_npx")));
  assert.ok(roots.npxBases.some((p) => p.includes("Roaming") && p.includes("_npx")));

  // 5. launchChromium falls back to channel: "msedge" on Windows when chrome and bundled chromium fail
  const launchAttempts = [];
  const fakeChromium = {
    async launch(opts) {
      launchAttempts.push(opts);
      if (opts.channel === "msedge") return { browser: "msedge" };
      throw new Error("Chrome not installed");
    },
  };
  const launched = await launchChromium(fakeChromium, "win32");
  assert.deepEqual(launched, { browser: "msedge" });
  assert.ok(launchAttempts.some((a) => a.channel === "msedge"));

  // 6. loadPlaywright resolves path.join(process.cwd(), "node_modules", "playwright")
  const tmpCwd = fs.mkdtempSync(path.join(os.tmpdir(), "rw-pw-cwd-"));
  try {
    const fakePwDir = path.join(tmpCwd, "node_modules", "playwright");
    fs.mkdirSync(fakePwDir, { recursive: true });
    fs.writeFileSync(
      path.join(fakePwDir, "package.json"),
      JSON.stringify({ name: "playwright", main: "index.js" }),
      "utf8"
    );
    fs.writeFileSync(
      path.join(fakePwDir, "index.js"),
      "module.exports = { source: 'cwd-playwright' };\n",
      "utf8"
    );
    const origCwd = process.cwd();
    process.chdir(tmpCwd);
    try {
      const resolvedPw = loadPlaywright();
      assert.equal(resolvedPw.source, "cwd-playwright");
    } finally {
      process.chdir(origCwd);
    }
  } finally {
    fs.rmSync(tmpCwd, { recursive: true, force: true });
  }
});

test("web template embeds assets/logo.svg as a 1-line inline SVG favicon in <head>", () => {
  const indexHtml = fs.readFileSync(resolveTemplatePath(REPO_ROOT), "utf8");
  const headMatch = indexHtml.match(/<head>([\s\S]*?)<\/head>/i);
  assert.ok(headMatch, "web/index.html must contain a <head> section");
  const iconMatch = headMatch[1].match(
    /<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="(data:image\/svg\+xml,[^"]+)">/
  );
  assert.ok(iconMatch, "web/index.html <head> must contain an inline SVG favicon <link>");
  assert.ok(!iconMatch[0].includes("\n"), "Inline SVG favicon <link> tag must be single-line");

  const decodedSvg = decodeURIComponent(iconMatch[1].slice("data:image/svg+xml,".length));
  assert.match(decodedSvg, /^<svg\b[\s\S]*<\/svg>$/);
  assert.ok(decodedSvg.includes("viewBox='0 0 128 128'") || decodedSvg.includes('viewBox="0 0 128 128"'));
  const logoSvg = fs.readFileSync(path.join(REPO_ROOT, "assets", "logo.svg"), "utf8").trim();
  assert.equal(decodedSvg.replace(/'/g, '"'), logoSvg, "Inline SVG favicon must match assets/logo.svg");
  assert.ok(decodedSvg.includes("bgGrad") && decodedSvg.includes("playGrad") && decodedSvg.includes("feDropShadow"));
  assert.ok(decodedSvg.includes("#eb5850") && decodedSvg.includes("#56d364"));
});
