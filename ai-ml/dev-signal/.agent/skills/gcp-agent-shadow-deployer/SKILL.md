---
name: gcp-agent-shadow-deployer
description: Implements the "Dark Canary" pattern for Cloud Run, allowing agents to be evaluated in production without serving user traffic.
---

# gcp-agent-shadow-deployer

This skill helps you implement safe, automated rollouts for your AI agents. Grounded in `evaluation_blog.md`, it uses Cloud Run revision tagging to deploy a "Shadow Version" for evaluation before promoting it to live traffic.

## Usage

Ask Antigravity to:
- "Deploy a shadow revision of my agent for evaluation"
- "Tag my new Cloud Run revision with the Git SHA"
- "Promote my shadow revision to 100% traffic"

## Shadow Pattern ("Dark Canary")

1. **Tag with SHA**: Every deployment is tagged with the current Git commit SHA (e.g., `sha-a1b2c3d`).
2. **--no-traffic**: The revision is deployed but receives 0% of the public service URL traffic.
3. **Shadow URL**: The deployment creates a unique, private URL (e.g., `https://sha-...---service.run.app`) for the evaluation runner.
4. **Promotion**: If evaluation metrics pass, the revision is promoted to 100% traffic.

## Shell Template

Refer to `scripts/deploy_shadow.sh` for the standard implementation.
