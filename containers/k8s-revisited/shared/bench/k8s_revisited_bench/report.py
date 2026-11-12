# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Render results/results.md from every CSV in a results directory.

For each CSV it lists the columns and, for numeric columns ending in _ms, a
percentile summary. Charts are rendered only if matplotlib is installed.

Usage: python3 -m k8s_revisited_bench.report results/
"""
import argparse
import csv
import glob
import os
import sys

from .stats import summarize


def numeric_ms_columns(rows):
    cols = []
    if not rows:
        return cols
    for key in rows[0].keys():
        if not key.endswith("_ms"):
            continue
        try:
            [float(r[key]) for r in rows if r.get(key) not in ("", None)]
            cols.append(key)
        except ValueError:
            pass
    return cols


def render(results_dir):
    lines = ["# Results", ""]
    env = os.path.join(results_dir, "env.json")
    if os.path.exists(env):
        lines += [f"Environment: [{os.path.basename(env)}]({os.path.basename(env)})", ""]
    for path in sorted(glob.glob(os.path.join(results_dir, "*.csv"))):
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        lines += [f"## {os.path.basename(path)}", "", f"{len(rows)} rows. Raw data: [{os.path.basename(path)}]({os.path.basename(path)})", ""]
        for col in numeric_ms_columns(rows):
            s = summarize([float(r[col]) for r in rows if r.get(col) not in ("", None)])
            if s["n"]:
                lines += [f"`{col}`: n={s['n']} p50={s['p50']:.2f} p95={s['p95']:.2f} p99={s['p99']:.2f} max={s['max']:.2f}", ""]
    return "\n".join(lines) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("results_dir", nargs="?", default="results")
    args = p.parse_args(argv)
    os.makedirs(args.results_dir, exist_ok=True)
    out = os.path.join(args.results_dir, "results.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(args.results_dir))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
