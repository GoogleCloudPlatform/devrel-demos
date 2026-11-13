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

"""Percentiles and summaries for a CSV column.

Usage: python3 -m k8s_revisited_bench.stats FILE.csv --column latency_ms [--group-by condition]
"""
import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict


def percentile(values, p):
    """Nearest-rank percentile, p in [0, 100]."""
    if not values:
        return float("nan")
    data = sorted(values)
    k = max(0, min(len(data) - 1, math.ceil(p / 100.0 * len(data)) - 1))
    return data[k]


def summarize(values):
    values = [v for v in values if not math.isnan(v)]
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "p50": percentile(values, 50),
        "p95": percentile(values, 95),
        "p99": percentile(values, 99),
        "p999": percentile(values, 99.9),
        "max": max(values),
    }


def load(path, column, group_by=None):
    groups = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                v = float(row[column])
            except (KeyError, ValueError):
                continue
            groups[row.get(group_by, "all") if group_by else "all"].append(v)
    return groups


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("csv")
    p.add_argument("--column", required=True)
    p.add_argument("--group-by")
    args = p.parse_args(argv)
    groups = load(args.csv, args.column, args.group_by)
    print("| group | n | p50 | p95 | p99 | p99.9 | mean |")
    print("|---|---|---|---|---|---|---|")
    for name, values in sorted(groups.items()):
        s = summarize(values)
        if s["n"] == 0:
            continue
        print(f"| {name} | {s['n']} | {s['p50']:.2f} | {s['p95']:.2f} | {s['p99']:.2f} | {s['p999']:.2f} | {s['mean']:.2f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
