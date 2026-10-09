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
 * Generate spoken walkthrough audio for each step using the dedicated Gemini TTS
 * audio generation model (`gemini-3.1-flash-tts-preview` via `generateContent`),
 * using a single female speaker ("Despina") and content-hash caching so identical
 * text is never re-generated.
 *
 * Usage:
 *   node scripts/generate_live_audio.mjs [--data <path/to/data.js>] [--out-dir <path/to/audio-dir>] [--voice Despina] [--force]
 *
 * Key resolution order:
 *   1. GEMINI_API_KEY environment variable
 *   2. macOS Keychain (service "gemini-api-key", account "$USER")
 *   3. .env file in working directory
 */

import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";

const DEFAULT_MODEL = process.env.GEMINI_TTS_MODEL || "gemini-3.1-flash-tts-preview";
const DEFAULT_VOICE = process.env.GEMINI_VOICE || "Despina"; // Single female speaker
const TTS_STYLE_PREFIX =
  "Speak the following codebase walkthrough step naturally at a relaxed, clear, conversational pace:\n";

function parseArgs(argv) {
  const opts = {
    dataFile: null,
    outDir: null,
    voice: DEFAULT_VOICE,
    model: DEFAULT_MODEL,
    force: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--data" && argv[i + 1]) opts.dataFile = path.resolve(argv[++i]);
    else if (a === "--out-dir" && argv[i + 1]) opts.outDir = path.resolve(argv[++i]);
    else if (a === "--voice" && argv[i + 1]) opts.voice = argv[++i];
    else if (a === "--model" && argv[i + 1]) opts.model = argv[++i];
    else if (a === "--force") opts.force = true;
  }
  return opts;
}

function resolveGeminiApiKey(repoRoot) {
  if (process.env.GEMINI_API_KEY && process.env.GEMINI_API_KEY.trim()) {
    return process.env.GEMINI_API_KEY.trim();
  }
  if (process.platform === "darwin") {
    try {
      const key = execFileSync(
        "security",
        ["find-generic-password", "-s", "gemini-api-key", "-w"],
        { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }
      ).trim();
      if (key) return key;
    } catch {}
  }
  const envCandidates = [path.resolve(".env")];
  if (repoRoot) envCandidates.push(path.join(repoRoot, ".env"));
  for (const envPath of envCandidates) {
    if (fs.existsSync(envPath)) {
      const envText = fs.readFileSync(envPath, "utf8");
      for (const line of envText.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (trimmed.startsWith("GEMINI_API_KEY=")) {
          const val = trimmed.slice("GEMINI_API_KEY=".length).trim().replace(/^['"]|['"]$/g, "");
          if (val) return val;
        }
      }
    }
  }
  throw new Error(
    "Could not resolve GEMINI_API_KEY from env, macOS keychain ('gemini-api-key'), or .env"
  );
}

function sanitizeForTts(rawText = "") {
  return rawText
    .replace(/`/g, "")
    .replace(/\b__([a-zA-Z0-9_]+)__/g, "$1") // __init__.py -> init.py
    .replace(/\b_([a-zA-Z0-9_]+)/g, "$1")    // _workflow.py -> workflow.py
    .replace(/_/g, " ")                      // cli_tools_click.py -> cli tools click.py
    .replace(/\s+/g, " ")
    .trim();
}

function computeContentHash(model, voice, text) {
  const clean = sanitizeForTts(text);
  return crypto
    .createHash("sha256")
    .update(`${model}|${voice}|${clean}`)
    .digest("hex")
    .slice(0, 16);
}

function createWavBuffer(pcmBuffer, sampleRate = 24000, numChannels = 1, bitsPerSample = 16) {
  const header = Buffer.alloc(44);
  const byteRate = (sampleRate * numChannels * bitsPerSample) / 8;
  const blockAlign = (numChannels * bitsPerSample) / 8;
  const dataSize = pcmBuffer.length;

  header.write("RIFF", 0);
  header.writeUInt32LE(36 + dataSize, 4);
  header.write("WAVE", 8);
  header.write("fmt ", 12);
  header.writeUInt32LE(16, 16); // Subchunk1Size (PCM)
  header.writeUInt16LE(1, 20);  // AudioFormat (1 = PCM)
  header.writeUInt16LE(numChannels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(byteRate, 28);
  header.writeUInt16LE(blockAlign, 32);
  header.writeUInt16LE(bitsPerSample, 34);
  header.write("data", 36);
  header.writeUInt32LE(dataSize, 40);

  return Buffer.concat([header, pcmBuffer]);
}

async function synthesizeTts(apiKey, text, { model = DEFAULT_MODEL, voice = DEFAULT_VOICE } = {}) {
  const cleanText = sanitizeForTts(text);
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
  const body = {
    contents: [
      {
        parts: [{ text: `${TTS_STYLE_PREFIX}${cleanText}` }],
      },
    ],
    generationConfig: {
      responseModalities: ["AUDIO"],
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: {
            voiceName: voice,
          },
        },
      },
    },
  };

  for (let attempt = 0; attempt < 4; attempt++) {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (resp.status === 429 && attempt < 3) {
      const waitMs = (attempt + 1) * 8000;
      process.stdout.write(`[429 rate-limit, retrying in ${waitMs / 1000}s] `);
      await new Promise((r) => setTimeout(r, waitMs));
      continue;
    }

    let json;
    try {
      json = await resp.json();
    } catch {
      throw new Error(`Gemini TTS API returned non-JSON response (HTTP ${resp.status})`);
    }
    if (!resp.ok || json.error) {
      throw new Error(`Gemini TTS API error (${resp.status}): ${JSON.stringify(json.error || json)}`);
    }

    const b64 = json?.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
    if (!b64) {
      throw new Error(`No audio data returned by ${model}`);
    }
    return Buffer.from(b64, "base64");
  }
}

function extractPcmSegments(wavBuffer, minWins = 10) {
  const sr = 24000;
  const totalSamples = Math.max(0, Math.floor((wavBuffer.length - 44) / 2));
  const totalDur = totalSamples / sr;
  const winSamples = Math.floor(sr * 0.02); // 20ms windows
  const isSilent = [];
  for (let i = 0; i < totalSamples; i += winSamples) {
    let sumSq = 0;
    let count = 0;
    for (let j = i; j < Math.min(totalSamples, i + winSamples); j++) {
      const s = wavBuffer.readInt16LE(44 + j * 2) / 32768;
      sumSq += s * s;
      count++;
    }
    isSilent.push(Math.sqrt(sumSq / Math.max(1, count)) < 0.008);
  }
  const segments = [];
  let segStartW = null;
  let silenceRun = 0;
  for (let w = 0; w < isSilent.length; w++) {
    if (!isSilent[w]) {
      if (segStartW === null) segStartW = w;
      silenceRun = 0;
    } else if (segStartW !== null) {
      silenceRun++;
      if (silenceRun >= minWins) {
        const endW = w - silenceRun + 1;
        segments.push({
          startSec: +(segStartW * 0.02).toFixed(2),
          endSec: +(endW * 0.02).toFixed(2),
        });
        segStartW = null;
        silenceRun = 0;
      }
    }
  }
  if (segStartW !== null) {
    segments.push({
      startSec: +(segStartW * 0.02).toFixed(2),
      endSec: +totalDur.toFixed(2),
    });
  }
  return { segments, totalDur, totalSamples, sr };
}

function sliceWavBase64(wavBuffer, startSec, endSec, sr = 24000, totalSamples = 0) {
  const s0 = Math.max(0, Math.floor(startSec * sr));
  const s1 = Math.min(totalSamples, Math.ceil(endSec * sr));
  const pcmLen = Math.max(0, (s1 - s0) * 2);
  const out = Buffer.alloc(44 + pcmLen);
  wavBuffer.copy(out, 0, 0, 44);
  out.writeUInt32LE(36 + pcmLen, 4);
  out.writeUInt32LE(pcmLen, 40);
  wavBuffer.copy(out, 44, 44 + s0 * 2, 44 + s1 * 2);
  return out.toString("base64");
}

function normalizeMatchText(s = "") {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function computeAcousticCueAt(alignedSegments, totalDur, phrase = "", cueIndex = 0) {
  if (cueIndex === 0 || !phrase || !alignedSegments?.length || !(totalDur > 0)) return 0;
  const normPhrase = normalizeMatchText(phrase);
  if (!normPhrase) return 0;

  for (const seg of alignedSegments) {
    const normSeg = normalizeMatchText(seg.text || "");
    const idx = normSeg.indexOf(normPhrase);
    if (idx >= 0) {
      const frac = normSeg.length > 0 ? idx / normSeg.length : 0;
      const exactSec = seg.startSec + (seg.endSec - seg.startSec) * frac;
      return Number(Math.min(0.99, Math.max(0, exactSec / totalDur)).toFixed(2));
    }
  }
  // Fallback: check across two consecutive segments in case a phrase spans a short pause
  for (let i = 0; i < alignedSegments.length - 1; i++) {
    const sA = alignedSegments[i];
    const sB = alignedSegments[i + 1];
    const normA = normalizeMatchText(sA.text || "");
    const normB = normalizeMatchText(sB.text || "");
    const combined = `${normA} ${normB}`.trim();
    const idx = combined.indexOf(normPhrase);
    if (idx >= 0) {
      if (idx < normA.length) {
        const frac = normA.length > 0 ? idx / normA.length : 0;
        const exactSec = sA.startSec + (sA.endSec - sA.startSec) * frac;
        return Number(Math.min(0.99, Math.max(0, exactSec / totalDur)).toFixed(2));
      } else {
        const idxB = Math.max(0, idx - normA.length - 1);
        const fracB = normB.length > 0 ? idxB / normB.length : 0;
        const exactSec = sB.startSec + (sB.endSec - sB.startSec) * fracB;
        return Number(Math.min(0.99, Math.max(0, exactSec / totalDur)).toFixed(2));
      }
    }
  }
  return null;
}

async function alignStepSegmentsWithGemini(apiKey, wavBuffer, narration, { hash, localCacheDir, sharedCacheDir, force = false }) {
  const localSegPath = path.join(localCacheDir, `${hash}.segments.json`);
  const sharedSegPath = path.join(sharedCacheDir, `${hash}.segments.json`);
  const { segments, totalDur, totalSamples, sr } = extractPcmSegments(wavBuffer, 10);

  if (!force && fs.existsSync(localSegPath)) {
    return { alignedSegments: JSON.parse(fs.readFileSync(localSegPath, "utf8")), totalDur };
  }
  if (!force && fs.existsSync(sharedSegPath)) {
    fs.copyFileSync(sharedSegPath, localSegPath);
    return { alignedSegments: JSON.parse(fs.readFileSync(sharedSegPath, "utf8")), totalDur };
  }

  const parts = [
    {
      text: `Exact narration script:\n"${narration}"\n\nTranscribe each numbered audio segment below using the exact words from the script. Return JSON array: [{"seg": 0, "text": "..."}]`,
    },
  ];
  segments.forEach((seg, idx) => {
    parts.push({ text: `Segment ${idx} (${seg.startSec}s - ${seg.endSec}s):` });
    parts.push({
      inlineData: {
        mimeType: "audio/wav",
        data: sliceWavBase64(wavBuffer, seg.startSec, seg.endSec, sr, totalSamples),
      },
    });
  });

  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=${apiKey}`;
  let parsed = null;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: AbortSignal.timeout(25000),
        body: JSON.stringify({
          contents: [{ parts }],
          generationConfig: {
            responseMimeType: "application/json",
            temperature: 0,
            thinkingConfig: { thinkingLevel: "MINIMAL" },
          },
        }),
      });
      const json = await resp.json();
      if (!resp.ok || json.error) {
        throw new Error(`Gemini segment alignment error (${resp.status}): ${JSON.stringify(json.error || json)}`);
      }
      parsed = JSON.parse(json.candidates[0].content.parts[0].text);
      break;
    } catch (err) {
      if (attempt === 2) throw err;
      await new Promise((r) => setTimeout(r, 1500));
    }
  }
  const alignedSegments = segments.map((s, idx) => {
    const found = parsed.find((p) => p.seg === idx);
    return { seg: idx, startSec: s.startSec, endSec: s.endSec, text: found?.text || "" };
  });
  fs.writeFileSync(localSegPath, JSON.stringify(alignedSegments, null, 2));
  if (localSegPath !== sharedSegPath) {
    fs.copyFileSync(localSegPath, sharedSegPath);
  }
  return { alignedSegments, totalDur };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const repoRoot = path.resolve(import.meta.dirname, "..");
  const defaultWebDir = path.join(repoRoot, "web");
  const dataFile = opts.dataFile || (
    fs.existsSync(path.join(defaultWebDir, "data.js"))
      ? path.join(defaultWebDir, "data.js")
      : path.join(defaultWebDir, "data-adk.js")
  );
  const siteDir = path.dirname(dataFile);
  const outDir = opts.outDir || path.join(siteDir, "audio");
  const sharedCacheDir = path.join(repoRoot, "web", "audio", "cache");
  const localCacheDir = path.join(outDir, "cache");
  fs.mkdirSync(outDir, { recursive: true });
  fs.mkdirSync(localCacheDir, { recursive: true });
  fs.mkdirSync(sharedCacheDir, { recursive: true });

  const sandbox = { window: {} };
  vm.runInNewContext(fs.readFileSync(dataFile, "utf8"), sandbox);
  const data = sandbox.window.WALKTHROUGH_DATA || sandbox.window.ADK_DATA;
  if (!data || !Array.isArray(data.walkthrough)) {
    throw new Error(`Invalid walkthrough data in ${dataFile} (expected window.WALKTHROUGH_DATA or window.ADK_DATA)`);
  }

  const { model, voice, force } = opts;
  let apiKey = null;

  console.log(
    `🎙️  Generating TTS audio for ${data.walkthrough.length} walkthrough steps from ${path.basename(dataFile)} (model: ${model}, female voice: ${voice})...`
  );

  const manifest = [];
  const stepBuffers = [];
  for (const st of data.walkthrough) {
    const hash = computeContentHash(model, voice, st.narration);
    const localCachedWav = path.join(localCacheDir, `${hash}.wav`);
    const sharedCachedWav = path.join(sharedCacheDir, `${hash}.wav`);
    const stepFileName = `step-${st.step}.wav`;
    const stepFilePath = path.join(outDir, stepFileName);

    process.stdout.write(`  • Step ${st.step}/${data.walkthrough.length} [${hash}]: "${st.title.replace(/`/g, "")}" ... `);

    let wavBuffer = null;
    if (!force && fs.existsSync(localCachedWav)) {
      wavBuffer = fs.readFileSync(localCachedWav);
    } else if (!force && fs.existsSync(sharedCachedWav)) {
      wavBuffer = fs.readFileSync(sharedCachedWav);
      fs.copyFileSync(sharedCachedWav, localCachedWav);
    }

    if (wavBuffer) {
      fs.writeFileSync(stepFilePath, wavBuffer);
      const pcmBytes = Math.max(0, wavBuffer.length - 44);
      const durationSec = +(pcmBytes / (24000 * 2)).toFixed(2);
      console.log(`cached (${durationSec}s -> audio/${stepFileName})`);
      stepBuffers.push({ st, hash, wavBuffer, durationSec });
      manifest.push({
        step: st.step,
        title: st.title,
        hash,
        model,
        voice,
        file: `audio/${stepFileName}`,
        cachedFile: `audio/cache/${hash}.wav`,
        durationSec,
      });
      continue;
    }

    if (!apiKey) apiKey = resolveGeminiApiKey(repoRoot);
    const t0 = Date.now();
    const pcm = await synthesizeTts(apiKey, st.narration, { model, voice });
    wavBuffer = createWavBuffer(pcm, 24000, 1, 16);
    fs.writeFileSync(localCachedWav, wavBuffer);
    if (localCachedWav !== sharedCachedWav) {
      fs.copyFileSync(localCachedWav, sharedCachedWav);
    }
    fs.writeFileSync(stepFilePath, wavBuffer);

    const durationSec = +(pcm.length / (24000 * 2)).toFixed(2);
    const elapsedSec = +((Date.now() - t0) / 1000).toFixed(2);
    console.log(`generated (${durationSec}s audio in ${elapsedSec}s -> audio/cache/${hash}.wav)`);
    stepBuffers.push({ st, hash, wavBuffer, durationSec });

    manifest.push({
      step: st.step,
      title: st.title,
      hash,
      model,
      voice,
      file: `audio/${stepFileName}`,
      cachedFile: `audio/cache/${hash}.wav`,
      durationSec,
    });
  }

  // Align cues against actual PCM silence segments + Gemini transcription
  if (!apiKey) {
    try {
      apiKey = resolveGeminiApiKey(repoRoot);
    } catch {}
  }
  if (apiKey) {
    console.log(`🎯 Aligning step cues to acoustic WAV segments via Gemini (gemini-3-flash-preview)...`);
    await Promise.all(
      stepBuffers.map(async ({ st, hash, wavBuffer, durationSec }, idx) => {
        try {
          const { alignedSegments } = await alignStepSegmentsWithGemini(apiKey, wavBuffer, st.narration, {
            hash,
            localCacheDir,
            sharedCacheDir,
            force,
          });
          manifest[idx].segments = alignedSegments;
          if (Array.isArray(st.cues)) {
            manifest[idx].alignedCues = st.cues.map((c, cIdx) => {
              const acousticAt = computeAcousticCueAt(alignedSegments, durationSec, c.phrase, cIdx);
              return {
                ...c,
                at: acousticAt !== null ? acousticAt : c.at,
              };
            });
          }
        } catch (err) {
          console.warn(`  ⚠️ Acoustic alignment warning on Step ${st.step}: ${err.message}`);
        }
      })
    );
  }

  fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));
  console.log(`✅ All ${manifest.length} TTS audio files ready in ${outDir} (with content-hash cache)`);
}

export {
  parseArgs,
  sanitizeForTts,
  computeContentHash,
  createWavBuffer,
  extractPcmSegments,
  computeAcousticCueAt,
};

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(import.meta.filename)) {
  main().catch((err) => {
    console.error("❌ Failed:", err.message);
    process.exit(1);
  });
}
