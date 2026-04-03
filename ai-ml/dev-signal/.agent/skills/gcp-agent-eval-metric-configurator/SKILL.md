---
name: gcp-agent-eval-metric-configurator
description: Provides templates for configuring Vertex AI Gen AI Evaluation metrics like GROUNDING, TOOL_USE_QUALITY, and ResponseMatch for specific agent domains.
---

# gcp-agent-eval-metric-configurator

This skill helps you configure sophisticated automated evaluation metrics. Grounded in `evaluation_blog.md`, it supports computation-based, rubric-based, and managed Vertex AI metrics.

## Usage

Ask Antigravity to:
- "Configure Grounding metrics for my researcher agent"
- "Add a Tool Use Quality evaluator to my pipeline"
- "Set up a ResponseMatch check against my reference answers"
- "Configure an adaptive rubric for style alignment"

## Metric Taxonomy

1. **Computation-Based**: JSON validity, Execution trajectory matching.
2. **Managed Rubric-Based (Vertex AI)**:
    - `GROUNDING`: Ensures responses are fully supported by context (RAG).
    - `TOOL_USE_QUALITY`: Checks if the right tool was called with correct parameters (no reference needed).
3. **Adaptive Rubrics**: Use LLM-as-a-judge to grade responses based on unique criteria generated for each prompt.

## Metric Templates

Refer to `resources/metric_templates.json` for standard definitions.
