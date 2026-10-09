# Pitch Generator Project Agent Rules

## Codebase Architecture & File Placement

1. **Production Code Locations Only**:
   - All production application code, specialist agents, workflow orchestrators, evaluation harnesses, and skills MUST live strictly in the canonical application directory: `pitch_generator/` (e.g. `pitch_generator/agent.py`, `pitch_generator/skills/brand-guidelines/SKILL.md`, `pitch_generator/app_utils/services.py`).
   - Top-level entrypoints: `call_agent.py` and `pitch_generator/__init__.py`.

2. **No Root Module Folders**:
   - NEVER create module subfolders (such as `module_1/`, `module_2/`, `module_3/`, `module_4/`) in the project root.
   - Reference/gold-standard lab solutions belong strictly in `.agents/solutions/module_<N>/` and must never be duplicated into the project root.

3. **Tooling & Verification Alignment**:
   - When introducing or testing lab steps, always verify against the real-world files in `pitch_generator/`.
   - The workspace verification script (`.agents/skills/lab-helper/scripts/verify_workspace.py`) maintains an `app_file_map` mapping codelab step artifacts to `pitch_generator/`. Every step must be mapped to its production counterpart so verification runs against `pitch_generator/`.

4. **Clean Workspace Integrity**:
   - Always run `git status` before finishing a task to ensure no untracked `module_<N>/` directories or temporary scratch files were inadvertently created in the project root.

5. **Provide prompts, not Python suggestions**:
   - When responding with "how to" type suggestions, provide example prompts the user can type that will accomplish the task. Avoid providing Python commandline instructions for the user to type. Assume the user is not going to use the terminal to enter commands and will only prompt you for changes.

6. **Canonical CLI Testing, Setup, Local Server & Cloud Run Deployment Scripts**:
   - **CLI Agent Testing**: Whenever asked to test or run the Pitch Generator agent with a prompt (e.g., `"Test the agent with 'Flying skateboards for cats'"`), ALWAYS execute `python3 call_agent.py "<prompt>"` (do NOT pass `--offline` unless explicitly asked).
   - **Cloud Run Deployment**: Whenever asked to deploy the application, agents, or frontend to Cloud Run, ALWAYS execute `bash scripts/deploy.sh` (do NOT run raw `gcloud run deploy` commands directly). `scripts/deploy.sh` automatically loads `.env`, detects whether `remote_visual_director` has been implemented in `pitch_generator/agent.py`, deploys `visual-director` first when present, and wires `VISUAL_DIRECTOR_URL` into `pitch-generator`.
   - **Cloud Infrastructure Setup**: Whenever asked to set up or provision Google Cloud prerequisites (Cloud Storage bucket, BigQuery dataset, Cloud Resource connection, or IAM bindings), ALWAYS execute `bash scripts/setup.sh`.
   - **Local Server Lifecycle**: Whenever asked to start, restart, check, or stop the local web server or frontend, ALWAYS use `bash .agents/skills/start-frontend/scripts/start_server.sh` (see `.agents/skills/start-frontend/SKILL.md`).

7. **Follow In-File Guideposts, Never Peek at `.agents/solutions/`, and Keep Verification On-Demand**:
   - **Follow In-File Guidepost Comments First**: Before designing or writing code for any user request, read the target file (`pitch_generator/agent.py`, `pitch_generator/app_utils/services.py`, or `pitch_generator/fast_api_app.py`) and locate the corresponding `# [Guidepost — Step <id>]` comment block. Always use the exact agent names, `output_key` bindings, function signatures, and integration symbols mentioned in that guidepost comment, and leave future guidepost comments for later steps intact.
   - **Never Read `.agents/solutions/` During Implementation**: Do NOT view, search, or read any files under `.agents/solutions/` when implementing features or answering coding requests. `.agents/solutions/` may ONLY be accessed when the learner explicitly asks for a hint, asks to verify a step, or asks to fix/remediate their workspace via the `lab-helper` skill.
   - **Strictly On-Demand Verification**: To conserve time and turns during the lab, do NOT run `verify_workspace.py` or unsolicited test suites after implementing a step unless the learner explicitly asks to verify, test, or troubleshoot their work.
   - **In-Place Surgical Remediation**: When the learner asks to remediate or fix a broken step, read the corresponding `.agents/solutions/` reference file and patch `pitch_generator/` in-place rather than overwriting the entire cumulative file, so earlier work, user customizations, and upcoming guidepost comments are preserved.

8. **Never Deploy Unless Explicitly Asked by the Learner**:
   - Do NOT run `bash scripts/deploy.sh`, `agents-cli deploy`, or `gcloud run deploy` automatically after making code changes. Cloud Run deployment takes several minutes, so wait until the learner explicitly asks you to deploy in their prompt.

