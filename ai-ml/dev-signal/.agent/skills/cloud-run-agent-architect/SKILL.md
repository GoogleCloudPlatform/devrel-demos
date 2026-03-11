---
name: cloud-run-agent-architect
description: Automates the generation of Terraform files for a secure Cloud Run deployment of an AI agent.
---

# cloud-run-agent-architect

This skill helps you provision secure, reproducible infrastructure on Google Cloud for your AI agents using Terraform. It follows the "least-privilege" principle and handles Secret Manager integration.

## Usage

Ask Antigravity to:
- "Generate Terraform files for my Cloud Run agent"
- "Create a secure service account for my agent"
- "Add my Reddit and Google Docs secrets to Terraform"

## Infrastructure Pattern

The generated infrastructure includes:
1. **Cloud Run Service**: Configured with automated secret injection and VPC egress if needed.
2. **Dedicated Service Account**: Granted specific roles like `roles/aiplatform.user` and `roles/secretmanager.secretAccessor`.
3. **Secret Manager**: Provisioned for sensitive API keys (e.g., `REDDIT_CLIENT_ID`, `DK_API_KEY`).
4. **Artifact Registry**: A private repository to host the agent's container images.

## Terraform Template

Refer to the included `resources/main.tf` and `resources/variables.tf` for the standard implementation.

### Key IAM Roles
- `roles/aiplatform.user`: To call Vertex AI models.
- `roles/logging.logWriter`: To export agent traces.
- `roles/storage.objectAdmin`: If the agent saves artifacts (e.g., images to GCS).
- `roles/secretmanager.secretAccessor`: To read secrets at runtime.
