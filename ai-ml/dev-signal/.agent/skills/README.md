# Google Cloud Agent Production Skills

This folder contains a suite of 13 Antigravity Skills designed to standardise the transition from AI prototypes to production-ready agents on Google Cloud. These skills are grounded in the professional roadmaps for infrastructure, evaluation, and security hardening.

## Skill Scopes

Antigravity supports two scopes for organizing skills:

1.  **Workspace Scope**: Located in `<workspace-root>/.agent/skills/` (this folder). These skills are specific to this project and are intended to be committed to version control so they are available to all collaborators on the project.
2.  **Global Scope**: Located in `~/.gemini/antigravity/skills/`. These skills are available across all projects on your machine. This is suitable for general utilities like "Format JSON," "Generate UUIDs," "Review Code Style," or integration with personal productivity tools.

## How to Use These Skills

1.  **Installation**: Locate skills in  `.agent/skills/` within your project root. Antigravity automatically detects them in this workspace.
2.  **Prompting**: Ask Antigravity for specific production patterns. For example:
    *   *"Configure Model Armor for my agent"*
    *   *"Deploy a shadow revision to Cloud Run"*
    *   *"Implement Trajectory Recall metrics"*
    *   *"Scaffold a Vertex AI Memory Bank integration"*

## Available Skills

### 🏗️ Production Agent
*   **[adk-memory-bank-initializer](./adk-memory-bank-initializer/SKILL.md)**: Vertex AI Memory Bank connection logic.
*   **[agent-containerizer](./agent-containerizer/SKILL.md)**: Mixed-runtime Dockerfiles (Python + Node.js).
*   **[cloud-run-agent-architect](./cloud-run-agent-architect/SKILL.md)**: Least-privilege Terraform for Cloud Run.
*   **[gcp-production-secret-handler](./gcp-production-secret-handler/SKILL.md)**: Secure in-memory secret fetching pattern.
*   **[mcp-connector-generator](./mcp-connector-generator/SKILL.md)**: Scaffolding for MCP server connections.

### 🛡️ Security 
*   **[gcp-agent-model-armor-shield](./gcp-agent-model-armor-shield/SKILL.md)**: Configures Model Armor (Prompt Injection, RAI filters).
*   **[gcp-agent-safety-gatekeeper](./gcp-agent-safety-gatekeeper/SKILL.md)**: Python integration boilerplate (`safety_util.py`).
*   **[gcp-agent-sdp-template-factory](./gcp-agent-sdp-template-factory/SKILL.md)**: Terraform for Sensitive Data Protection (PII redaction).

### 📊 Evaluation
*   **[gcp-agent-eval-engine-runner](./gcp-agent-eval-engine-runner/SKILL.md)**: Parallel inference and reasoning trace capture.
*   **[gcp-agent-eval-metric-configurator](./gcp-agent-eval-metric-configurator/SKILL.md)**: Setup for Grounding and Tool Use rubrics.
*   **[gcp-agent-golden-dataset-builder](./gcp-agent-golden-dataset-builder/SKILL.md)**: Tools for building datasets with reference trajectories.
*   **[gcp-agent-shadow-deployer](./gcp-agent-shadow-deployer/SKILL.md)**: "Dark Canary" deployment scripts (Cloud Run tagging).
*   **[gcp-agent-tool-trajectory-evaluator](./gcp-agent-tool-trajectory-evaluator/SKILL.md)**: Custom Python metrics for Precision and Recall.

### Pro tip - self improving skills!
Because these skills were AI-generated, they might not work perfectly for your specific environment on the first try. But that's actually the best part of working with an agentic IDE. If a skill doesn't work well for you, don't just manually fix the code, let the coding agent figure it out. Once it finds the solution, you can ask it to update the corresponding SKILL.md with the learned workflow. This will capture the corrected workflow for the future, ensuring the agent doesn't repeat the mistake while saving you tokens and time on the next run. Think of these as living documents that actively improve as you build.

