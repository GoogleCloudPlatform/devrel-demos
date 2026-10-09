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
  parseArgs as parseBuildArgs,
  validateWalkthroughData,
} from "../scripts/build_walkthrough.mjs";
import {
  computeAcousticCueAt,
  computeContentHash,
  createWavBuffer,
  extractPcmSegments,
  sanitizeForTts,
} from "../scripts/generate_live_audio.mjs";
import { parseArgs as parseVideoArgs } from "../scripts/render_video.mjs";

const REPO_ROOT = path.resolve(import.meta.dirname, "..");

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
        path.join(REPO_ROOT, "scripts", "build_walkthrough.mjs"),
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
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test("Skill manifest is valid and project layout is clean", () => {
  const skillMd = fs.readFileSync(
    path.join(REPO_ROOT, "skills", "repo-walkthrough", "SKILL.md"),
    "utf8"
  );
  assert.match(skillMd, /^---\nname:\s*repo-walkthrough\ndescription:/m);
  assert.ok(!fs.existsSync(path.join(REPO_ROOT, "poc")), "poc directory must not exist in shareable repo-walkthrough");
  assert.ok(!fs.existsSync(path.join(REPO_ROOT, ".claude-plugin")), ".claude-plugin directory must not exist");

  const localTermsPath = path.join(REPO_ROOT, "tests", "local_disallowed_terms.json");
  if (fs.existsSync(localTermsPath)) {
    const disallowedTerms = JSON.parse(fs.readFileSync(localTermsPath, "utf8"));
    const forbidden = new RegExp(disallowedTerms.join("|"), "i");
    for (const rel of [
      ".gitignore",
      "README.md",
      "TESTING.md",
      "skills/repo-walkthrough/SKILL.md",
      "skills/repo-walkthrough/references/data-schema.md",
      "web/index.html",
      "web/data-adk.js",
      "examples/self-walkthrough/data.js",
      "examples/cymbal-autos-multimodal/data.js",
      "examples/diff-5984e02-to-head/data.js",
      "tests/test_fetch_repo.py",
      "tests/test_pipeline.mjs",
      "tests/test_ui_e2e.mjs",
    ]) {
      const content = fs.readFileSync(path.join(REPO_ROOT, rel), "utf8");
      assert.ok(!forbidden.test(content), `Forbidden reference found in ${rel}`);
    }
  }
});
