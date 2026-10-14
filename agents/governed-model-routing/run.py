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

"""Run benchmark tasks with governed routing, choosing both models on every run.

    python run.py --task astropy__astropy-14508 \
        --workhorse gemini-3.8-flash:low --frontier gemini-4-argon:high

Runs each mode (routed, frontier_only, workhorse_only) as one Harbor job. Precedence for the
project: --project > shell environment > .env. Trials already completed with the same task,
mode, models and label are skipped, so baselines are shared across pairings and an
interrupted run can be resumed. New trials stop launching once the spend ledger reaches the
ceiling (list prices).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from router import MODES
from telemetry import check_spec, ledger_total, load_pricing

HERE = Path(__file__).resolve().parent
_VENV_HARBOR = Path(sys.executable).with_name("harbor")
HARBOR = str(_VENV_HARBOR) if _VENV_HARBOR.exists() else "harbor"


def load_env_file(path: Path, environ: dict) -> None:
    """Load KEY=VALUE lines without overriding variables that are already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip().removeprefix("export ").strip(), value.strip().strip("'\"")
        if key and key not in environ:
            environ[key] = value


def task_ref(dataset: str, task: str) -> str:
    """'astropy__astropy-14508' -> 'swe-bench/astropy__astropy-14508' for dataset 'swe-bench/...'."""
    return task if "/" in task else f"{dataset.split('/')[0]}/{task}"


def completed_trials(jobs_dir: Path) -> Counter:
    """Count finished trials by (task, mode, workhorse, frontier, label). Infra failures don't count."""
    counts: Counter = Counter()
    for result in jobs_dir.glob("*/*/result.json"):
        try:
            r = json.loads(result.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "trial_name" not in r:
            continue
        exc = (r.get("exception_info") or {}).get("exception_type")
        if exc and exc != "AgentTimeoutError":
            continue
        summary = result.parent / "agent" / "summary.json"
        if summary.exists() and json.loads(summary.read_text(encoding="utf-8")).get("stop_reason") == "spend_ceiling":
            continue
        kw = r.get("config", {}).get("agent", {}).get("kwargs", {}) or {}
        counts[run_key(r["task_name"], kw.get("mode", "routed"), kw.get("workhorse", ""),
                       kw.get("frontier", ""), kw.get("label", ""))] += 1
    return counts


def run_key(task: str, mode: str, workhorse: str, frontier: str, label: str) -> tuple:
    """Baselines depend on one model only, so they are shared across pairings."""
    if mode == "frontier_only":
        workhorse = "*"
    elif mode == "workhorse_only":
        frontier = "*"
    return (task, mode, workhorse, frontier, label)


def harbor_command(args, mode: str, tasks: list[str], ledger: Path, job_name: str, attempts: int) -> list[str]:
    cmd = [HARBOR, "run", "-d", args.dataset, "-n", str(args.concurrency), "-k", str(attempts),
           "-o", str(args.jobs_dir), "--job-name", job_name, "-a", "routing_agent:GovernedRoutingAgent",
           "--agent-timeout-multiplier", str(args.agent_timeout_multiplier),
           "--max-retries", "1", "--retry-exclude", "AgentTimeoutError", "--yes", "-q"]
    for t in tasks:
        cmd += ["-i", t]
    kwargs = {"workhorse": args.workhorse, "frontier": args.frontier, "mode": mode, "label": args.label,
              "ledger_path": str(ledger), "ceiling_usd": args.ceiling_usd}
    for key, value in kwargs.items():
        cmd += ["--ak", f"{key}={value}"]
    for extra in args.ak:
        cmd += ["--ak", extra]
    return cmd


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dataset", default="swe-bench/swe-bench-verified")
    p.add_argument("--task", action="append", required=True, help="Task id; repeat for several tasks")
    p.add_argument("--workhorse", required=True, help="MODEL_ID[:LEVEL], e.g. gemini-3.8-flash:low")
    p.add_argument("--frontier", required=True, help="MODEL_ID[:LEVEL], e.g. claude-opus-5-5:high")
    p.add_argument("--modes", default=",".join(MODES), help="Comma-separated subset of: " + ", ".join(MODES))
    p.add_argument("--attempts", type=int, default=3)
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--project", help="GCP project (overrides shell env and .env)")
    p.add_argument("--jobs-dir", type=Path, default=HERE / "jobs")
    p.add_argument("--ceiling-usd", type=float, default=250.0, help="Spend ceiling at list prices")
    p.add_argument("--label", default="", help="Tag for this batch, e.g. pilot or safeguards-demo")
    p.add_argument("--agent-timeout-multiplier", type=float, default=2.0)
    p.add_argument("--ak", action="append", default=[], help="Extra router option, e.g. budget_usd=0.3")
    p.add_argument("--dry-run", action="store_true", help="Print the Harbor commands without running them")
    args = p.parse_args(argv)

    env = dict(os.environ)
    if args.project:
        env["GOOGLE_CLOUD_PROJECT"] = args.project
    load_env_file(HERE / ".env", env)
    env.setdefault("GOOGLE_CLOUD_LOCATION", "global")
    env.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "true")
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(HERE), env.get("PYTHONPATH", "")]))
    if not env.get("GOOGLE_CLOUD_PROJECT"):
        p.error("no project: pass --project or set GOOGLE_CLOUD_PROJECT in the shell or in .env")

    pricing = load_pricing()
    try:
        workhorse, frontier = check_spec(args.workhorse, pricing), check_spec(args.frontier, pricing)
    except ValueError as e:
        p.error(str(e))
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    if bad := [m for m in modes if m not in MODES]:
        p.error(f"unknown mode(s): {bad}")

    args.jobs_dir = args.jobs_dir.resolve()
    ledger = args.jobs_dir / "ledger.jsonl"
    tasks = [task_ref(args.dataset, t) for t in args.task]
    print(f"project={env['GOOGLE_CLOUD_PROJECT']} location={env['GOOGLE_CLOUD_LOCATION']}")
    print(f"workhorse={workhorse} frontier={frontier} modes={modes} attempts={args.attempts} "
          f"concurrency={args.concurrency} label={args.label or '-'}")
    print(f"tasks={tasks}")

    done = completed_trials(args.jobs_dir)
    for mode in modes:
        spent = ledger_total(ledger, "cost_list")
        print(f"\n[{mode}] ledger so far: ${spent:.2f} (list prices) of ${args.ceiling_usd:.2f} ceiling")
        if spent >= args.ceiling_usd:
            print("Spend ceiling reached; not starting more trials.")
            break
        remaining: dict[int, list[str]] = {}
        for t in tasks:
            left = args.attempts - done[run_key(t, mode, str(workhorse), str(frontier), args.label)]
            if left > 0:
                remaining.setdefault(left, []).append(t)
        if not remaining:
            print("Already complete for these models and label; skipping.")
            continue
        for left, group in sorted(remaining.items(), reverse=True):  # one Harbor job per attempt count
            models = re.sub(r"[^A-Za-z0-9]+", "-", f"{workhorse}__{frontier}")
            job_name = f"{args.label or 'run'}-{mode}-{models}-k{left}-{datetime.now():%Y%m%d-%H%M%S}"
            cmd = harbor_command(args, mode, group, ledger, job_name, attempts=left)
            print("$ PYTHONPATH=. " + shlex.join(cmd))
            if args.dry_run:
                continue
            rc = subprocess.run(cmd, env=env, cwd=HERE, check=False).returncode
            if rc != 0:
                print(f"harbor exited with {rc}", file=sys.stderr)
    print(f"\nLedger total: ${ledger_total(ledger, 'cost_list'):.2f} list / "
          f"${ledger_total(ledger, 'cost_current'):.2f} current. Next: python report.py {args.jobs_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
