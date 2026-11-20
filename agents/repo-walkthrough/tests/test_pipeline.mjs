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
 *   - skills/repo-walkthrough/scripts/build_walkthrough.mjs
 *   - skills/repo-walkthrough/scripts/generate_live_audio.mjs
 *   - skills/repo-walkthrough/scripts/render_video.mjs
 *   - Skill & plugin manifests (SKILL.md, plugin.json, README.md, single-source assets/index.tmpl)
 */

import assert from "node:assert/strict";
import crypto from "node:crypto";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";
import vm from "node:vm";

import {
  computeSpokenOffset,
  detectPythonCmd,
  hasGeminiKey,
  hasSupportedNodeVersion,
  openTarget,
  parseArgs as parseBuildArgs,
  resolveDataFile,
  resolveRepoRoot as resolveBuildRepoRoot,
  resolveTemplatePath,
  validateWalkthroughData,
} from "../skills/repo-walkthrough/scripts/build_walkthrough.mjs";
import {
  DEFAULT_ALIGNMENT_MODEL,
  DEFAULT_MODEL,
  DEFAULT_SPEECH_STYLE,
  buildTtsRequestBody,
  computeAcousticCueAt,
  computeContentHash,
  createWavBuffer,
  extractPcmSegments,
  extractRawPcm,
  parseArgs as parseAudioArgs,
  resolveGeminiApiKey,
  resolveRepoRoot as resolveAudioRepoRoot,
  resolveSharedCacheDir,
  sanitizeForTts,
} from "../skills/repo-walkthrough/scripts/generate_live_audio.mjs";
import * as audioModule from "../skills/repo-walkthrough/scripts/generate_live_audio.mjs";
import {
  formatFfmpegConcatEntry,
  getPlaywrightSearchRoots,
  launchChromium,
  loadPlaywright,
  parseArgs as parseVideoArgs,
  resolveContainedAudioPath,
  resolveRepoRoot as resolveVideoRepoRoot,
} from "../skills/repo-walkthrough/scripts/render_video.mjs";

const REPO_ROOT = path.resolve(import.meta.dirname, "..");
const SKILL_DIR = path.join(REPO_ROOT, "skills", "repo-walkthrough");
const SKILL_SCRIPTS_DIR = path.join(SKILL_DIR, "scripts");
const SKILL_TEMPLATE_REL = "skills/repo-walkthrough/assets/index.tmpl";

function loadDataJs(filePath) {
  const windowObj = Object.create(null);
  const sandbox = Object.assign(Object.create(null), { window: windowObj });
  vm.runInNewContext(fs.readFileSync(filePath, "utf8"), sandbox, { timeout: 2000 });
  return windowObj.WALKTHROUGH_DATA || windowObj.ADK_DATA;
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
  assert.equal(selfData.repo, "GoogleCloudPlatform/devrel-demos");
  assert.equal(selfData.subpath, "agents/repo-walkthrough");
  assert.equal(cymbalData.subpath, "data-analytics/cymbal-autos-multimodal");
  assert.equal(diffData.diffRange, "5984e02..1c3c31b");

  // Verify every non-generated node path in self-walkthrough exists on disk
  for (const node of selfData.nodes) {
    if (!node.generated) {
      assert.ok(
        fs.existsSync(path.join(REPO_ROOT, node.path)),
        `self-walkthrough node '${node.id}' points to missing path '${node.path}'`
      );
    }
  }
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

test("Validator rejects overlapping nodes, invalid edge endpoints, non-integer step numbers, path traversal, and out-of-sync cue phrases", () => {
  const overlapping = makeSampleData(5);
  overlapping.nodes[1].x = overlapping.nodes[0].x + 20;
  overlapping.nodes[1].y = overlapping.nodes[0].y + 10;
  assert.throws(
    () => validateWalkthroughData(overlapping, "overlapping.js"),
    /overlap on the SVG canvas/
  );

  const badEdge = makeSampleData(5);
  badEdge.edges.push({ id: "bad", from: "n0", to: "nonexistent", detail: "bad" });
  assert.throws(
    () => validateWalkthroughData(badEdge, "badEdge.js"),
    /unknown 'to' node 'nonexistent'/
  );

  const badCue = makeSampleData(5);
  badCue.walkthrough[0].cues.push({ at: 0.8, nodes: ["ghost_node"], focus: "ghost_node" });
  assert.throws(
    () => validateWalkthroughData(badCue, "badCue.js"),
    /unknown cue node 'ghost_node'/
  );

  const badStep = makeSampleData(5);
  badStep.walkthrough[0].step = "../../evil";
  assert.throws(
    () => validateWalkthroughData(badStep, "badStep.js"),
    /must be an integer >= 1/
  );

  assert.throws(
    () => resolveContainedAudioPath("/tmp/site", "../outside.wav"),
    /outside site directory/
  );
  assert.equal(
    resolveContainedAudioPath("/tmp/site", "audio/step-1.wav"),
    path.resolve("/tmp/site", "audio/step-1.wav")
  );

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

test("Gemini 3.8 TTS defaults, strict v1beta generateContent payload keys, RIFF WAV subchunk extraction (zero header pop), and hash stability", () => {
  assert.equal(DEFAULT_MODEL, process.env.GEMINI_TTS_MODEL || "gemini-3.8-flash-tts");
  assert.equal(
    DEFAULT_ALIGNMENT_MODEL,
    process.env.GEMINI_ALIGNMENT_MODEL || "gemini-3-flash-preview"
  );

  const raw =
    "In `__init__.py` and `_workflow.py`, `cli_tools_click.py` dispatches to `Runner`.";
  const sanitized = sanitizeForTts(raw);
  assert.equal(
    sanitized,
    "In init.py and workflow.py, cli tools click.py dispatches to Runner."
  );
  assert.ok(!sanitized.includes("_"), "Sanitized TTS text must not contain underscores");
  assert.ok(!sanitized.includes("`"), "Sanitized TTS text must not contain backticks");

  const payload = buildTtsRequestBody(raw, { voice: "Despina" });
  assert.deepEqual(Object.keys(payload), ["contents", "generationConfig"]);
  assert.equal(payload.contents.length, 1);
  assert.deepEqual(Object.keys(payload.contents[0]), ["parts"]);
  assert.equal(payload.contents[0].parts.length, 1);

  const part = payload.contents[0].parts[0];
  assert.deepEqual(
    Object.keys(part),
    ["text", "speechMetadata"],
    "Part keys must match v1beta Part schema (text + speechMetadata)"
  );
  assert.equal(part.text, sanitized, "parts[0].text must be strictly verbatim sanitized text without style prefix");
  assert.ok(!part.text.toLowerCase().includes("speak the following"), "Style prompt must never appear in parts[0].text");
  assert.deepEqual(part.speechMetadata, { style: DEFAULT_SPEECH_STYLE });

  assert.deepEqual(
    Object.keys(payload.generationConfig),
    ["responseModalities", "responseFormat", "speechConfig"],
    "generationConfig keys must match v1beta GenerationConfig schema"
  );
  assert.deepEqual(payload.generationConfig.responseModalities, ["AUDIO"]);
  assert.deepEqual(payload.generationConfig.responseFormat, {
    audio: { mimeType: "AUDIO_L16", sampleRate: 24000 },
  });
  assert.deepEqual(payload.generationConfig.speechConfig, {
    voiceConfig: { prebuiltVoiceConfig: { voiceName: "Despina" } },
  });

  // RIFF stripping: verify silence-led PCM stays at 0 amplitude (0 header pop at t=0.00s)
  // across raw L16 PCM, canonical 44-byte RIFF WAV, and non-44-byte WAV with LIST + odd JUNK chunks
  const pcmSample = Buffer.alloc(4800); // first 200 samples are pure digital silence (0)
  for (let i = 200; i < 2400; i++) pcmSample.writeInt16LE(((i - 200) * 17) % 12000, i * 2);
  assert.deepEqual(extractRawPcm(pcmSample), pcmSample);

  const wrappedOnce = createWavBuffer(pcmSample, 24000, 1, 16);
  assert.equal(wrappedOnce.length, 44 + pcmSample.length);
  assert.deepEqual(extractRawPcm(wrappedOnce), pcmSample);

  // Double-passing a RIFF WAV buffer into createWavBuffer must NEVER double-wrap a second RIFF header or create a t=0 pop
  const rewrapped = createWavBuffer(wrappedOnce, 24000, 1, 16);
  assert.equal(rewrapped.length, 44 + pcmSample.length);
  assert.notEqual(rewrapped.subarray(44, 48).toString("ascii"), "RIFF");
  for (let s = 0; s < 200; s++) {
    assert.equal(
      rewrapped.readInt16LE(44 + s * 2),
      0,
      `Expected 0 header pop in leading silence sample ${s}, got ${rewrapped.readInt16LE(44 + s * 2)}`
    );
  }
  assert.deepEqual(rewrapped.subarray(44), pcmSample);

  // Construct a non-44-byte RIFF WAV containing a LIST metadata chunk + odd-length JUNK chunk before data
  const listPayload = Buffer.from("INFOISFTLavf60.16.100\0", "ascii");
  const listPaddedLen = listPayload.length + (listPayload.length % 2);
  const listChunk = Buffer.alloc(8 + listPaddedLen);
  listChunk.write("LIST", 0);
  listChunk.writeUInt32LE(listPayload.length, 4);
  listPayload.copy(listChunk, 8);

  const junkChunk = Buffer.alloc(8 + 6); // 5-byte odd JUNK chunk padded to 6 bytes
  junkChunk.write("JUNK", 0);
  junkChunk.writeUInt32LE(5, 4);

  const wavWithListAndJunk = Buffer.concat([
    Buffer.from("RIFF"),
    Buffer.alloc(4),
    Buffer.from("WAVE"),
    wrappedOnce.subarray(12, 36), // fmt  subchunk (24 bytes)
    listChunk,
    junkChunk,
    wrappedOnce.subarray(36), // data subchunk
  ]);
  wavWithListAndJunk.writeUInt32LE(wavWithListAndJunk.length - 8, 4);
  assert.ok(wavWithListAndJunk.length > 44 + pcmSample.length);

  const strippedListPcm = extractRawPcm(wavWithListAndJunk);
  assert.deepEqual(strippedListPcm, pcmSample);
  const canonicalFromListWav = createWavBuffer(wavWithListAndJunk, 24000, 1, 16);
  assert.equal(canonicalFromListWav.length, 44 + pcmSample.length);
  assert.equal(canonicalFromListWav.readInt16LE(44), 0, "Expected 0 pop at sample 0 after stripping LIST + JUNK RIFF header");

  const h1 = computeContentHash("gemini-3.8-flash-tts", "Despina", raw);
  const h2 = computeContentHash("gemini-3.8-flash-tts", "Despina", sanitized);
  assert.equal(h1, h2, "Hash of raw and sanitized text should be identical");
  assert.equal(h1.length, 16);
});

test("createWavBuffer, extractPcmSegments, and computeAcousticCueAt align voiced segments accurately", () => {
  const pcm = Buffer.alloc(24000 * 2 * 2);
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

test("computeAcousticCueAt returns null (not 0) for non-first cues with missing, empty, or unmatched phrases and anchors only cue 0 at 0", () => {
  const aligned = [
    { seg: 0, startSec: 18.24, endSec: 20.8, text: "03 vision extraction.sql inspects photos" },
    { seg: 1, startSec: 26.76, endSec: 29.52, text: "while 04 predictive pricing.sql combines traits" },
  ];
  assert.equal(computeAcousticCueAt(aligned, 60.76, undefined, 1), null, "missing phrase on cue 1 must be null");
  assert.equal(computeAcousticCueAt(aligned, 60.76, "", 2), null, "empty phrase on cue 2 must be null");
  assert.equal(computeAcousticCueAt(aligned, 60.76, "  !!  ", 1), null, "punctuation-only phrase must be null");
  assert.equal(computeAcousticCueAt(aligned, 60.76, "never spoken here", 1), null, "unmatched phrase must be null");
  assert.equal(computeAcousticCueAt([], 60.76, "03 vision extraction.sql", 1), null, "empty segments must be null");
  assert.equal(computeAcousticCueAt(null, 60.76, "03 vision extraction.sql", 1), null, "null segments must be null");
  assert.equal(computeAcousticCueAt(aligned, 0, "03 vision extraction.sql", 1), null, "zero duration must be null");

  assert.equal(computeAcousticCueAt(aligned, 60.76, undefined, 0), 0, "cue 0 always anchors at 0");
  assert.equal(computeAcousticCueAt(aligned, 60.76, "04 predictive pricing.sql", 0), 0, "cue 0 anchors at 0 even with a phrase");
  assert.equal(computeAcousticCueAt([], 60.76, "", 0), 0, "cue 0 anchors at 0 even without segments");
});

test("computeAcousticCueAt matches non-Latin phrases with Unicode-aware normalization", () => {
  const alignedJa = [
    { seg: 0, startSec: 0, endSec: 4, text: "これはテストです。" },
    { seg: 1, startSec: 5, endSec: 9, text: "次に日本語の説明をします。" },
  ];
  // "日本語" starts at char 2 of the 12-char normalized segment 1: 5 + 4 * (2 / 12) = 5.67s of 10s
  assert.equal(computeAcousticCueAt(alignedJa, 10, "日本語", 1), 0.57);
  assert.equal(computeAcousticCueAt(alignedJa, 10, "中文", 1), null, "unmatched non-Latin phrase must be null");
  assert.equal(computeAcousticCueAt([], 10, "日本語", 1), null, "non-Latin phrase with empty segments must be null");
  assert.equal(computeAcousticCueAt(alignedJa, 10, "日本語", 0), 0, "cue 0 still anchors at 0");
});

test("alignStepCues advances a monotonic search cursor so repeated phrases never jump backward", () => {
  assert.equal(
    typeof audioModule.alignStepCues,
    "function",
    "generate_live_audio.mjs must export alignStepCues(cues, alignedSegments, totalDur)"
  );
  const aligned = [
    { seg: 0, startSec: 1, endSec: 3, text: "the runner calls the agent" },
    { seg: 1, startSec: 4, endSec: 6, text: "then the runner calls the tool" },
    { seg: 2, startSec: 7, endSec: 9, text: "finally the runner returns" },
  ];
  const cues = [
    { at: 0, node: "a" },
    { at: 0.2, node: "b", phrase: "the runner" },
    { at: 0.3, node: "c" },
    { at: 0.5, node: "d", phrase: "the runner" },
    { at: 0.8, node: "e", phrase: "the runner" },
  ];
  const out = audioModule.alignStepCues(cues, aligned, 10);
  // 1 + 2 * 0/26 = 1.0s, 4 + 2 * 5/30 = 4.33s, 7 + 2 * 8/26 = 7.62s (of 10s)
  assert.deepEqual(
    out.map((c) => c.at),
    [0, 0.1, 0.3, 0.43, 0.76]
  );
  assert.deepEqual(
    out.map((c) => c.node),
    ["a", "b", "c", "d", "e"],
    "cue payloads must be preserved"
  );
  const phrased = out.filter((c) => c.phrase).map((c) => c.at);
  for (let i = 1; i < phrased.length; i++) {
    assert.ok(phrased[i] > phrased[i - 1], `repeated phrase cue ${i} moved backward: ${phrased}`);
  }
  // Without a cursor each call is independent and finds the first occurrence
  assert.equal(computeAcousticCueAt(aligned, 10, "the runner", 3), 0.1);
});

test("Real web/data-adk.js cues without a phrase keep their authored timing (0 clobbered to 0)", () => {
  const adkData = loadDataJs(path.join(REPO_ROOT, "web", "data-adk.js"));
  const totalDur = 60;
  const missing = [];
  const clobbered = [];
  for (const st of adkData.walkthrough) {
    const aligned = [{ seg: 0, startSec: 0, endSec: totalDur, text: st.narration }];
    (st.cues || []).forEach((c, cIdx) => {
      if (cIdx === 0 || c.phrase) return;
      missing.push(`step ${st.step} cue ${cIdx}`);
      // Mirrors the main() merge: `at: acousticAt !== null ? acousticAt : c.at`
      const acousticAt = computeAcousticCueAt(aligned, totalDur, c.phrase, cIdx);
      const at = acousticAt !== null ? acousticAt : c.at;
      if (at !== c.at) clobbered.push(`step ${st.step} cue ${cIdx}: ${c.at} -> ${at}`);
    });
  }
  assert.equal(missing.length, 20, "bundled ADK example should have 20 non-first cues without a phrase");
  assert.deepEqual(
    clobbered,
    [],
    `${clobbered.length} of ${missing.length} phrase-less ADK cues were clobbered:\n${clobbered.join("\n")}`
  );

  assert.equal(typeof audioModule.alignStepCues, "function", "generate_live_audio.mjs must export alignStepCues");
  for (const st of adkData.walkthrough) {
    const aligned = [{ seg: 0, startSec: 0, endSec: totalDur, text: st.narration }];
    const out = audioModule.alignStepCues(st.cues, aligned, totalDur);
    assert.equal(out[0].at, 0, `step ${st.step} cue 0 must anchor at 0`);
    st.cues.forEach((c, cIdx) => {
      if (cIdx > 0 && !c.phrase) {
        assert.equal(out[cIdx].at, c.at, `step ${st.step} cue ${cIdx} must keep authored at`);
      }
    });
  }
});

test("CLI --help / -h exits 0 without mutating examples, and unknown flags or missing .html fail fast", () => {
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

  assert.equal(parseBuildArgs(["--help"]).help, true);
  assert.equal(parseBuildArgs(["-h"]).help, true);
  assert.equal(parseAudioArgs(["--help"]).help, true);
  assert.equal(parseVideoArgs(["--help"]).help, true);

  for (const parser of [parseBuildArgs, parseAudioArgs, parseVideoArgs]) {
    assert.throws(() => parser(["--unknown-flag"]), /Unknown option/);
  }
  assert.throws(() => parseBuildArgs(["--mode", "invalid"]), /Invalid --mode/);
  assert.throws(() => parseBuildArgs(["--speed", "0.2"]), /--speed must be between 0.5 and 2.0/);
  assert.throws(() => parseVideoArgs(["--speed", "2.5"]), /--speed must be between 0.5 and 2.0/);
  assert.throws(() => parseVideoArgs(["--fps", "0"]), /--fps must be between 1 and 60/);

  // Running --help on each script must exit 0 and leave examples/self-walkthrough/index.html untouched
  const selfHtmlPath = path.join(REPO_ROOT, "examples", "self-walkthrough", "index.html");
  const beforeHash = crypto.createHash("sha256").update(fs.readFileSync(selfHtmlPath)).digest("hex");

  for (const scriptName of [
    "build_walkthrough.mjs",
    "generate_live_audio.mjs",
    "render_video.mjs",
  ]) {
    const helpOut = execFileSync(
      process.execPath,
      [path.join(SKILL_SCRIPTS_DIR, scriptName), "--help"],
      { encoding: "utf8" }
    );
    assert.match(helpOut, /Usage:/);
  }
  if (process.platform !== "win32") {
    const shHelp = execFileSync("bash", [path.join(SKILL_SCRIPTS_DIR, "render_video.sh"), "--help"], {
      encoding: "utf8",
    });
    assert.match(shHelp, /Usage:/);
  }
  const afterHash = crypto.createHash("sha256").update(fs.readFileSync(selfHtmlPath)).digest("hex");
  assert.equal(afterHash, beforeHash, "--help must never modify examples/self-walkthrough/index.html");

  // Running render_video.mjs on a directory containing only index.tmpl (no built index.html) must fail clearly
  const tmplOnlyDir = fs.mkdtempSync(path.join(os.tmpdir(), "rw-tmpl-only-"));
  try {
    fs.copyFileSync(path.join(REPO_ROOT, SKILL_TEMPLATE_REL), path.join(tmplOnlyDir, "index.tmpl"));
    assert.throws(
      () =>
        execFileSync(
          process.execPath,
          [path.join(SKILL_SCRIPTS_DIR, "render_video.mjs"), "--dir", tmplOnlyDir],
          { stdio: "pipe" }
        ),
      /Missing built website/
    );
  } finally {
    fs.rmSync(tmplOnlyDir, { recursive: true, force: true });
  }
});

test("build_walkthrough.mjs builds standalone site from both custom data.js and web/data-adk.js, and works from an isolated standalone skill copy", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "rw-test-"));
  try {
    // 1. Build from web/data-adk.js into an output folder (verifies data-adk.js is copied to data.js)
    const adkOutDir = path.join(tmpDir, "adk-site");
    execFileSync(
      process.execPath,
      [
        path.join(SKILL_SCRIPTS_DIR, "build_walkthrough.mjs"),
        "--data",
        path.join(REPO_ROOT, "web", "data-adk.js"),
        "--out-dir",
        adkOutDir,
        "--mode",
        "website",
        "--no-tts",
      ],
      { stdio: "pipe" }
    );
    assert.ok(fs.existsSync(path.join(adkOutDir, "index.html")));
    assert.ok(fs.existsSync(path.join(adkOutDir, "data.js")), "web/data-adk.js must be copied to outDir/data.js");
    const builtAdkHtml = fs.readFileSync(path.join(adkOutDir, "index.html"), "utf8");
    assert.ok(!builtAdkHtml.includes('src="data-adk.js"'), "Standalone build must strip data-adk.js tag");
    assert.ok(builtAdkHtml.includes('src="data.js"'), "Standalone build must load data.js");

    // 2. Copy ONLY skills/repo-walkthrough into an isolated .agents/skills/repo-walkthrough path
    const standaloneHome = path.join(tmpDir, "isolated-home", ".agents", "skills", "repo-walkthrough");
    fs.mkdirSync(path.dirname(standaloneHome), { recursive: true });
    fs.cpSync(SKILL_DIR, standaloneHome, { recursive: true });
    assert.ok(fs.existsSync(path.join(standaloneHome, "assets", "index.tmpl")));

    const standaloneOut = path.join(tmpDir, "standalone-out");
    fs.mkdirSync(standaloneOut, { recursive: true });
    const sampleDataPath = path.join(standaloneOut, "data.js");
    fs.writeFileSync(
      sampleDataPath,
      `window.WALKTHROUGH_DATA = ${JSON.stringify(makeSampleData(4), null, 2)};\n`,
      "utf8"
    );

    execFileSync(
      process.execPath,
      [
        path.join(standaloneHome, "scripts", "build_walkthrough.mjs"),
        "--data",
        sampleDataPath,
        "--out-dir",
        standaloneOut,
        "--mode",
        "website",
        "--no-tts",
      ],
      { stdio: "pipe" }
    );
    const builtHtml = fs.readFileSync(path.join(standaloneOut, "index.html"), "utf8");
    assert.ok(builtHtml.includes("--g-red-light: #F28B82"));
    assert.match(
      builtHtml,
      /<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="data:image\/svg\+xml,[^"]+">/,
      "Standalone skill copy must preserve inline SVG favicon in generated index.html"
    );
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test("Single-source template, README GFM table, SKILL.md, and plugin.json manifests are valid and clean", () => {
  // Single copy of index.tmpl inside skills/repo-walkthrough/assets/index.tmpl (deleted from web/)
  assert.equal(
    fs.existsSync(path.join(REPO_ROOT, SKILL_TEMPLATE_REL)),
    true,
    "skills/repo-walkthrough/assets/index.tmpl must exist"
  );
  assert.equal(
    fs.existsSync(path.join(REPO_ROOT, "web", "index.tmpl")),
    false,
    "web/index.tmpl must not exist (single source in skills/repo-walkthrough/assets/index.tmpl)"
  );
  assert.equal(
    fs.existsSync(path.join(REPO_ROOT, "web", "index.html")),
    false,
    "web/index.html must not exist"
  );

  // README.md must use clean single-line GFM pipe rows (zero Pandoc ': ... :' continuations)
  const readmeMd = fs.readFileSync(path.join(REPO_ROOT, "README.md"), "utf8");
  assert.ok(!/^:\s+/m.test(readmeMd), "README.md must not contain multiline ': ... :' broken table rows");
  assert.match(readmeMd, /^\|\s*\*\*Python 3\*\*\s*\|/m);
  assert.match(readmeMd, /git sparse-checkout set agents\/repo-walkthrough/);
  assert.match(readmeMd, /~\/\.gemini\/config\/skills\/repo-walkthrough/);
  assert.ok(
    !/gemini\s*cli|gemini-cli|~\/\.gemini\/skills\/|\.gemini\/skills\//i.test(readmeMd),
    "README.md must not reference Gemini CLI or legacy .gemini/skills install paths"
  );

  const skillMd = fs.readFileSync(path.join(SKILL_DIR, "SKILL.md"), "utf8");
  assert.ok(
    !/gemini\s*cli|gemini-cli|~\/\.gemini\/skills\/|\.gemini\/skills\//i.test(skillMd),
    "SKILL.md must not reference Gemini CLI or legacy .gemini/skills install paths"
  );
  assert.match(skillMd, /^---\r?\nname:\s*repo-walkthrough\r?\ndescription:/m);
  assert.ok(!/^license:/m.test(skillMd), "SKILL.md frontmatter should not include license field");
  assert.match(skillMd, /^\s*author:\s*Google\s*$/m, "SKILL.md metadata.author should be Google");
  assert.ok(!skillMd.includes("~/projects/"), "SKILL.md must not hardcode ~/projects/ paths");
  assert.match(skillMd, /node\s+<skill-dir>\/scripts\/build_walkthrough\.mjs\s+--check-prereqs/);
  assert.ok(skillMd.includes("python3 <skill-dir>/scripts/fetch_repo.py"));
  assert.ok(
    !skillMd.includes("<plugin-root>/skills/repo-walkthrough/scripts/"),
    "SKILL.md commands must use <skill-dir>/scripts/ for standalone portability"
  );
  assert.ok(skillMd.includes("$env:TEMP"), "SKILL.md must use $env:TEMP for Windows PowerShell");
  assert.ok(!skillMd.includes(";"), "SKILL.md prose must avoid semicolons");

  // Verify skills/repo-walkthrough/scripts is a real directory
  assert.equal(fs.lstatSync(SKILL_SCRIPTS_DIR).isSymbolicLink(), false);
  assert.equal(fs.statSync(SKILL_SCRIPTS_DIR).isDirectory(), true);
  for (const requiredScript of [
    "build_walkthrough.mjs",
    "fetch_repo.py",
    "generate_live_audio.mjs",
    "render_video.mjs",
    "render_video.sh",
  ]) {
    assert.ok(fs.existsSync(path.join(SKILL_SCRIPTS_DIR, requiredScript)));
  }

  const pluginJsonPath = path.join(REPO_ROOT, "plugin.json");
  const pluginManifest = JSON.parse(fs.readFileSync(pluginJsonPath, "utf8"));
  assert.equal(pluginManifest.name, "repo-walkthrough");
  assert.equal(pluginManifest.displayName, "Repo Walkthrough");
  assert.ok(!/plugin|antigravity|gemini/i.test(pluginManifest.displayName));
  assert.equal(pluginManifest.version, "1.0.0");
  assert.ok(pluginManifest.description.length >= 120 && pluginManifest.description.length <= 160);
  assert.equal(pluginManifest.logo, "assets/logo.svg");
  assert.ok(fs.existsSync(path.join(REPO_ROOT, pluginManifest.logo)));
  assert.ok(!("license" in pluginManifest));
  assert.match(pluginManifest.homepage || "", /^https:\/\//);
  assert.match(pluginManifest.repository || "", /^https:\/\//);
  assert.equal(pluginManifest.suggestedPrompts?.length, 3);
  assert.ok(Array.isArray(pluginManifest.keywords) && pluginManifest.keywords.length >= 4);
});

test("resolveRepoRoot and resolveTemplatePath handle plugin installs, standalone skill copies, and test fixtures", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-deref-"));
  try {
    // 1. Plugin layout (plugin.json + skills/repo-walkthrough/assets/index.tmpl)
    const pluginRoot = path.join(tmpRoot, "plugin-install");
    fs.mkdirSync(path.join(pluginRoot, "skills", "repo-walkthrough", "assets"), { recursive: true });
    fs.mkdirSync(path.join(pluginRoot, "skills", "repo-walkthrough", "scripts"), { recursive: true });
    fs.writeFileSync(path.join(pluginRoot, "plugin.json"), '{"name":"repo-walkthrough"}', "utf8");
    const tmplPath = path.join(pluginRoot, "skills", "repo-walkthrough", "assets", "index.tmpl");
    fs.writeFileSync(tmplPath, "<html>tmpl</html>", "utf8");
    const derefScripts = path.join(pluginRoot, "skills", "repo-walkthrough", "scripts");

    for (const fn of [resolveBuildRepoRoot, resolveAudioRepoRoot, resolveVideoRepoRoot]) {
      assert.equal(fn(derefScripts), pluginRoot);
    }
    assert.equal(resolveTemplatePath(pluginRoot, derefScripts), tmplPath);

    // 2. Standalone skill copy under .agents/skills/repo-walkthrough (parent .agents has no plugin.json)
    const agentsRoot = path.join(tmpRoot, "project", ".agents");
    const standaloneSkill = path.join(agentsRoot, "skills", "repo-walkthrough");
    fs.mkdirSync(path.join(standaloneSkill, "assets"), { recursive: true });
    fs.mkdirSync(path.join(standaloneSkill, "scripts"), { recursive: true });
    const standaloneTmpl = path.join(standaloneSkill, "assets", "index.tmpl");
    fs.writeFileSync(standaloneTmpl, "<html>standalone</html>", "utf8");
    const standaloneScripts = path.join(standaloneSkill, "scripts");

    for (const fn of [resolveBuildRepoRoot, resolveAudioRepoRoot, resolveVideoRepoRoot]) {
      assert.equal(fn(standaloneScripts), standaloneSkill);
    }
    assert.equal(resolveTemplatePath(standaloneSkill, standaloneScripts), standaloneTmpl);

    // 3. resolveDataFile requires explicit --data or outDir/data.js (never defaults to examples/)
    assert.equal(resolveDataFile({ dataFile: null, outDir: null }, REPO_ROOT, REPO_ROOT), null);
    assert.equal(
      resolveDataFile({ dataFile: null, outDir: path.join(tmpRoot, "no-out") }, pluginRoot, pluginRoot),
      null
    );
    const outDataDir = path.join(tmpRoot, "out-with-data");
    fs.mkdirSync(outDataDir, { recursive: true });
    const outDataJs = path.join(outDataDir, "data.js");
    fs.writeFileSync(outDataJs, "window.WALKTHROUGH_DATA = {};", "utf8");
    assert.equal(
      resolveDataFile({ dataFile: null, outDir: outDataDir }, pluginRoot, pluginRoot),
      outDataJs
    );
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test("resolveSharedCacheDir uses PLUGIN_DATA or ~/.cache and falls back to localCacheDir when read-only", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-cache-"));
  try {
    const localCache = path.join(tmpRoot, "local-cache");
    fs.mkdirSync(localCache, { recursive: true });

    const pluginDataDir = path.join(tmpRoot, "plugin-data");
    const resolvedPluginCache = resolveSharedCacheDir(localCache, { PLUGIN_DATA: pluginDataDir }, tmpRoot);
    assert.equal(resolvedPluginCache, path.join(pluginDataDir, "audio-cache"));
    assert.ok(fs.existsSync(resolvedPluginCache));

    const fakeHome = path.join(tmpRoot, "home");
    const resolvedHomeCache = resolveSharedCacheDir(localCache, {}, fakeHome);
    assert.equal(resolvedHomeCache, path.join(fakeHome, ".cache", "repo-walkthrough", "audio"));
    assert.ok(fs.existsSync(resolvedHomeCache));

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

test("Read-only installed plugin directory (chmod -R a-w / icacls) builds website and runs cached audio without failing", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-ro-plugin-"));
  const roPluginDir = path.join(tmpRoot, "plugin");
  const outDir = path.join(tmpRoot, "out");
  const pluginDataDir = path.join(tmpRoot, "plugin-data");
  try {
    fs.mkdirSync(path.join(roPluginDir, "skills", "repo-walkthrough", "assets"), { recursive: true });
    fs.writeFileSync(path.join(roPluginDir, "plugin.json"), '{"name":"repo-walkthrough"}', "utf8");
    fs.copyFileSync(
      resolveTemplatePath(REPO_ROOT),
      path.join(roPluginDir, "skills", "repo-walkthrough", "assets", "index.tmpl")
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

    const sharedAudioCache = path.join(pluginDataDir, "audio-cache");
    fs.mkdirSync(sharedAudioCache, { recursive: true });
    const stepHash = computeContentHash(
      DEFAULT_MODEL,
      "Despina",
      sample.walkthrough[0].narration
    );
    const dummyWav = createWavBuffer(Buffer.alloc(24000 * 2), 24000, 1, 16);
    fs.writeFileSync(path.join(sharedAudioCache, `${stepHash}.wav`), dummyWav);

    if (process.platform === "win32") {
      execFileSync("attrib", ["+R", path.join(roPluginDir, "*"), "/S", "/D"]);
      execFileSync("icacls", [roPluginDir, "/deny", "*S-1-1-0:(OI)(CI)(WD,AD,WEA,WA)"]);
    } else {
      execFileSync("chmod", ["-R", "a-w", roPluginDir]);
    }

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

test("Security: loadPlaywright and --check-prereqs never execute node_modules committed in an untrusted cwd", () => {
  const untrustedCwd = fs.mkdtempSync(path.join(os.tmpdir(), "rw-untrusted-cwd-"));
  const marker = path.join(untrustedCwd, "PWNED");
  try {
    for (const pkg of ["playwright-core", "playwright"]) {
      const pkgDir = path.join(untrustedCwd, "node_modules", pkg);
      fs.mkdirSync(pkgDir, { recursive: true });
      fs.writeFileSync(path.join(pkgDir, "package.json"), JSON.stringify({ name: pkg, main: "index.js" }));
      fs.writeFileSync(
        path.join(pkgDir, "index.js"),
        `require("fs").appendFileSync(${JSON.stringify(marker)}, ${JSON.stringify(`${pkg} executed\n`)});\n` +
          `module.exports = { chromium: { launch: async () => { throw new Error("attacker stub"); } } };\n`
      );
    }
    const childEnv = { ...process.env, NODE_PATH: "" };

    const renderUrl = pathToFileURL(path.join(SKILL_SCRIPTS_DIR, "render_video.mjs")).href;
    spawnSync(
      process.execPath,
      [
        "--input-type=module",
        "-e",
        `import { loadPlaywright } from ${JSON.stringify(renderUrl)}; try { loadPlaywright(); } catch {}`,
      ],
      { cwd: untrustedCwd, env: childEnv, encoding: "utf8", timeout: 60000 }
    );
    assert.equal(
      fs.existsSync(marker),
      false,
      `loadPlaywright() executed attacker code from <cwd>/node_modules: ${fs.existsSync(marker) ? fs.readFileSync(marker, "utf8").trim() : ""}`
    );

    spawnSync(process.execPath, [path.join(SKILL_SCRIPTS_DIR, "build_walkthrough.mjs"), "--check-prereqs"], {
      cwd: untrustedCwd,
      env: childEnv,
      encoding: "utf8",
      timeout: 60000,
    });
    assert.equal(
      fs.existsSync(marker),
      false,
      `build_walkthrough.mjs --check-prereqs executed attacker code from <cwd>/node_modules: ${fs.existsSync(marker) ? fs.readFileSync(marker, "utf8").trim() : ""}`
    );
  } finally {
    fs.rmSync(untrustedCwd, { recursive: true, force: true });
  }
});

test("Security: resolveGeminiApiKey prefers user-scoped keys and the OS store over an untrusted <cwd>/.env", () => {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rw-apikey-untrusted-"));
  try {
    const untrustedCwd = path.join(tmpRoot, "untrusted-clone");
    const fakeRepo = path.join(tmpRoot, "plugin-root");
    const emptyHome = path.join(tmpRoot, "empty-home");
    for (const d of [untrustedCwd, fakeRepo, emptyHome]) fs.mkdirSync(d, { recursive: true });
    fs.writeFileSync(path.join(untrustedCwd, ".env"), "GEMINI_API_KEY=untrusted_repo_key\n", "utf8");
    const noStore = () => "";
    const base = { env: {}, platform: "linux", cwd: untrustedCwd, homedir: emptyHome, runner: noStore };

    const configHome = path.join(tmpRoot, "config-home");
    fs.mkdirSync(path.join(configHome, ".config", "repo-walkthrough"), { recursive: true });
    fs.writeFileSync(path.join(configHome, ".config", "repo-walkthrough", ".env"), "GEMINI_API_KEY=user_trusted_key\n");
    assert.equal(
      resolveGeminiApiKey(fakeRepo, { ...base, homedir: configHome }),
      "user_trusted_key",
      "~/.config/repo-walkthrough/.env must beat <cwd>/.env"
    );

    const geminiHome = path.join(tmpRoot, "gemini-home");
    fs.mkdirSync(path.join(geminiHome, ".gemini"), { recursive: true });
    fs.writeFileSync(path.join(geminiHome, ".gemini", ".env"), "GEMINI_API_KEY=user_gemini_key\n");
    assert.equal(
      resolveGeminiApiKey(fakeRepo, { ...base, homedir: geminiHome }),
      "user_gemini_key",
      "~/.gemini/.env must beat <cwd>/.env"
    );

    const pluginData = path.join(tmpRoot, "plugin-data");
    fs.mkdirSync(pluginData, { recursive: true });
    fs.writeFileSync(path.join(pluginData, ".env"), "GEMINI_API_KEY=plugin_data_key\n");
    assert.equal(
      resolveGeminiApiKey(fakeRepo, { ...base, env: { PLUGIN_DATA: pluginData } }),
      "plugin_data_key",
      "$PLUGIN_DATA/.env must beat <cwd>/.env"
    );

    assert.equal(
      resolveGeminiApiKey(fakeRepo, { ...base, runner: (cmd) => (cmd === "secret-tool" ? "os_store_key\n" : "") }),
      "os_store_key",
      "OS credential store must beat <cwd>/.env"
    );

    assert.equal(
      resolveGeminiApiKey(fakeRepo, { ...base, env: { GEMINI_API_KEY: "env_key" }, homedir: configHome }),
      "env_key",
      "GEMINI_API_KEY env var always wins"
    );
    assert.equal(
      resolveGeminiApiKey(fakeRepo, base),
      "untrusted_repo_key",
      "<cwd>/.env stays available only as the last-resort fallback"
    );
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test("Cross-platform GEMINI_API_KEY resolution and strict scoping", () => {
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

    fs.writeFileSync(path.join(cwdDir, ".env"), "GEMINI_API_KEY=from-cwd-env\n", "utf8");
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
  } finally {
    fs.rmSync(tmpRoot, { recursive: true, force: true });
  }
});

test("Cross-platform helpers: openTarget (rundll32 on win32, blocks .tmpl), detectPythonCmd, Node >= 20.11, formatFfmpegConcatEntry, and launchChromium msedge fallback", async () => {
  const calls = [];
  const mockRunner = (cmd, args) => {
    calls.push({ cmd, args });
  };

  // Never opens raw .tmpl files on any OS
  assert.equal(openTarget("/path/to/index.tmpl", "darwin", mockRunner), false);
  assert.equal(openTarget("C:\\out\\index.tmpl", "win32", mockRunner), false);
  assert.equal(openTarget("/path/to/index.tmpl", "linux", mockRunner), false);
  assert.equal(calls.length, 0);

  assert.equal(openTarget("/path/to/index.html", "darwin", mockRunner), true);
  assert.deepEqual(calls.pop(), { cmd: "open", args: ["/path/to/index.html"] });

  const trickyWinTarget = "C:\\Users\\dev\\R&D (1) %TEMP%\\index.html";
  assert.equal(openTarget(trickyWinTarget, "win32", mockRunner), true);
  assert.deepEqual(calls.pop(), {
    cmd: "rundll32.exe",
    args: ["url.dll,FileProtocolHandler", trickyWinTarget],
  });

  assert.equal(openTarget("/path/to/index.html", "linux", mockRunner), true);
  assert.deepEqual(calls.pop(), { cmd: "xdg-open", args: ["/path/to/index.html"] });

  assert.doesNotThrow(() => {
    const ok = openTarget("/path/to/index.html", "linux", () => {
      const err = new Error("spawn xdg-open ENOENT");
      err.code = "ENOENT";
      throw err;
    });
    assert.equal(ok, false);
  });

  // detectPythonCmd verifies Python 3 and prioritizes py -3 ahead of Windows Store python stub on win32
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

  assert.equal(hasSupportedNodeVersion("20.11.0"), true);
  assert.equal(hasSupportedNodeVersion("22.4.1"), true);
  assert.equal(hasSupportedNodeVersion("20.9.0"), false);

  assert.equal(
    formatFfmpegConcatEntry("C:\\Users\\dev\\out\\audio\\step-1.wav"),
    "file 'C:/Users/dev/out/audio/step-1.wav'"
  );
  assert.equal(
    formatFfmpegConcatEntry("C:\\Users\\O'Connor\\audio\\step-1.wav"),
    "file 'C:/Users/O'\\''Connor/audio/step-1.wav'"
  );

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
      let cwdResolved = null;
      try {
        cwdResolved = loadPlaywright();
      } catch {}
      assert.notEqual(cwdResolved?.source, "cwd-playwright", "must never load playwright from an untrusted cwd");
    } finally {
      process.chdir(origCwd);
    }
    const origPwPath = process.env.PLAYWRIGHT_MODULE_PATH;
    process.env.PLAYWRIGHT_MODULE_PATH = fakePwDir;
    try {
      assert.equal(loadPlaywright().source, "cwd-playwright", "explicit PLAYWRIGHT_MODULE_PATH opt-in is honored");
    } finally {
      if (origPwPath === undefined) delete process.env.PLAYWRIGHT_MODULE_PATH;
      else process.env.PLAYWRIGHT_MODULE_PATH = origPwPath;
    }
  } finally {
    fs.rmSync(tmpCwd, { recursive: true, force: true });
  }
});

test("Viewer template and all 3 rebuilt examples embed assets/logo.svg as a 1-line inline SVG favicon in <head>", () => {
  const logoSvg = fs.readFileSync(path.join(REPO_ROOT, "assets", "logo.svg"), "utf8").trim();
  const targets = [
    resolveTemplatePath(REPO_ROOT),
    path.join(REPO_ROOT, "examples", "self-walkthrough", "index.html"),
    path.join(REPO_ROOT, "examples", "cymbal-autos-multimodal", "index.html"),
    path.join(REPO_ROOT, "examples", "diff-5984e02-to-head", "index.html"),
  ];
  for (const target of targets) {
    const html = fs.readFileSync(target, "utf8");
    const headMatch = html.match(/<head>([\s\S]*?)<\/head>/i);
    assert.ok(headMatch, `${target} must contain a <head> section`);
    const iconMatch = headMatch[1].match(
      /<link\s+rel="icon"\s+type="image\/svg\+xml"\s+href="(data:image\/svg\+xml,[^"]+)">/
    );
    assert.ok(iconMatch, `${target} <head> must contain an inline SVG favicon <link>`);
    assert.ok(!iconMatch[0].includes("\n"), "Inline SVG favicon <link> tag must be single-line");
    const decodedSvg = decodeURIComponent(iconMatch[1].slice("data:image/svg+xml,".length));
    assert.equal(decodedSvg.replace(/'/g, '"'), logoSvg, `Inline SVG favicon in ${target} must match assets/logo.svg`);
  }
});
