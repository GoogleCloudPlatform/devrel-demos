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
 * Render a smooth animated MP4 walkthrough video directly from a built
 * `index.html?video=1` + `audio/manifest.json` site directory using headless
 * Chromium/Chrome/Edge and ffmpeg.
 *
 * Usage:
 *   node skills/repo-walkthrough/scripts/render_video.mjs --dir <site-dir> [--out <out.mp4>] [--fps 12] [--speed 1.0]
 *
 * Unlike static slide concatenation, this renders every frame in full-width video mode (`?video=1`):
 *   - Hides the right-hand code inspector sidebar so the layered graph fills 1440x900
 *   - Shows the full layered overview with all left section headers on Step 1
 *   - Smooth cubic ease-in-out camera pan & zoom transitions on Steps 2..N
 *   - Continuously moving bottom timeline status bar from Step 1 -> Step N
 *   - Single light-blue (#8AB4F8) node spotlighting (`cues`) synced to spoken narration
 *   - Flowing dashed SVG arrow connectors
 */

import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);

const USAGE_TEXT = `Usage:
  node skills/repo-walkthrough/scripts/render_video.mjs --dir <site-dir> [options]

Options:
  --dir <dir>        Built website directory containing index.html, data.js, and audio/manifest.json
  --out <file.mp4>   Output MP4 file path (defaults to <site-dir>/walkthrough.mp4)
  --fps <number>     Frames per second between 1 and 60 (default: 12, or VIDEO_FPS)
  --speed <number>   Playback speed multiplier between 0.5 and 2.0 (default: 1.0, or VIDEO_SPEED)
  -h, --help         Show this help message and exit
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

function requirePathValue(argv, index, flag) {
  const val = argv[index + 1];
  if (val === undefined || val === "" || val.startsWith("-")) {
    throw new Error(`Option ${flag} requires a value. Pass --help for usage.`);
  }
  return val;
}

function requireNumericValue(argv, index, flag) {
  const val = argv[index + 1];
  if (val === undefined || val === "") {
    throw new Error(`Option ${flag} requires a numeric value. Pass --help for usage.`);
  }
  return Number(val);
}

function parseArgs(argv) {
  const opts = {
    dir: null,
    out: null,
    fps: Number(process.env.VIDEO_FPS || 12),
    speed: Number(process.env.VIDEO_SPEED || 1.0),
    help: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-h" || a === "--help") {
      opts.help = true;
    } else if (a === "--dir") {
      opts.dir = path.resolve(requirePathValue(argv, i++, "--dir"));
    } else if (a === "--out") {
      opts.out = path.resolve(requirePathValue(argv, i++, "--out"));
    } else if (a === "--fps") {
      opts.fps = requireNumericValue(argv, i++, "--fps");
    } else if (a === "--speed") {
      opts.speed = requireNumericValue(argv, i++, "--speed");
    } else {
      throw new Error(`Unknown option: ${a}. Pass --help for usage.`);
    }
  }
  if (opts.help) {
    return opts;
  }
  if (!Number.isFinite(opts.fps) || opts.fps < 1 || opts.fps > 60) {
    throw new Error("--fps must be between 1 and 60");
  }
  if (!Number.isFinite(opts.speed) || !(opts.speed >= 0.5 && opts.speed <= 2.0)) {
    throw new Error("--speed must be between 0.5 and 2.0");
  }
  return opts;
}

function checkFfmpeg() {
  try {
    execFileSync("ffmpeg", ["-version"], { stdio: "ignore" });
  } catch {
    throw new Error(
      "ffmpeg is required for video rendering but was not found on PATH. Install it via 'brew install ffmpeg' (macOS), 'apt install ffmpeg' (Linux), or 'winget install Gyan.FFmpeg' (Windows)."
    );
  }
}

function getPlaywrightSearchRoots({
  platform = process.platform,
  env = process.env,
  homedir = os.homedir(),
} = {}) {
  const joinPath = platform === "win32" ? path.win32.join : path.join;
  const npmCmd = platform === "win32" ? "npm.cmd" : "npm";
  const npxBases = [joinPath(homedir, ".npm", "_npx")];
  if (env.LOCALAPPDATA) {
    npxBases.push(joinPath(env.LOCALAPPDATA, "npm-cache", "_npx"));
  }
  if (env.APPDATA) {
    npxBases.push(joinPath(env.APPDATA, "npm-cache", "_npx"));
  }
  return { npmCmd, npxBases };
}

function queryGlobalNpmRoot(platform = process.platform, npmCmd = "npm") {
  try {
    if (platform === "win32") {
      return execFileSync("cmd.exe", ["/d", "/s", "/c", `${npmCmd} root -g`], {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "ignore"],
      }).trim();
    }
    return execFileSync(npmCmd, ["root", "-g"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
  } catch {
    return "";
  }
}

function loadPlaywright() {
  // Never resolve from process.cwd(): the cwd may be an untrusted clone with committed
  // node_modules. Bare names resolve relative to this script (plugin or skill install) only.
  const candidates = [];
  if (process.env.PLAYWRIGHT_MODULE_PATH && process.env.PLAYWRIGHT_MODULE_PATH.trim()) {
    candidates.push(path.resolve(process.env.PLAYWRIGHT_MODULE_PATH.trim()));
  }
  candidates.push("playwright-core", "playwright");
  const { npmCmd, npxBases } = getPlaywrightSearchRoots();

  const globalRoot = queryGlobalNpmRoot(process.platform, npmCmd);
  if (globalRoot) {
    candidates.push(
      path.join(globalRoot, "playwright-core"),
      path.join(globalRoot, "playwright")
    );
  }

  for (const npxBase of npxBases) {
    if (fs.existsSync(npxBase)) {
      for (const entry of fs.readdirSync(npxBase)) {
        const pCore = path.join(npxBase, entry, "node_modules", "playwright-core");
        const pFull = path.join(npxBase, entry, "node_modules", "playwright");
        if (fs.existsSync(pCore)) candidates.push(pCore);
        if (fs.existsSync(pFull)) candidates.push(pFull);
      }
    }
  }

  for (const c of candidates) {
    try {
      return require(c);
    } catch {}
  }
  throw new Error(
    "Could not load 'playwright-core' or 'playwright'. Install it with 'npm install -g playwright-core' or 'npx playwright-core --version'."
  );
}

function formatFfmpegConcatEntry(filePath) {
  const normalized = String(filePath).replace(/\\/g, "/").replace(/'/g, "'\\''");
  return `file '${normalized}'`;
}

async function launchChromium(chromium, platform = process.platform) {
  const attempts = [{ headless: true, channel: "chrome" }, { headless: true }];
  if (platform === "win32") {
    attempts.push({ headless: true, channel: "msedge" });
  }
  let lastErr = null;
  for (const launchOpts of attempts) {
    try {
      return await chromium.launch(launchOpts);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("Could not launch Chromium, Chrome, or Edge");
}

function resolveContainedAudioPath(webDir, relFile) {
  const cleanRel = String(relFile || "").trim();
  if (!cleanRel) {
    throw new Error("Audio manifest entry is missing 'file'.");
  }
  const resolvedWeb = path.resolve(webDir);
  const resolvedWav = path.resolve(resolvedWeb, cleanRel);
  const relFromWeb = path.relative(resolvedWeb, resolvedWav);
  if (relFromWeb.startsWith("..") || path.isAbsolute(relFromWeb)) {
    throw new Error(`Audio manifest entry '${cleanRel}' resolves outside site directory.`);
  }
  return resolvedWav;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    process.stdout.write(USAGE_TEXT);
    return;
  }

  checkFfmpeg();

  const FPS = opts.fps;
  const SPEED = opts.speed;
  const TRANSITION_SEC = 0.75 / SPEED;
  const GAP_SEC = 0.45;

  const repoRoot = resolveRepoRoot(import.meta.dirname);
  const webDir = path.resolve(opts.dir || path.join(repoRoot, "web"));
  const htmlPath = path.join(webDir, "index.html");
  if (!fs.existsSync(htmlPath)) {
    throw new Error(
      `Missing built website ${htmlPath}. Build the end-product website first with 'node skills/repo-walkthrough/scripts/build_walkthrough.mjs --data <path/to/data.js> --out-dir <dir>' (never open raw .tmpl files directly).`
    );
  }

  const audioDir = path.join(webDir, "audio");
  const manifestPath = path.join(audioDir, "manifest.json");
  if (!fs.existsSync(manifestPath)) {
    throw new Error(
      `Missing ${manifestPath}. Run 'node skills/repo-walkthrough/scripts/generate_live_audio.mjs --data <path/to/data.js>' first.`
    );
  }

  const outMp4 = opts.out || path.join(webDir, "walkthrough.mp4");
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  if (!Array.isArray(manifest) || manifest.length === 0) {
    throw new Error(`Audio manifest ${manifestPath} is empty.`);
  }
  const totalSteps = manifest.length;

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "repo-walkthrough-video-"));
  let browser = null;
  let ff = null;

  try {
    // 1. Build a single concatenated WAV audio track with a 0.45s gap between steps
    const fullAudioWav = path.join(tmpDir, "full-audio.wav");
    const silenceWav = path.join(tmpDir, "silence.wav");
    const concatListTxt = path.join(tmpDir, "audio-concat.txt");

    execFileSync(
      "ffmpeg",
      [
        "-y",
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=24000:cl=mono",
        "-t",
        String(GAP_SEC),
        "-c:a",
        "pcm_s16le",
        silenceWav,
      ],
      { stdio: "ignore" }
    );

    const concatLines = [];
    const stepTimings = [];
    let cursorSec = 0;

    for (let i = 0; i < totalSteps; i++) {
      const item = manifest[i];
      const wavPath = resolveContainedAudioPath(webDir, item.file);
      if (!fs.existsSync(wavPath)) {
        throw new Error(`Missing step audio WAV file: ${wavPath}`);
      }
      const dur = Number(item.durationSec) / SPEED;
      const segDur = dur + (i < totalSteps - 1 ? GAP_SEC / SPEED : 0.25 / SPEED);

      stepTimings.push({
        stepIndex: i,
        prevStepIndex: Math.max(0, i - 1),
        startSec: cursorSec,
        audioDurSec: dur,
        endSec: cursorSec + segDur,
      });
      cursorSec += segDur;

      concatLines.push(formatFfmpegConcatEntry(wavPath));
      if (i < totalSteps - 1) {
        concatLines.push(formatFfmpegConcatEntry(silenceWav));
      }
    }

    fs.writeFileSync(concatListTxt, concatLines.join("\n") + "\n");
    const concatFfmpegArgs = ["-y", "-f", "concat", "-safe", "0", "-i", concatListTxt];
    if (SPEED !== 1) {
      concatFfmpegArgs.push("-filter:a", `atempo=${SPEED}`);
    }
    concatFfmpegArgs.push("-c:a", "pcm_s16le", fullAudioWav);
    execFileSync("ffmpeg", concatFfmpegArgs, { stdio: "ignore" });

    const totalDurationSec = cursorSec;
    const totalFrames = Math.ceil(totalDurationSec * FPS);

    console.log(
      `🎬 Rendering ${totalFrames} animated frames (${totalDurationSec.toFixed(1)}s @ ${FPS}fps, speed ${SPEED}x) -> ${outMp4}...`
    );

    // 2. Launch headless Chrome (or Edge on Windows) and open built index.html?video=1
    const { chromium } = loadPlaywright();
    browser = await launchChromium(chromium);
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      deviceScaleFactor: 1,
    });
    const page = await context.newPage();
    const pageUrl = `${pathToFileURL(htmlPath).href}?video=1`;
    await page.goto(pageUrl, {
      waitUntil: "networkidle",
    });
    await page.evaluate(async () => {
      if (document.fonts && document.fonts.ready) {
        await document.fonts.ready;
      }
    });

    // Apply acoustically aligned cue timestamps from manifest.json if available
    await page.evaluate((manifestItems) => {
      const d = window.WALKTHROUGH_DATA || window.ADK_DATA;
      if (!d || !Array.isArray(d.walkthrough)) return;
      for (let i = 0; i < manifestItems.length; i++) {
        if (Array.isArray(manifestItems[i]?.alignedCues) && d.walkthrough[i]) {
          d.walkthrough[i].cues = manifestItems[i].alignedCues;
        }
      }
    }, manifest);

    // Disable CSS transitions during deterministic frame stepping so every frame is exact
    await page.addStyleTag({
      content: `
        .node-group, .node-rect, .edge-group, .edge-path, .tl-mark {
          transition: none !important;
        }
      `,
    });

    const cdp = await context.newCDPSession(page);

    // 3. Spawn ffmpeg reading JPEG frames from stdin and muxing with fullAudioWav
    fs.mkdirSync(path.dirname(outMp4), { recursive: true });
    ff = spawn(
      "ffmpeg",
      [
        "-loglevel",
        "error",
        "-y",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-framerate",
        String(FPS),
        "-i",
        "-",
        "-i",
        fullAudioWav,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "fast",
        "-crf",
        "20",
        "-r",
        "30",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        outMp4,
      ],
      { stdio: ["pipe", "ignore", "inherit"] }
    );
    // Watch ffmpeg from the moment it spawns so a mid-stream exit can never strand the frame loop
    let ffExitInfo = null;
    const ffExited = new Promise((resolve) => {
      ff.once("error", (err) => {
        ffExitInfo ??= { error: err };
        resolve(ffExitInfo);
      });
      ff.once("close", (code, signal) => {
        ffExitInfo ??= { code, signal };
        resolve(ffExitInfo);
      });
    });
    const ffFailure = () => {
      const info = ffExitInfo || {};
      if (info.error) return new Error(`Failed to start ffmpeg: ${info.error.message}`);
      return new Error(`ffmpeg exited with ${info.signal ? `signal ${info.signal}` : `code ${info.code}`}`);
    };
    ff.stdin.on("error", (err) => {
      if (err.code !== "EPIPE") {
        console.error("ffmpeg stdin error:", err);
      }
    });

    for (let frame = 0; frame < totalFrames; frame++) {
      if (ffExitInfo) {
        throw ffFailure();
      }
      const t = frame / FPS;
      let activeSeg = stepTimings[stepTimings.length - 1];
      for (const seg of stepTimings) {
        if (t >= seg.startSec && t < seg.endSec) {
          activeSeg = seg;
          break;
        }
      }

      const localT = Math.max(0, t - activeSeg.startSec);
      const camTransition =
        activeSeg.stepIndex === 0 ? 1 : Math.min(1, localT / TRANSITION_SEC);
      const stepProgress = Math.min(1, localT / Math.max(0.1, activeSeg.audioDurSec));

      const startAnchor =
        totalSteps > 1 ? (100 * activeSeg.stepIndex) / (totalSteps - 1) : 0;
      const endAnchor =
        activeSeg.stepIndex < totalSteps - 1
          ? (100 * (activeSeg.stepIndex + 1)) / (totalSteps - 1)
          : 100;
      const segProgress = Math.min(
        1,
        localT / Math.max(0.1, activeSeg.endSec - activeSeg.startSec)
      );
      const timelinePct = startAnchor + (endAnchor - startAnchor) * segProgress;
      const dashOffset = -((t * 22) % 12).toFixed(2);

      await page.evaluate(
        (state) => {
          window.renderWalkthroughFrame(state);
        },
        {
          stepIndex: activeSeg.stepIndex,
          prevStepIndex: activeSeg.prevStepIndex,
          camTransition,
          stepProgress,
          timelinePct,
          dashOffset,
        }
      );

      const { data } = await cdp.send("Page.captureScreenshot", {
        format: "jpeg",
        quality: 90,
      });
      const buf = Buffer.from(data, "base64");
      const canWrite = ff.stdin.write(buf);
      if (!canWrite) {
        let onDrain = null;
        const drained = new Promise((resolve) => {
          onDrain = resolve;
          ff.stdin.once("drain", onDrain);
        });
        await Promise.race([drained, ffExited]);
        ff.stdin.off("drain", onDrain);
        if (ffExitInfo) {
          throw ffFailure();
        }
      }

      if (frame % (FPS * 10) === 0 || frame === totalFrames - 1) {
        process.stdout.write(
          `  • Frame ${frame + 1}/${totalFrames} (${((100 * (frame + 1)) / totalFrames).toFixed(0)}%)\n`
        );
      }
    }

    ff.stdin.end();
    const exitInfo = await ffExited;
    if (exitInfo.error || exitInfo.code !== 0) {
      throw ffFailure();
    }

    console.log(`✅ Rendered smooth animated walkthrough video to: ${outMp4}`);
  } finally {
    if (ff && ff.exitCode === null && ff.signalCode === null) {
      ff.stdin.destroy();
      ff.kill();
    }
    if (browser) {
      try {
        await browser.close();
      } catch {}
    }
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

export {
  checkFfmpeg,
  formatFfmpegConcatEntry,
  getPlaywrightSearchRoots,
  launchChromium,
  loadPlaywright,
  parseArgs,
  resolveContainedAudioPath,
  resolveRepoRoot,
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
    console.error("❌ Video render failed:", err.message || err);
    process.exit(1);
  });
}
