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
 * Generate spoken walkthrough audio for each step using the GA Gemini TTS
 * audio generation model (`gemini-3.8-flash-tts` by default, or
 * `gemini-3.8-flash-lite-tts` via `GEMINI_TTS_MODEL` / `--model`), using a
 * single female speaker ("Despina") and content-hash caching so identical
 * text is never re-generated.
 *
 * Usage:
 *   node skills/repo-walkthrough/scripts/generate_live_audio.mjs --data <path/to/data.js> [--out-dir <path/to/audio-dir>] [--voice Despina] [--model gemini-3.8-flash-tts] [--force]
 *
 * Key resolution order:
 *   1. GEMINI_API_KEY environment variable
 *   2. User-scoped .env / gemini_api_key files: $PLUGIN_DATA, %APPDATA%/repo-walkthrough,
 *      ~/.config/repo-walkthrough, and ~/.gemini
 *   3. OS credential store (service "gemini-api-key" across macOS Keychain, Linux secret-tool, and Windows Credential Manager)
 *   4. <repoRoot>/.env of the installed plugin or skill
 *   5. <cwd>/.env only when REPO_WALKTHROUGH_ALLOW_CWD_ENV=1, since the cwd may be an untrusted clone
 * Key files must be regular files (symlinks are followed only to regular files) of at most 64 KiB.
 */

import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import vm from "node:vm";

const DEFAULT_MODEL = process.env.GEMINI_TTS_MODEL || "gemini-3.8-flash-tts";
const DEFAULT_ALIGNMENT_MODEL =
  process.env.GEMINI_ALIGNMENT_MODEL || "gemini-3-flash-preview";
const DEFAULT_VOICE = process.env.GEMINI_VOICE || "Despina";
const DEFAULT_SPEECH_STYLE = "relaxed, clear, conversational pace";

const USAGE_TEXT = `Usage:
  node skills/repo-walkthrough/scripts/generate_live_audio.mjs --data <path/to/data.js> [options]

Options:
  --data <file>      Path to data.js containing window.WALKTHROUGH_DATA
  --out-dir <dir>    Output audio directory (defaults to <site-dir>/audio)
  --voice <name>     Prebuilt Gemini TTS voice name (default: Despina)
  --model <id>       Gemini TTS model ID (default: gemini-3.8-flash-tts, or gemini-3.8-flash-lite-tts)
  --force            Re-synthesize all steps even if cached WAV files exist
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

function resolveSharedCacheDir(localCacheDir, env = process.env, homedir = os.homedir()) {
  const preferred =
    env.PLUGIN_DATA && env.PLUGIN_DATA.trim()
      ? path.join(env.PLUGIN_DATA.trim(), "audio-cache")
      : path.join(homedir, ".cache", "repo-walkthrough", "audio");
  try {
    fs.mkdirSync(preferred, { recursive: true });
    fs.accessSync(preferred, fs.constants.W_OK);
    return preferred;
  } catch {
    return localCacheDir;
  }
}

function requireOptionValue(argv, index, flag) {
  const val = argv[index + 1];
  if (val === undefined || val === "" || val.startsWith("-")) {
    throw new Error(`Option ${flag} requires a value. Pass --help for usage.`);
  }
  return val;
}

function parseArgs(argv) {
  const opts = {
    dataFile: null,
    outDir: null,
    voice: DEFAULT_VOICE,
    model: DEFAULT_MODEL,
    force: false,
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
    } else if (a === "--voice") {
      opts.voice = requireOptionValue(argv, i++, "--voice");
    } else if (a === "--model") {
      opts.model = requireOptionValue(argv, i++, "--model");
    } else if (a === "--force") {
      opts.force = true;
    } else {
      throw new Error(`Unknown option: ${a}. Pass --help for usage.`);
    }
  }
  return opts;
}

const MAX_KEY_FILE_BYTES = 64 * 1024;

function readKeyFromEnvFile(envPath) {
  if (!envPath) return null;
  let envText;
  try {
    // Reject devices, FIFOs, and directories, including via symlink, and oversized files
    const link = fs.lstatSync(envPath);
    if (!link.isFile() && !link.isSymbolicLink()) return null;
    const st = link.isSymbolicLink() ? fs.statSync(envPath) : link;
    if (!st.isFile() || st.size > MAX_KEY_FILE_BYTES) return null;
    envText = fs.readFileSync(envPath, "utf8");
  } catch {
    return null;
  }
  if (path.basename(envPath) === "gemini_api_key") {
    const raw = envText.trim();
    if (raw && !raw.includes("\n") && !raw.startsWith("#")) return raw;
  }
  for (const line of envText.split(/\r?\n/)) {
    const gemMatch = line.match(/^\s*(?:export\s+)?GEMINI_API_KEY\s*=\s*(.*)$/);
    if (gemMatch) {
      const val = gemMatch[1].trim().replace(/^['"]|['"]$/g, "");
      if (val) return val;
    }
  }
  return null;
}

// Run helper executables from this script's directory, never the user's cwd, which may be an
// untrusted clone. On Windows also stop cmd.exe and CreateProcess from searching the cwd first.
function safeExecOptions(extra = {}, platform = process.platform, env = process.env) {
  const opts = { ...extra, cwd: import.meta.dirname };
  if (platform === "win32") {
    opts.env = { ...(extra.env || env), NoDefaultCurrentDirectoryInExePath: "1" };
  }
  return opts;
}

function queryOsCredentialStore(platform = process.platform, runner = execFileSync) {
  if (platform === "darwin") {
    try {
      const out = runner(
        "security",
        ["find-generic-password", "-s", "gemini-api-key", "-w"],
        safeExecOptions({ encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }, platform)
      );
      if (out && out.trim()) return out.trim();
    } catch {}
  } else if (platform === "linux") {
    try {
      const out = runner(
        "secret-tool",
        ["lookup", "service", "gemini-api-key"],
        safeExecOptions({ encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }, platform)
      );
      if (out && out.trim()) return out.trim();
    } catch {}
  } else if (platform === "win32") {
    try {
      const psCmd =
        "$c = if (Get-Command Get-StoredCredential -ErrorAction SilentlyContinue) { Get-StoredCredential -Target 'gemini-api-key' -ErrorAction SilentlyContinue } else { $null }; " +
        "if ($c -and $c.GetNetworkCredential().Password) { $c.GetNetworkCredential().Password } " +
        "else { [Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User') }";
      const out = runner(
        "powershell.exe",
        ["-NoProfile", "-NonInteractive", "-Command", psCmd],
        safeExecOptions({ encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }, platform)
      );
      if (out && out.trim()) return out.trim();
    } catch {}
  }
  return null;
}

function resolveGeminiApiKey(
  repoRoot,
  {
    env = process.env,
    platform = process.platform,
    cwd = process.cwd(),
    homedir = os.homedir(),
    runner = execFileSync,
  } = {}
) {
  if (env.GEMINI_API_KEY && env.GEMINI_API_KEY.trim()) {
    return env.GEMINI_API_KEY.trim();
  }
  // User-scoped locations first. The cwd may be an untrusted clone, so its .env is opt-in only.
  const envCandidates = [];
  if (env.PLUGIN_DATA && env.PLUGIN_DATA.trim()) {
    envCandidates.push(path.join(env.PLUGIN_DATA.trim(), ".env"));
  }
  if (env.APPDATA && env.APPDATA.trim()) {
    envCandidates.push(path.join(env.APPDATA.trim(), "repo-walkthrough", ".env"));
    envCandidates.push(path.join(env.APPDATA.trim(), "repo-walkthrough", "gemini_api_key"));
  }
  if (homedir) {
    envCandidates.push(path.join(homedir, ".config", "repo-walkthrough", ".env"));
    envCandidates.push(path.join(homedir, ".config", "repo-walkthrough", "gemini_api_key"));
    envCandidates.push(path.join(homedir, ".gemini", ".env"));
    envCandidates.push(path.join(homedir, ".gemini", "gemini_api_key"));
  }
  for (const envPath of envCandidates) {
    const val = readKeyFromEnvFile(envPath);
    if (val) return val;
  }
  const storeKey = queryOsCredentialStore(platform, runner);
  if (storeKey) return storeKey;

  const repoCandidates = [];
  if (repoRoot) repoCandidates.push(path.join(repoRoot, ".env"));
  if (env.REPO_WALKTHROUGH_ALLOW_CWD_ENV === "1") repoCandidates.push(path.resolve(cwd, ".env"));
  for (const envPath of repoCandidates) {
    const val = readKeyFromEnvFile(envPath);
    if (val) return val;
  }

  if (platform === "win32") {
    throw new Error(
      'Could not resolve GEMINI_API_KEY. Set $env:GEMINI_API_KEY="YOUR_KEY" in PowerShell (or setx GEMINI_API_KEY "YOUR_KEY"), or add GEMINI_API_KEY=... to %APPDATA%\\repo-walkthrough\\.env or ~/.gemini/.env.'
    );
  }
  if (platform === "darwin") {
    throw new Error(
      'Could not resolve GEMINI_API_KEY. Run export GEMINI_API_KEY="YOUR_KEY", store it in macOS Keychain (security add-generic-password -a "$USER" -s gemini-api-key -w "YOUR_KEY"), or add GEMINI_API_KEY=... to ~/.config/repo-walkthrough/.env or ~/.gemini/.env.'
    );
  }
  throw new Error(
    'Could not resolve GEMINI_API_KEY. Run export GEMINI_API_KEY="YOUR_KEY", store it via secret-tool (secret-tool store --label=gemini-api-key service gemini-api-key), or add GEMINI_API_KEY=... to ~/.config/repo-walkthrough/.env or ~/.gemini/.env.'
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

function extractRawPcm(audioBuffer) {
  if (!Buffer.isBuffer(audioBuffer) || audioBuffer.length < 12) {
    return audioBuffer;
  }
  if (
    audioBuffer.subarray(0, 4).toString("ascii") !== "RIFF" ||
    audioBuffer.subarray(8, 12).toString("ascii") !== "WAVE"
  ) {
    return audioBuffer;
  }
  let offset = 12;
  while (offset + 8 <= audioBuffer.length) {
    const chunkId = audioBuffer.subarray(offset, offset + 4).toString("ascii");
    const chunkSize = audioBuffer.readUInt32LE(offset + 4);
    const dataStart = offset + 8;
    if (chunkId === "data") {
      return Buffer.from(
        audioBuffer.subarray(dataStart, Math.min(audioBuffer.length, dataStart + chunkSize))
      );
    }
    offset = dataStart + chunkSize + (chunkSize % 2);
  }
  return audioBuffer.length >= 44 ? Buffer.from(audioBuffer.subarray(44)) : audioBuffer;
}

function createWavBuffer(pcmBuffer, sampleRate = 24000, numChannels = 1, bitsPerSample = 16) {
  const rawPcm = extractRawPcm(pcmBuffer);
  const header = Buffer.alloc(44);
  const byteRate = (sampleRate * numChannels * bitsPerSample) / 8;
  const blockAlign = (numChannels * bitsPerSample) / 8;
  const dataSize = rawPcm.length;

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

  return Buffer.concat([header, rawPcm]);
}

function buildTtsRequestBody(
  text,
  { voice = DEFAULT_VOICE, style = DEFAULT_SPEECH_STYLE } = {}
) {
  const cleanText = sanitizeForTts(text);
  const part = style ? { text: cleanText, speechMetadata: { style } } : { text: cleanText };
  return {
    contents: [
      {
        parts: [part],
      },
    ],
    generationConfig: {
      responseModalities: ["AUDIO"],
      responseFormat: {
        audio: {
          mimeType: "AUDIO_L16",
          sampleRate: 24000,
        },
      },
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: {
            voiceName: voice,
          },
        },
      },
    },
  };
}

async function synthesizeTts(
  apiKey,
  text,
  { model = DEFAULT_MODEL, voice = DEFAULT_VOICE, style = DEFAULT_SPEECH_STYLE } = {}
) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`;
  const body = buildTtsRequestBody(text, { voice, style });

  for (let attempt = 0; attempt < 4; attempt++) {
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": apiKey,
      },
      signal: AbortSignal.timeout(60000),
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
    return extractRawPcm(Buffer.from(b64, "base64"));
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
  return String(s).toLowerCase().replace(/[^\p{L}\p{N}]+/gu, " ").trim();
}

/**
 * Returns the cue start as a 0..0.99 fraction of the step audio.
 * Cue 0 always anchors at 0. Any other cue returns null (keep the authored `at`)
 * when its phrase is missing, empty, or not found in the aligned segments.
 * Pass a shared `cursor` object ({ pos: 0 }) across a step's cues so repeated
 * phrases resolve to successive occurrences instead of jumping back to the first.
 */
function computeAcousticCueAt(alignedSegments, totalDur, phrase = "", cueIndex = 0, cursor = null) {
  if (cueIndex === 0) return 0;
  if (!phrase || !alignedSegments?.length || !(totalDur > 0)) return null;
  const normPhrase = normalizeMatchText(phrase);
  if (!normPhrase) return null;

  // Join normalized segment texts so a phrase can span a short pause between segments.
  const spans = [];
  let combined = "";
  for (const seg of alignedSegments) {
    const text = normalizeMatchText(seg.text || "");
    if (!text) continue;
    if (combined) combined += " ";
    spans.push({ seg, start: combined.length, text });
    combined += text;
  }

  const idx = combined.indexOf(normPhrase, cursor?.pos || 0);
  if (idx < 0) return null;
  if (cursor) cursor.pos = idx + normPhrase.length;

  const span = spans.findLast((s) => s.start <= idx);
  const frac = (idx - span.start) / span.text.length;
  const exactSec = span.seg.startSec + (span.seg.endSec - span.seg.startSec) * frac;
  return Number(Math.min(0.99, Math.max(0, exactSec / totalDur)).toFixed(2));
}

function alignStepCues(cues, alignedSegments, totalDur) {
  const cursor = { pos: 0 };
  return cues.map((c, cIdx) => {
    const acousticAt = computeAcousticCueAt(alignedSegments, totalDur, c.phrase, cIdx, cursor);
    return { ...c, at: acousticAt !== null ? acousticAt : c.at };
  });
}

async function alignStepSegmentsWithGemini(
  apiKey,
  wavBuffer,
  narration,
  { hash, localCacheDir, sharedCacheDir, force = false, alignmentModel = DEFAULT_ALIGNMENT_MODEL }
) {
  const localSegPath = path.join(localCacheDir, `${hash}.segments.json`);
  const sharedSegPath = path.join(sharedCacheDir, `${hash}.segments.json`);
  const { segments, totalDur, totalSamples, sr } = extractPcmSegments(wavBuffer, 10);

  if (!force && fs.existsSync(localSegPath)) {
    return { alignedSegments: JSON.parse(fs.readFileSync(localSegPath, "utf8")), totalDur };
  }
  if (!force && fs.existsSync(sharedSegPath)) {
    try {
      fs.copyFileSync(sharedSegPath, localSegPath);
    } catch {}
    return { alignedSegments: JSON.parse(fs.readFileSync(sharedSegPath, "utf8")), totalDur };
  }
  if (!apiKey) {
    return null;
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

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(alignmentModel)}:generateContent`;
  let parsed = null;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey,
        },
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
        const err = new Error(
          `Gemini segment alignment error (${resp.status}): ${JSON.stringify(json.error || json)}`
        );
        err.status = resp.status;
        throw err;
      }
      parsed = JSON.parse(json.candidates[0].content.parts[0].text);
      break;
    } catch (err) {
      if (attempt === 2 || (err.status && err.status >= 400 && err.status < 500 && err.status !== 429)) {
        throw err;
      }
      await new Promise((r) => setTimeout(r, 1500));
    }
  }
  const alignedSegments = segments.map((s, idx) => {
    const found = parsed.find((p) => p.seg === idx);
    return { seg: idx, startSec: s.startSec, endSec: s.endSec, text: found?.text || "" };
  });
  fs.writeFileSync(localSegPath, JSON.stringify(alignedSegments, null, 2));
  if (localSegPath !== sharedSegPath) {
    try {
      fs.copyFileSync(localSegPath, sharedSegPath);
    } catch {}
  }
  return { alignedSegments, totalDur };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    process.stdout.write(USAGE_TEXT);
    return;
  }

  const repoRoot = resolveRepoRoot(import.meta.dirname);
  const outDirCandidateData = opts.outDir
    ? path.join(path.dirname(opts.outDir), "data.js")
    : null;
  const dataFile =
    opts.dataFile ||
    (outDirCandidateData && fs.existsSync(outDirCandidateData) ? outDirCandidateData : null);

  if (!dataFile) {
    throw new Error(
      "Missing --data <path/to/data.js>. Pass --data <path/to/data.js> (or --help for usage)."
    );
  }
  if (!fs.existsSync(dataFile)) {
    throw new Error(`Data file not found: ${dataFile}`);
  }

  const siteDir = path.dirname(dataFile);
  const outDir = opts.outDir || path.join(siteDir, "audio");
  const localCacheDir = path.join(outDir, "cache");
  fs.mkdirSync(outDir, { recursive: true });
  fs.mkdirSync(localCacheDir, { recursive: true });
  const sharedCacheDir = resolveSharedCacheDir(localCacheDir);
  const legacyRepoCacheDir = path.join(repoRoot, "web", "audio", "cache");

  const windowObj = Object.create(null);
  const sandbox = Object.assign(Object.create(null), { window: windowObj });
  vm.runInNewContext(fs.readFileSync(dataFile, "utf8"), sandbox, { timeout: 2000 });
  const data = windowObj.WALKTHROUGH_DATA || windowObj.ADK_DATA;
  if (!data || !Array.isArray(data.walkthrough)) {
    throw new Error(
      `Invalid walkthrough data in ${dataFile} (expected window.WALKTHROUGH_DATA or window.ADK_DATA)`
    );
  }

  for (const st of data.walkthrough) {
    if (!Number.isInteger(st.step) || st.step < 1) {
      throw new Error(`Invalid walkthrough step number '${st.step}': expected an integer >= 1.`);
    }
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
    const legacyCachedWav = path.join(legacyRepoCacheDir, `${hash}.wav`);
    const stepFileName = `step-${st.step}.wav`;
    const stepFilePath = path.join(outDir, stepFileName);

    process.stdout.write(
      `  • Step ${st.step}/${data.walkthrough.length} [${hash}]: "${String(st.title || "").replace(/`/g, "")}" ... `
    );

    let wavBuffer = null;
    if (!force && fs.existsSync(localCachedWav)) {
      wavBuffer = createWavBuffer(fs.readFileSync(localCachedWav), 24000, 1, 16);
    } else if (!force && fs.existsSync(sharedCachedWav)) {
      wavBuffer = createWavBuffer(fs.readFileSync(sharedCachedWav), 24000, 1, 16);
      if (localCachedWav !== sharedCachedWav) {
        fs.writeFileSync(localCachedWav, wavBuffer);
      }
    } else if (!force && fs.existsSync(legacyCachedWav)) {
      wavBuffer = createWavBuffer(fs.readFileSync(legacyCachedWav), 24000, 1, 16);
      fs.writeFileSync(localCachedWav, wavBuffer);
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
      try {
        fs.copyFileSync(localCachedWav, sharedCachedWav);
      } catch {}
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

  // Align cues against actual PCM silence segments + Gemini transcription (or cached segments)
  if (!apiKey) {
    try {
      apiKey = resolveGeminiApiKey(repoRoot);
    } catch {}
  }
  if (apiKey) {
    console.log(
      `🎯 Aligning step cues to acoustic WAV segments via Gemini (${DEFAULT_ALIGNMENT_MODEL})...`
    );
  }
  for (let idx = 0; idx < stepBuffers.length; idx++) {
    const { st, hash, wavBuffer, durationSec } = stepBuffers[idx];
    try {
      const alignedResult = await alignStepSegmentsWithGemini(apiKey, wavBuffer, st.narration, {
        hash,
        localCacheDir,
        sharedCacheDir,
        force,
      });
      if (!alignedResult) continue;
      const { alignedSegments } = alignedResult;
      manifest[idx].segments = alignedSegments;
      if (Array.isArray(st.cues)) {
        manifest[idx].alignedCues = alignStepCues(st.cues, alignedSegments, durationSec);
      }
    } catch (err) {
      console.warn(`  ⚠️ Acoustic alignment warning on Step ${st.step}: ${err.message}`);
    }
  }

  fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));
  console.log(`✅ All ${manifest.length} TTS audio files ready in ${outDir} (with content-hash cache)`);
}

export {
  DEFAULT_ALIGNMENT_MODEL,
  DEFAULT_MODEL,
  DEFAULT_SPEECH_STYLE,
  DEFAULT_VOICE,
  alignStepCues,
  buildTtsRequestBody,
  computeAcousticCueAt,
  computeContentHash,
  createWavBuffer,
  extractPcmSegments,
  extractRawPcm,
  parseArgs,
  resolveGeminiApiKey,
  resolveRepoRoot,
  resolveSharedCacheDir,
  safeExecOptions,
  sanitizeForTts,
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
    console.error("❌ Failed:", err.message);
    process.exit(1);
  });
}
