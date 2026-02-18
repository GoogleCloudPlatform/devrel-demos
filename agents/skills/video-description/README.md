# Video Description Skill

This directory contains the "Video Description" skill, designed to help AI agents generate video descriptions.

## Contents

- **[SKILL.md](SKILL.md)**: The main instruction file for the AI agent. It defines the workflow for analyzing transcripts and drafting descriptions.
- **[references/TEMPLATES.md](references/TEMPLATES.md)**: A collection of standard templates for different video types (Technical, Entertainment, Product).
- **[references/EXAMPLES.md](references/EXAMPLES.md)**: Few-shot examples to guide the agent's output style.
- **[assets/evaluations.json](assets/evaluations.json)**: A set of test cases used to verify the skill's performance and regression testing.

## Scripts

The `scripts/` directory contains utilities to ensure quality and correctness:

### Validation (`scripts/validate.py`)

Checks a generated description file against best practices (e.g., length, hashtags, links, timestamps).

**Usage:**

```bash
python3 scripts/validate.py <path_to_description_file>
```

### Regression Testing (`scripts/test_validate.py`)

A `pytest` suite that uses `evaluations.json` to verify that the agent logic (mocked or real) meets the defined expectations.

**Usage:**

```bash
pytest scripts/test_validate.py
```
