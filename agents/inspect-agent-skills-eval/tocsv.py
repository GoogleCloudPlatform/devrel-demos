# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
tocsv.py

Extracts Inspect AI logs and exports them to a CSV optimized for Google Sheets
and Looker Studio, including dynamic cost calculations and visualization sparklines.
"""

import glob
import os
import string
import sys

import pandas as pd
from inspect_ai.analysis import EvalModel, SampleColumn, SampleScores, samples_df
from inspect_ai.log import EvalSample

# --- Model Pricing Config ---
# Standard pricing per 1 million tokens for Gemini models.
# "Introducing Gemini 3.6 Flash, 3.5 Flash-Lite..." (Retrieved Jul 21, 2026) blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/
# Note: If running evaluations with other models, add their pricing here.
MODEL_PRICING = {
    "google/gemini-3.5-flash-lite": {
        "input_cost_per_million": 0.30,
        "output_cost_per_million": 2.50
    },
    "google/gemini-3.6-flash": {
        "input_cost_per_million": 1.50,
        "output_cost_per_million": 7.50
    }
}

# --- Sheets Layout Constants ---
SHEETS_START_ROW = 2  # First data row in Google Sheets (after header)

# --- Sheets Column Mappings ---
# Maps columns to Sheets letters (A, B, C...) dynamically to avoid "magic letters".
COLUMN_ORDER = [
    "model", "skill_group", "score", "score_sparkline",
    "latency", "latency_sparkline", "input_tokens", "output_tokens",
    "cost", "cost_sparkline",
    "is_baseline_or_has_activated_skill",
    "completed",
    # Included last to make the sheet easier to read
    "score_stderr", "score_lower", "score_upper"
]

# Assumes <=26 columns. Add multi-letter (AA, AB) logic if list expands.
COL_LETTERS = {col: string.ascii_uppercase[i] for i, col in enumerate(COLUMN_ORDER)}

# Sheets sparkline barchart color scheme (Yellow, Teal, Purple)
COLOR_HIGH, COLOR_MID, COLOR_LOW = "#fde725", "#21908d", "#440154"
PERCENTILE_HIGH_THRESHOLD = 0.75
PERCENTILE_MID_THRESHOLD = 0.50

# In cell bar chart templates `{{` used to disambiguate formatting braces from sheets options
SPARKLINE_FORMULA_TEMPLATE = f"""=IF(ISBLANK({{cell}}), "Incomplete", SPARKLINE(
  {{cell}},
  {{{{
    "charttype", "bar";
    "max", MAX({{column_range}});
    "color1",
      IFS(
        {{cell}} >= PERCENTILE({{column_range}}, {PERCENTILE_HIGH_THRESHOLD}), "{COLOR_HIGH}",
        {{cell}} >= PERCENTILE({{column_range}}, {PERCENTILE_MID_THRESHOLD}), "{COLOR_MID}",
        TRUE, "{COLOR_LOW}"
      )
  }}}}
))"""

def _sum_if_list(val):
    """Sums a list if the value is a list, otherwise returns the value."""
    return sum(val) if isinstance(val, list) else val


def is_baseline_or_has_activated_skill(sample: EvalSample) -> bool:
    """Returns True for baseline control runs OR runs that activated a skill (representing skill uptake in Inspect AI)."""
    skill_group = (sample.metadata or {}).get("skill_group", "")
    # Python generator comprehension: lazily flattens nested message->tool_call loops into any()
    return "Baseline" in str(skill_group) or not skill_group or any(
        getattr(tool_call, "function", None) in ("skill", "activate_skill")
        for message in (sample.messages or [])
        for tool_call in (getattr(message, "tool_calls", None) or [])
    )


# 1. Extract raw telemetry data from Inspect logs (Single-Pass Read)
df = samples_df(
    "./logs",
    # Restrict to only the columns relevant to our analysis
    columns=EvalModel + SampleScores + [
        SampleColumn("skill_group", path="metadata.skill_group"),
        SampleColumn("latency", path="working_time"),
        SampleColumn("input_tokens", path="model_usage.*.input_tokens"),
        SampleColumn("output_tokens", path="model_usage.*.output_tokens"),
        # Extract boolean indicating if baseline control or activated skill run (full=True loads messages)
        SampleColumn("is_baseline_or_has_activated_skill", path=is_baseline_or_has_activated_skill, full=True),
        # Unhandled exceptions, API quota/429 errors, or container crashes (inspect_ai.log.EvalSample.error)
        SampleColumn("error", path="error"),
        # Enforced resource limit truncations like time/token limits (inspect_ai.log.EvalSample.limit)
        SampleColumn("limit", path="limit"),
    ],
    parallel=True
)

# 2. Harmonize custom scorer column names to 'score'.
# We explicitly ignore helper '_metadata' columns to avoid renaming the wrong column if Inspect outputs multiple matches.
score_cols = [col for col in df.columns if col.startswith("score_") and not col.endswith("_metadata")]
if score_cols:
    df = df.rename(columns={score_cols[0]: "score"})
    # Distinguish infra failure (quota/timeout/limits) from capability.
    # Samples are complete ONLY if there was no error, no limit hit, and a valid score.
    # Preserves CSV audit trail; filter in Looker for clean capability metrics.
    df["completed"] = df["error"].isna() & df["limit"].isna() & df["score"].notna()

# Calculate standard error of the mean for the 'score' column grouped by model and skill_group.
# Although N=1 cohort collapse won't occur under our setup, we handle it defensively here.
standard_error_of_the_mean_series = df.groupby(["model", "skill_group"])["score"].sem().fillna(0.0)
df = df.merge(standard_error_of_the_mean_series.rename("score_stderr"), on=["model", "skill_group"], how="left")

# Calculate upper and lower confidence limits (standard error of the mean bounds)
df["score_lower"] = df["score"] - df["score_stderr"]
df["score_upper"] = df["score"] + df["score_stderr"]

# 3. Aggregate target and grading tokens to compute total usage per run.
for col in ["input_tokens", "output_tokens"]:
    df[col] = pd.to_numeric(
        df[col].apply(_sum_if_list), errors="coerce"
    ).fillna(0).astype(int)

# 4. Retrieve pricing and compute actual costs dynamically per model.
# We fail-fast with a clear error if the model is not defined in our pricing config.
unique_models = df["model"].unique()
for model in unique_models:
    if model not in MODEL_PRICING:
        raise KeyError(
            f"Pricing metadata for model '{model}' not found in MODEL_PRICING dictionary.\n"
            f"Please open 'tocsv.py' and add pricing values for '{model}' to the MODEL_PRICING dict."
        )

# Map pricing values (per million tokens) to the dataframe
input_rates_per_million = df["model"].map(lambda m: MODEL_PRICING[m]["input_cost_per_million"])
output_rates_per_million = df["model"].map(lambda m: MODEL_PRICING[m]["output_cost_per_million"])

df["cost"] = (
    (df["input_tokens"] * (input_rates_per_million / 1_000_000)) +
    (df["output_tokens"] * (output_rates_per_million / 1_000_000))
)

# 5. Inject Google Sheets formulas for sparklines.
max_row = len(df) + 1
sparkline_mappings = [("score", "score_sparkline"), 
                      ("latency", "latency_sparkline"), 
                      ("cost", "cost_sparkline")]

for data_col, spark_col in sparkline_mappings:
    col_let = COL_LETTERS[data_col]
    col_range = f"{col_let}${SHEETS_START_ROW}:{col_let}${max_row}"
    df[spark_col] = [
        SPARKLINE_FORMULA_TEMPLATE.format(
            cell=f"{col_let}{row}", 
            column_range=col_range
        )
        for row in range(SHEETS_START_ROW, len(df) + SHEETS_START_ROW)
    ]

# 6. Finalize column order to match the predefined spreadsheet layout.
df = df[COLUMN_ORDER]

# 7. Export CSV
df.to_csv("data_mega_export.csv", index=False)
print("Success! Created 'data_mega_export.csv'.")
