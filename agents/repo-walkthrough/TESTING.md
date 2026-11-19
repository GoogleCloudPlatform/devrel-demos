# Testing Guide (`repo-walkthrough`)

Unit, pipeline, end-to-end browser, clean-room Linux container (`bwrap`), and cross-platform Windows/macOS verification guide for `repo-walkthrough`.

## Quick Run (All Automated Tests)

```bash
# 1. Validate plugin manifest and skill bundle strictly (0 errors, 0 warnings)
agy plugin validate . --strict

# 2. Python repository & git-diff analyzer tests
python3 tests/test_fetch_repo.py -v

# 3. Node.js validator, TTS, cross-platform helpers, and build pipeline tests
node tests/test_pipeline.mjs

# 4. Headless Chromium/Edge UI, mobile/desktop SVG geometry, and MP4 video E2E tests
node tests/test_ui_e2e.mjs
```

## What Each Suite Verifies

### 1. Repository Analyzer (`tests/test_fetch_repo.py`)

Tests [skills/repo-walkthrough/scripts/fetch_repo.py](./skills/repo-walkthrough/scripts/fetch_repo.py):
- GitHub URL normalization (`owner/repo`, `.git` suffixes, and monorepo `/tree/<branch>/<subpath>` URLs).
- Architectural file ranking and filtering across Python, JS/TS, SQL, and Jupyter notebooks.
- Automatic grouping of candidate files into architectural layers.
- Local directory analysis, symlink containment, UTF-8 non-ASCII git diff extraction (`-c core.quotePath=false`), 3-dot `merge-base` diff resolution, and leading-`-` git flag rejection.
- Spoken narration markdown export (`--export-voice`).
- Plugin and standalone skill root resolution plus safe `open_target` behavior (`os.startfile` on Windows, refusing `.tmpl` templates, and non-crashing headless fallback).

### 2. Build Pipeline, Validator, Plugin & Cross-Platform Helpers (`tests/test_pipeline.mjs`)

Tests [skills/repo-walkthrough/scripts/build_walkthrough.mjs](./skills/repo-walkthrough/scripts/build_walkthrough.mjs), [skills/repo-walkthrough/scripts/generate_live_audio.mjs](./skills/repo-walkthrough/scripts/generate_live_audio.mjs), [skills/repo-walkthrough/scripts/render_video.mjs](./skills/repo-walkthrough/scripts/render_video.mjs), and [plugin.json](./plugin.json):
- Schema and zero-overlap geometry validation across all included walkthrough datasets ([web/data-adk.js](./web/data-adk.js), [examples/self-walkthrough/data.js](./examples/self-walkthrough/data.js), [examples/cymbal-autos-multimodal/data.js](./examples/cymbal-autos-multimodal/data.js), and [examples/diff-5984e02-to-head/data.js](./examples/diff-5984e02-to-head/data.js)).
- Support for 3-to-6 layer architectures (with 5 layers as the default).
- Rejection of overlapping nodes, invalid edge endpoints, non-integer step numbers, and out-of-sync `cues`.
- Gemini 3.8 TTS request builder (`gemini-3.8-flash-tts`, `speechMetadata.style`, `responseFormat.audio` `AUDIO_L16` at `24000` Hz, zero style prefix in `parts[0].text`), defensive RIFF WAV `"data"` subchunk extraction (`extractRawPcm`), filename sanitization, and voiced segment alignment.
- Safe `-h` / `--help` execution (exiting `0` with zero file mutations) and unknown-flag rejection across all CLI scripts.
- Standalone website bundling (`--mode website --no-tts`), `web/data-adk.js` copying, standalone `skills/repo-walkthrough` folder copy execution (resolving `skills/repo-walkthrough/assets/index.tmpl` with zero parent directories), `plugin.json` manifest rules, and `SKILL.md` relative-path integrity.
- Read-only plugin install directory (`chmod -R a-w` / `icacls`) audio cache fallback (`$PLUGIN_DATA/audio-cache` -> `~/.cache/repo-walkthrough/audio` -> `localCacheDir`).
- Cross-platform `GEMINI_API_KEY` resolution order (`GEMINI_API_KEY` -> `./.env` -> `$PLUGIN_DATA/.env` -> `~/.config/repo-walkthrough/.env` / `%APPDATA%\repo-walkthrough\.env` -> `~/.gemini/.env` -> `<repoRoot>/.env` -> OS credential store `gemini-api-key`) and OS-specific error hints.
- Cross-platform helpers: `openTarget` (`open` on macOS, `rundll32.exe url.dll,FileProtocolHandler` on Windows, `xdg-open` on Linux, refusing `.tmpl`), `detectPythonCmd` (`python3` -> `py -3` -> `python` verified as Python 3), Windows FFmpeg concat escaping (`formatFfmpegConcatEntry`), Windows Playwright `_npx` discovery, and `channel: "msedge"` fallback.

### 3. Browser UI, Geometry & Video E2E (`tests/test_ui_e2e.mjs`)

Launches headless Chrome/Chromium/Edge via Playwright and verifies across [web/data-adk.js](./web/data-adk.js) and all three built `examples/*/index.html` pages:
- **Desktop (`1440x900`) & Mobile (`390x844`, `360x640`) Layout**: Zero node overlaps, zero text or badge overflows, non-zero mobile SVG graph height, zero horizontal viewport overflow (`scrollWidth <= clientWidth`), zero dock collisions, WCAG AA contrast, inline SVG favicon rendering, and DOM XSS / `javascript:` / `//` URL rejection.
- **Interactive Walkthrough Controls**: Audio playback, pause/resume position memory, section navigation, `-5s`/`+5s` skipping, and playback speed selection.
- **Video Rendering (`?video=1`)**: Full-width camera framing across all steps without clipping nodes, `os.tmpdir()` scratch frame cleanup, and `ffprobe` verification of the rendered H.264/AAC MP4 output.

---

## Clean-Room Linux Container (`bwrap`) Verification

To verify the plugin in a clean-room Linux sandbox with an isolated `$HOME` and read-only installed plugin files (`--ro-bind`):

```bash
CLEAN_HOME="$(mktemp -d /tmp/rw-clean-linux-home.XXXXXX)"
OUT_DIR="$(mktemp -d /tmp/rw-clean-out.XXXXXX)"

# 1. Validate & install plugin into isolated HOME
HOME="$CLEAN_HOME" agy plugin validate . --strict
HOME="$CLEAN_HOME" agy plugin install .

# 2. Run inside bwrap with read-only plugin mount and isolated HOME
bwrap \
  --ro-bind /usr /usr \
  --ro-bind /lib /lib \
  --ro-bind-try /lib64 /lib64 \
  --ro-bind /bin /bin \
  --ro-bind /etc /etc \
  --proc /proc \
  --dev /dev \
  --bind "$CLEAN_HOME" "$CLEAN_HOME" \
  --ro-bind "$CLEAN_HOME/.gemini/config/plugins/repo-walkthrough" "$CLEAN_HOME/.gemini/config/plugins/repo-walkthrough" \
  --bind "$OUT_DIR" "$OUT_DIR" \
  --setenv HOME "$CLEAN_HOME" \
  --setenv PATH "/usr/bin:/bin" \
  --unshare-all \
  -- bash -c '
    SKILL_DIR="$HOME/.gemini/config/plugins/repo-walkthrough/skills/repo-walkthrough"
    python3 "$SKILL_DIR/scripts/fetch_repo.py" "$HOME/.gemini/config/plugins/repo-walkthrough" --json "'"$OUT_DIR"'/analysis.json"
    node "$SKILL_DIR/scripts/build_walkthrough.mjs" --data "$HOME/.gemini/config/plugins/repo-walkthrough/examples/self-walkthrough/data.js" --out-dir "'"$OUT_DIR"'/site" --mode website --no-tts --open
  '

rm -rf "$CLEAN_HOME" "$OUT_DIR"
```

---

## Windows Verification Checklist (PowerShell)

Use this copy-pasteable checklist on Windows 10/11 (PowerShell) to verify prerequisites, standalone skill execution, unit tests, website generation, and MP4 video export.

### 1. Windows Prerequisites

| Prerequisite | Check Command (PowerShell) | Install / Setup Command (PowerShell) |
| :--- | :--- | :--- |
| **Node.js 20.11+** | `node --version` | `winget install OpenJS.NodeJS.LTS` |
| **Python 3** (`py -3` or `python`) | `py -3 --version` or `python --version` | `winget install Python.Python.3.12` |
| **FFmpeg** *(for `--mode video`)* | `ffmpeg -version` | `winget install Gyan.FFmpeg` |
| **Chrome or Edge + Playwright** | `npx playwright-core --version` | `npm install -g playwright-core` (uses installed Chrome or falls back to built-in Microsoft Edge `channel: "msedge"`) |
| **`GEMINI_API_KEY`** | `if ($env:GEMINI_API_KEY) { "OK" }` | `$env:GEMINI_API_KEY = "YOUR_API_KEY"` (or persist via `New-Item -ItemType Directory -Force "$HOME\.gemini" \| Out-Null; Set-Content "$HOME\.gemini\.env" "GEMINI_API_KEY=YOUR_API_KEY"`) |

### 2. Copy-Paste PowerShell End-to-End Verification

```powershell
# 1. Navigate to the plugin directory in your devrel-demos checkout
Set-Location "path\to\devrel-demos\agents\repo-walkthrough"

# 2. Check prerequisites (verifies Python 3, Node.js >= 20.11, Gemini API key, FFmpeg, and Playwright)
node .\skills\repo-walkthrough\scripts\build_walkthrough.mjs --check-prereqs

# 3. Run Python & Node.js unit test suites (prefer py -3 over the Windows Store python.exe stub)
if (Get-Command py -ErrorAction SilentlyContinue) {
  py -3 .\tests\test_fetch_repo.py -v
} else {
  python .\tests\test_fetch_repo.py -v
}
node .\tests\test_pipeline.mjs

# 4. Copy the standalone skill directory to $env:TEMP and verify end-to-end execution
$StandaloneSkill = Join-Path $env:TEMP "rw-standalone-skill\repo-walkthrough"
$OutDir = Join-Path $env:TEMP "rw-win-verify"
New-Item -ItemType Directory -Force (Split-Path $StandaloneSkill), $OutDir | Out-Null
Copy-Item -Recurse -Force .\skills\repo-walkthrough $StandaloneSkill

# 4a. Analyze the repository into $env:TEMP\rw-win-verify\repo-analysis.json
if (Get-Command py -ErrorAction SilentlyContinue) {
  py -3 "$StandaloneSkill\scripts\fetch_repo.py" . --json "$OutDir\repo-analysis.json"
} else {
  python "$StandaloneSkill\scripts\fetch_repo.py" . --json "$OutDir\repo-analysis.json"
}

# 4b. Build and auto-open the standalone interactive Website (uses rundll32.exe url.dll,FileProtocolHandler)
node "$StandaloneSkill\scripts\build_walkthrough.mjs" `
  --data .\examples\self-walkthrough\data.js `
  --out-dir "$OutDir\site" `
  --mode website `
  --no-tts `
  --open

# 4c. (Optional, requires GEMINI_API_KEY + ffmpeg) Build Website + voice-narrated MP4 Video
if ($env:GEMINI_API_KEY -or (Test-Path "$HOME\.gemini\.env")) {
  node "$StandaloneSkill\scripts\build_walkthrough.mjs" `
    --data .\examples\self-walkthrough\data.js `
    --out-dir "$OutDir\video-site" `
    --mode video `
    --open
}

# 5. Run full browser UI, SVG geometry & video E2E tests (Chrome/Chromium/Edge)
node .\tests\test_ui_e2e.mjs
```

---

### Windows-Specific Notes

- **DirectWrite Web-Font Swap (`document.fonts.ready`)**: On Windows DirectWrite, initial synchronous `buildGraph()` measured `getComputedTextLength()` against the narrower fallback monospace font (`Consolas`) before `Roboto Mono` finished downloading. Re-running `buildGraph()` and `updateHighlights()` when `document.fonts.ready` resolves in [skills/repo-walkthrough/assets/index.tmpl](./skills/repo-walkthrough/assets/index.tmpl) (and awaiting `document.fonts.ready` in [render_video.mjs](./skills/repo-walkthrough/scripts/render_video.mjs) and [tests/test_ui_e2e.mjs](./tests/test_ui_e2e.mjs)) ensures exact `Roboto Mono` and `Inter` text truncation on Windows.
- **Safe File Launching (`os.startfile` & `rundll32.exe`)**: On Windows, [fetch_repo.py](./skills/repo-walkthrough/scripts/fetch_repo.py) uses `os.startfile` and [build_walkthrough.mjs](./skills/repo-walkthrough/scripts/build_walkthrough.mjs) invokes `rundll32.exe url.dll,FileProtocolHandler` directly without `cmd.exe`, preventing command splitting on paths containing `&`, spaces, parentheses, or `%VAR%` tokens.
- **Windows `npm.cmd` / `npx` & `msedge` Fallback**: [render_video.mjs](./skills/repo-walkthrough/scripts/render_video.mjs) resolves global Playwright installs via `cmd.exe /d /s /c "npm.cmd root -g"`, checks `%LOCALAPPDATA%\npm-cache\_npx` and `%APPDATA%\npm-cache\_npx`, normalizes Windows drive paths via `pathToFileURL`, and falls back to `channel: "msedge"` when Chrome is absent.
