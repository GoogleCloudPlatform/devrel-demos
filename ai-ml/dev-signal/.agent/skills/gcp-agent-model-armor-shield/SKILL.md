---
name: gcp-agent-model-armor-shield
description: Configures Model Armor security policies (Prompt Injection, Jailbreak, RAI filters).
---

# gcp-agent-model-armor-shield

This skill configures Model Armor as an intelligent firewall for your AI agents. Grounded in `security_blog.md`, it protects against prompt injection, jailbreaking, malicious URLs, and links to SDP templates for data privacy.

## Usage

Ask Antigravity to:
- "Configure Model Armor for my agent"
- "Add prompt injection protection to my security policy"
- "Set up RAI filters for hate speech and harassment"
- "Link my SDP templates to Model Armor via Terraform"

## Protection Layers

1. **Detection Filters**: Prompt Injection, Jailbreak, and Malicious URI detection.
2. **RAI Settings**: Configurable confidence levels for Hate Speech, Harassment, Sexually Explicit, and Dangerous Content.
3. **SDP Integration**: Hooks for Advanced Sensitive Data Protection (linking to Inspect/De-identify templates).

## Terraform Boilerplate

Refer to `resources/model_armor.tf` for the standard configuration.
