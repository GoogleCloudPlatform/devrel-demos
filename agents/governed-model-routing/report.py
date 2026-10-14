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

"""Cost per resolved task from Harbor job folders, compared within each pairing.

    python report.py jobs/ [--basis current|list|YYYY-MM-DD] [--plots plots/] [-o report.md]

cost per resolved task = total cost of all counted attempts / number resolved.
Failed attempts count (you pay for them). Infra errors and trials skipped by the
spend ceiling are listed separately and left out of the comparison.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median

from providers import Usage
from router import label_turn
from telemetry import call_cost, load_pricing, rates, switch_tax

MODE_ORDER = ("routed", "frontier_only", "workhorse_only")


def turn_labels(records: list[dict]) -> Counter:
    """Recompute turn labels from the stored tool calls (so label heuristics can improve later)."""
    counts: Counter = Counter()
    for rec in records:
        if rec["turn"] == 0:
            continue
        labels = [label_turn(c["name"], c["args"]) for c in rec.get("calls", [])]
        counts[next((x for x in ("edit", "test", "explore") if x in labels), "other")] += 1
    return counts
TRIGGERS = {
    "planning": "Plan-only call before the loop (turn 0)",
    "gate_failures": "3 consecutive lint/test gate failures on one file",
    "signature_mutation": "Existing public signature removed or changed",
    "schema_failure": "No tool call, unknown tool or invalid arguments",
}


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
                       "label": label, "outcome": outcome, "exception": exc, "cost": cost, "switch_tax": tax,
                       "summary": summary, "records": records})
    return trials


def pairing_rows(trials: list[dict], workhorse: str, frontier: str) -> dict[str, list[dict]]:
    """Routed runs for the pairing, plus the baselines that share its models."""
    return {"routed": [t for t in trials if t["mode"] == "routed" and (t["workhorse"], t["frontier"]) == (workhorse, frontier)],
            "frontier_only": [t for t in trials if t["mode"] == "frontier_only" and t["frontier"] == frontier],
            "workhorse_only": [t for t in trials if t["mode"] == "workhorse_only" and t["workhorse"] == workhorse]}


def aggregate(trials: list[dict]) -> dict:
    counted = [t for t in trials if t["outcome"] in ("resolved", "unresolved")]
    resolved = sum(t["outcome"] == "resolved" for t in counted)
    total = sum(t["cost"] for t in counted)
    calls = sum(t["summary"].get("calls", 0) for t in counted)
    frontier_calls = sum(t["summary"].get("tiers", {}).get("frontier", {}).get("calls", 0) for t in counted)
    return {"attempts": len(counted), "resolved": resolved,
            "rate": resolved / len(counted) if counted else None, "cost": total,
            "cost_per_attempt": total / len(counted) if counted else None,
            "cost_per_resolved": total / resolved if resolved else None,
            "avg_turns": sum(t["summary"].get("turns", 0) for t in counted) / len(counted) if counted else None,
            "frontier_share": frontier_calls / calls if calls else None,
            "switches": sum(t["summary"].get("model_switches", 0) for t in counted),
            "switch_tax": sum(t["switch_tax"] for t in counted),
            "infra_errors": sum(t["outcome"] == "infra_error" for t in trials)}


def money(x: float | None) -> str:
    return "n/a" if x is None else f"${x:,.3f}"


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.0%}"


def render(trials: list[dict], pricing: dict, basis: str) -> str:
    pairings = sorted({(t["workhorse"], t["frontier"]) for t in trials if t["mode"] == "routed"})
    out = [f"# Governed routing report ({len(trials)} trials, prices: {basis}, pricing as of {pricing.get('as_of')})", "",
           "Cost per resolved task = total cost of counted attempts / resolved attempts. Compare rows within a pairing.", "",
           "| Pairing | Mode | Attempts | Resolved | Success | Total cost | Cost/attempt | **Cost/resolved** "
           "| Avg turns | Frontier share | Model switches | Switch tax | Infra errors |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for wh, fr in pairings:
        for mode, rows in pairing_rows(trials, wh, fr).items():
            a = aggregate(rows)
            out.append(f"| {wh} → {fr} | {mode} | {a['attempts']} | {a['resolved']} | {pct(a['rate'])} | {money(a['cost'])} "
                       f"| {money(a['cost_per_attempt'])} | **{money(a['cost_per_resolved'])}** "
                       f"| {a['avg_turns']:.1f} | {pct(a['frontier_share'])} | {a['switches']} | {money(a['switch_tax'])} "
                       f"| {a['infra_errors']} |" if a["attempts"] else
                       f"| {wh} → {fr} | {mode} | 0 | | | | | | | | | | {a['infra_errors']} |")
    out += ["", "## Per task (resolved/attempts, cost)", "",
            "| Task | Pairing | " + " | ".join(MODE_ORDER) + " |", "|---|---|" + "---|" * len(MODE_ORDER)]
    for task in sorted({t["task"] for t in trials}):
        for wh, fr in pairings:
            cells = []
            for rows in pairing_rows([t for t in trials if t["task"] == task], wh, fr).values():
                a = aggregate(rows)
                cells.append(f"{a['resolved']}/{a['attempts']} ({money(a['cost'])})" if a["attempts"] else "-")
            out.append(f"| {task} | {wh} → {fr} | " + " | ".join(cells) + " |")
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
    pairings = sorted({(t["workhorse"], t["frontier"]) for t in trials if t["mode"] == "routed"})
    colors = {"routed": "#1a73e8", "frontier_only": "#d93025", "workhorse_only": "#188038"}
    if pairings:
        fig, ax = plt.subplots(figsize=(10, 4.5))
        width = 0.26
        for i, mode in enumerate(MODE_ORDER):
            values = [aggregate(pairing_rows(trials, wh, fr)[mode])["cost_per_resolved"] or 0 for wh, fr in pairings]
            bars = ax.bar([x + (i - 1) * width for x in range(len(pairings))], values, width, label=mode, color=colors[mode])
            ax.bar_label(bars, labels=[f"${v:.2f}" if v else "n/a" for v in values], fontsize=8)
        ax.set_xticks(range(len(pairings)), [f"{wh}\n→ {fr}" for wh, fr in pairings], fontsize=8)
        ax.set_ylabel("Cost per resolved task (USD)")
        ax.set_title("Cost per resolved task, within each pairing")
        ax.legend()
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
        fig, ax = plt.subplots(figsize=(12, 2.8))
        for r in recs:
            color = "#d93025" if r["tier"] == "frontier" else "#188038"
            ax.add_patch(plt.Rectangle((r["turn"], 0), 0.9, 1, color=color, hatch="//" if r["turn"] == 0 else None, alpha=0.9))
        ax2 = ax.twinx()
        ax2.plot([r["turn"] + 0.45 for r in recs], [r["cum_cost_current"] for r in recs], color="black", linewidth=1.5)
        ax2.set_ylabel("Cumulative cost (USD)")
        ax.set_xlim(0, len(recs))
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
        ax.set_yticks([])
        ax.set_xlabel("Turn (0 = plan call)   red = frontier, green = workhorse")
        ax.set_title(f"{chosen['task']} | {chosen['workhorse']} → {chosen['frontier']} | {chosen['outcome']}")
        fig.tight_layout()
        fig.savefig(out_dir / "trajectory_strip.png", dpi=200)
        plt.close(fig)
    fired, suppressed = Counter(), Counter()
    for t in trials:
        trig = t["summary"].get("triggers", {})
        if t["mode"] == "routed":
            fired.update(trig.get("fired", {}))
        suppressed.update(trig.get("suppressed", {}))
    fig, ax = plt.subplots(figsize=(10, 2.6))
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
