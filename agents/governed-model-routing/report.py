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

"""Cost per resolved task from Harbor job folders, one row per configuration.

    python report.py jobs/ [--basis current|list|YYYY-MM-DD] [--plots plots/] [-o report.md]

A configuration is (harness variant, mode, models). cost per resolved task = total cost of
all counted attempts / number resolved. Failed attempts count (you pay for them). Infra
errors and trials skipped by the spend ceiling are listed separately and left out.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from statistics import median

from providers import Usage
from router import label_turn
from telemetry import call_cost, load_pricing, rates, switch_tax, trial_variant

MODE_ORDER = ("routed", "frontier_only", "workhorse_only")
TRIGGERS = {
    "planning": "Plan-only call before the loop (turn 0)",
    "gate_failures": "3 consecutive lint/test gate failures on one file",
    "signature_mutation": "Existing public signature removed or changed",
    "schema_failure": "No tool call, unknown tool or invalid arguments",
    "stalled": "N turns in a row without a change to a tracked file",
}


def turn_labels(records: list[dict]) -> Counter:
    """Recompute turn labels from the stored tool calls (so label heuristics can improve later)."""
    counts: Counter = Counter()
    for rec in records:
        if rec["turn"] == 0:
            continue
        labels = [label_turn(c["name"], c["args"]) for c in rec.get("calls", [])]
        counts[next((x for x in ("edit", "test", "explore") if x in labels), "other")] += 1
    return counts


def load_trials(jobs_dir: Path, pricing: dict, basis: str, labels: list[str], exclude: list[str]) -> list[dict]:
    trials = []
    for result_path in sorted(jobs_dir.glob("*/*/result.json")):
        r = json.loads(result_path.read_text(encoding="utf-8"))
        kw = (r.get("config", {}).get("agent", {}) or {}).get("kwargs") or {}
        if "trial_name" not in r or not kw.get("workhorse"):
            continue
        label = str(kw.get("label", ""))
        if (labels and label not in labels) or label in exclude:
            continue
        agent_dir = result_path.parent / "agent"
        summary = json.loads((agent_dir / "summary.json").read_text()) if (agent_dir / "summary.json").exists() else {}
        traj = agent_dir / "trajectory.jsonl"
        records = [json.loads(line) for line in traj.read_text().splitlines() if line.strip()] if traj.exists() else []
        cost = sum(call_cost(rates(pricing, rec["model_id"], basis), Usage(**rec["usage"])) for rec in records)
        tax = sum(switch_tax(rates(pricing, rec["model_id"], basis), Usage(**rec["usage"]))
                  for rec in records if rec.get("model_switch"))
        exc = (r.get("exception_info") or {}).get("exception_type")
        reward = ((r.get("verifier_result") or {}).get("rewards") or {}).get("reward")
        if summary.get("stop_reason") == "spend_ceiling":
            outcome = "skipped"
        elif exc and exc != "AgentTimeoutError":  # an agent timeout is still graded by the verifier
            outcome = "infra_error"
        else:
            outcome = "resolved" if reward is not None and float(reward) >= 1.0 else "unresolved"
        trials.append({"task": r["task_name"].split("/")[-1], "trial": r["trial_name"],
                       "mode": kw.get("mode", "routed"), "workhorse": kw["workhorse"], "frontier": kw["frontier"],
                       "variant": trial_variant(summary, kw), "label": label, "outcome": outcome,
                       "exception": exc, "cost": cost, "switch_tax": tax, "summary": summary, "records": records})
    return trials


def config_of(t: dict) -> tuple[str, str, str, str]:
    """(variant, mode, workhorse, frontier). A baseline run depends on one model only."""
    return (t["variant"], t["mode"], "-" if t["mode"] == "frontier_only" else t["workhorse"],
            "-" if t["mode"] == "workhorse_only" else t["frontier"])


def configs(trials: list[dict]) -> list[tuple[str, str, str, str]]:
    return sorted({config_of(t) for t in trials}, key=lambda c: (c[0], c[2], c[3], MODE_ORDER.index(c[1])))


def rows_for(trials: list[dict], config: tuple) -> list[dict]:
    return [t for t in trials if config_of(t) == config]


def aggregate(trials: list[dict]) -> dict:
    counted = [t for t in trials if t["outcome"] in ("resolved", "unresolved")]
    resolved = sum(t["outcome"] == "resolved" for t in counted)
    total = sum(t["cost"] for t in counted)
    calls = sum(t["summary"].get("calls", 0) for t in counted)
    frontier_calls = sum(t["summary"].get("tiers", {}).get("frontier", {}).get("calls", 0) for t in counted)
    tier0 = [t["summary"].get("tier0", {}) for t in counted]
    first_edits = [x["first_tracked_edit_turn"] for x in tier0 if x.get("first_tracked_edit_turn")]
    return {"attempts": len(counted), "resolved": resolved,
            "rate": resolved / len(counted) if counted else None, "cost": total,
            "cost_per_attempt": total / len(counted) if counted else None,
            "cost_per_resolved": total / resolved if resolved else None,
            "median_turns": median(t["summary"].get("turns", 0) for t in counted) if counted else None,
            "frontier_share": frontier_calls / calls if calls else None,
            "switches": sum(t["summary"].get("model_switches", 0) for t in counted),
            "switch_tax": sum(t["switch_tax"] for t in counted),
            "auto_verify": sum(x.get("auto_verify_runs", 0) for x in tier0),
            "nudges": sum(x.get("nudges", 0) for x in tier0),
            "first_edit": median(first_edits) if first_edits else None,
            "infra_errors": sum(t["outcome"] == "infra_error" for t in trials)}


def money(x: float | None) -> str:
    return "n/a" if x is None else f"${x:,.3f}"


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def num(x: float | None) -> str:
    return "n/a" if x is None else f"{x:g}"


def render(trials: list[dict], pricing: dict, basis: str) -> str:
    out = [f"# Governed routing report ({len(trials)} trials, prices: {basis}, pricing as of {pricing.get('as_of')})", "",
           "Cost per resolved task = total cost of counted attempts / resolved attempts. "
           "Compare rows that share a harness variant and models.", "",
           "| Harness | Mode | Workhorse | Frontier | Attempts | Resolved | Success | Total cost | Cost/attempt "
           "| **Cost/resolved** | Median turns | Frontier share | Model switches | Switch tax | Infra errors |",
           "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for c in configs(trials):
        a = aggregate(rows_for(trials, c))
        head = " | ".join(c)
        out.append(f"| {head} | {a['attempts']} | {a['resolved']} | {pct(a['rate'])} | {money(a['cost'])} "
                   f"| {money(a['cost_per_attempt'])} | **{money(a['cost_per_resolved'])}** | {num(a['median_turns'])} "
                   f"| {pct(a['frontier_share'])} | {a['switches']} | {money(a['switch_tax'])} | {a['infra_errors']} |"
                   if a["attempts"] else f"| {head} | 0 | | | | | | | | | | {a['infra_errors']} |")
    out += ["", "## Per task", "", "| Task | Harness | Mode | Workhorse | Frontier | Resolved | Cost | Median turns |",
            "|---|---|---|---|---|---:|---:|---:|"]
    for task in sorted({t["task"] for t in trials}):
        for c in configs([t for t in trials if t["task"] == task]):
            a = aggregate(rows_for([t for t in trials if t["task"] == task], c))
            out.append(f"| {task} | {' | '.join(c)} | {a['resolved']}/{a['attempts']} | {money(a['cost'])} "
                       f"| {num(a['median_turns'])} |")
    out += ["", "## Tier 0 activity", "",
            "| Harness | Mode | Workhorse | Frontier | Auto-verify runs | Nudges | Median turn of first tracked edit |",
            "|---|---|---|---|---:|---:|---:|"]
    for c in configs(trials):
        a = aggregate(rows_for(trials, c))
        out.append(f"| {' | '.join(c)} | {a['auto_verify']} | {a['nudges']} | {num(a['first_edit'])} |")
    labels = Counter()
    for t in trials:
        if t["mode"] == "frontier_only" and t["outcome"] in ("resolved", "unresolved"):
            labels.update(turn_labels(t["records"]))
    total = sum(labels.values())
    out += ["", "## What frontier-only turns were spent on", "",
            "| Label | Turns | Share |", "|---|---:|---:|"]
    out += [f"| {k} | {labels[k]} | {pct(labels[k] / total if total else None)} |" for k in ("explore", "edit", "test", "other")]
    fired, suppressed, sticky, safeguards = Counter(), Counter(), 0, Counter()
    for t in trials:
        trig = t["summary"].get("triggers", {})
        if t["mode"] == "routed":
            fired.update(trig.get("fired", {}))
            sticky += trig.get("sticky_turns", 0)
            safeguards.update(trig.get("safeguards", {}))
        suppressed.update(trig.get("suppressed", {}))
    out += ["", "## Triggers in routed runs", "", "| Trigger | Signal | Fired | Suppressed (incl. forced modes) |",
            "|---|---|---:|---:|"]
    out += [f"| {k} | {v} | {fired[k]} | {suppressed[k]} |" for k, v in TRIGGERS.items()]
    out += ["", f"Sticky-lock turns: {sticky}. Safeguard decisions: {dict(safeguards) or 'none'}."]
    other = [t for t in trials if t["outcome"] in ("infra_error", "skipped")]
    if other:
        out += ["", "## Left out of the comparison", "", "| Trial | Outcome | Exception | Cost |", "|---|---|---|---:|"]
        out += [f"| {t['trial']} | {t['outcome']} | {t['exception'] or ''} | {money(t['cost'])} |" for t in other]
    out += ["", f"Total spend across all trials ({basis} prices): {money(sum(t['cost'] for t in trials))}"]
    return "\n".join(out) + "\n"


def plot(trials: list[dict], out_dir: Path, strip_trial: str | None = None) -> None:
    import matplotlib
    import matplotlib.ticker
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_dir.mkdir(parents=True, exist_ok=True)
    colors = {"routed": "#1a73e8", "frontier_only": "#d93025", "workhorse_only": "#188038"}
    cs = [c for c in configs(trials) if aggregate(rows_for(trials, c))["attempts"]]
    if cs:
        values = [aggregate(rows_for(trials, c))["cost_per_resolved"] or 0 for c in cs]
        fig, ax = plt.subplots(figsize=(max(8, 1.6 * len(cs)), 4.8))
        bars = ax.bar(range(len(cs)), values, color=[colors[c[1]] for c in cs])
        ax.bar_label(bars, labels=[f"${v:.2f}" if v else "n/a" for v in values], fontsize=8)
        ax.set_xticks(range(len(cs)), [f"{m}\n{wh} → {fr}\n{v}".replace("- → ", "").replace(" → -", "")
                                       for v, m, wh, fr in cs], fontsize=7)
        ax.set_ylabel("Cost per resolved task (USD)")
        ax.set_title("Cost per resolved task by configuration")
        fig.tight_layout()
        fig.savefig(out_dir / "cost_per_resolved.png", dpi=200)
        plt.close(fig)
    routed = [t for t in trials if t["mode"] == "routed" and t["records"]]
    chosen = next((t for t in routed if t["trial"] == strip_trial), None)
    if chosen is None and routed:
        resolved = [t for t in routed if t["outcome"] == "resolved"] or routed
        mid = median(t["summary"].get("tiers", {}).get("frontier", {}).get("calls", 0) for t in resolved)
        chosen = min(resolved, key=lambda t: abs(t["summary"].get("tiers", {}).get("frontier", {}).get("calls", 0) - mid))
    if chosen:
        recs = chosen["records"]
        short = {"planning": "plan", "stalled": "stall", "gate_failures": "gates", "sticky_lock": "lock",
                 "signature_mutation": "API", "schema_failure": "schema"}
        fig, ax = plt.subplots(figsize=(12, 3.2))
        for r in recs:
            color = "#d93025" if r["tier"] == "frontier" else "#188038"
            ax.add_patch(plt.Rectangle((r["turn"], 0), 0.9, 1, color=color, hatch="//" if r["turn"] == 0 else None, alpha=0.9))
            if r["tier"] == "frontier" and r["reason"] in short:  # the audit trail: why this turn went up
                ax.text(r["turn"] + 0.45, 1.04, short[r["reason"]], rotation=90, fontsize=7, ha="center", va="bottom")
            harness = r.get("harness") or {}
            if harness.get("progress"):
                ax.plot(r["turn"] + 0.45, -0.08, marker="^", color="black", markersize=5, clip_on=False)
            if harness.get("nudge"):
                ax.plot(r["turn"] + 0.45, -0.08, marker="o", color="#f9ab00", markersize=4, clip_on=False)
        ax2 = ax.twinx()
        ax2.plot([r["turn"] + 0.45 for r in recs], [r["cum_cost_current"] for r in recs], color="black", linewidth=1.5)
        ax2.set_ylabel("Cumulative cost (USD)")
        ax.set_xlim(0, len(recs))
        ax.set_ylim(-0.15, 1.45)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.set_yticks([])
        ax.set_xlabel("Turn (0 = plan call)   red = frontier (label = trigger), green = workhorse, "
                      "▲ = tracked file changed, ● = harness nudge")
        task = re.sub(r"^instance_[^_]+__([^-]+)-([0-9a-f]{8}).*$", r"\1 (SWE-bench Pro, \2)", chosen["task"])
        ax.set_title(f"{task} | {chosen['workhorse']} → {chosen['frontier']} | {chosen['variant']} "
                     f"| {chosen['outcome']}")
        fig.tight_layout()
        fig.savefig(out_dir / "trajectory_strip.png", dpi=200)
        plt.close(fig)
    fired, suppressed = Counter(), Counter()
    for t in trials:
        trig = t["summary"].get("triggers", {})
        if t["mode"] == "routed":
            fired.update(trig.get("fired", {}))
        suppressed.update(trig.get("suppressed", {}))
    fig, ax = plt.subplots(figsize=(10, 2.9))
    ax.axis("off")
    table = ax.table(cellText=[[k, v, str(fired[k]), str(suppressed[k])] for k, v in TRIGGERS.items()],
                     colLabels=["Trigger", "Deterministic signal", "Fired (routed)", "Suppressed"],
                     loc="center", cellLoc="left", colWidths=[0.18, 0.52, 0.14, 0.14])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.6)
    fig.tight_layout()
    fig.savefig(out_dir / "triggers.png", dpi=200)
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("jobs_dir", type=Path)
    p.add_argument("--basis", default="current", help="current (today's prices), list, or YYYY-MM-DD")
    p.add_argument("--label", action="append", default=[], help="Only include these labels (repeatable)")
    p.add_argument("--exclude-label", action="append", default=None,
                   help="Labels to leave out (default: safeguards-demo)")
    p.add_argument("--plots", type=Path, help="Write PNG charts to this directory")
    p.add_argument("--strip-trial", help="Trial name for the trajectory strip chart")
    p.add_argument("-o", "--output", type=Path, help="Write the Markdown report to this file")
    args = p.parse_args(argv)
    pricing = load_pricing()
    exclude = args.exclude_label if args.exclude_label is not None else ["safeguards-demo"]
    trials = load_trials(args.jobs_dir, pricing, args.basis, args.label, exclude)
    text = render(trials, pricing, args.basis)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
    if args.plots:
        plot(trials, args.plots, args.strip_trial)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
