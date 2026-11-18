# repo-walkthrough

Interactive codebase architecture graph website and voice-narrated MP4
walkthrough video for any repository.

Packaged as a standard
[Agent Skill (`SKILL.md`)](./skills/repo-walkthrough/SKILL.md) compatible with
**Antigravity**, **Claude Code**, and more (any agent supporting
[Agent Skills (`agentskills.io`)](https://agentskills.io)). All examples in this
repository were generated with
**[Gemini 4 Argon](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/)**.

![Interactive codebase walkthrough viewer][preview-image]

![Animated walkthrough video preview][video-preview-gif]

## Output Modes

1.  **Website (`--mode website`)**
    -   Generates an interactive web page where you can explore the repository's
        architecture layer by layer, click any file or connection to inspect its
        role and code, and play a step-by-step voice-narrated walkthrough.
2.  **Website + Video (`--mode video`)**
    -   Builds the interactive website and exports an MP4 video that walks
        through the architecture step by step, zooming into each layer and
        highlighting files as they are explained.

## Prerequisites

Check your local environment with:

```bash
node skills/repo-walkthrough/scripts/build_walkthrough.mjs --check-prereqs
```

| Requirement          | Website        | Website + Video  | Notes             |
:                      : (`--mode       : (`--mode video`) :                   :
:                      : website`)      :                  :                   :
| :------------------- | :------------- | :--------------- | :---------------- |
| **Python 3**         | Required       | Required         | Analyzes local or |
:                      :                :                  : GitHub            :
:                      :                :                  : repositories.     :
| **Node.js 20+**      | Required       | Required         | Runs the build,   |
:                      :                :                  : audio, and video  :
:                      :                :                  : scripts.          :
| **`GEMINI_API_KEY`** | Optional       | **Required**     | Generates Gemini  |
:                      : (`--no-tts`    :                  : TTS narration.    :
:                      : uses browser   :                  :                   :
:                      : speech)        :                  :                   :
| **`ffmpeg`**         | Not required   | **Required**     | Encodes the       |
:                      :                :                  : walkthrough       :
:                      :                :                  : video.            :
| **Playwright +       | Optional       | **Required**     | Renders video     |
: Chrome**             :                :                  : frames in         :
:                      :                :                  : headless Chrome.  :
| **`gh` CLI**         | Optional       | Optional         | Needed only for   |
:                      : (private repos : (private repos   : private GitHub    :
:                      : only)          : only)            : repositories.     :

## Project Structure

```text
repo-walkthrough/
├── plugin.json                         # Antigravity plugin manifest
├── README.md
├── assets/
│   └── logo.svg                        # Plugin icon
├── skills/
│   └── repo-walkthrough/
│       ├── SKILL.md                    # Agent Skill definition
│       ├── references/
│       │   └── data-schema.md          # Layout rules & WALKTHROUGH_DATA schema
│       └── scripts/
│           ├── fetch_repo.py           # Repository & git-diff analyzer
│           ├── build_walkthrough.mjs   # Validator & website/video builder
│           ├── generate_live_audio.mjs # Gemini TTS audio generator
│           ├── render_video.mjs        # MP4 video renderer
│           └── render_video.sh         # Shell wrapper for render_video.mjs
└── web/
    └── index.tmpl                      # Interactive graph & walkthrough viewer
```

## Quick Start

```bash
# 1. Analyze a repository (or pass --diff <base>..<head> for a git diff)
python3 skills/repo-walkthrough/scripts/fetch_repo.py <repo-or-path> --json /tmp/repo-analysis.json

# 2a. Build & open the interactive Website
node skills/repo-walkthrough/scripts/build_walkthrough.mjs --data <path/to/data.js> --mode website --open

# 2b. Build the interactive Website + MP4 Video
node skills/repo-walkthrough/scripts/build_walkthrough.mjs --data <path/to/data.js> --mode video --open
```

## Installing the Plugin or Skill

-   **Antigravity**: Install **Repo Walkthrough** from the Antigravity Plugin
    Marketplace (`Customizations > Plugins` or `/plugin`), run
    `agy plugin install ./agents/repo-walkthrough`, or copy/symlink
    `skills/repo-walkthrough` to `~/.gemini/config/skills/repo-walkthrough`.
-   **Claude Code**: Copy or symlink `skills/repo-walkthrough` to
    `~/.claude/skills/repo-walkthrough` (or `.claude/skills/repo-walkthrough` in
    a project).
-   **Other Agents (`agentskills.io`)**: Copy or symlink
    `skills/repo-walkthrough` into your agent's `skills/` directory (e.g.,
    `.agents/skills/repo-walkthrough`).

[preview-image]: https://raw.githubusercontent.com/GoogleCloudPlatform/devrel-demos/main/agents/repo-walkthrough/docs/preview.png
[video-preview-gif]: https://raw.githubusercontent.com/GoogleCloudPlatform/devrel-demos/main/agents/repo-walkthrough/docs/video-preview.gif
