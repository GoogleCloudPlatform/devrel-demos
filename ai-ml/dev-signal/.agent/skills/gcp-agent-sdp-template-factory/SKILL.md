---
name: gcp-agent-sdp-template-factory
description: Standardizes the creation of Sensitive Data Protection (DLP) templates for PII and credential redaction.
---

# gcp-agent-sdp-template-factory

This skill helps you identify and protect sensitive data (PII, credentials, secrets) using Google Cloud Sensitive Data Protection (DLP). Grounded in `security_blog.md`, it supports both Inspect and De-identification (Redaction) templates.

## Usage

Ask Antigravity to:
- "Create an SDP Inspect template for PII and API keys"
- "Add a redaction template to mask credit card numbers"
- "Generate Terraform for my DLP inspector"
- "Set up a de-identification policy for my agent logs"

## Pattern: Inspect & Redact

1. **Inspect Template**: Defines *what* to look for (e.g., `PERSON_NAME`, `CREDIT_CARD_NUMBER`, `GCP_API_KEY`).
2. **De-identify Template**: Defines *how* to transform it (e.g., `Replace` with `[redacted]`, `Mask` with `#`).

## Terraform Boilerplate

Refer to `resources/sdp_templates.tf` for the standard infrastructure-as-code implementation.
