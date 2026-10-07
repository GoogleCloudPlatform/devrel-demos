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
