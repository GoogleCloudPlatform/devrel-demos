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

"""Run tasks under each condition and record one CSV row per run."""
import csv
import datetime
import json
import os
import time

from .checkers import extract_yaml, feedback_text, run_checks, verdict

CONDITIONS = ["bare", "context_skill", "repair_loop"]
FIELDS = ["timestamp", "ep", "task_id", "condition", "run", "model", "temperature", "turns", "passed",
          "first_try_pass", "stale_api_hits", "checks_failed", "checks_skipped", "tokens_in", "tokens_out", "wall_ms"]


def details_path_for(out_path):
    """results/agent-check.csv -> results/agent-check-details.jsonl"""
    root, _ = os.path.splitext(out_path)
    return root + "-details.jsonl"


def run_one(task, condition, run, model, ctx, max_turns, details=None):
    start = time.monotonic()
    feedback = None
    first_pass = None
    passed = False
    stale_total = tokens_in = tokens_out = 0
    results = []
    limit = max_turns if condition == "repair_loop" else 1
    turn = 0
    for turn in range(1, limit + 1):
        reply = model.generate(task, condition, turn, feedback)
        tokens_in += reply.tokens_in
        tokens_out += reply.tokens_out
        results, stale = run_checks(extract_yaml(reply.text), task, ctx)
        stale_total += stale
        if details is not None:
            details.write(json.dumps({
                "task_id": task.id, "condition": condition, "run": run, "turn": turn, "model": model.name,
                "reply": reply.text, "checks": [{"name": r.name, "status": r.status, "detail": r.detail} for r in results],
            }) + "\n")
        passed = verdict(results, ctx.require_all)
        if turn == 1:
            first_pass = passed
        if passed:
            break
        feedback = feedback_text(results)
    return {
        "turns": turn,
        "passed": "true" if passed else "false",
        "first_try_pass": "true" if first_pass else "false",
        "stale_api_hits": stale_total,
        "checks_failed": ";".join(r.name for r in results if r.status == "fail"),
        "checks_skipped": ";".join(r.name for r in results if r.status == "skipped"),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "wall_ms": round((time.monotonic() - start) * 1000, 1),
    }


def run_tasks(ep, tasks, conditions, runs, model, ctx, max_turns, out_path):
    """Writes one CSV row per run to out_path, and every reply with its check results
    to the matching -details.jsonl file."""
    rows = []
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    details = open(details_path_for(out_path), "w", encoding="utf-8")
    try:
        _run_all(ep, tasks, conditions, runs, model, ctx, max_turns, rows, details)
    finally:
        # Keep whatever finished if a run fails partway (for example on a quota error).
        details.close()
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
    return rows


def _run_all(ep, tasks, conditions, runs, model, ctx, max_turns, rows, details):
    for task in tasks:
        for condition in conditions:
            if condition not in task.conditions:
                continue
            for run in range(1, (runs or task.runs_per_condition) + 1):
                row = {
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                    "ep": ep,
                    "task_id": task.id,
                    "condition": condition,
                    "run": run,
                    "model": model.name,
                    "temperature": model.temperature,
                }
                row.update(run_one(task, condition, run, model, ctx, max_turns, details))
                rows.append(row)
