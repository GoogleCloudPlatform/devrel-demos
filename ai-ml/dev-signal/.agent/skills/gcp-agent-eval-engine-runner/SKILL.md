---
name: gcp-agent-eval-engine-runner
description: Boilerplate for a production evaluation runner that performs parallel inference, captures reasoning traces via SSE, and integrates with the Vertex AI Gen AI Evaluation service.
---

# gcp-agent-eval-engine-runner

This skill provides the "engine" for your automated evaluation pipeline. Grounded in `evaluation_blog.md`, it handles the complexity of running hundreds of parallel requests against a shadow revision while capturing the full "Thinking Process" (Reasoning Trace).

## Usage

Ask Antigravity to:
- "Create an evaluation runner script for my agent"
- "Implement parallel inference for my golden dataset"
- "Capture SSE traces for tool trajectory evaluation"

## Engine Pattern

1. **Parallel Inference**: Uses `asyncio.Semaphore` to throttle requests (preventing DDOS of the shadow service).
2. **SSE Capture**: Connects to the ADK `POST /run_sse` endpoint to stream intermediate events.
3. **Dataset Enrichment**: Appends `response` and `intermediate_events` to the input dataset.
4. **Vertex AI Integration**: Submits the enriched dataset to the `create_evaluation_run` API.

## Python Boilerplate

Refer to `scripts/evaluate_agent_boilerplate.py` for the core implementation.
