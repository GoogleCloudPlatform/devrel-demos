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
 * Render a smooth animated MP4 walkthrough video directly from `index.html?video=1`
 * + `audio/manifest.json` using headless Chromium and ffmpeg.
 *
 * Usage:
 *   node scripts/render_video.mjs [--dir <site-dir>] [--data <data.js>] [--out <out.mp4>] [--fps 12]
 *
 * Unlike static slide concatenation, this renders every frame in full-width video mode (`?video=1`):
 *   - Hides the right-hand code inspector sidebar so the 5-layer graph fills 1440x900
 *   - Shows the full 5-layer overview with all left section headers on Step 1
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

function parseArgs(argv) {
  const opts = {
    dir: null,
    data: null,
    out: null,
    fps: Number(process.env.VIDEO_FPS || 12),
    speed: Number(process.env.VIDEO_SPEED || 1.0),
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--dir" && argv[i + 1]) opts.dir = path.resolve(argv[++i]);
    else if (a === "--data" && argv[i + 1]) opts.data = argv[++i];
    else if (a === "--out" && argv[i + 1]) opts.out = path.resolve(argv[++i]);
    else if (a === "--fps" && argv[i + 1]) opts.fps = Number(argv[++i]);
    else if (a === "--speed" && argv[i + 1]) opts.speed = Number(argv[++i]);
  }
  if (!(opts.speed >= 0.5 && opts.speed <= 2.0)) {
    throw new Error("--speed must be between 0.5 and 2.0");
  }
  return opts;
}

function checkFfmpeg() {
  try {
    execFileSync("ffmpeg", ["-version"], { stdio: "ignore" });
  } catch {
    throw new Error(
      "ffmpeg is required for video rendering but was not found on PATH. Install it via 'brew install ffmpeg' (macOS) or 'apt install ffmpeg' (Linux)."
    );
  }
}

function loadPlaywright() {
  const candidates = ["playwright-core", "playwright"];

  try {
    const globalRoot = execFileSync("npm", ["root", "-g"], {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    if (globalRoot) {
      candidates.push(
        path.join(globalRoot, "playwright-core"),
        path.join(globalRoot, "playwright")
      );
    }
  } catch {}

  const npxBase = path.join(os.homedir(), ".npm", "_npx");
  if (fs.existsSync(npxBase)) {
    for (const entry of fs.readdirSync(npxBase)) {
      const pCore = path.join(npxBase, entry, "node_modules", "playwright-core");
      const pFull = path.join(npxBase, entry, "node_modules", "playwright");
      if (fs.existsSync(pCore)) candidates.push(pCore);
      if (fs.existsSync(pFull)) candidates.push(pFull);
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

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  checkFfmpeg();

  const FPS = opts.fps;
  const SPEED = opts.speed;
  const TRANSITION_SEC = 0.75 / SPEED;
  const GAP_SEC = 0.45;

  const repoRoot = path.resolve(import.meta.dirname, "..");
  const webDir = opts.dir || path.join(repoRoot, "web");
  const audioDir = path.join(webDir, "audio");
  const manifestPath = path.join(audioDir, "manifest.json");
  const defaultOutName = fs.existsSync(path.join(webDir, "data.js"))
    ? "walkthrough.mp4"
    : "adk-walkthrough.mp4";
  const outMp4 = opts.out || path.join(webDir, defaultOutName);

  if (!fs.existsSync(manifestPath)) {
    throw new Error(`Missing ${manifestPath}. Run 'node scripts/generate_live_audio.mjs' first.`);
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  const totalSteps = manifest.length;

  // 1. Build a single concatenated WAV audio track with a 0.45s gap between steps
  const tmpDir = path.join(audioDir, ".tmp-video");
  fs.mkdirSync(tmpDir, { recursive: true });
  const fullAudioWav = path.join(tmpDir, "full-audio.wav");
  const silenceWav = path.join(tmpDir, "silence.wav");
  const concatListTxt = path.join(tmpDir, "audio-concat.txt");

  execFileSync("ffmpeg", [
    "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
    "-t", String(GAP_SEC), "-c:a", "pcm_s16le", silenceWav
  ], { stdio: "ignore" });

  const concatLines = [];
  const stepTimings = [];
  let cursorSec = 0;

  for (let i = 0; i < totalSteps; i++) {
    const item = manifest[i];
    const wavPath = path.join(webDir, item.file);
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

    concatLines.push(`file '${wavPath}'`);
    if (i < totalSteps - 1) {
      concatLines.push(`file '${silenceWav}'`);
    }
  }

  fs.writeFileSync(concatListTxt, concatLines.join("\n") + "\n");
  const concatFfmpegArgs = [
    "-y", "-f", "concat", "-safe", "0", "-i", concatListTxt,
  ];
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

  // 2. Launch headless Chrome and open index.html?video=1
  const { chromium } = loadPlaywright();
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      channel: "chrome",
    });
  } catch {
    browser = await chromium.launch({ headless: true });
  }
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  const query = new URLSearchParams({ video: "1" });
  if (opts.data) query.set("data", opts.data);
  const pageUrl = `${pathToFileURL(path.join(webDir, "index.html")).href}?${query.toString()}`;
  await page.goto(pageUrl, {
    waitUntil: "networkidle",
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
  const ff = spawn(
    "ffmpeg",
    [
      "-y",
      "-f", "image2pipe",
      "-vcodec", "mjpeg",
      "-framerate", String(FPS),
      "-i", "-",
      "-i", fullAudioWav,
      "-c:v", "libx264",
      "-pix_fmt", "yuv420p",
      "-preset", "fast",
      "-crf", "20",
      "-r", "30",
      "-c:a", "aac",
      "-b:a", "192k",
      "-shortest",
      "-movflags", "+faststart",
      outMp4,
    ],
    { stdio: ["pipe", "ignore", "ignore"] }
  );

  for (let frame = 0; frame < totalFrames; frame++) {
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
      activeSeg.stepIndex === 0
        ? 1
        : Math.min(1, localT / TRANSITION_SEC);
    const stepProgress = Math.min(1, localT / Math.max(0.1, activeSeg.audioDurSec));

    const startAnchor = totalSteps > 1 ? (100 * activeSeg.stepIndex) / (totalSteps - 1) : 0;
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

    await page.evaluate((state) => {
      window.renderWalkthroughFrame(state);
    }, {
      stepIndex: activeSeg.stepIndex,
      prevStepIndex: activeSeg.prevStepIndex,
      camTransition,
      stepProgress,
      timelinePct,
      dashOffset,
    });

    const { data } = await cdp.send("Page.captureScreenshot", {
      format: "jpeg",
      quality: 90,
    });
    const buf = Buffer.from(data, "base64");
    const canWrite = ff.stdin.write(buf);
    if (!canWrite) {
      await new Promise((resolve) => ff.stdin.once("drain", resolve));
    }

    if (frame % (FPS * 10) === 0 || frame === totalFrames - 1) {
      process.stdout.write(
        `  • Frame ${frame + 1}/${totalFrames} (${((100 * (frame + 1)) / totalFrames).toFixed(0)}%)\n`
      );
    }
  }

  ff.stdin.end();
  await new Promise((resolve, reject) => {
    ff.on("close", (code) =>
      code === 0 ? resolve() : reject(new Error(`ffmpeg exited with ${code}`))
    );
  });

  await browser.close();
  fs.rmSync(tmpDir, { recursive: true, force: true });
  console.log(`✅ Rendered smooth animated walkthrough video to: ${outMp4}`);
}

export { parseArgs, loadPlaywright };

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(import.meta.filename)) {
  main().catch((err) => {
    console.error("❌ Video render failed:", err);
    process.exit(1);
  });
}
