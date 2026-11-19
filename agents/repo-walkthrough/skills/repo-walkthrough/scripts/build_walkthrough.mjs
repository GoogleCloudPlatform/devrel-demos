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
 *   node skills/repo-walkthrough/scripts/build_walkthrough.mjs --check-prereqs
 *   node skills/repo-walkthrough/scripts/build_walkthrough.mjs --data <path/to/data.js> [--out-dir <dir>] [--mode website|video] [--no-tts] [--open]
 */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

import { resolveGeminiApiKey } from "./generate_live_audio.mjs";
import { checkFfmpeg, launchChromium, loadPlaywright } from "./render_video.mjs";

const USAGE_TEXT = `Usage:
  node skills/repo-walkthrough/scripts/build_walkthrough.mjs --check-prereqs
  node skills/repo-walkthrough/scripts/build_walkthrough.mjs --data <path/to/data.js> [options]

Options:
  --data <file>        Path to data.js containing window.WALKTHROUGH_DATA
  --out-dir <dir>      Target website output directory (defaults to dirname of --data)
  --out-video <file>   Output MP4 file path when --mode video is used
  --mode <mode>        Output mode: 'website' (default) or 'video'
  --website            Shorthand for --mode website
  --video              Shorthand for --mode video
  --speed <number>     Video playback speed between 0.5 and 2.0 (default: 1.0)
  --no-tts             Skip Gemini TTS synthesis in website mode (uses browser speech fallback)
  --open               Open the built index.html (and MP4 in video mode) in the default viewer
  --check-prereqs      Check Python 3, Node.js >= 20.11, Gemini API key, ffmpeg, and Playwright
  -h, --help           Show this help message and exit
`;

function isPluginOrRepoRoot(dir) {
  return (
    fs.existsSync(path.join(dir, "plugin.json")) ||
    fs.existsSync(path.join(dir, "web", "index.html")) ||
    fs.existsSync(path.join(dir, "web", "index.tmpl")) ||
    fs.existsSync(path.join(dir, "web", "data-adk.js"))
  );
}

function resolveRepoRoot(scriptDir = import.meta.dirname) {
  const pluginCandidate = path.resolve(scriptDir, "../../..");
  const directCandidate = path.resolve(scriptDir, "..");
  if (isPluginOrRepoRoot(pluginCandidate)) {
    return pluginCandidate;
  }
  if (isPluginOrRepoRoot(directCandidate)) {
    return directCandidate;
  }
  return directCandidate;
}

function resolveTemplatePath(repoRoot, scriptDir = import.meta.dirname) {
  const candidates = [
    path.join(repoRoot, "skills", "repo-walkthrough", "assets", "index.tmpl"),
    path.join(repoRoot, "assets", "index.tmpl"),
    path.join(repoRoot, "web", "index.html"),
    path.join(repoRoot, "web", "index.tmpl"),
    path.join(path.resolve(scriptDir, ".."), "assets", "index.tmpl"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return candidates[0];
}

function resolveDataFile(opts, _repoRoot, _cwd = process.cwd()) {
  if (opts.dataFile) return opts.dataFile;
  if (opts.outDir) {
    const outDataCandidate = path.join(opts.outDir, "data.js");
    if (fs.existsSync(outDataCandidate)) {
      return outDataCandidate;
    }
  }
  return null;
}

function resolveSiblingScript(repoRoot, scriptName, scriptDir = import.meta.dirname) {
  const localCandidate = path.join(scriptDir, scriptName);
  if (fs.existsSync(localCandidate)) return localCandidate;
  const skillCandidate = path.join(
    repoRoot,
    "skills",
    "repo-walkthrough",
    "scripts",
    scriptName
  );
  if (fs.existsSync(skillCandidate)) return skillCandidate;
  return path.join(repoRoot, "scripts", scriptName);
}

function requireOptionValue(argv, index, flag, allowLeadingDash = false) {
  const val = argv[index + 1];
  if (val === undefined || val === "" || (!allowLeadingDash && val.startsWith("-"))) {
    throw new Error(`Option ${flag} requires a value. Pass --help for usage.`);
  }
  return val;
}

function parseArgs(argv) {
  const opts = {
    dataFile: null,
    outDir: null,
    outVideo: null,
    mode: "website",
    speed: null,
    noTts: false,
    open: false,
    checkPrereqs: false,
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-h" || a === "--help") {
      opts.help = true;
    } else if (a === "--data") {
      opts.dataFile = path.resolve(requireOptionValue(argv, i++, "--data"));
    } else if (a === "--out-dir") {
      opts.outDir = path.resolve(requireOptionValue(argv, i++, "--out-dir"));
    } else if (a === "--out-video") {
      opts.outVideo = path.resolve(requireOptionValue(argv, i++, "--out-video"));
    } else if (a === "--mode") {
      opts.mode = requireOptionValue(argv, i++, "--mode").toLowerCase();
    } else if (a === "--speed") {
      opts.speed = requireOptionValue(argv, i++, "--speed", true);
    } else if (a === "--video") {
      opts.mode = "video";
    } else if (a === "--website") {
      opts.mode = "website";
    } else if (a === "--no-tts") {
      opts.noTts = true;
    } else if (a === "--open") {
      opts.open = true;
    } else if (a === "--check-prereqs") {
      opts.checkPrereqs = true;
    } else {
      throw new Error(`Unknown option: ${a}. Pass --help for usage.`);
    }
  }
  if (opts.help) {
    return opts;
  }
  if (opts.mode !== "website" && opts.mode !== "video") {
    throw new Error(`Invalid --mode '${opts.mode}'. Expected 'website' or 'video'.`);
  }
  if (opts.speed !== null) {
    const s = Number(opts.speed);
    if (!Number.isFinite(s) || !(s >= 0.5 && s <= 2.0)) {
      throw new Error("--speed must be between 0.5 and 2.0");
    }
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

const PY3_CHECK_CODE = "import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)";

function detectPythonCmd(platform = process.platform, probe = hasCmd) {
  if (probe("python3", ["-c", PY3_CHECK_CODE])) {
    return { cmd: "python3", args: [] };
  }
  if (platform === "win32" && probe("py", ["-3", "-c", PY3_CHECK_CODE])) {
    return { cmd: "py", args: ["-3"] };
  }
  if (probe("python", ["-c", PY3_CHECK_CODE])) {
    return { cmd: "python", args: [] };
  }
  if (platform !== "win32" && probe("py", ["-3", "-c", PY3_CHECK_CODE])) {
    return { cmd: "py", args: ["-3"] };
  }
  return null;
}

function hasSupportedNodeVersion(versionStr = process.versions.node) {
  const [major, minor] = String(versionStr || "0.0.0")
    .split(".")
    .map((x) => parseInt(x, 10) || 0);
  return major > 20 || (major === 20 && minor >= 11);
}

function hasGeminiKey(repoRoot = resolveRepoRoot(import.meta.dirname), options = {}) {
  try {
    return Boolean(resolveGeminiApiKey(repoRoot, options));
  } catch {
    return false;
  }
}

function hasPlaywrightInstalled() {
  try {
    loadPlaywright();
    return true;
  } catch {
    return false;
  }
}

async function verifyVideoPrerequisites() {
  checkFfmpeg();
  const { chromium } = loadPlaywright();
  const browser = await launchChromium(chromium);
  await browser.close();
}

function openTarget(targetPath, platform = process.platform, runner = execFileSync) {
  if (!targetPath || String(targetPath).toLowerCase().endsWith(".tmpl")) {
    return false;
  }
  try {
    if (platform === "darwin") {
      runner("open", [targetPath], { stdio: "ignore" });
    } else if (platform === "win32") {
      runner("rundll32.exe", ["url.dll,FileProtocolHandler", targetPath], { stdio: "ignore" });
    } else {
      runner("xdg-open", [targetPath], { stdio: "ignore" });
    }
    return true;
  } catch {
    console.log(`ℹ️  Could not auto-open in this environment. Open manually: ${targetPath}`);
    return false;
  }
}

function checkPrereqsReport() {
  const pyInfo = detectPythonCmd();
  const nodeOk = hasSupportedNodeVersion();
  const gh = hasCmd("gh", ["auth", "status"]);
  const key = hasGeminiKey();
  const ffmpeg = hasCmd("ffmpeg", ["-version"]);
  const pw = hasPlaywrightInstalled();
  const pyLabel = pyInfo ? [pyInfo.cmd, ...pyInfo.args].join(" ") : "";

  console.log("=== repo-walkthrough Prerequisites ===");
  console.log(
    `  • Python 3 (repo analyzer):          ${pyInfo ? `✅ installed (${pyLabel})` : "❌ missing"}`
  );
  console.log(
    `  • Node.js >= 20.11 (TTS & builder):  ${nodeOk ? `✅ installed (${process.version})` : `❌ unsupported (${process.version}, need >= 20.11)`}`
  );
  console.log(
    `  • GitHub CLI 'gh' (private repos):   ${gh ? "✅ authenticated" : "⚪ optional (not needed for local or public GitHub repos)"}`
  );
  console.log(
    `  • Gemini API Key (Despina TTS):      ${key ? "✅ available (env / keychain / .env)" : "⚪ optional for website (falls back to Web Speech), required for video"}`
  );
  console.log(
    `  • FFmpeg (MP4 video muxing):         ${ffmpeg ? "✅ installed" : "❌ missing (required only for '--mode video')"}`
  );
  console.log(
    `  • Playwright (Chrome/Edge video):    ${pw ? "✅ installed" : "⚪ optional for website, required for '--mode video'"}`
  );
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
    if (
      typeof n.x !== "number" ||
      typeof n.y !== "number" ||
      typeof n.w !== "number" ||
      typeof n.h !== "number"
    ) {
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
    if (!Number.isInteger(st.step) || st.step < 1) {
      errors.push(`Step '${st.step}' must be an integer >= 1.`);
    }
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
            errors.push(
              `Step ${st.step} cue phrase "${c.phrase}" appears earlier in narration than the previous cue.`
            );
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
  if (opts.help) {
    process.stdout.write(USAGE_TEXT);
    return;
  }
  if (opts.checkPrereqs) {
    checkPrereqsReport();
    return;
  }

  const repoRoot = resolveRepoRoot(import.meta.dirname);
  const templateHtml = resolveTemplatePath(repoRoot, import.meta.dirname);
  if (!fs.existsSync(templateHtml)) {
    throw new Error(`Viewer template not found: ${templateHtml}`);
  }
  const dataFile = resolveDataFile(opts, repoRoot);

  if (!dataFile) {
    throw new Error(
      "Missing --data <path/to/data.js>. Pass --data <path/to/data.js> (or --help for usage)."
    );
  }
  if (!fs.existsSync(dataFile)) {
    throw new Error(`Data file not found: ${dataFile}`);
  }

  const windowObj = Object.create(null);
  const sandbox = Object.assign(Object.create(null), { window: windowObj });
  vm.runInNewContext(fs.readFileSync(dataFile, "utf8"), sandbox, { timeout: 2000 });
  const data = windowObj.WALKTHROUGH_DATA || windowObj.ADK_DATA;
  validateWalkthroughData(data, path.basename(dataFile));

  // Fail fast on ffmpeg + Playwright/browser BEFORE running paid Gemini TTS in video mode
  if (opts.mode === "video") {
    await verifyVideoPrerequisites();
  }

  const outDir = opts.outDir || path.dirname(dataFile);
  fs.mkdirSync(outDir, { recursive: true });

  const targetHtml = path.join(outDir, "index.html");
  if (path.resolve(templateHtml) !== path.resolve(targetHtml)) {
    const htmlText = fs
      .readFileSync(templateHtml, "utf8")
      .replace(/<script src="data-adk\.js"><\/script>\r?\n?/, "");
    fs.writeFileSync(targetHtml, htmlText, "utf8");
  }
  const targetDataJs = path.join(outDir, "data.js");
  if (path.resolve(dataFile) !== path.resolve(targetDataJs)) {
    fs.copyFileSync(dataFile, targetDataJs);
  }

  console.log(`🌐 Website ready at: ${targetHtml}`);

  // Synthesize TTS audio if requested or if in video mode
  const shouldRunTts =
    opts.mode === "video" || (!opts.noTts && hasGeminiKey(repoRoot));

  if (shouldRunTts) {
    execFileSync(
      process.execPath,
      [
        resolveSiblingScript(repoRoot, "generate_live_audio.mjs", import.meta.dirname),
        "--data",
        targetDataJs,
        "--out-dir",
        path.join(outDir, "audio"),
      ],
      { stdio: "inherit" }
    );
  } else {
    console.log(
      "ℹ️  Skipping Gemini TTS generation (website will use browser SpeechSynthesis fallback)."
    );
  }

  if (opts.mode === "video") {
    const rawSlug = data.subpath
      ? data.title || data.subpath
      : data.repo || data.title || "repo";
    const slug = rawSlug.replace(/[^A-Za-z0-9_-]+/g, "-").replace(/^-|-$/g, "");
    const outMp4 = opts.outVideo || path.join(outDir, `${slug}-walkthrough.mp4`);
    const renderArgs = [
      resolveSiblingScript(repoRoot, "render_video.mjs", import.meta.dirname),
      "--dir",
      outDir,
      "--out",
      outMp4,
    ];
    if (opts.speed) {
      renderArgs.push("--speed", String(opts.speed));
    }
    execFileSync(process.execPath, renderArgs, { stdio: "inherit" });
    if (opts.open) {
      openTarget(outMp4);
    }
  }

  if (opts.open) {
    openTarget(targetHtml);
  }
}

export {
  computeSpokenOffset,
  detectPythonCmd,
  hasGeminiKey,
  hasSupportedNodeVersion,
  openTarget,
  parseArgs,
  resolveDataFile,
  resolveRepoRoot,
  resolveTemplatePath,
  spokenWeight,
  validateWalkthroughData,
};

function isExecutedDirectly(argv1 = process.argv[1], metaFilename = import.meta.filename) {
  if (!argv1) return false;
  try {
    return fs.realpathSync(argv1) === fs.realpathSync(metaFilename);
  } catch {
    return path.resolve(argv1) === path.resolve(metaFilename);
  }
}

if (isExecutedDirectly()) {
  main().catch((err) => {
    console.error("❌ Build failed:", err.message);
    process.exit(1);
  });
}
