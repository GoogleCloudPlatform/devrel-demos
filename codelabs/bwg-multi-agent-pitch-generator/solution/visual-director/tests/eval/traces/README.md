# Pre-generated traces

`brand-fit-traces.json` is one recorded run of the Visual Director over
`../datasets/brand-fit-dataset.json`: the art direction the agent wrote for each
of the six briefs, plus the `generate_key_visual` tool calls it made.

Recorded 2026-09-18 against `gemini-3.8-flash` for the agent and
`gemini-3.1-flash-lite-image` for the tool. Every case shows the same shape:
`load_skill` for `brand-guidelines`, then `generate_key_visual`, then the art
direction as the final response. The rendered images are not in here — only the
tool call and the artifact metadata it returned.

It exists so that `agents-cli eval grade` works with nothing but a key:

```bash
export GEMINI_API_KEY="your-ai-studio-key"   # or rely on ADC
agents-cli eval grade --traces tests/eval/traces/ --metrics custom_brand_fit
```

Generating traces needs a Google Cloud project with Vertex AI and image model
quota. Grading them does not. Once the lab project is deleted, this file is what
keeps the eval runnable.

## Do not write new runs here

`--traces` accepts a file or a directory. Given a directory it globs every
`*.json` inside and merges the cases, so a second file here means the judge
grades twelve cases instead of six. Send your own runs to `artifacts/traces/`
instead:

```bash
agents-cli eval generate \
  --dataset tests/eval/datasets/brand-fit-dataset.json \
  --output artifacts/traces/ \
  --concurrency 1
```

## Refreshing this file

Regenerate when the agent's instruction, model, or the dataset changes —
otherwise the traces describe an agent that no longer exists. From the
`visual-director` project, with the Vertex environment variables exported:

```bash
agents-cli eval generate \
  --dataset tests/eval/datasets/brand-fit-dataset.json \
  --output tests/eval/traces/brand-fit-traces.json \
  --concurrency 1
```

`--concurrency 1` is deliberate: six renders at once exhausts the image model's
per-minute quota on a lab project and every case fails with `429
RESOURCE_EXHAUSTED`. Naming the output as a file, rather than a directory, keeps
the filename stable instead of adding a timestamped second copy.
