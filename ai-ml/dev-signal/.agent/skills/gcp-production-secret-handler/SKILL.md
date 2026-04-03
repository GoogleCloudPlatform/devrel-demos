---
name: gcp-production-secret-handler
description: Implements the "in-memory only" secret pattern for Google Cloud production agents.
---

# gcp-production-secret-handler

This skill implements the secure pattern for secret handling used in the `dev-signal` agent. It ensures sensitive credentials (API keys, client secrets) are fetched from Google Secret Manager directly into local memory, avoiding global environment variables that can be leaked through logs or traces.

## Usage

Ask Antigravity to:
- "Implement secure secret handling for my production agent"
- "Use the dev-signal secret pattern"
- "Fetch secrets from Secret Manager into a dictionary"

## The Pattern

1. **Local Dev**: Uses a `.env` file for fast iteration.
2. **Production**: Uses the `google-cloud-secret-manager` SDK to fetch specific versions of secrets.
3. **Isolation**: Secrets are stored in a Python dictionary (`SECRETS`) and passed as explicit parameters to toolset constructors or agent initializers.
4. **No global env injection**: Avoids using `os.environ[secret_id] = value`.

## Python Boilerplate

Refer to the included `scripts/env_utils.py` for the standard implementation.
