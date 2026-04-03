---
name: gcp-agent-tool-trajectory-evaluator
description: Provides custom Python metrics for configuring Vertex AI Gen AI Evaluation to measure Trajectory Precision, Recall, and Order Match.
---

# gcp-agent-tool-trajectory-evaluator

This skill provides the specialized Python logic needed to evaluate how an agent uses its tools. Grounded in `evaluation_blog.md`, it moves beyond "Did the tool run?" to "Were the tools used correctly and efficiently?"

## Usage

Ask Antigravity to:
- "Implement Trajectory Precision and Recall metrics"
- "Set up an Order Match metric for my multi-step agent"
- "Add a custom trajectory scorer to my Vertex AI evaluation"

## Metric Definitions

1. **Trajectory Precision**: Measures what percentage of called tools were actually specified in the reference.
2. **Trajectory Recall**: Measures what percentage of required tools were successfully called by the agent.
3. **In-Order Match**: Checks if the required tools were called in the correct sequence (even if other non-essential tools were called in between).

## implementation Pattern

Refer to `scripts/trajectory_metrics.py`. These functions are designed to be serialized and passed to Vertex AI via `CustomCodeExecutionSpec`.
