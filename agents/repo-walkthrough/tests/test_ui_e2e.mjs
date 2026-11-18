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
 * End-to-End Headless Browser UI, Visual Geometry, Transport Controls, and Video Tests.
 *
 * Verifies in real Chromium via Playwright:
 *   1. Visual & SVG Geometry:
 *      - Zero node-to-node overlaps in screen space
 *      - Zero text overflow (.node-title and .node-sub fit strictly inside .node-rect)
 *      - Zero layer-header-to-node collisions (.layer-band-label stays left of all nodes)
 *      - All SVG edge arrows have valid paths, arrowheads (marker-end), and connect node boundaries
 *      - Bottom dock (.walk-info, .walk-controls, .transport, .speed-pills, #timeline) never overlaps or overflows
 *   2. Interactive Transport & Audio Controls:
 *      - Play / Pause toggle (#playBtn) remembers exact audio timestamp on pause & resume
 *      - Persistent play state across #nextBtn, #prevBtn, and timeline scrubbing
 *      - Music-player #prevBtn behavior (restarts section if >0.5s in, else goes to previous section)
 *      - #back5Btn (-5s) and #fwd5Btn (+5s) seeking and rolling smoothly across section boundaries
 *      - Speed pills (0.8x, 0.9x, 1x, 1.1x, 1.2x) updating playbackRate and active pill state
 *   3. Flexible Layer Scaling (3, 5, and 6 layers):
 *      - Dynamic FULL_VB viewBox height adapts cleanly to 3-layer, 5-layer, and 6-layer graphs
 *   4. Deterministic Video Mode (?video=1 & window.renderWalkthroughFrame) + MP4 ffprobe verification
 */

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { createWavBuffer } from "../skills/repo-walkthrough/scripts/generate_live_audio.mjs";
import { loadPlaywright } from "../skills/repo-walkthrough/scripts/render_video.mjs";

const REPO_ROOT = path.resolve(import.meta.dirname, "..");
const SKILL_SCRIPTS_DIR = path.join(REPO_ROOT, "skills", "repo-walkthrough", "scripts");
const WEB_TEMPLATE_URL = fs.existsSync(path.join(REPO_ROOT, "web", "index.html"))
  ? "/web/index.html"
  : "/web/index.tmpl";

function prepareSelfWalkthroughSiteWithAudio(durationSec = 22) {
  const srcSiteDir = path.join(REPO_ROOT, "examples", "self-walkthrough");
  if (fs.existsSync(path.join(srcSiteDir, "audio", "step-1.wav"))) {
    return { siteDir: srcSiteDir, cleanup: () => {} };
  }
  const tmpSiteDir = fs.mkdtempSync(path.join(os.tmpdir(), "rw-e2e-site-"));
  fs.copyFileSync(path.join(srcSiteDir, "index.html"), path.join(tmpSiteDir, "index.html"));
  fs.copyFileSync(path.join(srcSiteDir, "data.js"), path.join(tmpSiteDir, "data.js"));
  const audioDir = path.join(tmpSiteDir, "audio");
  fs.mkdirSync(audioDir, { recursive: true });
  const wavBuf = createWavBuffer(Buffer.alloc(24000 * 2 * durationSec), 24000, 1, 16);
  const manifest = [];
  for (let step = 1; step <= 6; step++) {
    const fileName = `step-${step}.wav`;
    fs.writeFileSync(path.join(audioDir, fileName), wavBuf);
    manifest.push({
      step,
      title: `Step ${step}`,
      file: `audio/${fileName}`,
      durationSec,
    });
  }
  fs.writeFileSync(path.join(audioDir, "manifest.json"), JSON.stringify(manifest, null, 2));
  return {
    siteDir: tmpSiteDir,
    cleanup: () => fs.rmSync(tmpSiteDir, { recursive: true, force: true }),
  };
}

function startStaticServer(rootDir) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const reqUrl = new URL(req.url, "http://127.0.0.1");
      const relPath = decodeURIComponent(reqUrl.pathname === "/" ? "/index.html" : reqUrl.pathname);
      const filePath = path.join(rootDir, relPath);
      if (!filePath.startsWith(rootDir) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        res.writeHead(404);
        res.end("Not found");
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      const mime =
        ext === ".html" || ext === ".tmpl"
          ? "text/html; charset=utf-8"
          : ext === ".js"
          ? "application/javascript; charset=utf-8"
          : ext === ".wav"
          ? "audio/wav"
          : ext === ".json"
          ? "application/json"
          : "application/octet-stream";

      const stat = fs.statSync(filePath);
      const range = req.headers.range;
      if (range && ext === ".wav") {
        const m = range.match(/bytes=(\d+)-(\d*)/);
        const start = m ? parseInt(m[1], 10) : 0;
        const end = m && m[2] ? parseInt(m[2], 10) : stat.size - 1;
        res.writeHead(206, {
          "Content-Range": `bytes ${start}-${end}/${stat.size}`,
          "Accept-Ranges": "bytes",
          "Content-Length": end - start + 1,
          "Content-Type": mime,
        });
        fs.createReadStream(filePath, { start, end }).pipe(res);
        return;
      }

      res.writeHead(200, {
        "Content-Type": mime,
        "Content-Length": stat.size,
        "Accept-Ranges": "bytes",
      });
      fs.createReadStream(filePath).pipe(res);
    });
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({ server, baseUrl: `http://127.0.0.1:${port}` });
    });
  });
}

async function launchBrowser() {
  const { chromium } = loadPlaywright();
  try {
    return await chromium.launch({
      headless: true,
      channel: "chrome",
      args: ["--autoplay-policy=no-user-gesture-required"],
    });
  } catch {
    return await chromium.launch({
      headless: true,
      args: ["--autoplay-policy=no-user-gesture-required"],
    });
  }
}

test("Visual & SVG geometry inspection: zero text overflow, valid arrows, zero overlaps (self-walkthrough, ADK, and cymbal-autos-multimodal)", async () => {
  const browser = await launchBrowser();
  const { server, baseUrl } = await startStaticServer(REPO_ROOT);

  try {
    for (const pagePath of [
      "/examples/self-walkthrough/index.html",
      "/examples/cymbal-autos-multimodal/index.html",
      "/examples/diff-5984e02-to-head/index.html",
      WEB_TEMPLATE_URL,
    ]) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", (e) => errors.push(e.message));

      await page.goto(`${baseUrl}${pagePath}`, { waitUntil: "networkidle" });
      assert.equal(errors.length, 0, `Page errors on ${pagePath}: ${errors.join("; ")}`);

      const report = await page.evaluate(async () => {
        if (document.fonts && document.fonts.ready) {
          await document.fonts.ready;
        }
        // Static example snapshots predating the web/index.html document.fonts.ready
        // hook measured getComputedTextLength() against the OS fallback monospace font
        // before Roboto Mono finished downloading; re-apply the template's truncation
        // rule once web fonts are ready.
        for (const g of document.querySelectorAll(".node-group")) {
          const rect = g.querySelector(".node-rect");
          const title = g.querySelector(".node-title");
          const sub = g.querySelector(".node-sub");
          const diffBadge = g.querySelector(".node-diff");
          const w = parseFloat(rect.getAttribute("width") || "0");
          const diffW = diffBadge ? diffBadge.getComputedTextLength() + 10 : 0;
          const maxTitleW = w - 24 - diffW;
          const maxSubW = w - 24;
          while (title.textContent.length > 6 && title.getComputedTextLength() > maxTitleW) {
            title.textContent = title.textContent.slice(0, -2) + "…";
          }
          while (sub.textContent.length > 6 && sub.getComputedTextLength() > maxSubW) {
            sub.textContent = sub.textContent.slice(0, -2) + "…";
          }
        }
        const textOverflows = [];
        const nodeGroups = Array.from(document.querySelectorAll(".node-group"));

        for (const g of nodeGroups) {
          const rect = g.querySelector(".node-rect");
          const title = g.querySelector(".node-title");
          const sub = g.querySelector(".node-sub");
          const diffBadge = g.querySelector(".node-diff");
          const rBox = rect.getBBox();
          const tBox = title.getBBox();
          const sBox = sub.getBBox();
          const label = title.textContent;

          if (tBox.x < rBox.x || tBox.x + tBox.width > rBox.x + rBox.width - 4) {
            textOverflows.push(
              `title ("${label}") right ${(tBox.x - rBox.x + tBox.width).toFixed(1)} > rect width ${rBox.width}`
            );
          }
          if (diffBadge) {
            const dBox = diffBadge.getBBox();
            if (tBox.x + tBox.width > dBox.x - 2) {
              textOverflows.push(
                `title ("${label}") collided with diff badge ("${diffBadge.textContent}")`
              );
            }
          }
          if (sBox.x < rBox.x || sBox.x + sBox.width > rBox.x + rBox.width - 4) {
            textOverflows.push(
              `sub ("${sub.textContent}") right ${(sBox.x - rBox.x + sBox.width).toFixed(1)} > rect width ${rBox.width}`
            );
          }
          if (sBox.y + sBox.height > rBox.y + rBox.height - 2) {
            textOverflows.push(
              `sub ("${sub.textContent}") bottom ${(sBox.y - rBox.y + sBox.height).toFixed(1)} > rect height ${rBox.height}`
            );
          }
        }

        // Check layer labels don't collide with any node
        const labelCollisions = [];
        const labels = Array.from(document.querySelectorAll(".layer-band-label"));
        for (const lbl of labels) {
          const lBox = lbl.getBBox();
          const lRight = lBox.x + lBox.width;
          if (lRight > 195) {
            labelCollisions.push(`Layer label "${lbl.textContent}" right edge ${lRight.toFixed(1)} exceeds x=195`);
          }
        }

        // Check all edge paths & arrow markers
        const invalidEdges = [];
        const edgePaths = Array.from(document.querySelectorAll(".edge-path"));
        for (const p of edgePaths) {
          const len = p.getTotalLength();
          const marker = p.getAttribute("marker-end");
          if (!(len > 10)) {
            invalidEdges.push(`Edge has zero/tiny path length: ${len}`);
          }
          if (!marker || !marker.startsWith("url(#arr")) {
            invalidEdges.push(`Edge missing arrowhead marker-end: ${marker}`);
          }
        }

        // Check bottom dock layout doesn't overlap or overflow viewport
        const infoRect = document.querySelector(".walk-info").getBoundingClientRect();
        const ctrlRect = document.querySelector(".walk-controls").getBoundingClientRect();
        const dockOverlap = infoRect.right > ctrlRect.left + 2;
        const viewportOverflow = ctrlRect.right > window.innerWidth;
        const inspHref = document.querySelector("#inspector .insp-title a")?.getAttribute("href") || "";
        const diffBadgeCount = document.querySelectorAll(".node-diff").length;
        const diffLineAddCount = document.querySelectorAll("#inspector .diff-line-add").length;

        return {
          nodeCount: nodeGroups.length,
          edgeCount: edgePaths.length,
          diffBadgeCount,
          diffLineAddCount,
          textOverflows,
          labelCollisions,
          invalidEdges,
          dockOverlap,
          viewportOverflow,
          inspHref,
        };
      });

      assert.ok(report.nodeCount >= 12, `Expected >=12 nodes in ${pagePath}`);
      assert.ok(report.edgeCount >= 11, `Expected >=11 edges in ${pagePath}`);
      assert.deepEqual(
        report.textOverflows,
        [],
        `Node text overflowed box in ${pagePath}:\n  ${report.textOverflows.join("\n  ")}`
      );
      assert.deepEqual(
        report.labelCollisions,
        [],
        `Layer label collision in ${pagePath}:\n  ${report.labelCollisions.join("\n  ")}`
      );
      assert.deepEqual(
        report.invalidEdges,
        [],
        `Invalid edge arrows in ${pagePath}:\n  ${report.invalidEdges.join("\n  ")}`
      );
      assert.equal(report.dockOverlap, false, `walk-info overlapped walk-controls in ${pagePath}`);
      assert.equal(report.viewportOverflow, false, `walk-controls overflowed viewport in ${pagePath}`);
      if (pagePath.includes("cymbal-autos-multimodal")) {
        assert.equal(
          report.inspHref,
          "https://github.com/GoogleCloudPlatform/devrel-demos/blob/main/data-analytics/cymbal-autos-multimodal/scripts/setup/00_copy_data.sh",
          "Expected DATA.subpath to be prepended to GitHub blob link in inspector"
        );
      }
      if (pagePath.includes("self-walkthrough")) {
        const docsDir = path.join(REPO_ROOT, "docs");
        const previewPng = path.join(docsDir, "preview.png");
        if (!fs.existsSync(previewPng)) {
          fs.mkdirSync(docsDir, { recursive: true });
          await page.screenshot({ path: previewPng });
        }
      }
      if (pagePath.includes("diff-5984e02-to-head")) {
        assert.equal(report.diffBadgeCount, 12, "Expected all 12 diff nodes to render +added/-deleted SVG badges");
        assert.ok(report.diffLineAddCount > 0, "Expected inspector code-box to highlight +added diff lines");
      }

      if (pagePath === WEB_TEMPLATE_URL) {
        const xssCheck = await page.evaluate(() => {
          const d = window.WALKTHROUGH_DATA || window.ADK_DATA;
          const n0 = d.nodes[0];
          const orig = {
            path: n0.path,
            label: n0.label,
            sublabel: n0.sublabel,
            url: n0.url,
          };
          n0.path = '<img src=x onerror="window.__xss=1">';
          n0.label = '<b>unsafeLabel</b>';
          n0.sublabel = '" onclick="window.__xss=2';
          n0.url = "javascript:alert(1)";
          const gs = document.querySelectorAll(".node-group");
          if (gs.length > 1) gs[1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
          gs[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
          const inspHtml = document.querySelector("#inspector .insp-title")?.innerHTML || "";
          const hasAnchor = Boolean(document.querySelector("#inspector .insp-title a"));
          const hasImg = Boolean(document.querySelector("#inspector .insp-title img"));
          n0.url = "https://example.com/a?x=1&y=\"2\"";
          if (gs.length > 1) gs[1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
          gs[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
          const safeAnchorHref =
            document.querySelector("#inspector .insp-title a")?.getAttribute("href") || "";
          Object.assign(n0, orig);
          return { inspHtml, hasAnchor, hasImg, safeAnchorHref, xss: Boolean(window.__xss) };
        });
        assert.equal(xssCheck.xss, false, "Inspector must never execute injected HTML/JS");
        assert.equal(xssCheck.hasImg, false, "Inspector must escape <img ...> in n.path");
        assert.equal(xssCheck.hasAnchor, false, "Inspector must reject javascript: URLs in n.url");
        assert.ok(xssCheck.inspHtml.includes("&lt;img"), "Inspector innerHTML must contain escaped &lt;img");
        assert.equal(xssCheck.safeAnchorHref, 'https://example.com/a?x=1&y="2"');
      }

      await context.close();
    }
  } finally {
    server.close();
    await browser.close();
  }
});

test("Interactive player controls: Play/Pause exact position memory, -5s/+5s cross-section skip, smart Prev, and speed pills", async () => {
  const browser = await launchBrowser();
  const { siteDir, cleanup } = prepareSelfWalkthroughSiteWithAudio(22);
  const { server, baseUrl } = await startStaticServer(siteDir);

  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto(`${baseUrl}/index.html`, { waitUntil: "networkidle" });

    const PLAY_D = "M8 5.5v13l11-6.5z";
    const PAUSE_D = "M7.5 5h3.2v14H7.5zM13.3 5h3.2v14h-3.2z";

    // 1. Initial state is Step 1, paused
    assert.equal(await page.textContent("#stepNum"), "STEP 1 / 6");
    assert.equal(await page.getAttribute("#ppicon path", "d"), PLAY_D);

    // 2. Click Play -> starts playing, icon changes to PAUSE_D
    await page.click("#playBtn");
    await page.waitForFunction(
      (expectedD) => document.querySelector("#ppicon path").getAttribute("d") === expectedD,
      PAUSE_D
    );

    // 3. Click +5s (#fwd5Btn) twice -> advances currentTime to ~10s
    await page.click("#fwd5Btn");
    await page.click("#fwd5Btn");
    await page.waitForTimeout(120);

    // 4. Click Pause (#playBtn) -> pauses at ~10s and remembers exact position
    await page.click("#playBtn");
    assert.equal(await page.getAttribute("#ppicon path", "d"), PLAY_D);
    const tlAtPause = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(tlAtPause > 5, `Expected timeline fill > 5% after +10s seek, got ${tlAtPause}%`);

    // Wait 250ms while paused and confirm timeline does not reset or drift
    await page.waitForTimeout(250);
    const tlStillPaused = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(Math.abs(tlStillPaused - tlAtPause) < 0.2, "Paused position should stay fixed");

    // 5. Click Play (#playBtn) again on the same section -> resumes from ~10s (does NOT reset to 0%)
    await page.click("#playBtn");
    await page.waitForTimeout(100);
    const tlAfterResume = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(
      tlAfterResume >= tlAtPause - 0.5,
      `Expected resume to continue from ${tlAtPause}%, but got ${tlAfterResume}%`
    );

    // 6. Smart #prevBtn: when >0.5s into Step 1, clicking #prevBtn restarts Step 1 to 0% while staying on Step 1
    await page.click("#prevBtn");
    await page.waitForTimeout(80);
    assert.equal(await page.textContent("#stepNum"), "STEP 1 / 6");
    const tlAfterRestart = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(tlAfterRestart < 3, `Expected #prevBtn to restart Step 1 near 0%, got ${tlAfterRestart}%`);

    // 7. While playing, clicking #nextBtn switches to Step 2 and automatically continues playing
    await page.click("#nextBtn");
    assert.equal(await page.textContent("#stepNum"), "STEP 2 / 6");
    assert.equal(await page.getAttribute("#ppicon path", "d"), PAUSE_D);

    // 8. Pause on Step 2 at ~0s, then click #back5Btn (-5s) -> rolls back into the tail of Step 1!
    await page.click("#playBtn"); // pause near start of Step 2
    await page.click("#back5Btn");
    await page.waitForTimeout(150);
    assert.equal(
      await page.textContent("#stepNum"),
      "STEP 1 / 6",
      "Expected -5s near start of Step 2 to roll back into Step 1"
    );
    const tlRolledBack = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(
      tlRolledBack > 14 && tlRolledBack < 20,
      `Expected timeline in tail of Step 1 (14-20%), got ${tlRolledBack}%`
    );

    // 9. Click #fwd5Btn (+5s) twice from the tail of Step 1 -> rolls forward into Step 2!
    await page.click("#fwd5Btn");
    await page.click("#fwd5Btn");
    await page.waitForTimeout(150);
    assert.equal(
      await page.textContent("#stepNum"),
      "STEP 2 / 6",
      "Expected +5s from tail of Step 1 to roll forward into Step 2"
    );

    // 10. Speed pills (.spd): clicking 1.2x highlights pill and updates playback speed
    await page.click('.spd[data-s="1.2"]');
    const is12On = await page.$eval('.spd[data-s="1.2"]', (el) => el.classList.contains("on"));
    const is10On = await page.$eval('.spd[data-s="1"]', (el) => el.classList.contains("on"));
    assert.equal(is12On, true);
    assert.equal(is10On, false);

    await context.close();
  } finally {
    server.close();
    await browser.close();
    cleanup();
  }
});

test("Video mode (?video=1), deterministic renderWalkthroughFrame, and MP4 output verification", async () => {
  const browser = await launchBrowser();
  const siteDir = path.join(REPO_ROOT, "examples", "self-walkthrough");
  const { server, baseUrl } = await startStaticServer(siteDir);

  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto(`${baseUrl}/index.html?video=1`, { waitUntil: "networkidle" });

    const videoLayout = await page.evaluate(() => {
      const asideVisible = getComputedStyle(document.querySelector("aside")).display !== "none";
      const camVisible = getComputedStyle(document.querySelector(".cam-controls")).display !== "none";
      const controlsVisible = getComputedStyle(document.querySelector(".walk-controls")).display !== "none";
      window.renderWalkthroughFrame({
        stepIndex: 2,
        prevStepIndex: 1,
        camTransition: 1,
        stepProgress: 0.5,
        timelinePct: 40,
        dashOffset: -12,
      });
      return {
        asideVisible,
        camVisible,
        controlsVisible,
        stepNum: document.querySelector("#stepNum").textContent,
        tlWidth: document.querySelector("#tl-fill").style.width,
        iconD: document.querySelector("#ppicon path").getAttribute("d"),
      };
    });

    assert.equal(videoLayout.asideVisible, false, "Inspector sidebar must be hidden in ?video=1");
    assert.equal(videoLayout.camVisible, false, "Camera zoom controls must be hidden in ?video=1");
    assert.equal(videoLayout.controlsVisible, true, "Transport controls should be visible in ?video=1");
    assert.equal(videoLayout.stepNum, "STEP 3 / 6");
    assert.equal(videoLayout.tlWidth, "40%");
    assert.equal(videoLayout.iconD, "M7.5 5h3.2v14H7.5zM13.3 5h3.2v14h-3.2z");

    // Verify camera framing across all steps never slices any node box at the viewBox edges
    const slicedNodes = await page.evaluate(() => {
      const stepCount = window.WALKTHROUGH_DATA.walkthrough.length;
      const sliced = [];
      for (let i = 0; i < stepCount; i++) {
        window.renderWalkthroughFrame({
          stepIndex: i,
          prevStepIndex: i,
          camTransition: 1,
          stepProgress: 0.5,
          timelinePct: 50,
          dashOffset: 0,
        });
        const [vx, vy, vw, vh] = document
          .getElementById("graph-svg")
          .getAttribute("viewBox")
          .split(/\s+/)
          .map(Number);
        for (const n of WALKTHROUGH_DATA.nodes) {
          const overlapsX = n.x < vx + vw && n.x + n.w > vx;
          const overlapsY = n.y < vy + vh && n.y + n.h > vy;
          if (overlapsX && overlapsY) {
            const fullyInsideX = n.x >= vx && n.x + n.w <= vx + vw;
            const fullyInsideY = n.y >= vy && n.y + n.h <= vy + vh;
            if (!fullyInsideX || !fullyInsideY) {
              sliced.push(
                `Step ${i + 1}: node "${n.id}" (${n.x},${n.y},${n.w}x${n.h}) sliced by viewBox (${vx},${vy},${vw}x${vh})`
              );
            }
          }
        }
      }
      return sliced;
    });
    assert.deepEqual(slicedNodes, [], `Camera viewBox sliced nodes:\n  ${slicedNodes.join("\n  ")}`);

    // Capture Step 4 screenshot for visual verification if scratch dir is configured
    const scratchDirEnv = process.env.REPO_WALKTHROUGH_SCRATCH_DIR;
    if (scratchDirEnv && fs.existsSync(scratchDirEnv)) {
      await page.evaluate(() => {
        window.renderWalkthroughFrame({
          stepIndex: 3,
          prevStepIndex: 3,
          camTransition: 1,
          stepProgress: 0.5,
          timelinePct: 58,
          dashOffset: -8,
        });
      });
      await page.screenshot({ path: path.join(scratchDirEnv, "self-video-step4.png") });
    }

    await context.close();
  } finally {
    server.close();
    await browser.close();
  }

  // Verify the rendered MP4 file via ffprobe (rendering a fast synthetic MP4 in clean checkouts)
  let mp4Path = path.join(
    REPO_ROOT,
    "examples",
    "self-walkthrough",
    "ykdojo-repo-walkthrough-walkthrough.mp4"
  );
  let minDurationSec = 100;
  let cleanupVideoDir = () => {};
  if (!fs.existsSync(mp4Path)) {
    const prep = prepareSelfWalkthroughSiteWithAudio(1);
    cleanupVideoDir = prep.cleanup;
    // Trim manifest to 2 steps so clean-checkout E2E video render finishes in ~3s
    const manifestPath = path.join(prep.siteDir, "audio", "manifest.json");
    const shortManifest = JSON.parse(fs.readFileSync(manifestPath, "utf8")).slice(0, 2);
    fs.writeFileSync(manifestPath, JSON.stringify(shortManifest, null, 2));
    mp4Path = path.join(prep.siteDir, "test-walkthrough.mp4");
    execFileSync(
      process.execPath,
      [
        path.join(SKILL_SCRIPTS_DIR, "render_video.mjs"),
        "--dir",
        prep.siteDir,
        "--out",
        mp4Path,
        "--fps",
        "6",
      ],
      { stdio: "pipe" }
    );
    minDurationSec = 1.5;
  }
  try {
    assert.ok(fs.existsSync(mp4Path), "Expected rendered walkthrough MP4 to exist");
    const probeJson = JSON.parse(
      execFileSync(
        "ffprobe",
        ["-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height", "-of", "json", mp4Path],
        { encoding: "utf8" }
      )
    );
    const codecs = probeJson.streams.map((s) => s.codec_name);
    assert.ok(codecs.includes("h264"), "Expected H.264 video stream");
    assert.ok(codecs.includes("aac"), "Expected AAC audio stream");
    assert.ok(
      parseFloat(probeJson.format.duration) > minDurationSec,
      `Expected walkthrough video duration > ${minDurationSec}s`
    );
  } finally {
    cleanupVideoDir();
  }
});

test("Flexible layer counts (3, 4, and 6 layers): visual geometry, FULL_VB scaling, and camera framing in Chromium", async () => {
  const os = await import("node:os");
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "repo-walkthrough-layers-"));
  const indexHtml = fs.readFileSync(path.join(REPO_ROOT, WEB_TEMPLATE_URL.slice(1)), "utf8");

  const palette = [
    { color: "#4285F4", accent: "#8AB4F8", bg: "rgba(66, 133, 244, 0.08)" },
    { color: "#FBBC04", accent: "#FDD663", bg: "rgba(251, 188, 4, 0.08)" },
    { color: "#FF8A65", accent: "#FFAB91", bg: "rgba(255, 138, 101, 0.08)" },
    { color: "#34A853", accent: "#81C995", bg: "rgba(52, 168, 83, 0.08)" },
    { color: "#A142F4", accent: "#C58AF9", bg: "rgba(161, 66, 244, 0.08)" },
    { color: "#26C6DA", accent: "#80DEEA", bg: "rgba(38, 198, 218, 0.08)" },
  ];
  const layerNames = [
    "CLI & Entry Surface",
    "Routing & Gateway",
    "Orchestration Engine",
    "Domain Services",
    "Execution Runtime",
    "Storage & Telemetry",
  ];

  for (const count of [3, 4, 6]) {
    const layers = Array.from({ length: count }, (_, i) => ({
      id: `layer_${i}`,
      name: layerNames[i],
      ...palette[i],
    }));
    const nodes = [];
    const edges = [];
    for (let i = 0; i < count; i++) {
      const y = 26 + i * 122;
      const cols = [
        { suffix: "a", x: 210, w: 235, label: `module_${i}_alpha.py`, sub: `${layerNames[i]} Alpha` },
        { suffix: "b", x: 485, w: 235, label: `module_${i}_beta.py`, sub: `${layerNames[i]} Beta` },
        { suffix: "c", x: 760, w: 235, label: `module_${i}_gamma.py`, sub: `${layerNames[i]} Gamma` },
      ];
      for (const c of cols) {
        nodes.push({
          id: `n_${i}_${c.suffix}`,
          label: c.label,
          sub: c.sub,
          path: `src/layer_${i}/${c.label}`,
          layer: `layer_${i}`,
          lines: 120 + i * 20,
          x: c.x,
          y,
          w: c.w,
          h: 58,
          role: `Handles ${c.sub} responsibilities in layer ${i + 1} of ${count}.`,
          snippet: `class Layer${i}${c.suffix.toUpperCase()}:\n    def execute(self):\n        return True`,
        });
      }
      if (i > 0) {
        for (const s of ["a", "b", "c"]) {
          edges.push({
            id: `n_${i - 1}_${s}>n_${i}_${s}`,
            from: `n_${i - 1}_${s}`,
            to: `n_${i}_${s}`,
            label: "calls",
            detail: `Delegates from layer ${i} to layer ${i + 1}.`,
          });
        }
      }
    }

    // Walkthrough steps covering overview, top layers, middle layers (for 5/6), and bottom layers
    const walkthrough = [
      {
        step: 1,
        title: `${count}-Layer Architecture Overview`,
        focusNode: "n_0_a",
        activeNodes: nodes.map((n) => n.id),
        activeEdges: edges.map((e) => e.id),
        summary: `Full ${count}-layer architecture overview spanning all ${nodes.length} components.`,
        narration: `Overview of the ${count}-layer architecture.`,
      },
      {
        step: 2,
        title: `Upper Layers (Layers 1-2 of ${count})`,
        focusNode: "n_0_b",
        activeNodes: ["n_0_a", "n_0_b", "n_1_a", "n_1_b"],
        activeEdges: ["n_0_a>n_1_a", "n_0_b>n_1_b"],
        summary: `Upper-layer request flow across layers 1 and 2.`,
        narration: `Upper layers request flow.`,
      },
      ...(count === 6
        ? [
            {
              step: 3,
              title: `Middle Layers Window (Layers 2-4 of ${count})`,
              focusNode: "n_2_b",
              activeNodes: ["n_1_b", "n_2_b", "n_3_b"],
              activeEdges: ["n_1_b>n_2_b", "n_2_b>n_3_b"],
              summary: `Middle 3-layer window framing layers 2, 3, and 4 cleanly between inter-layer gaps.`,
              narration: `Middle layers window.`,
            },
            {
              step: 4,
              title: `Lower-Middle Layers Window (Layers 3-5 of ${count})`,
              focusNode: "n_3_c",
              activeNodes: ["n_2_c", "n_3_c", "n_4_c"],
              activeEdges: ["n_2_c>n_3_c", "n_3_c>n_4_c"],
              summary: `Lower-middle 3-layer window framing layers 3, 4, and 5.`,
              narration: `Lower middle layers window.`,
            },
          ]
        : []),
      {
        step: count === 6 ? 5 : 3,
        title: `Bottom Layers (Layers ${count - 1}-${count} of ${count})`,
        focusNode: `n_${count - 1}_b`,
        activeNodes: [`n_${count - 2}_b`, `n_${count - 2}_c`, `n_${count - 1}_b`, `n_${count - 1}_c`],
        activeEdges: [`n_${count - 2}_b>n_${count - 1}_b`, `n_${count - 2}_c>n_${count - 1}_c`],
        summary: `Bottom-layer execution and storage flow.`,
        narration: `Bottom layers flow.`,
      },
    ];

    fs.writeFileSync(
      path.join(tmpDir, `data-${count}.js`),
      `window.WALKTHROUGH_DATA = ${JSON.stringify(
        {
          repo: `example/${count}-layer-repo`,
          branch: "main",
          title: `${count}-layer-repo`,
          subtitle: `${count}-Layer Architecture Walkthrough Verification`,
          layers,
          nodes,
          edges,
          walkthrough,
        },
        null,
        2
      )};\n`,
      "utf8"
    );
    fs.writeFileSync(
      path.join(tmpDir, `index-${count}.html`),
      indexHtml.replace('src="data-adk.js"', `src="data-${count}.js"`),
      "utf8"
    );
  }

  const browser = await launchBrowser();
  const { server, baseUrl } = await startStaticServer(tmpDir);
  const scratchDir = process.env.REPO_WALKTHROUGH_SCRATCH_DIR || "";

  try {
    for (const count of [3, 4, 6]) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await context.newPage();

      // 1. Check interactive mode
      await page.goto(`${baseUrl}/index-${count}.html`, { waitUntil: "networkidle" });
      const interactiveReport = await page.evaluate(() => {
        const [vx, vy, vw, vh] = document
          .getElementById("graph-svg")
          .getAttribute("viewBox")
          .split(/\s+/)
          .map(Number);
        const labels = Array.from(document.querySelectorAll(".layer-band-label"));
        const camR = document.querySelector(".cam-controls").getBoundingClientRect();
        const camOverlaps = [];
        for (const rect of document.querySelectorAll(".node-rect")) {
          const r = rect.getBoundingClientRect();
          if (r.right > camR.left && r.left < camR.right && r.bottom > camR.top && r.top < camR.bottom) {
            camOverlaps.push(rect.parentElement.querySelector(".node-title").textContent);
          }
        }
        return { vx, vy, vw, vh, bandCount: labels.length, camOverlaps };
      });
      assert.equal(interactiveReport.bandCount, count, `Expected ${count} layer bands`);
      assert.deepEqual(
        interactiveReport.camOverlaps,
        [],
        `cam-controls overlapped nodes in ${count}-layer interactive view: ${interactiveReport.camOverlaps.join(", ")}`
      );

      if (fs.existsSync(scratchDir)) {
        await page.screenshot({ path: path.join(scratchDir, `layers-${count}-interactive.png`) });
      }

      // 2. Check video mode (?video=1) across ALL walkthrough steps (overview, top, middle, bottom)
      await page.goto(`${baseUrl}/index-${count}.html?video=1`, { waitUntil: "networkidle" });
      const sliced = await page.evaluate(() => {
        const steps = window.WALKTHROUGH_DATA.walkthrough.length;
        const errs = [];
        for (let i = 0; i < steps; i++) {
          window.renderWalkthroughFrame({
            stepIndex: i,
            prevStepIndex: i,
            camTransition: 1,
            stepProgress: 0.5,
            timelinePct: (100 * i) / Math.max(1, steps - 1),
            dashOffset: -6,
          });
          const [vx, vy, vw, vh] = document
            .getElementById("graph-svg")
            .getAttribute("viewBox")
            .split(/\s+/)
            .map(Number);
          for (const n of window.WALKTHROUGH_DATA.nodes) {
            const overlapsX = n.x < vx + vw && n.x + n.w > vx;
            const overlapsY = n.y < vy + vh && n.y + n.h > vy;
            if (overlapsX && overlapsY) {
              const insideX = n.x >= vx && n.x + n.w <= vx + vw;
              const insideY = n.y >= vy && n.y + n.h <= vy + vh;
              if (!insideX || !insideY) {
                errs.push(`Step ${i + 1}: node ${n.id} (${n.x},${n.y},${n.w}x${n.h}) sliced by (${vx},${vy},${vw}x${vh})`);
              }
            }
          }
        }
        return errs;
      });
      assert.deepEqual(sliced, [], `${count}-layer camera sliced nodes:\n  ${sliced.join("\n  ")}`);

      if (fs.existsSync(scratchDir)) {
        // Screenshot Step 1 (full overview) and Step 3 (middle/bottom zoomed step) in video mode
        await page.evaluate(() => {
          window.renderWalkthroughFrame({
            stepIndex: 0,
            prevStepIndex: 0,
            camTransition: 1,
            stepProgress: 0.5,
            timelinePct: 10,
            dashOffset: 0,
          });
        });
        await page.screenshot({ path: path.join(scratchDir, `layers-${count}-video-step1.png`) });

        await page.evaluate(() => {
          window.renderWalkthroughFrame({
            stepIndex: 2,
            prevStepIndex: 2,
            camTransition: 1,
            stepProgress: 0.5,
            timelinePct: 60,
            dashOffset: -8,
          });
        });
        await page.screenshot({ path: path.join(scratchDir, `layers-${count}-video-zoomed.png`) });
      }

      await context.close();
    }
  } finally {
    server.close();
    await browser.close();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test("Inline SVG favicon in web/index.html and generated walkthrough website renders crisply in Chromium", async () => {
  const tmpSiteDir = fs.mkdtempSync(path.join(os.tmpdir(), "rw-favicon-e2e-"));
  const dataPath = path.join(REPO_ROOT, "examples", "self-walkthrough", "data.js");
  execFileSync(
    process.execPath,
    [
      path.join(SKILL_SCRIPTS_DIR, "build_walkthrough.mjs"),
      "--data",
      dataPath,
      "--out-dir",
      tmpSiteDir,
      "--mode",
      "website",
      "--no-tts",
    ],
    { stdio: "pipe" }
  );

  const browser = await launchBrowser();
  const { server, baseUrl } = await startStaticServer(tmpSiteDir);
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto(`${baseUrl}/index.html`, { waitUntil: "networkidle" });

    const faviconCheck = await page.evaluate(async () => {
      const link = document.querySelector('head link[rel="icon"][type="image/svg+xml"]');
      if (!link) return { exists: false };
      const href = link.getAttribute("href") || "";
      const img = new Image();
      const loaded = await new Promise((resolve) => {
        img.onload = () => resolve(true);
        img.onerror = () => resolve(false);
        img.src = href;
      });
      if (!loaded) return { exists: true, href, loaded: false };
      const canvas = document.createElement("canvas");
      canvas.width = 128;
      canvas.height = 128;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, 128, 128);
      const centerPixel = Array.from(ctx.getImageData(64, 64, 1, 1).data);
      const playBadgePixel = Array.from(ctx.getImageData(88, 90, 1, 1).data);
      return {
        exists: true,
        loaded: true,
        startsWithDataSvg: href.startsWith("data:image/svg+xml,"),
        naturalWidth: img.naturalWidth,
        naturalHeight: img.naturalHeight,
        centerAlpha: centerPixel[3],
        playBadgeRed: playBadgePixel[0],
        playBadgeAlpha: playBadgePixel[3],
      };
    });

    assert.equal(faviconCheck.exists, true, "Generated index.html must include SVG favicon <link> in <head>");
    assert.equal(faviconCheck.startsWithDataSvg, true, "Favicon href must use data:image/svg+xml,");
    assert.equal(faviconCheck.loaded, true, "Chromium must decode inline SVG favicon data URI without error");
    assert.equal(faviconCheck.naturalWidth, 128);
    assert.equal(faviconCheck.naturalHeight, 128);
    assert.equal(faviconCheck.centerAlpha, 255, "Favicon rounded background rect must render opaque");
    assert.ok(faviconCheck.playBadgeRed > 180 && faviconCheck.playBadgeAlpha === 255, "Favicon play badge gradient/triangle must render");

    await context.close();
  } finally {
    server.close();
    await browser.close();
    fs.rmSync(tmpSiteDir, { recursive: true, force: true });
  }
});
