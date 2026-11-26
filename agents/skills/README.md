# Google Cloud & Dev Ecosystem Agent Skills

A collection of specialized **Agent Skills** to supercharge your AI agents in [Google Antigravity](https://antigravity.google) (App, CLI, and IDE) with deep knowledge of Google Cloud and developer workflows.

## 📂 Included Skills

| Skill Name | Description |
|---------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `go-project-setup` | Standardized setup for new Go (Golang) projects and services. Activate to ensure clean, idiomatic project structures and implement production-ready patterns. |
| `latest-software-version` | Real-time source of truth for software and model versions. Activate when adding dependencies, installing packages, or identifying Gemini model names. |
| `video-description` | Generates optimized descriptions for video platforms from transcripts and supplementary material. |

## 🚀 Installation

> **Note:** Antigravity CLI (`agy`) replaced Gemini CLI. See the [migration guide](https://antigravity.google/docs/cli/gcli-migration) to move legacy `.gemini/skills/` folders to `.agents/skills/`.

### Option 1: Global Install (Antigravity CLI, App, and IDE)

To make these skills available across all workspaces in Antigravity CLI (`agy`), Antigravity App, and Antigravity IDE:

1. Clone this repository:

   ```bash
   git clone https://github.com/GoogleCloudPlatform/devrel-demos.git ~/devrel-demos
   ```

1. Link the skills to your global Antigravity configuration:

   ```bash
   # Create the global skills directory if it doesn't exist
   mkdir -p ~/.gemini/config/skills

   # Symlink a skill
   ln -sfn ~/devrel-demos/agents/skills/video-description ~/.gemini/config/skills/video-description
   ```

1. Verify installation by running `/skills` inside `agy` (or `/skills reload` in an active session), or open **Customizations** in the Antigravity App or IDE.

### Option 2: Project-Specific (Workspace)

To enable these skills only for a specific project, copy the skill folder into your project's `.agents/skills` directory:

```bash
cd my-project
mkdir -p .agents/skills
cp -r ~/devrel-demos/agents/skills/video-description .agents/skills/
```

## 🛠 Usage Examples

**Go Project Setup:**

> "Create a new Go project for a web service."

**Software Versions:**

> "Check the latest version of React and update my package.json."

**Generating Video Descriptions:**

> "Create a YouTube video description from this transcript."

## 📏 Standards

Please follow these rules to ensure the AI agent understands your skill:

1. **Folder Structure**: Each skill gets its own folder inside `agents/skills/`.
1. **SKILL.md**: Must contain valid YAML frontmatter including `name` and `description`.
1. **Linting**: Ensure code passes `ruff` checks and markdown is properly formatted.
