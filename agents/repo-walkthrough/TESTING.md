# Testing Guide (`repo-walkthrough`)

Unit, pipeline, and end-to-end browser tests for `repo-walkthrough`.

## Quick Run (All Tests)

```bash
# 1. Python repository & git-diff analyzer tests
python3 tests/test_fetch_repo.py -v

# 2. Node.js validator, TTS, and build pipeline tests
node --test tests/test_pipeline.mjs

# 3. Headless Chromium UI, SVG geometry, and MP4 video E2E tests
node --test tests/test_ui_e2e.mjs
```

## What Each Suite Verifies

### 1. Repository Analyzer (`tests/test_fetch_repo.py`)

Tests [scripts/fetch_repo.py](./scripts/fetch_repo.py):
- GitHub URL normalization (`owner/repo`, `.git` suffixes, and monorepo `/tree/<branch>/<subpath>` URLs).
- Architectural file ranking and filtering across Python, JS/TS, SQL, and Jupyter notebooks.
- Automatic grouping of candidate files into architectural layers.
- Local directory analysis and `--diff <base>..<head>` unified diff extraction.
- Markdown export (`--export-voice`) for `gemini-voice`.

### 2. Build Pipeline, Validator & TTS (`tests/test_pipeline.mjs`)

Tests [scripts/build_walkthrough.mjs](./scripts/build_walkthrough.mjs), [scripts/generate_live_audio.mjs](./scripts/generate_live_audio.mjs), and [scripts/render_video.mjs](./scripts/render_video.mjs):
- Schema and zero-overlap geometry validation across all included walkthrough datasets ([web/data-adk.js](./web/data-adk.js), [examples/self-walkthrough/data.js](./examples/self-walkthrough/data.js), [examples/cymbal-autos-multimodal/data.js](./examples/cymbal-autos-multimodal/data.js), and [examples/diff-5984e02-to-head/data.js](./examples/diff-5984e02-to-head/data.js)).
- Support for 3-to-6 layer architectures (with 5 layers as the default).
- Rejection of overlapping nodes, invalid edge endpoints, and out-of-sync `cues`.
- TTS filename sanitization, WAV header creation, and voiced segment alignment.
- Standalone website bundling (`--mode website --no-tts`) and skill manifest integrity.

### 3. Browser UI, Geometry & Video E2E (`tests/test_ui_e2e.mjs`)

Launches headless Chrome via Playwright and verifies:
- **SVG Graph Geometry**: Zero node overlaps, zero text or badge overflows, zero layer-header collisions, and valid arrow paths across 3-to-6 layer graphs.
- **Interactive Walkthrough Controls**: Audio playback, pause/resume position memory, section navigation, `-5s`/`+5s` skipping, and playback speed selection.
- **Video Rendering (`?video=1`)**: Full-width camera framing across all steps without clipping nodes, plus `ffprobe` verification of the rendered H.264/AAC MP4 output.
