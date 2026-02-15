# Google Cloud & Dev Ecosystem Agent Skills

A collection of specialized **Agent Skills** to supercharge your AI agents (Gemini CLI, Antigravity) with deep knowledge of Google Cloud Platform and developer workflows.

## 📂 Included Skills

| Skill Name                | Description                                                                                                                                                                   |
|---------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `go-project-setup`        | Standardized setup for new Go (Golang) projects and services. Activate to ensure clean, idiomatic project structures and implement production-ready patterns.                 |
| `latest-software-version` | Real-time source of truth for software and model versions. Activate when adding dependencies, installing packages, or identifying Gemini model names.                         |
| `video-description`       | Generates optimized descriptions for video platforms from transcripts and supplementary material.                                                                             |

## 🚀 Installation

### Option 1: Gemini CLI (Global Install)

To make these skills available to Gemini in your terminal anywhere:

1. Clone this repository:

   ```bash
   git clone https://github.com/GoogleCloudPlatform/devrel-demos.git ~/devrel-demos
   ```

2. Link the skills to your Gemini configuration:

   ```bash
   # Create the skills directory if it doesn't exist
   mkdir -p ~/.gemini/skills

   # Symlink specific skills (Recommended)
   ln -s ~/devrel-demos/agents/skills/video-description ~/.gemini/skills/video-description
   
   # OR symlink the entire folder (if supported by your version)
   # ln -s ~/devrel-demos/agents/skills/* ~/.gemini/skills/
   ```

3. Verify installation:

   ```bash
   gemini skills list
   ```

### Option 2: Project-Specific (Workspace)

To enable these skills only for a specific project, copy the skill folder into your project's agent directory:

```bash
cd my-project
mkdir -p .gemini/skills
cp -r ~/devrel-demos/agents/skills/video-description .gemini/skills/
```

### Option 3: Google Antigravity (IDE)

Antigravity automatically discovers skills in standard locations.

1. Copy the skill folder you need.
2. Place it in `~/.gemini/antigravity/skills/` (for User scope) or your project's `.agent/skills/` folder (for Project scope).
3. Restart the Antigravity editor (or reload window).
4. The agent will now intuitively know how to use these tools when you ask it to "deploy" or "debug".

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
2. **SKILL.md**: Must contain valid YAML frontmatter including `name` and `description`.
3. **Linting**: Ensure code passes `ruff` checks and markdown is properly formatted.
