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

"""Command line for the agent check.

Usage:
  python3 -m agent_check --ep 01 [--fake-model] [--runs 10] [--out results/agent-check.csv]
"""
import argparse
import os
import pathlib
import sys

from .checkers import CheckContext
from .models import make_model
from .runner import CONDITIONS, run_tasks
from .tasks import load_tasks

PKG = pathlib.Path(__file__).resolve().parent
TASK_DIR = PKG.parent / "tasks"
FIXTURE_DIR = PKG.parent / "fixtures"
SKILL = PKG.parent.parent / "skills" / "k8s-1.37" / "SKILL.md"


def build_parser():
    p = argparse.ArgumentParser(prog="agent_check", description="Run an episode's agent-check tasks under three conditions and write a CSV.")
    p.add_argument("--ep", required=True, help="episode number, for example 01")
    p.add_argument("--tasks", help="task file (default: tasks/epNN.yaml)")
    p.add_argument("--conditions", default=",".join(CONDITIONS), help="comma-separated subset of " + ",".join(CONDITIONS))
    p.add_argument("--runs", type=int, help="runs per task and condition (default: the task file's runs_per_condition)")
    p.add_argument("--max-turns", type=int, default=5, help="turn limit for the repair_loop condition")
    p.add_argument("--model", default=os.environ.get("PINNED_FLASH_MODEL", ""), help="model name (default: $PINNED_FLASH_MODEL)")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--fake-model", action="store_true", help="offline model with canned outputs, for testing the pipeline")
    p.add_argument("--context", default=os.environ.get("KUBE_CONTEXT", ""), help="kubectl context for server-side dry-run")
    p.add_argument("--skill", default=str(SKILL), help="context file used by the context_skill condition")
    p.add_argument("--require-all-checks", action="store_true", help="count a skipped check as a failure (use for published runs)")
    p.add_argument("--out", default="results/agent-check.csv")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    ep = args.ep.zfill(2)
    task_file = pathlib.Path(args.tasks) if args.tasks else TASK_DIR / f"ep{ep}.yaml"
    tasks = load_tasks(task_file)
    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    unknown = set(conditions) - set(CONDITIONS)
    if unknown:
        raise SystemExit(f"unknown condition(s): {', '.join(sorted(unknown))}")
    model = make_model(fake=args.fake_model, name=args.model, temperature=args.temperature, fixtures=FIXTURE_DIR, skill_path=args.skill)
    # The fake model is an offline pipeline test: no server-side dry-run against a real
    # cluster unless --context is given on the command line.
    explicit_context = any(a == "--context" or a.startswith("--context=") for a in (argv or sys.argv[1:]))
    kube_context = args.context if (explicit_context or not args.fake_model) else ""
    ctx = CheckContext(kube_context=kube_context, require_all=args.require_all_checks)
    try:
        rows = run_tasks(ep, tasks, conditions, args.runs, model, ctx, args.max_turns, args.out)
    finally:
        model.close()
    passed = sum(1 for r in rows if r["passed"] == "true")
    print(f"agent check ep{ep}: {passed}/{len(rows)} runs passed; wrote {args.out}")
    return 0
