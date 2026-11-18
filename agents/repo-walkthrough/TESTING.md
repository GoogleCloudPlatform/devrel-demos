# Testing Guide (`repo-walkthrough`)

Unit, pipeline, end-to-end browser, clean-room Linux container (`bwrap`), and Windows verification guide for `repo-walkthrough`.

## Quick Run (All Automated Tests)

```bash
# 1. Validate plugin manifest and skill bundle strictly (0 errors, 0 warnings)
agy plugin validate . --strict

# 2. Python repository & git-diff analyzer tests
python3 tests/test_fetch_repo.py -v

# 3. Node.js validator, TTS, cross-platform helpers, and build pipeline tests
node tests/test_pipeline.mjs

# 4. Headless Chromium UI, SVG geometry, and MP4 video E2E tests
node tests/test_ui_e2e.mjs
```

## What Each Suite Verifies

### 1. Repository Analyzer (`tests/test_fetch_repo.py`)

Tests [skills/repo-walkthrough/scripts/fetch_repo.py](./skills/repo-walkthrough/scripts/fetch_repo.py):
- GitHub URL normalization (`owner/repo`, `.git` suffixes, and monorepo `/tree/<branch>/<subpath>` URLs).
- Architectural file ranking and filtering across Python, JS/TS, SQL, and Jupyter notebooks.
- Automatic grouping of candidate files into architectural layers.
- Local directory analysis and `--diff <base>..<head>` unified diff extraction.
- Markdown export (`--export-voice`) for `gemini-voice`.
- Symlink-dereferenced `resolve_repo_root` (`scripts/` vs `skills/repo-walkthrough/scripts/`) and headless Linux `open_target` non-crash behavior.

### 2. Build Pipeline, Validator, Plugin & Cross-Platform Helpers (`tests/test_pipeline.mjs`)

Tests [skills/repo-walkthrough/scripts/build_walkthrough.mjs](./skills/repo-walkthrough/scripts/build_walkthrough.mjs), [skills/repo-walkthrough/scripts/generate_live_audio.mjs](./skills/repo-walkthrough/scripts/generate_live_audio.mjs), [skills/repo-walkthrough/scripts/render_video.mjs](./skills/repo-walkthrough/scripts/render_video.mjs), and [plugin.json](./plugin.json):
- Schema and zero-overlap geometry validation across all included walkthrough datasets ([web/data-adk.js](./web/data-adk.js), [examples/self-walkthrough/data.js](./examples/self-walkthrough/data.js), [examples/cymbal-autos-multimodal/data.js](./examples/cymbal-autos-multimodal/data.js), and [examples/diff-5984e02-to-head/data.js](./examples/diff-5984e02-to-head/data.js)).
- Support for 3-to-6 layer architectures (with 5 layers as the default).
- Rejection of overlapping nodes, invalid edge endpoints, and out-of-sync `cues`.
- TTS filename sanitization, WAV header creation, and voiced segment alignment.
- Standalone website bundling (`--mode website --no-tts`), `plugin.json` manifest rules, and `SKILL.md` relative-path integrity.
- Dereferenced symlink `resolveRepoRoot` (`skills/repo-walkthrough/scripts/*.mjs` resolving `web/index.tmpl`).
- Read-only plugin install directory (`chmod -R a-w`) audio cache fallback (`$PLUGIN_DATA/audio-cache` -> `~/.cache/repo-walkthrough/audio` -> `localCacheDir`).
- Cross-platform `GEMINI_API_KEY` resolution order (`GEMINI_API_KEY` -> `./.env` -> `$PLUGIN_DATA/.env` -> `~/.config/repo-walkthrough/.env` / `%APPDATA%\repo-walkthrough\.env` -> `~/.gemini/.env` -> `<repoRoot>/.env` -> OS credential store `gemini-api-key`) and OS-specific error hints.
- Cross-platform helpers: `openTarget` (`darwin`/`win32`/`linux` + headless `ENOENT` resilience), `detectPythonCmd` (`python3` -> `python` -> `py -3`), Windows FFmpeg concat backslash/quote escaping (`formatFfmpegConcatEntry`), Windows Playwright `_npx` discovery (`npm.cmd`, `%LOCALAPPDATA%\npm-cache\_npx`, `%APPDATA%\npm-cache\_npx`), and `channel: "msedge"` fallback.

### 3. Browser UI, Geometry & Video E2E (`tests/test_ui_e2e.mjs`)

Launches headless Chrome/Chromium/Edge via Playwright and verifies:
- **SVG Graph Geometry**: Zero node overlaps, zero text or badge overflows, zero layer-header collisions, and valid arrow paths across 3-to-6 layer graphs.
- **Interactive Walkthrough Controls**: Audio playback, pause/resume position memory, section navigation, `-5s`/`+5s` skipping, and playback speed selection.
- **Video Rendering (`?video=1`)**: Full-width camera framing across all steps without clipping nodes, plus `ffprobe` verification of the rendered H.264/AAC MP4 output.

---

## Clean-Room Linux Container (`bwrap`) Verification

To verify the plugin in a clean-room Linux sandbox with an isolated `$HOME`, read-only installed plugin files (`--ro-bind`), and no personal `~/.gemini` or `~/projects` directory visible:

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

Use this copy-pasteable checklist on Windows 10/11 (PowerShell) to verify prerequisites, plugin installation, unit tests, website generation, and MP4 video export.

### 1. Windows Prerequisites

| Prerequisite | Check Command (PowerShell) | Install / Setup Command (PowerShell) |
| :--- | :--- | :--- |
| **Node.js 20+** | `node --version` | `winget install OpenJS.NodeJS.LTS` |
| **Python 3** (`python` or `py -3`) | `python --version` or `py -3 --version` | `winget install Python.Python.3.12` |
| **FFmpeg** *(for `--mode video`)* | `ffmpeg -version` | `winget install Gyan.FFmpeg` |
| **Chrome or Edge + Playwright** | `npx playwright-core --version` | `npm install -g playwright-core` (uses installed Chrome or falls back to built-in Microsoft Edge `channel: "msedge"`) |
| **`GEMINI_API_KEY`** | `if ($env:GEMINI_API_KEY) { "OK" }` | `$env:GEMINI_API_KEY = "YOUR_API_KEY"` (or persist via `New-Item -ItemType Directory -Force "$HOME\.gemini" \| Out-Null; Set-Content "$HOME\.gemini\.env" "GEMINI_API_KEY=YOUR_API_KEY"`) |

### 2. Copy-Paste PowerShell End-to-End Verification

```powershell
# 1. Navigate to the plugin directory in your devrel-demos checkout
Set-Location "$HOME\projects\devrel-demos\agents\repo-walkthrough"

# 2. Check prerequisites (verifies Python/py -3, Node.js, Gemini API key, and FFmpeg)
node .\skills\repo-walkthrough\scripts\build_walkthrough.mjs --check-prereqs

# 3. Run Python & Node.js unit test suites
if (Get-Command python -ErrorAction SilentlyContinue) {
  python .\tests\test_fetch_repo.py -v
} else {
  py -3 .\tests\test_fetch_repo.py -v
}
node .\tests\test_pipeline.mjs

# 4. Validate and install the Antigravity plugin
agy plugin validate . --strict
agy plugin install .
agy plugin list

# 5. Run the installed skill scripts from the dereferenced plugin directory
$SkillDir = "$HOME\.gemini\config\plugins\repo-walkthrough\skills\repo-walkthrough"
$OutDir = Join-Path $env:TEMP "rw-win-verify"
New-Item -ItemType Directory -Force $OutDir | Out-Null

# 5a. Analyze the repository into $env:TEMP\rw-win-verify\repo-analysis.json
if (Get-Command python -ErrorAction SilentlyContinue) {
  python "$SkillDir\scripts\fetch_repo.py" . --json "$OutDir\repo-analysis.json"
} else {
  py -3 "$SkillDir\scripts\fetch_repo.py" . --json "$OutDir\repo-analysis.json"
}

# 5b. Build and auto-open the standalone interactive Website (uses cmd /c start "")
node "$SkillDir\scripts\build_walkthrough.mjs" `
  --data .\examples\self-walkthrough\data.js `
  --out-dir "$OutDir\site" `
  --mode website `
  --no-tts `
  --open

# 5c. (Optional, requires GEMINI_API_KEY + ffmpeg) Build Website + voice-narrated MP4 Video
if ($env:GEMINI_API_KEY -or (Test-Path "$HOME\.gemini\.env")) {
  node "$SkillDir\scripts\build_walkthrough.mjs" `
    --data .\examples\self-walkthrough\data.js `
    --out-dir "$OutDir\video-site" `
    --mode video `
    --open
}

# 6. Run full browser UI, SVG geometry & video E2E tests (Chrome/Chromium/Edge)
node .\tests\test_ui_e2e.mjs
```

---

## Cross-Platform Verification Matrix (Linux, macOS, and Windows)

| Check | Linux (`Ubuntu 24.04 x86_64` & `bwrap`) | macOS (`Darwin arm64`) | Windows (`Windows Server 2022` & `Windows Server 2025`) |
| :--- | :--- | :--- | :--- |
| **`agy plugin validate --strict` & `install`** | PASS (`1.0.0`, 1 skill in isolated `$HOME`) | PASS (`1.0.0`, 1 skill in isolated `$HOME`) | PASS (`agy.exe` `1.0.0`, 1 skill in isolated `%USERPROFILE%` on `Windows Server 2022`) |
| **`tests/test_fetch_repo.py`** | PASS (`10/10`) | PASS (`10/10`) | PASS (`10/10` on `Windows Server 2022` and `Windows Server 2025`) |
| **`tests/test_pipeline.mjs`** | PASS (`15/15`) | PASS (`15/15`) | PASS (`15/15` on `Windows Server 2025`) |
| **`tests/test_ui_e2e.mjs` (Playwright Chromium)** | PASS (`5/5`) | PASS (`5/5`) | PASS (`5/5` in Headless Chrome on `Windows Server 2025`) |
| **Read-Only Plugin Bundle + Website & MP4 Video (`ffprobe`)** | PASS (`--ro-bind` / `chmod -R a-w`, `h264` + `aac` `1440x900` MP4) | PASS (`chmod -R a-w`, live `253.12s` `1440x900` `h264` + `aac` MP4 with Gemini TTS `Despina`) | PASS (`attrib +R` + `icacls /deny` + `fetch_repo.py` + `build_walkthrough.mjs` + `render_video.mjs` `1440x900` `h264` + `aac` MP4) |

### Windows-Specific Notes & Fixes

- **DirectWrite Web-Font Swap (`document.fonts.ready`)**: On Windows DirectWrite, initial synchronous `buildGraph()` measured `getComputedTextLength()` against the narrower fallback monospace font (`Consolas`) before `Roboto Mono` finished downloading, causing long SQL and JSON node titles in `cymbal-autos-multimodal` to overflow by ~2px once `Roboto Mono` swapped in. Re-running `buildGraph()` and `updateHighlights()` when `document.fonts.ready` resolves in [web/index.tmpl](./web/index.tmpl) (and awaiting `document.fonts.ready` in [tests/test_ui_e2e.mjs](./tests/test_ui_e2e.mjs)) ensures exact `Roboto Mono` and `Inter` text truncation on Windows.
- **Windows `npm.cmd` / `npx.cmd` & `fileURLToPath` Resolution**: [skills/repo-walkthrough/scripts/render_video.mjs](./skills/repo-walkthrough/scripts/render_video.mjs) uses `npm.cmd` (`shell: true` on `win32`), checks `%LOCALAPPDATA%\npm-cache\_npx` and `%APPDATA%\npm-cache\_npx`, normalizes Windows drive paths (`C:\`, `D:\`) via `pathToFileURL` / `fileURLToPath`, and falls back to `channel: "msedge"` when Chrome is absent.

