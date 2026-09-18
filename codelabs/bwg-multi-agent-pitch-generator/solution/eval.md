# Evaluate the Visual Director

The lab judged the *rendered images* in BigQuery with `ObjectRef` and `AI.SCORE`.
This is the other half: judging the **art direction text**, before any pixels exist,
against the same brand guidelines the agent loads as a skill.

Both use one rubric. `visual_director/skills/brand-guidelines/SKILL.md` tells the
agent how to write, and `tests/eval/brand_fit.py` reads that same file at grading
time to decide whether it listened. Edit the skill and the eval moves with it.

| Surface | Judges | When |
| --- | --- | --- |
| `agents-cli eval` | The art direction the agent wrote | Offline, before rendering |
| BigQuery `AI.SCORE` | The image that came out | After the asset is in Cloud Storage |

## What you need

The two halves of an eval run have different requirements, which matters once your
lab project is gone:

| Command | Runs | Needs |
| --- | --- | --- |
| `eval generate` | Your agent, once per case | A Google Cloud project with Vertex AI, plus image model quota |
| `eval grade` | The judge, over saved traces | Application Default Credentials **or** a free AI Studio `GEMINI_API_KEY` |

So you can grade pre-generated traces with nothing but an API key, and only need a
project when you want to re-run the agent itself.

## Run it

From the `visual-director` project:

```bash
cd solution/visual-director
uv sync --extra eval
```

### Everything at once

Runs the agent over the six briefs, then grades the results:

```bash
agents-cli eval run --dataset tests/eval/datasets/brand-fit-dataset.json
```

`eval generate` starts a local server, dispatches the cases in parallel, and tears
it down. Each case calls the image model, so this is the slow, quota-hungry half.

### Grade only

If `tests/eval/traces/` already holds traces, skip straight to judging:

```bash
export GEMINI_API_KEY="your-ai-studio-key"   # or rely on ADC
agents-cli eval grade --traces tests/eval/traces/ --metrics custom_brand_fit
```

### Generate your own traces

```bash
agents-cli eval generate \
  --dataset tests/eval/datasets/brand-fit-dataset.json \
  --output tests/eval/traces/
```

## Reading the results

Six briefs, chosen to spread the scores rather than flatter the agent:

| Case | What it tests |
| --- | --- |
| `skateboarding_cats` | The lab's own prompt, as a baseline |
| `rainy_commuter_bike` | A plain brief with no traps |
| `sunrise_coffee_ritual` | A brief that suits the house style naturally |
| `neon_energy_drink` | The client asks for neon cyan, magenta, and lens flare — all forbidden |
| `logo_hero_sneaker` | Marketing asks for a large logo and on-image text — forbidden |
| `crowded_festival_stage` | Implies a crowd shot from above — the guidelines want one subject at eye level |

The last three are the interesting ones. The guidelines say the subject comes from
the brief and the treatment comes from the house rules, so a good agent takes the
energy drink and refuses the neon. An agent that simply does what the brief asks
will score 1 or 2 and the judge will quote the rule it broke in `violations`.

That gap is the point of the eval. A prompt change that quietly makes the agent
more agreeable shows up here as a score drop, long before anyone notices the
campaign looks off-brand.

## Going further

```bash
agents-cli eval compare BASE.json CANDIDATE.json   # regression check between two runs
agents-cli eval analyze RESULTS.json               # cluster the failure modes
agents-cli eval metric list                        # the built-in metrics
```

A second judge ships with the scaffold: `custom_response_quality` grades generic
accuracy, relevance, and clarity. Select it with
`--metrics custom_response_quality` when you want quality independent of brand.

See the [Evaluation Guide](https://google.github.io/agents-cli/guide/evaluation/)
for the full surface.
