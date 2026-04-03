---
name: gcp-agent-golden-dataset-builder
description: Assists developers in collecting and structuring a library of diverse examples ("Golden Dataset") required for data-driven evaluation, including tool trajectories.
---

# gcp-agent-golden-dataset-builder

This skill helps you build the foundation for data-driven agent development: the Golden Dataset. Grounded in `evaluation_blog.md`, it focuses on verifying not just the final answer, but the "Thinking Process" (Reasoning Trace).

## Usage

Ask Antigravity to:
- "Build a golden dataset with tool trajectories"
- "Structure my evaluation data for tool call validation"
- "Create a template for my Course Creator agent evaluation"

## Dataset Pattern

A production-ready dataset uses the `.jsonl` format and includes:
1. **`prompt`**: The user input.
2. **`reference`**: The ground truth answer (for semantic ResponseMatch).
3. **`reference_trajectory`**: A list of expected tool calls. This allows the evaluator to check if the agent used the right tools in the right order.

## Example Structure

Refer to `examples/trajectory_dataset.jsonl` for the implementation. Note the use of `tool_name` and `tool_input` in the trajectory.
