# Inspect AI Agent Evaluation Framework & Reproduction Guide

This repository contains the evaluation scripts, dataset configurations, and telemetry exporters accompanying the blog series **"Terminal to Team Sync: Collaborative AI Evals"**.

---

## 📖 Preface: Architectural Overview & Design Intent

This repository and technical manual serve as the definitive technical companion to the blog series **"Terminal to Team Sync: Collaborative AI Evals"**.

While the blog series explores the high-level narrative, analytical trade-offs, and team workflows of LLM agent evaluations, this README provides the definitive technical specification. It houses all diagnostic taxonomies, external configuration schemas (`questions.json`, `thrifty_system_prompt.txt`), rate-limiting defenses (`version="0.51.0"`), and KaTeX score curving math in a single self-contained reference.

Whether you are seeking to reproduce the benchmark sweeps presented in the blog series, inspect granular sample-level trace diagnostics in `inspect view`, or export telemetry to Data Studio dashboards, this document guides you through the full evaluation lifecycle.

---

## 📋 Prerequisites & Setup

Before running evaluation sweeps or telemetry parsing scripts, prepare your environment by installing required packages and exporting API credentials.

### Downloading the Demo (`giget`)
You can download this single demo directory without cloning the entire repository:

```bash
npx -y giget@latest gh+git:GoogleCloudPlatform/devrel-demos/agents/inspect-agent-skills-eval inspect-evals
cd inspect-evals
```

### Environment & Dependencies
Ensure you have Python 3.10+ installed. Initialize a virtual environment and install the required dependencies:

> [!NOTE]
> Evaluation sweeps were benchmarked using **Python 3.13**, `inspect-ai` (`v0.3.247`), `inspect-swe` (`v0.2.66`), `inspect-viz` (`v0.4.1`), and `pandas` (`v3.0.3`). If upstream PyPI updates introduce breaking API changes, pin package versions to match this tested baseline.

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Inspect AI and telemetry dependencies
pip install inspect-ai inspect-swe inspect-viz pandas
```

### API Key Configuration
Export your Gemini API Key before running evaluation tasks:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

---

## 🗂️ Repository Structure

To support a clean separation of concerns, the repository is organized into distinct execution, configuration, visualization, and telemetry components that work in concert across the evaluation lifecycle:

* **[`skills-eval.py`](skills-eval.py)**: Main evaluation engine built on Inspect AI. Configures dynamic solvers, grader models, and multi-fact scoring rubrics.
* **[`questions.json`](questions.json)**: External dataset configuration containing evaluation questions, prompts, target skills, and atomic facts.
* **[`thrifty_system_prompt.txt`](thrifty_system_prompt.txt)**: Optimized system prompt template enforcing token thriftiness and dynamic format string interpolation (`{time_limit_str}`, `{web_access_instruction}`).
* **[`inspect_viz_heatmap.py`](inspect_viz_heatmap.py)**: Custom matrix visualization script generating score heatmaps using `inspect_viz`.
* **[`tocsv.py`](tocsv.py)**: Telemetry log parser that computes audit flags (`completed`, `is_baseline_or_has_activated_skill`) and outputs `data_mega_export.csv`.
* **`google-skills/`**: External repository containing domain skill definitions (`gemini-api`, `gcloud`). Must be cloned locally (`git clone https://github.com/google/skills.git google-skills`) and updated manually via `git pull` to ingest new or updated skill definitions.

---

## ⚙️ Evaluation Pipeline Architecture & Technical Reference

The evaluation harness (`skills-eval.py`) implements three core architectural dimensions designed for running automated, high-concurrency benchmarks in production CI/CD pipelines. These dimensions ensure that test parameters remain maintainable, infrastructure quotas remain protected, and grading rubrics remain statistically rigorous:

### 1. External Configurations
To decouple test parameters from Python execution logic:
* **`questions.json`**: Stores test prompts (`prompt`), target skills (`skill`), and rubric criteria (`facts`) outside Python code. This allows adding test samples or updating prompt baselines in CI/CD without modifying `skills-eval.py`.
* **`thrifty_system_prompt.txt`**: Serves as a dynamic prompt template with format string interpolation (`{time_limit_str}`, `{web_access_instruction}`).
  * `--time-limit 300` interpolates "300 seconds" into `{time_limit_str}` to enforce a time budget on agent execution.
  * `-T web_access=false` interpolates `WEB_ACCESS_PROHIBITED_INSTRUCTION` into `{web_access_instruction}`, curtailing web search loops to minimize token spend and latency.

### 2. Quota Management & Infrastructure Protection
To protect API rate limits and infrastructure quotas during high-throughput evaluation sweeps:
* **Solver Tool Version Pinning**: Solvers instantiated via `solver=gemini_cli(...)` are explicitly pinned to a specific release version (`version="0.51.0"`). Omitting this defaults to `"auto"`, which issues an unauthenticated HTTP GET request to GitHub's release API on every task initialization, triggering `HTTP 403 Rate Limit Exceeded` failures under parallel sweeps.
* **Token Thriftiness**: The system prompt explicitly instructs agents to focus output strictly on solving the question, preventing conversational verbosity and saving output token quota.
* **Dynamic Token Pricing & Fail-Fast Error Handling**: Model token costs per 1M tokens are registered in [`MODEL_PRICING`](tocsv.py#L21) in `tocsv.py`.
  
  > [!WARNING]
  > **Fail-Fast KeyError Behavior**: If `tocsv.py` processes evaluation logs containing a model missing from [`MODEL_PRICING`](tocsv.py#L21), it immediately halts and raises a `KeyError` at [line 134](tocsv.py#L134).

### 3. Decoupled Grader & Multidimensional Rubrics
To eliminate solver quota starvation and improve evaluation precision:
* **Grader Model Isolation**: Solvers (`google/gemini-3.5-flash-lite`, `google/gemini-3.6-flash`) are decoupled from the grader (`GRADER_MODEL = "google/gemini-3.1-flash-lite"`), isolating API quota pools and enabling lightweight, lower-cost grading.
* **Atomic Fact Verification & Quadratic Curving**: Instead of evaluating full answers using monolithic string matching (`model_graded_qa`), `make_fact_scorer` checks atomic facts individually (emitting binary `1.0` or `0.0` scores). The `custom_reducer` averages fact scores and applies quadratic curving:

$$\text{mean score} = \frac{\sum_{i=1}^{N} \text{score}_i}{N} \quad \text{where } \text{score}_i \in \{0.0, 1.0\}$$

$$\text{curved score} = \frac{\lfloor \text{SCORING SCALE} \times (\text{mean score})^2 \rfloor}{\text{SCORING SCALE}}$$

> [!IMPORTANT]
> **Quadratic Curving Penalty**: By squaring the raw fact mean score ($\text{mean}^2$), partial completions are intentionally penalized in [`custom_reducer()`](skills-eval.py#L108). This demands high precision for production deployment while ensuring a 1.0 score remains attainable through targeted skill refinement.

---

## 🚀 Reproduction Guide

With the environment configured and pipeline architecture established, you can execute evaluation sweeps, perform diagnostic log auditing, generate matrix heatmaps, and extract structured telemetry using the step-by-step reproduction instructions below.

### Executing Benchmark Sweeps

1. **Clone Skill Repository**: Ensure domain skill definitions are cloned into `google-skills/` before running benchmark sweeps:
```bash
git clone https://github.com/google/skills.git google-skills
```

2. **Execute Benchmark Sweep**: Run the evaluation sweep across models, skill conditions, samples, and epochs:

```bash
inspect eval skills-eval.py \
  --model google/gemini-3.5-flash-lite,google/gemini-3.6-flash \
  --time-limit 300 \
  --epochs 2 \
  --max-tasks 4 \
  -T web_access=false
```

#### CLI Parameter Reference
* **`--model`**: Specifies target solver models evaluated head-to-head (`google/gemini-3.5-flash-lite`, `google/gemini-3.6-flash`).
* **`--time-limit`**: Enforces a 300-second per-task execution timeout (interpolated into `{time_limit_str}` in `thrifty_system_prompt.txt`).
* **`--epochs`**: Repeats sample runs ($N=2$) to smooth out LLM non-deterministic variance.
* **`--max-tasks`**: Sets 4-way parallel worker concurrency (16 total runs: 2 models × 4 skills × 2 epochs @ 5 min max each, reducing maximum sweep runtime from 80 minutes down to 20 minutes).
* **`-T web_access=false`**: Dynamic keyword argument passed to tasks via `**kwargs` in `skills-eval.py`. Disables internet access to curtail web search loops and minimize token spend.

---

### Local Diagnostic Trace Analysis (`inspect view`)

Once evaluation logs are generated, step down from macro execution summaries into micro sample-level execution traces using Inspect AI's built-in web TUI log viewer:

```bash
inspect view
```

* Navigate to `http://localhost:7575` in your browser.
* **Cohort Sorting**: Click the **Model** column header to sort runs head-to-head by solver capability, or click **Skill Group** to group runs by experimental skill condition against baseline controls.
* **Sample Inspection**: Click any sample row to open the **Sample Details** panel $\rightarrow$ **Transcript Tab** to inspect multi-turn agent conversations, shell tool executions, and system prompt injections.
* **Sandbox Noise vs. Model Reasoning**:
  * **Model Reasoning Loop**: Same tool called repeatedly with identical parameters; high output token count accompanied by degraded scoring.
  * **Environment Noise**: Sandbox network timeouts, container initialization crashes, or uninstalled binary packages. Requires environment correction prior to evaluating model capability.

#### Diagnostic Mental Models for Eval Comparison (Skill vs. Baseline)

When comparing baseline controls against skill-augmented runs, evaluate performance across five diagnostic outcomes:

1. 🥇 **High-Efficiency Capability Lift (Best Outcome)**
   * **What you see**: Accuracy improves substantially while token consumption and latency decrease.
   * **Interpretation**: `SKILL.md` provided vital domain SOPs eliminating trial-and-error debugging loops.
   * **Action Item**: Green light for production deployment. Audit for skill overfitting if questions ask for hyper-specialized text rather than general execution capability.

2. 🟢 **High-Efficiency Capability Lift (Good Outcome)**
   * **What you see**: Accuracy improves materially while token consumption and latency increase moderately.
   * **Interpretation**: `SKILL.md` improved reasoning quality or search efficiency, though thinking traces became slightly more verbose.
   * **Action Item**: Positive indicator. Test across larger, more complex workloads to verify if token/latency cost increases justify accuracy gains.

3. ⚠️ **Cost-Bloated Pyric Victory (Unflattering Outcome)**
   * **What you see**: Accuracy increases marginally (+5-10%), but token consumption and latency explode.
   * **Interpretation**: Agent uses the skill but gets caught in inefficient, looping multi-turn container execution paths.
   * **Action Item**: Inspect transcript tool call traces to identify repeated command failures or inefficient container loops.

4. ⚪ **Baseline Parity / Superfluous Skill (Neutral Outcome)**
   * **What you see**: Baseline and Skilled runs yield near-identical accuracy and latency metrics.
   * **Interpretation**: Skill is ignored entirely or merely duplicates the model's in-built knowledge.
   * **Action Item**: Verify skill ingestion in transcripts (`activate_skill`). If un-ingested, the eval tests baseline reasoning rather than skill utility.

5. 🔴 **Context Overload & Skill Regression (Unflattering Outcome)**
   * **What you see**: Accuracy does not increase while token consumption and latency spike.
   * **Interpretation**: `SKILL.md` prompt is ambiguous, overly long, or conflicts with base instructions—causing context window bloat and prompt confusion.
   * **Action Item**: Audit system prompt injection and per-fact score breakdowns in transcripts and scoring tabs.

---

### Custom Matrix Visualization (`inspect_viz_heatmap.py`)

To aggregate sample runs and visualize macro performance across model and skill cohorts, generate 2D score heatmaps using `inspect_viz`:

```bash
python3 inspect_viz_heatmap.py
```

This processes raw `.eval` log files in `logs/` and outputs interactive visual heatmaps locally.

---

### Telemetry Extraction (`tocsv.py`)

To bridge terminal log inspection with executive reporting in Google Sheets or Data Studio, process raw evaluation logs into a flat, enriched CSV format:

```bash
python3 tocsv.py
```

This parses raw `.eval` logs in `logs/` and outputs `data_mega_export.csv`, injecting pre-computed audit flags (`completed`, `is_baseline_or_has_activated_skill`) and in-cell Sheets sparkline formulas parsed directly by [`tocsv.py`](tocsv.py).

### Data Science Audit Flags & Rationale

1. **`completed` (Conditional Accuracy vs. Infrastructure Noise)**:
   * **Filter Rationale**: Isolates pure model intelligence on clean runs (`completed = TRUE`) from infrastructure noise (`FALSE` for rate limits, container crashes, or task timeouts).
   * **Survivorship Bias**: Comparing `completed = ALL` against `completed = TRUE` exposes survivorship bias under quota-constrained benchmarks (e.g., `-T web_access=true`).

2. **`is_baseline_or_has_activated_skill` (Bayesian Skill Uptake)**:
   * **Filter Rationale**: Evaluated via generator comprehension in `is_baseline_or_has_activated_skill()` in [`tocsv.py`](tocsv.py) to check tool call traces for `activate_skill`.
   * **Bayesian Uptake**: Distinguishes active tool uptake (`TRUE`) from dormant runs (`FALSE`, where a mounted skill was ignored by the model), enabling baseline update analyses.
