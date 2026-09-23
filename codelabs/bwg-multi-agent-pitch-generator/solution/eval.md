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
| `eval generate` | Your agent, once per case | A Google Cloud project with Vertex AI, the Vertex environment variables exported, plus image model quota |
| `eval grade` | The judge, over saved traces | Application Default Credentials **or** a free AI Studio `GEMINI_API_KEY` — one or the other, never both |

So you can grade pre-generated traces with nothing but an API key, and only need a
project when you want to re-run the agent itself.

## Run it

From the repository root, set up the environment and the project:

```bash
source ./setenv.sh
cd solution/visual-director
uv sync --extra eval
```

`setenv.sh` sits at the repository root and exports `GOOGLE_GENAI_USE_VERTEXAI`,
`GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`. Those variables live only as
long as the shell session, so source it again in every new Cloud Shell tab, then
check them:

```bash
echo "$GOOGLE_GENAI_USE_VERTEXAI $GOOGLE_CLOUD_PROJECT $GOOGLE_CLOUD_LOCATION"
```

You want `true`, your project ID, and `global`. Without
`GOOGLE_GENAI_USE_VERTEXAI` the client falls back to the Gemini API, and since the
agent pins `location="global"`, every case fails with `Gemini API does not support
project/location`. A `GEMINI_API_KEY` is no substitute: it grades, it cannot
generate. Run `unset GEMINI_API_KEY` if you exported one earlier.

### Everything at once

Runs the agent over the six briefs, then grades the results:

```bash
agents-cli eval run --dataset tests/eval/datasets/brand-fit-dataset.json
```

`eval generate` starts a local server, dispatches the cases in parallel, and tears
it down. Each case calls the image model, so this is the slow, quota-hungry half.

On a lab project, six renders at once is usually more than the image model's
per-minute quota allows, and you get `429 RESOURCE_EXHAUSTED`. Serialize them:

```bash
agents-cli eval run --dataset tests/eval/datasets/brand-fit-dataset.json --concurrency 1
```

A throttled call can also surface as `Malformed agent event: missing content` on
the cases either side of it, because older `agents-cli` releases treat an empty
event as fatal. Upgrade before you debug that one:

```bash
uv tool upgrade google-agents-cli   # or: pip install --upgrade google-agents-cli
```

### Grade only

`tests/eval/traces/brand-fit-traces.json` ships with the repo: one run of the
agent over all six briefs, captured on a working project. Judging it needs no
project of your own, so this path survives the lab project going away.

The judge builds a bare `genai.Client()`, which reads whatever the environment
offers. The two ways to feed it are exclusive, and having both is not "either
works" — the Vertex variables win and the key is ignored. Pick one.

With an AI Studio key and no Google Cloud at all:

```bash
unset GOOGLE_GENAI_USE_VERTEXAI GOOGLE_CLOUD_PROJECT GOOGLE_CLOUD_LOCATION
export GEMINI_API_KEY="your-ai-studio-key"
agents-cli eval grade --traces tests/eval/traces/ --metrics custom_brand_fit
```

Or, inside the lab, on Application Default Credentials:

```bash
source ./setenv.sh   # from the repository root
unset GEMINI_API_KEY
agents-cli eval grade --traces tests/eval/traces/ --metrics custom_brand_fit
```

Run it from the `visual-director` project root either way: the judge reads the
rubric from `visual_director/skills/brand-guidelines/SKILL.md`, relative to the
project. A `.env` in the project is loaded too, so a stale
`GOOGLE_GENAI_USE_VERTEXAI=true` in there quietly overrides the key.

`--metrics custom_brand_fit` is what keeps a project optional. The metric runs
in the CLI's own process, so nothing reaches the Vertex eval service. Select a
metric that is not local and a configured project becomes mandatory.

This is also the honest way to read a rubric change. Edit
`brand-guidelines/SKILL.md`, grade the same traces again, and the score moves
because the rubric moved, not because the agent drew something different.

### Generate your own traces

Keep your runs out of `tests/eval/traces/`. A directory passed to `--traces` is
globbed for every `*.json` inside, so your run would be graded alongside the
shipped one:

```bash
agents-cli eval generate \
  --dataset tests/eval/datasets/brand-fit-dataset.json \
  --output artifacts/traces/ \
  --concurrency 1

agents-cli eval grade --traces artifacts/traces/ --metrics custom_brand_fit
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
