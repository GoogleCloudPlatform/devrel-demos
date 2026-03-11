---
name: gcp-agent-shadow-deployer
description: Implements the "Dark Canary" pattern for Cloud Run, allowing agents to be evaluated in production without serving user traffic.
---

# gcp-agent-shadow-deployer

This skill helps you implement safe, automated rollouts for your AI agents. Based on the **"Evaluating Agent Performance"** codelab, it uses Cloud Run revision tagging to deploy a **Shadow Revision** for evaluation before promoting it to live traffic. This enables **System-Level Evaluation** (latency, network, auth) rather than just unit testing.

## Usage

Ask Antigravity to:
- "Deploy a shadow revision of my agent for evaluation"
- "Tag my new Cloud Run revision with the Git SHA"
- "Promote my shadow revision to 100% traffic"

## Shadow Pattern ("Dark Canary")

1. **Tag with Commit Hash**: Every deployment is tagged with the current Git commit hash (e.g., `c-a1b2c3d`).
2. **--no-traffic**: The revision is deployed with **0%** traffic.
3. **Shadow URL**: Access the revision via a dedicated tag URL: `https://[TAG]---[SERVICE]-[HASH]-[REGION].a.run.app`.
4. **Promotion**: If evaluation metrics (Final Response Match, Tool Use Quality) pass, promote the revision to 100% traffic.

## Shell Template

Refer to `scripts/deploy_shadow.sh` for the standard implementation.
