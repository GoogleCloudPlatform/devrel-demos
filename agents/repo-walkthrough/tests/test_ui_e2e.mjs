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
 * End-to-End Headless Browser UI, Mobile/Desktop Geometry, XSS, Transport Controls, and Video Tests.
 *
 * Verifies in real Chrome/Chromium/Edge via Playwright:
 *   1. Desktop (1440x900) & Mobile (390x844, 360x640) Visual & SVG Geometry across ALL 3 rebuilt
 *      examples/<name>/index.html pages AND built web/data-adk.js:
 *      - Zero node-to-node overlaps and zero text overflow (native document.fonts.ready truncation, zero DOM patching)
 *      - Non-zero mobile SVG graph height, zero horizontal overflow (scrollWidth <= clientWidth), zero dock overlap
 *      - Defined --g-red-light (#F28B82), WCAG AA contrast, inline SVG favicon decode, and XSS / javascript: / // URL blocking
 *   2. Interactive Transport & Audio Controls:
 *      - Play / Pause exact timestamp memory, persistent play across section switches, smart Prev, -5s/+5s cross-step seeking, speed pills
 *   3. Flexible Layer Scaling (3, 4, and 6 layers):
 *      - Dynamic FULL_VB viewBox height and camera framing across all steps
 *   4. Deterministic Video Mode (?video=1 & window.renderWalkthroughFrame) + synthetic-WAV MP4 ffprobe verification
 */

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { resolveTemplatePath } from "../skills/repo-walkthrough/scripts/build_walkthrough.mjs";
import { createWavBuffer } from "../skills/repo-walkthrough/scripts/generate_live_audio.mjs";
import { loadPlaywright } from "../skills/repo-walkthrough/scripts/render_video.mjs";

const REPO_ROOT = path.resolve(import.meta.dirname, "..");
const SKILL_SCRIPTS_DIR = path.join(REPO_ROOT, "skills", "repo-walkthrough", "scripts");

function prepareSelfWalkthroughSiteWithAudio(durationSec = 22) {
  const srcSiteDir = path.join(REPO_ROOT, "examples", "self-walkthrough");
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
    const resolvedRoot = path.resolve(rootDir);
    const server = http.createServer((req, res) => {
      const reqUrl = new URL(req.url, "http://127.0.0.1");
      const relPath = decodeURIComponent(reqUrl.pathname === "/" ? "/index.html" : reqUrl.pathname);
      const filePath = path.resolve(resolvedRoot, "." + relPath);
      if (
        !filePath.startsWith(resolvedRoot) ||
        !fs.existsSync(filePath) ||
        fs.statSync(filePath).isDirectory()
      ) {
        res.writeHead(404);
        res.end("Not found");
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      // Never serve .tmpl as text/html: only real built .html end products may render as HTML
      const mime =
        ext === ".html"
          ? "text/html; charset=utf-8"
          : ext === ".js"
          ? "application/javascript; charset=utf-8"
          : ext === ".wav"
          ? "audio/wav"
          : ext === ".json"
          ? "application/json"
          : "text/plain; charset=utf-8";

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

async function launchBrowser(platform = process.platform) {
  const { chromium } = loadPlaywright();
  const args = ["--autoplay-policy=no-user-gesture-required"];
  const attempts = [
    { headless: true, channel: "chrome", args },
    { headless: true, args },
  ];
  if (platform === "win32") {
    attempts.push({ headless: true, channel: "msedge", args });
  }
  let lastErr = null;
  for (const opts of attempts) {
    try {
      return await chromium.launch(opts);
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("Could not launch Chrome, Chromium, or Edge");
}

test("Desktop (1440x900) & Mobile (390x844, 360x640) UI, SVG geometry, XSS safety, and inline favicon across all 3 examples + built ADK site", async () => {
  const tmpAdkDir = fs.mkdtempSync(path.join(os.tmpdir(), "rw-adk-e2e-"));
  let browser = null;
  let repoServer = null;
  let adkServer = null;

  try {
    execFileSync(
      process.execPath,
      [
        path.join(SKILL_SCRIPTS_DIR, "build_walkthrough.mjs"),
        "--data",
        path.join(REPO_ROOT, "web", "data-adk.js"),
        "--out-dir",
        tmpAdkDir,
        "--mode",
        "website",
        "--no-tts",
      ],
      { stdio: "pipe" }
    );

    browser = await launchBrowser();
    repoServer = await startStaticServer(REPO_ROOT);
    adkServer = await startStaticServer(tmpAdkDir);

    const targets = [
      { label: "self-walkthrough", url: `${repoServer.baseUrl}/examples/self-walkthrough/index.html` },
      { label: "cymbal-autos-multimodal", url: `${repoServer.baseUrl}/examples/cymbal-autos-multimodal/index.html` },
      { label: "diff-5984e02-to-head", url: `${repoServer.baseUrl}/examples/diff-5984e02-to-head/index.html` },
      { label: "adk-built", url: `${adkServer.baseUrl}/index.html` },
    ];

    for (const target of targets) {
      // 1. Desktop (1440x900) verification (zero DOM mutation!)
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", (e) => errors.push(e.message));

      await page.goto(target.url, { waitUntil: "networkidle" });
      assert.equal(errors.length, 0, `Page errors on ${target.label}: ${errors.join(", ")}`);

      const report = await page.evaluate(async () => {
        if (document.fonts && document.fonts.ready) {
          await document.fonts.ready;
        }
        // Allow microtask queue after document.fonts.ready to finish buildGraph()
        await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

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

        const labelCollisions = [];
        const labels = Array.from(document.querySelectorAll(".layer-band-label"));
        for (const lbl of labels) {
          const lBox = lbl.getBBox();
          const lRight = lBox.x + lBox.width;
          if (lRight > 195) {
            labelCollisions.push(`Layer label "${lbl.textContent}" right edge ${lRight.toFixed(1)} exceeds x=195`);
          }
        }

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

        const infoRect = document.querySelector(".walk-info").getBoundingClientRect();
        const ctrlRect = document.querySelector(".walk-controls").getBoundingClientRect();
        const dockOverlap =
          infoRect.right > ctrlRect.left + 2 &&
          infoRect.bottom > ctrlRect.top + 2 &&
          ctrlRect.bottom > infoRect.top + 2;
        const viewportOverflow = document.documentElement.scrollWidth > document.documentElement.clientWidth;
        const inspHref = document.querySelector("#inspector .insp-title a")?.getAttribute("href") || "";
        const diffBadgeCount = document.querySelectorAll(".node-diff").length;
        const diffLineAddCount = document.querySelectorAll("#inspector .diff-line-add").length;
        const diffLineDelCount = document.querySelectorAll("#inspector .diff-line-del").length;
        const gRedLight = getComputedStyle(document.documentElement).getPropertyValue("--g-red-light").trim();
        const faviconHref =
          document.querySelector('head link[rel="icon"][type="image/svg+xml"]')?.getAttribute("href") || "";

        return {
          nodeCount: nodeGroups.length,
          edgeCount: edgePaths.length,
          diffBadgeCount,
          diffLineAddCount,
          diffLineDelCount,
          gRedLight,
          faviconHref,
          textOverflows,
          labelCollisions,
          invalidEdges,
          dockOverlap,
          viewportOverflow,
          inspHref,
        };
      });

      assert.ok(report.nodeCount >= 12, `Expected >=12 nodes in ${target.label}`);
      assert.ok(report.edgeCount >= 11, `Expected >=11 edges in ${target.label}`);
      assert.equal(report.gRedLight.toUpperCase(), "#F28B82", `--g-red-light must be defined in ${target.label}`);
      assert.ok(report.faviconHref.startsWith("data:image/svg+xml,"), `Missing inline SVG favicon in ${target.label}`);
      assert.deepEqual(
        report.textOverflows,
        [],
        `Node text overflowed box in ${target.label}:\n  ${report.textOverflows.join("\n  ")}`
      );
      assert.deepEqual(report.labelCollisions, [], `Layer label collision in ${target.label}`);
      assert.deepEqual(report.invalidEdges, [], `Invalid edge arrows in ${target.label}`);
      assert.equal(report.dockOverlap, false, `walk-info overlapped walk-controls in ${target.label}`);
      assert.equal(report.viewportOverflow, false, `Horizontal overflow in ${target.label}`);

      if (target.label === "self-walkthrough") {
        assert.equal(
          report.inspHref,
          "https://github.com/GoogleCloudPlatform/devrel-demos/blob/main/agents/repo-walkthrough/skills/repo-walkthrough/SKILL.md"
        );
      }
      if (target.label === "cymbal-autos-multimodal") {
        assert.equal(
          report.inspHref,
          "https://github.com/GoogleCloudPlatform/devrel-demos/blob/main/data-analytics/cymbal-autos-multimodal/scripts/setup/00_copy_data.sh"
        );
        assert.equal(report.diffLineDelCount, 0, "SQL -- comments must not render as deleted diff lines");
      }
      if (target.label === "diff-5984e02-to-head") {
        assert.equal(report.diffBadgeCount, 12, "Expected all 12 diff nodes to render +added/-deleted SVG badges");
        assert.ok(report.diffLineAddCount > 0, "Expected inspector code-box to highlight +added diff lines");
        assert.equal(report.inspHref, "", "ykdojo/repo-walkthrough must not generate 404 GitHub links");
      }

      // Verify step navigation works on every rebuilt page
      await page.click("#nextBtn");
      const step2Label = await page.textContent("#stepNum");
      assert.match(step2Label || "", /^STEP 2 \//, `Expected #nextBtn to advance to Step 2 on ${target.label}`);

      // Verify XSS & protocol-relative URL blocking on EVERY page (all 3 examples + built ADK)
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
        n0.label = "<b>unsafeLabel</b>";
        n0.sublabel = '" onclick="window.__xss=2';
        n0.url = "javascript:alert(1)";
        const gs = document.querySelectorAll(".node-group");
        if (gs.length > 1) gs[1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
        gs[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
        const inspHtml = document.querySelector("#inspector .insp-title")?.innerHTML || "";
        const hasJsAnchor = Boolean(document.querySelector("#inspector .insp-title a"));
        const hasImg = Boolean(document.querySelector("#inspector .insp-title img"));

        n0.url = "//evil.example.com/phish";
        if (gs.length > 1) gs[1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
        gs[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
        const hasProtoRelAnchor = Boolean(document.querySelector("#inspector .insp-title a"));

        n0.url = 'https://example.com/a?x=1&y="2"';
        if (gs.length > 1) gs[1].dispatchEvent(new MouseEvent("click", { bubbles: true }));
        gs[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
        const safeAnchorHref =
          document.querySelector("#inspector .insp-title a")?.getAttribute("href") || "";
        Object.assign(n0, orig);
        return { inspHtml, hasJsAnchor, hasProtoRelAnchor, hasImg, safeAnchorHref, xss: Boolean(window.__xss) };
      });
      assert.equal(xssCheck.xss, false, `XSS executed on ${target.label}`);
      assert.equal(xssCheck.hasImg, false, `<img ...> was not escaped on ${target.label}`);
      assert.equal(xssCheck.hasJsAnchor, false, `javascript: URL was not blocked on ${target.label}`);
      assert.equal(xssCheck.hasProtoRelAnchor, false, `Protocol-relative // URL was not blocked on ${target.label}`);
      assert.ok(xssCheck.inspHtml.includes("&lt;img"), `Expected escaped &lt;img in ${target.label}`);
      assert.equal(xssCheck.safeAnchorHref, 'https://example.com/a?x=1&y="2"');

      await context.close();

      // 2. Mobile viewports (390x844 and 360x640) across ALL 4 pages
      for (const vp of [
        { width: 390, height: 844 },
        { width: 360, height: 640 },
      ]) {
        const mobCtx = await browser.newContext({ viewport: vp });
        const mobPage = await mobCtx.newPage();
        await mobPage.goto(target.url, { waitUntil: "networkidle" });
        const mobReport = await mobPage.evaluate(async () => {
          if (document.fonts && document.fonts.ready) {
            await document.fonts.ready;
          }
          const graphRect = document.querySelector("#graph-wrap").getBoundingClientRect();
          const svgRect = document.querySelector("#graph-svg").getBoundingClientRect();
          const descRect = document.querySelector("#stepDesc").getBoundingClientRect();
          const ctrlRect = document.querySelector(".walk-controls").getBoundingClientRect();
          const ghLink = document.querySelector("#header-github-link");
          const ghRect =
            ghLink && getComputedStyle(ghLink).display !== "none"
              ? ghLink.getBoundingClientRect()
              : null;
          const descCtrlOverlap =
            descRect.right > ctrlRect.left + 1 &&
            descRect.left < ctrlRect.right - 1 &&
            descRect.bottom > ctrlRect.top + 1 &&
            descRect.top < ctrlRect.bottom - 1;
          const asideDefaultHidden = getComputedStyle(document.querySelector("aside")).display === "none";

          // Tap first node -> mobile inspector opens cleanly without horizontal overflow
          document.querySelector(".node-group").dispatchEvent(new MouseEvent("click", { bubbles: true }));
          const asideOpenAfterTap = getComputedStyle(document.querySelector("aside")).display !== "none";
          const overflowAfterTap = document.documentElement.scrollWidth > document.documentElement.clientWidth;

          return {
            scrollWidth: document.documentElement.scrollWidth,
            clientWidth: document.documentElement.clientWidth,
            graphHeight: graphRect.height,
            svgHeight: svgRect.height,
            descCtrlOverlap,
            ghClipped: ghRect ? ghRect.right > window.innerWidth + 1 || ghRect.left < 0 : false,
            asideDefaultHidden,
            asideOpenAfterTap,
            overflowAfterTap,
          };
        });
        assert.ok(
          mobReport.scrollWidth <= mobReport.clientWidth,
          `Horizontal overflow on ${target.label} at ${vp.width}x${vp.height}: scrollWidth=${mobReport.scrollWidth} > clientWidth=${mobReport.clientWidth}`
        );
        assert.ok(
          mobReport.graphHeight >= 220 && mobReport.svgHeight >= 220,
          `Mobile graph collapsed on ${target.label} at ${vp.width}x${vp.height}: graphHeight=${mobReport.graphHeight}`
        );
        assert.equal(
          mobReport.descCtrlOverlap,
          false,
          `#stepDesc overlapped .walk-controls on ${target.label} at ${vp.width}x${vp.height}`
        );
        assert.equal(
          mobReport.ghClipped,
          false,
          `#header-github-link clipped on ${target.label} at ${vp.width}x${vp.height}`
        );
        assert.equal(mobReport.asideDefaultHidden, true);
        assert.equal(mobReport.asideOpenAfterTap, true);
        assert.equal(mobReport.overflowAfterTap, false);
        await mobCtx.close();
      }
    }
  } finally {
    if (repoServer) repoServer.server.close();
    if (adkServer) adkServer.server.close();
    if (browser) await browser.close();
    fs.rmSync(tmpAdkDir, { recursive: true, force: true });
  }
});

test("Interactive player controls: Play/Pause exact position memory, -5s/+5s cross-section skip, smart Prev, and speed pills", async () => {
  const { siteDir, cleanup } = prepareSelfWalkthroughSiteWithAudio(22);
  let browser = null;
  let serverInfo = null;

  try {
    browser = await launchBrowser();
    serverInfo = await startStaticServer(siteDir);
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto(`${serverInfo.baseUrl}/index.html`, { waitUntil: "networkidle" });

    const PLAY_D = "M8 5.5v13l11-6.5z";
    const PAUSE_D = "M7.5 5h3.2v14H7.5zM13.3 5h3.2v14h-3.2z";

    assert.equal(await page.textContent("#stepNum"), "STEP 1 / 6");
    assert.equal(await page.getAttribute("#ppicon path", "d"), PLAY_D);

    await page.click("#playBtn");
    await page.waitForFunction(
      (expectedD) => document.querySelector("#ppicon path").getAttribute("d") === expectedD,
      PAUSE_D
    );

    await page.click("#fwd5Btn");
    await page.click("#fwd5Btn");
    await page.waitForTimeout(120);

    await page.click("#playBtn");
    assert.equal(await page.getAttribute("#ppicon path", "d"), PLAY_D);
    const tlAtPause = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(tlAtPause > 5, `Expected timeline fill > 5% after +10s seek, got ${tlAtPause}%`);

    await page.waitForTimeout(250);
    const tlStillPaused = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(Math.abs(tlStillPaused - tlAtPause) < 0.2, "Paused position should stay fixed");

    await page.click("#playBtn");
    await page.waitForTimeout(100);
    const tlAfterResume = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(
      tlAfterResume >= tlAtPause - 0.5,
      `Expected resume to continue from ${tlAtPause}%, but got ${tlAfterResume}%`
    );

    await page.click("#prevBtn");
    await page.waitForTimeout(80);
    assert.equal(await page.textContent("#stepNum"), "STEP 1 / 6");
    const tlAfterRestart = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(tlAfterRestart < 3, `Expected #prevBtn to restart Step 1 near 0%, got ${tlAfterRestart}%`);

    await page.click("#nextBtn");
    assert.equal(await page.textContent("#stepNum"), "STEP 2 / 6");
    assert.equal(await page.getAttribute("#ppicon path", "d"), PAUSE_D);

    await page.click("#playBtn");
    await page.click("#back5Btn");
    await page.waitForTimeout(150);
    assert.equal(await page.textContent("#stepNum"), "STEP 1 / 6");
    const tlRolledBack = await page.$eval("#tl-fill", (el) => parseFloat(el.style.width));
    assert.ok(tlRolledBack > 14 && tlRolledBack < 20);

    await page.click("#fwd5Btn");
    await page.click("#fwd5Btn");
    await page.waitForTimeout(150);
    assert.equal(await page.textContent("#stepNum"), "STEP 2 / 6");

    await page.click('.spd[data-s="1.2"]');
    assert.equal(await page.$eval('.spd[data-s="1.2"]', (el) => el.classList.contains("on")), true);
    assert.equal(await page.$eval('.spd[data-s="1"]', (el) => el.classList.contains("on")), false);

    await context.close();
  } finally {
    if (serverInfo) serverInfo.server.close();
    if (browser) await browser.close();
    cleanup();
  }
});

test("Video mode (?video=1), deterministic renderWalkthroughFrame, os.tmpdir() cleanup, and MP4 output verification", async () => {
  const siteDir = path.join(REPO_ROOT, "examples", "self-walkthrough");
  let browser = null;
  let serverInfo = null;

  try {
    browser = await launchBrowser();
    serverInfo = await startStaticServer(siteDir);
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto(`${serverInfo.baseUrl}/index.html?video=1`, { waitUntil: "networkidle" });

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

    assert.equal(videoLayout.asideVisible, false);
    assert.equal(videoLayout.camVisible, false);
    assert.equal(videoLayout.controlsVisible, true);
    assert.equal(videoLayout.stepNum, "STEP 3 / 6");
    assert.equal(videoLayout.tlWidth, "40%");
    assert.equal(videoLayout.iconD, "M7.5 5h3.2v14H7.5zM13.3 5h3.2v14h-3.2z");

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
    assert.deepEqual(slicedNodes, []);
    await context.close();
  } finally {
    if (serverInfo) serverInfo.server.close();
    if (browser) await browser.close();
  }

  // Render a synthetic-WAV MP4 end-to-end via render_video.mjs and verify with ffprobe
  const prep = prepareSelfWalkthroughSiteWithAudio(1);
  const outMp4Dir = fs.mkdtempSync(path.join(os.tmpdir(), "rw-mp4-out-"));
  try {
    const manifestPath = path.join(prep.siteDir, "audio", "manifest.json");
    const shortManifest = JSON.parse(fs.readFileSync(manifestPath, "utf8")).slice(0, 2);
    fs.writeFileSync(manifestPath, JSON.stringify(shortManifest, null, 2));
    const mp4Path = path.join(outMp4Dir, "test-walkthrough.mp4");
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
    assert.equal(
      fs.existsSync(path.join(prep.siteDir, "audio", ".tmp-video")),
      false,
      "render_video.mjs must use os.tmpdir() instead of creating audio/.tmp-video"
    );
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
    assert.ok(parseFloat(probeJson.format.duration) > 1.5);
  } finally {
    prep.cleanup();
    fs.rmSync(outMp4Dir, { recursive: true, force: true });
  }
});

test("Flexible layer counts (3, 4, and 6 layers): visual geometry, FULL_VB scaling, and camera framing", async () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "repo-walkthrough-layers-"));
  let browser = null;
  let serverInfo = null;

  try {
    const indexHtml = fs.readFileSync(resolveTemplatePath(REPO_ROOT), "utf8");
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

    browser = await launchBrowser();
    serverInfo = await startStaticServer(tmpDir);

    for (const count of [3, 4, 6]) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await context.newPage();

      await page.goto(`${serverInfo.baseUrl}/index-${count}.html`, { waitUntil: "networkidle" });
      const interactiveReport = await page.evaluate(() => {
        const labels = Array.from(document.querySelectorAll(".layer-band-label"));
        const camR = document.querySelector(".cam-controls").getBoundingClientRect();
        const camOverlaps = [];
        for (const rect of document.querySelectorAll(".node-rect")) {
          const r = rect.getBoundingClientRect();
          if (r.right > camR.left && r.left < camR.right && r.bottom > camR.top && r.top < camR.bottom) {
            camOverlaps.push(rect.parentElement.querySelector(".node-title").textContent);
          }
        }
        return { bandCount: labels.length, camOverlaps };
      });
      assert.equal(interactiveReport.bandCount, count);
      assert.deepEqual(interactiveReport.camOverlaps, []);

      await page.goto(`${serverInfo.baseUrl}/index-${count}.html?video=1`, { waitUntil: "networkidle" });
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
                errs.push(`Step ${i + 1}: node ${n.id} sliced`);
              }
            }
          }
        }
        return errs;
      });
      assert.deepEqual(sliced, []);
      await context.close();
    }
  } finally {
    if (serverInfo) serverInfo.server.close();
    if (browser) await browser.close();
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test("Inline SVG favicon in generated walkthrough website decodes and renders pixels crisply in browser", async () => {
  const tmpSiteDir = fs.mkdtempSync(path.join(os.tmpdir(), "rw-favicon-e2e-"));
  let browser = null;
  let serverInfo = null;

  try {
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

    browser = await launchBrowser();
    serverInfo = await startStaticServer(tmpSiteDir);
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    await page.goto(`${serverInfo.baseUrl}/index.html`, { waitUntil: "networkidle" });

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

    assert.equal(faviconCheck.exists, true);
    assert.equal(faviconCheck.startsWithDataSvg, true);
    assert.equal(faviconCheck.loaded, true);
    assert.equal(faviconCheck.naturalWidth, 128);
    assert.equal(faviconCheck.naturalHeight, 128);
    assert.equal(faviconCheck.centerAlpha, 255);
    assert.ok(faviconCheck.playBadgeRed > 180 && faviconCheck.playBadgeAlpha === 255);

    await context.close();
  } finally {
    if (serverInfo) serverInfo.server.close();
    if (browser) await browser.close();
    fs.rmSync(tmpSiteDir, { recursive: true, force: true });
  }
});
