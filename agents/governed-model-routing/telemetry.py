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

"""Pricing, cost accounting and per-trial telemetry (trajectory, tokens, cost).

Raw token usage is always recorded, so any trial can be re-priced later
(`report.py --basis list|current|YYYY-MM-DD`).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import asdict
from datetime import date
from pathlib import Path

import yaml

from providers import ModelSpec, Step, Usage, parse_spec
from router import FRONTIER, WORKHORSE, Decision, Signals, label_turn

PRICING_PATH = Path(__file__).with_name("pricing.yaml")
_TRIGGERS = ("planning", "gate_failures", "signature_mutation", "schema_failure")


def load_pricing(path: str | Path | None = None) -> dict:
    with open(path or PRICING_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rates(pricing: dict, model_id: str, basis: str = "current") -> dict:
    """Price block for a model. basis: 'current' (today), 'list', or an ISO date."""
    entry = pricing["models"][model_id]
    if basis == "list" or "current" not in entry:
        return entry["list"]
    on = date.today() if basis == "current" else date.fromisoformat(basis)
    current = entry["current"]
    return current if on <= date.fromisoformat(str(current["until"])) else entry["list"]


def check_spec(spec: str, pricing: dict) -> ModelSpec:
    """Validate MODEL_ID[:LEVEL] against pricing.yaml. Raises ValueError with the options."""
    s = parse_spec(spec)
    models = pricing["models"]
    if s.model_id not in models:
        raise ValueError(f"Unknown model '{s.model_id}'. Supported: {', '.join(sorted(models))}")
    levels = models[s.model_id].get("levels") or []
    if s.level and s.level not in levels:
        allowed = ", ".join(levels) if levels else "none (omit the level to use the model default)"
        raise ValueError(f"Level '{s.level}' is not supported for {s.model_id}. Allowed: {allowed}")
    return s


def call_cost(rate: dict, u: Usage) -> float:
    """USD for one call. Long-context rates apply to every token once the prompt crosses the threshold."""
    long = u.prompt_tokens >= rate.get("long_context_threshold", float("inf"))

    def r(key: str) -> float:
        base = rate.get(key, rate["input"] if key == "cache_write" else 0.0)
        return rate.get(f"{key}_long", base) if long else base

    return (u.input_uncached * r("input") + u.cache_read * r("cache_read")
            + u.cache_write * r("cache_write") + u.output * r("output")) / 1e6


def switch_tax(rate: dict, u: Usage) -> float:
    """Upper-bound extra cost of reading the history cold after a model switch."""
    write = rate.get("cache_write", rate["input"])
    return (u.input_uncached * (rate["input"] - rate["cache_read"])
            + u.cache_write * (write - rate["cache_read"])) / 1e6


def ledger_total(path: str | Path, key: str = "cost_list") -> float:
    p = Path(path)
    if not p.exists():
        return 0.0
    with p.open(encoding="utf-8") as f:
        return sum(json.loads(line).get(key, 0.0) for line in f if line.strip())


def _sum_usage(records: list[dict]) -> dict:
    keys = ("input_uncached", "cache_read", "cache_write", "output", "thinking")
    return {k: sum(r["usage"][k] for r in records) for k in keys}


def _turn_label(labels: list[str]) -> str:
    for label in ("plan", "edit", "test", "explore"):
        if label in labels:
            return label
    return "other"


class Telemetry:
    """Writes trajectory.jsonl as the trial runs; summary.json and timeline.md at the end."""

    def __init__(self, logs_dir: str | Path, pricing: dict, meta: dict, ledger_path: str | Path):
        self.dir = Path(logs_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pricing, self.meta, self.ledger_path = pricing, meta, Path(ledger_path)
        self.records: list[dict] = []
        self.cost_current = 0.0
        self.cost_list = 0.0
        self._last_model: str | None = None
        self._last_tier: str | None = None
        self._loop_keys: list[str] = []
        self._finished = False

    def record(self, turn: int, decision: Decision, spec: ModelSpec, step: Step,
               results: list[tuple], signals: Signals) -> dict:
        u = step.usage
        rate_now, rate_list = rates(self.pricing, spec.model_id), rates(self.pricing, spec.model_id, "list")
        cost_c, cost_l = call_cost(rate_now, u), call_cost(rate_list, u)
        model_switch = self._last_model is not None and spec.model_id != self._last_model
        self.cost_current += cost_c
        self.cost_list += cost_l
        labels = ["plan"] if turn == 0 else [label_turn(c.name, c.args) for c in step.calls]
        rec = {
            "turn": turn, "tier": decision.tier, "model": str(spec), "model_id": spec.model_id,
            "provider": spec.provider, "reason": decision.reason, "detail": decision.detail,
            "suppressed": decision.suppressed,
            "calls": [{"name": c.name, "args": c.args} for c in step.calls],
            "labels": labels, "turn_label": _turn_label(labels),
            "results": [{"name": c.name, "exit_code": code, "chars": len(out), "preview": out[:400]}
                        for c, out, code in results],
            "gate": {"file": signals.gate_file, "passed": signals.gate_passed,
                     "removed_signatures": signals.removed_signatures, "schema_error": signals.schema_error},
            "usage": asdict(u),
            "model_switch": model_switch,
            "tier_switch": self._last_tier is not None and decision.tier != self._last_tier,
            "cache_hit_ratio": round(u.cache_read / u.prompt_tokens, 3) if u.prompt_tokens else None,
            "cost_current": round(cost_c, 6), "cost_list": round(cost_l, 6),
            "switch_tax_current": round(switch_tax(rate_now, u), 6) if model_switch else 0.0,
            "switch_tax_list": round(switch_tax(rate_list, u), 6) if model_switch else 0.0,
            "cum_cost_current": round(self.cost_current, 6), "cum_cost_list": round(self.cost_list, 6),
            "latency_s": step.latency_s, "finish_reason": step.finish_reason, "text": step.text[:4000],
        }
        self._last_model, self._last_tier = spec.model_id, decision.tier
        self.records.append(rec)
        with (self.dir / "trajectory.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        if turn > 0:
            outputs = "".join(out for _, out, _ in results)
            self._loop_keys.append(hashlib.sha256(
                (json.dumps(rec["calls"], sort_keys=True, default=str) + outputs).encode()).hexdigest())
        return rec

    def loop_detected(self, repeats: int = 5) -> bool:
        """Circuit breaker: the same tool call with the same output `repeats` times in a row.

        Set above the gate-failure threshold (3) so a stuck workhorse escalates to the frontier
        first; the hard stop is reserved for loops the frontier does not break either.
        """
        tail = self._loop_keys[-repeats:]
        return len(tail) == repeats and len(set(tail)) == 1

    def summary(self, stop_reason: str, error: str | None = None) -> dict:
        recs = self.records
        loop = [r for r in recs if r["turn"] > 0]
        tiers = {}
        for tier in (WORKHORSE, FRONTIER):
            rs = [r for r in recs if r["tier"] == tier]
            tiers[tier] = {"calls": len(rs), "tokens": _sum_usage(rs),
                           "cost_current": round(sum(r["cost_current"] for r in rs), 6),
                           "cost_list": round(sum(r["cost_list"] for r in rs), 6)}
        switches = [r for r in recs if r["model_switch"]]
        steady = [r for r in recs if not r["model_switch"] and r["cache_hit_ratio"] is not None and r["turn"] > 1]
        mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None  # noqa: E731
        return {
            **self.meta,
            "stop_reason": stop_reason, "error": error,
            "turns": len(loop), "calls": len(recs),
            "tiers": tiers, "total_tokens": _sum_usage(recs),
            "cost_current": round(self.cost_current, 6), "cost_list": round(self.cost_list, 6),
            "triggers": {
                "fired": dict(Counter(r["reason"] for r in recs if r["reason"] in _TRIGGERS)),
                "sticky_turns": sum(r["reason"] == "sticky_lock" for r in recs),
                "suppressed": dict(Counter(r["suppressed"] for r in recs if r["suppressed"])),
                "safeguards": dict(Counter(r["reason"] for r in recs if r["reason"] in ("budget_downshift", "cap_reached"))),
            },
            "model_switches": len(switches),
            "tier_switches": sum(r["tier_switch"] for r in recs),
            "switch_tax_current": round(sum(r["switch_tax_current"] for r in recs), 6),
            "switch_tax_list": round(sum(r["switch_tax_list"] for r in recs), 6),
            "cache_hit_ratio": {"switch_calls": mean([r["cache_hit_ratio"] for r in switches if r["cache_hit_ratio"] is not None]),
                                "other_calls": mean([r["cache_hit_ratio"] for r in steady])},
            "turn_labels": dict(Counter(r["turn_label"] for r in loop)),
            "pricing": {"as_of": self.pricing.get("as_of"), "source": self.pricing.get("source")},
        }

    def finish(self, context, stop_reason: str, error: str | None = None) -> dict:
        """Write summary.json, timeline.md and the ledger entry; populate Harbor's AgentContext."""
        if self._finished:
            return {}
        self._finished = True
        summary = self.summary(stop_reason, error)
        (self.dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        (self.dir / "timeline.md").write_text(self.timeline(summary), encoding="utf-8")
        entry = {"trial": self.meta.get("trial"), "task": self.meta.get("task"), "mode": self.meta.get("mode"),
                 "label": self.meta.get("label"), "workhorse": self.meta.get("workhorse"),
                 "frontier": self.meta.get("frontier"), "stop_reason": stop_reason,
                 "cost_current": round(self.cost_current, 6), "cost_list": round(self.cost_list, 6)}
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        if context is not None:
            self._fill_context(context, summary)
        return summary

    def _fill_context(self, context, summary: dict) -> None:
        from harbor.models.agent.context import ModelUsage  # Harbor is only needed at runtime

        totals = summary["total_tokens"]
        context.n_input_tokens = totals["input_uncached"] + totals["cache_read"] + totals["cache_write"]
        context.n_cache_tokens = totals["cache_read"]
        context.n_output_tokens = totals["output"]
        context.cost_usd = round(self.cost_current, 6)
        per_model: dict[str, ModelUsage] = {}
        for r in self.records:
            m = per_model.setdefault(r["model"], ModelUsage(cost_usd=0.0))
            u = r["usage"]
            m.n_input_tokens += u["input_uncached"] + u["cache_read"] + u["cache_write"]
            m.n_cache_tokens += u["cache_read"]
            m.n_output_tokens += u["output"]
            m.cost_usd = round((m.cost_usd or 0.0) + r["cost_current"], 6)
        context.model_usage = per_model
        context.metadata = {"routing": {k: summary[k] for k in (
            "mode", "workhorse", "frontier", "label", "stop_reason", "turns", "triggers",
            "model_switches", "cost_current", "cost_list")}}

    def timeline(self, summary: dict) -> str:
        strip = " ".join("P" if r["turn"] == 0 else ("F" if r["tier"] == FRONTIER else "W") for r in self.records)
        lines = [
            f"# {summary.get('task')} | mode={summary.get('mode')} | workhorse={summary.get('workhorse')}"
            f" | frontier={summary.get('frontier')}",
            "",
            f"Strip: `{strip}`  (P = plan call, F = frontier turn, W = workhorse turn)",
            "",
            f"Stop reason: {summary['stop_reason']} | turns: {summary['turns']} | "
            f"cost: ${summary['cost_current']:.4f} current (${summary['cost_list']:.4f} list) | "
            f"model switches: {summary['model_switches']}",
            "",
            "| Turn | Tier | Model | Reason | Action | Label | Input (cached) | Output (thinking) | Cost |",
            "|---:|---|---|---|---|---|---:|---:|---:|",
        ]
        for r in self.records:
            u = r["usage"]
            prompt = u["input_uncached"] + u["cache_read"] + u["cache_write"]
            if r["calls"]:
                c = r["calls"][0]
                arg = c["args"].get("command") or c["args"].get("path") or c["args"].get("summary") or ""
                action = f"{c['name']}: {str(arg)[:60]}" + (f" (+{len(r['calls']) - 1})" if len(r["calls"]) > 1 else "")
            else:
                action = "plan" if r["turn"] == 0 else "(no tool call)"
            reason = r["reason"] + (f" [suppressed {r['suppressed']}]" if r["suppressed"] else "")
            cells = [str(r["turn"]), r["tier"], r["model"], reason, action, r["turn_label"],
                     f"{prompt:,} ({u['cache_read']:,})", f"{u['output']:,} ({u['thinking']:,})",
                     f"${r['cost_current']:.4f}"]
            lines.append("| " + " | ".join(cell.replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
        return "\n".join(lines) + "\n"
