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
 * Validate a `data.js` walkthrough file and build either:
 *   1. Website only (`--mode website`)
 *   2. Website + full-width animated MP4 video (`--mode video`)
 *
 * Usage:
 *   node scripts/build_walkthrough.mjs --check-prereqs
 *   node scripts/build_walkthrough.mjs --data <path/to/data.js> [--out-dir <dir>] [--mode website|video] [--no-tts] [--open]
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

function parseArgs(argv) {
  const opts = {
    dataFile: null,
    outDir: null,
    outVideo: null,
    mode: "website", // "website" | "video"
    speed: null,
    noTts: false,
    open: false,
    checkPrereqs: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--data" && argv[i + 1]) opts.dataFile = path.resolve(argv[++i]);
    else if (a === "--out-dir" && argv[i + 1]) opts.outDir = path.resolve(argv[++i]);
    else if (a === "--out-video" && argv[i + 1]) opts.outVideo = path.resolve(argv[++i]);
    else if (a === "--mode" && argv[i + 1]) opts.mode = argv[++i].toLowerCase();
    else if (a === "--speed" && argv[i + 1]) opts.speed = argv[++i];
    else if (a === "--video") opts.mode = "video";
    else if (a === "--website") opts.mode = "website";
    else if (a === "--no-tts") opts.noTts = true;
    else if (a === "--open") opts.open = true;
    else if (a === "--check-prereqs") opts.checkPrereqs = true;
  }
  return opts;
}

function hasCmd(cmd, args = ["--version"]) {
  try {
    execFileSync(cmd, args, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

function hasGeminiKey() {
  if (process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY.trim()) return true;
  try {
    const k = execFileSync(
      "security",
      ["find-generic-password", "-s", "gemini-api-key", "-w"],
      { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }
    ).trim();
    if (k) return true;
  } catch {}
  if (fs.existsSync(".env")) {
    const envText = fs.readFileSync(".env", "utf8");
    for (const line of envText.split(/\r?\n/)) {
      const match = line.match(/^\s*GEMINI_API_KEY\s*=\s*(.*)$/);
      if (match) {
        const val = match[1].trim().replace(/^['"]|['"]$/g, "");
        if (val) return true;
      }
    }
  }
  return false;
}

function checkPrereqsReport() {
  const py = hasCmd("python3", ["--version"]);
  const node = hasCmd("node", ["--version"]);
  const gh = hasCmd("gh", ["auth", "status"]);
  const key = hasGeminiKey();
  const ffmpeg = hasCmd("ffmpeg", ["-version"]);

  console.log("=== repo-walkthrough Prerequisites ===");
  console.log(`  • Python 3 (repo analyzer):          ${py ? "✅ installed" : "❌ missing"}`);
  console.log(`  • Node.js >= 20 (TTS & builder):     ${node ? "✅ installed (" + process.version + ")" : "❌ missing"}`);
  console.log(`  • GitHub CLI 'gh' (private repos):   ${gh ? "✅ authenticated" : "⚪ optional (not needed for local or public GitHub repos)"}`);
  console.log(`  • Gemini API Key (Despina TTS):      ${key ? "✅ available (env / macOS Keychain / .env)" : "⚪ optional for website (falls back to Web Speech), required for video"}`);
  console.log(`  • FFmpeg (MP4 video muxing):         ${ffmpeg ? "✅ installed" : "❌ missing (required only for '--mode video')"}`);
}

function spokenWeight(text = "") {
  let w = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1] || "";
    if ((ch === "." || ch === "!" || ch === "?" || ch === ";" || ch === ":") && /\s/.test(next)) {
      w += 12;
    } else if ((ch === "," || ch === "-") && /\s/.test(next)) {
      w += 6;
    } else if (/\s/.test(ch)) {
      w += 0.3;
    } else {
      w += 1.0;
    }
  }
  return w;
}

function computeSpokenOffset(narration = "", phrase = "") {
  if (!narration || !phrase) return 0;
  const idx = narration.toLowerCase().indexOf(phrase.toLowerCase());
  if (idx < 0) return -1;
  if (idx === 0) return 0;
  const total = Math.max(1, spokenWeight(narration));
  const prefix = spokenWeight(narration.slice(0, idx));
  return Number((prefix / total).toFixed(2));
}

function validateWalkthroughData(data, fileLabel) {
  const errors = [];
  const warnings = [];

  if (!data || typeof data !== "object") {
    throw new Error(`${fileLabel}: window.WALKTHROUGH_DATA (or window.ADK_DATA) is missing.`);
  }
  if (!Array.isArray(data.layers) || data.layers.length === 0) {
    errors.push("Missing 'layers' array.");
  }
  if (!Array.isArray(data.nodes) || data.nodes.length === 0) {
    errors.push("Missing 'nodes' array.");
  }
  if (!Array.isArray(data.edges)) {
    errors.push("Missing 'edges' array.");
  }
  if (!Array.isArray(data.walkthrough) || data.walkthrough.length === 0) {
    errors.push("Missing 'walkthrough' steps array.");
  }
  if (errors.length) {
    throw new Error(`${fileLabel} validation failed:\n  - ${errors.join("\n  - ")}`);
  }

  const layerIds = new Set(data.layers.map((l) => l.id));
  const nodeById = new Map();

  for (const n of data.nodes) {
    if (!n.id || !n.label || !n.path) {
      errors.push(`Node ${JSON.stringify(n.id || n.label)} is missing 'id', 'label', or 'path'.`);
    }
    if (!layerIds.has(n.layer)) {
      errors.push(`Node '${n.id}' references unknown layer '${n.layer}'.`);
    }
    if (typeof n.x !== "number" || typeof n.y !== "number" || typeof n.w !== "number" || typeof n.h !== "number") {
      errors.push(`Node '${n.id}' is missing numeric x, y, w, h coordinates.`);
    } else if (n.x < 195) {
      warnings.push(
        `Node '${n.id}' has x=${n.x} (< 200), which may overlap left layer headers (x: 14..190).`
      );
    }
    nodeById.set(n.id, n);
  }

  // Check bounding-box overlap between nodes
  const nodes = data.nodes;
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];
      const overlapX = a.x < b.x + b.w && a.x + a.w > b.x;
      const overlapY = a.y < b.y + b.h && a.y + a.h > b.y;
      if (overlapX && overlapY) {
        errors.push(`Nodes '${a.id}' and '${b.id}' overlap on the SVG canvas.`);
      }
    }
  }

  const edgeIds = new Set();
  for (const e of data.edges) {
    if (!nodeById.has(e.from)) errors.push(`Edge '${e.id}' has unknown 'from' node '${e.from}'.`);
    if (!nodeById.has(e.to)) errors.push(`Edge '${e.id}' has unknown 'to' node '${e.to}'.`);
    edgeIds.add(e.id);
  }

  for (const st of data.walkthrough) {
    if (!nodeById.has(st.focusNode)) {
      errors.push(`Step ${st.step} has unknown focusNode '${st.focusNode}'.`);
    }
    for (const nid of st.activeNodes || []) {
      if (!nodeById.has(nid)) {
        errors.push(`Step ${st.step} activeNodes references unknown node '${nid}'.`);
      }
    }
    for (const eid of st.activeEdges || []) {
      if (!edgeIds.has(eid)) {
        errors.push(`Step ${st.step} activeEdges references unknown edge '${eid}'.`);
      }
    }
    let prevAt = -1;
    let prevCharIdx = -1;
    for (const c of st.cues || []) {
      for (const cn of c.nodes || []) {
        if (!nodeById.has(cn)) {
          errors.push(`Step ${st.step} references unknown cue node '${cn}'.`);
        }
      }
      if (c.focus && !nodeById.has(c.focus)) {
        errors.push(`Step ${st.step} references unknown cue focus node '${c.focus}'.`);
      }
      if (c.phrase && st.narration) {
        const charIdx = st.narration.toLowerCase().indexOf(c.phrase.toLowerCase());
        if (charIdx < 0) {
          errors.push(`Step ${st.step} cue phrase "${c.phrase}" was not found in step narration.`);
        } else {
          if (charIdx < prevCharIdx) {
            errors.push(`Step ${st.step} cue phrase "${c.phrase}" appears earlier in narration than the previous cue.`);
          }
          prevCharIdx = charIdx;
          const expectedAt = computeSpokenOffset(st.narration, c.phrase);
          if (typeof c.at !== "number") {
            c.at = expectedAt;
          } else if (Math.abs(c.at - expectedAt) > 0.08) {
            errors.push(
              `Step ${st.step} cue phrase "${c.phrase}" has at=${c.at}, which drifts from spoken offset ${expectedAt} by >0.08.`
            );
          }
        }
      }
      if (typeof c.at === "number") {
        if (c.at < 0 || c.at >= 1) {
          errors.push(`Step ${st.step} cue has out-of-range at=${c.at} (expected 0.0 <= at < 1.0).`);
        } else if (c.at < prevAt) {
          errors.push(`Step ${st.step} cues are not in chronological order (${c.at} < ${prevAt}).`);
        }
        prevAt = c.at;
      }
    }
    if (!st.summary || !st.narration) {
      errors.push(`Step ${st.step} is missing 'summary' or 'narration'.`);
    }
  }

  if (warnings.length) {
    for (const w of warnings) console.warn(`⚠️  ${w}`);
  }
  if (errors.length) {
    throw new Error(`${fileLabel} validation failed:\n  - ${errors.join("\n  - ")}`);
  }
  console.log(
    `✅ Validated ${fileLabel}: ${data.layers.length} layers, ${data.nodes.length} nodes, ${data.edges.length} edges, ${data.walkthrough.length} walkthrough steps (zero overlaps).`
  );
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.checkPrereqs) {
    checkPrereqsReport();
    return;
  }

  const repoRoot = path.resolve(import.meta.dirname, "..");
  const templateHtml = path.join(repoRoot, "web", "index.html");
  const dataFile = opts.dataFile || path.join(repoRoot, "web", "data-adk.js");

  if (!fs.existsSync(dataFile)) {
    throw new Error(`Data file not found: ${dataFile}`);
  }

  const sandbox = { window: {} };
  vm.runInNewContext(fs.readFileSync(dataFile, "utf8"), sandbox);
  const data = sandbox.window.WALKTHROUGH_DATA || sandbox.window.ADK_DATA;
  validateWalkthroughData(data, path.basename(dataFile));

  const outDir = opts.outDir || path.dirname(dataFile);
  fs.mkdirSync(outDir, { recursive: true });

  const targetHtml = path.join(outDir, "index.html");
  if (path.resolve(templateHtml) !== path.resolve(targetHtml)) {
    const htmlText = fs
      .readFileSync(templateHtml, "utf8")
      .replace('<script src="data-adk.js"></script>\n', "");
    fs.writeFileSync(targetHtml, htmlText, "utf8");
  }
  const targetDataJs = path.join(outDir, "data.js");
  if (
    path.resolve(dataFile) !== path.resolve(targetDataJs) &&
    path.basename(dataFile) !== "data-adk.js"
  ) {
    fs.copyFileSync(dataFile, targetDataJs);
  }

  console.log(`🌐 Website ready at: ${targetHtml}`);

  // Synthesize TTS audio if requested or if in video mode
  const shouldRunTts =
    opts.mode === "video" || (!opts.noTts && hasGeminiKey());

  if (shouldRunTts) {
    execFileSync(
      process.execPath,
      [
        path.join(repoRoot, "scripts", "generate_live_audio.mjs"),
        "--data",
        dataFile,
        "--out-dir",
        path.join(outDir, "audio"),
      ],
      { stdio: "inherit" }
    );
  } else {
    console.log("ℹ️  Skipping Gemini TTS generation (website will use browser SpeechSynthesis fallback).");
  }

  if (opts.mode === "video") {
    const rawSlug = (data.subpath ? (data.title || data.subpath) : (data.repo || data.title || "repo"));
    const slug = rawSlug.replace(/[^A-Za-z0-9_-]+/g, "-").replace(/^-|-$/g, "");
    const outMp4 = opts.outVideo || path.join(outDir, `${slug}-walkthrough.mp4`);
    const renderArgs = [
      path.join(repoRoot, "scripts", "render_video.mjs"),
      "--dir",
      outDir,
      "--out",
      outMp4,
    ];
    if (opts.speed) {
      renderArgs.push("--speed", String(opts.speed));
    }
    if (path.resolve(outDir) === path.resolve(path.join(repoRoot, "web")) && path.basename(dataFile) !== "data-adk.js") {
      renderArgs.push("--data", path.basename(dataFile));
    }
    execFileSync(process.execPath, renderArgs, { stdio: "inherit" });
    if (opts.open) {
      execFileSync("open", [outMp4], { stdio: "ignore" });
    }
  }

  if (opts.open) {
    execFileSync("open", [targetHtml], { stdio: "ignore" });
  }
}

export { computeSpokenOffset, parseArgs, spokenWeight, validateWalkthroughData };

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(import.meta.filename)) {
  main().catch((err) => {
    console.error("❌ Build failed:", err.message);
    process.exit(1);
  });
}
