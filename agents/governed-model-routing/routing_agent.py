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

"""Harbor agent that routes every turn between a workhorse and a frontier model.

    PYTHONPATH=. harbor run -d swe-bench/swe-bench-verified -i swe-bench/<task> \
        -a routing_agent:GovernedRoutingAgent \
        --ak workhorse=gemini-3.8-flash:low --ak frontier=gemini-4-argon:high

Security note: model-written commands run only inside the task's Docker container that
Harbor creates for the trial (its sandbox). Nothing the model writes is executed on the host,
and no host credentials or environment variables are passed into the container.
TODO(security): container network egress follows each task's `allow_internet` setting
(true for SWE-bench Verified). For untrusted repositories, restrict egress with Harbor's
environment network options; this demo leaves the benchmark defaults unchanged.
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import shlex
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from harbor.agents.base import BaseAgent
from harbor.agents.options import AgentOptions
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from providers import Step, ToolCall, ToolResults, ToolSpec, UserText, make_model
from router import (FRONTIER, WORKHORSE, GovernedRouter, RouterConfig, Signals, is_test_command,
                    removed_signatures, syntax_error)
from telemetry import Telemetry, check_spec, ledger_total, load_pricing

# --- Prompts ------------------------------------------------------------------------------

PLAN_SYSTEM = ("You are a senior software engineer planning a fix. You cannot run tools in this step; "
               "base the plan on the issue and the repository overview.")

SYSTEM_PROMPT = """You are an autonomous software engineer fixing an issue in the repository in the current directory.
Tools:
- bash: run a non-interactive shell command in the repository root (each call starts a fresh shell).
- edit_file: replace one exact, unique occurrence of old_str with new_str in a file.
- finish: call once the fix is implemented and verified.
Rules:
- Work in small steps: inspect the code, reproduce the problem, fix it, verify the fix.
- Change source files only. Do not modify existing tests.
- Prefer edit_file for code changes.
- Lines starting with [gate] come from automatic checks in the harness. Take them into account.
- Every response must include at least one tool call."""

NO_TOOL_CALL_HINT = ("Your last response did not include a tool call. "
                     "Continue by calling one of the tools: bash, edit_file or finish.")


def plan_prompt(instruction: str, repo_map: str) -> str:
    return (f"<issue>\n{instruction}\n</issue>\n\n<repository_overview>\n{repo_map}\n</repository_overview>\n\n"
            "Write a concise plan, at most 12 short lines: likely root causes, the files and functions to "
            "inspect first, how to reproduce the problem, and how to verify the fix. Do not write code.")


def task_message(instruction: str, repo_map: str, plan: str) -> str:
    return (f"<issue>\n{instruction}\n</issue>\n\n<repository_overview>\n{repo_map}\n</repository_overview>\n\n"
            f"<plan>\n{plan.strip() or '(no plan)'}\n</plan>\n\n"
            "Fix the issue. Follow the plan where it holds up and adjust it when the code says otherwise. "
            "Call finish when the fix is verified.")


# --- Tools (one Pydantic model per tool: the schema the model sees and the validator) -----

class Bash(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = Field(min_length=1, description="Shell command to run in the repository root.")


class EditFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, description="File path relative to the repository root.")
    old_str: str = Field(min_length=1, description="Exact text to replace. Must occur exactly once in the file.")
    new_str: str = Field(description="Replacement text.")


class Finish(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, description="What was changed and how it was verified.")


TOOL_MODELS: dict[str, type[BaseModel]] = {"bash": Bash, "edit_file": EditFile, "finish": Finish}
_DESCRIPTIONS = {
    "bash": "Run a non-interactive shell command in the repository root and return its output and exit code.",
    "edit_file": "Replace one exact, unique occurrence of old_str with new_str in a file.",
    "finish": "Finish the task once the fix is implemented and verified.",
}


def _clean_schema(schema: dict) -> dict:
    """Pydantic JSON schema without 'title' keys (noise for the model)."""
    if isinstance(schema, dict):
        return {k: _clean_schema(v) for k, v in schema.items() if k != "title"}
    return schema


TOOLS = [ToolSpec(name, _DESCRIPTIONS[name], _clean_schema(model.model_json_schema()))
         for name, model in TOOL_MODELS.items()]


def validate_calls(step: Step) -> tuple[list[tuple[ToolCall, BaseModel | None, str | None]], str | None]:
    """Trigger 4: structural validation of the model's tool calls."""
    if not step.calls:
        return [], "no tool call" + (f" (finish_reason={step.finish_reason})" if step.finish_reason else "")
    checked, problems = [], []
    for call in step.calls:
        model = TOOL_MODELS.get(call.name)
        if model is None:
            problem = f"unknown tool '{call.name}'"
        else:
            try:
                checked.append((call, model.model_validate(call.args), None))
                continue
            except ValidationError as e:
                problem = f"invalid arguments for {call.name}: " + "; ".join(
                    f"{'.'.join(map(str, err['loc'])) or 'arguments'}: {err['msg']}"
                    for err in e.errors(include_url=False))
        checked.append((call, None, problem))
        problems.append(problem)
    return checked, "; ".join(problems) or None


# --- Environment helpers (all commands run inside the task container) ---------------------

_CONDA = "if [ -f /opt/miniconda3/bin/activate ]; then . /opt/miniconda3/bin/activate testbed >/dev/null 2>&1 || true; fi"


def shell(command: str, timeout_sec: int) -> str:
    """Wrap a model command: repo env active, pipefail, and a hard timeout inside the container."""
    script = f"set -o pipefail\n{_CONDA}\n{command}"
    return f"timeout -k 5 {int(timeout_sec)} bash -c {shlex.quote(script)}"


def clip(text: str, head: int = 6000, tail: int = 4000) -> str:
    if len(text) <= head + tail:
        return text
    return f"{text[:head]}\n[... {len(text) - head - tail} characters omitted ...]\n{text[-tail:]}"


async def run_bash(env: BaseEnvironment, command: str, timeout_sec: int) -> tuple[str, int]:
    try:
        res = await env.exec(shell(command, timeout_sec), timeout_sec=timeout_sec + 30)
    except RuntimeError as e:  # Harbor's exec timeout backstop
        return f"[exit code 124] command timed out after {timeout_sec}s ({e})", 124
    code = res.return_code
    note = f"\n[command timed out after {timeout_sec}s]" if code == 124 else ""
    return f"[exit code {code}]\n{clip((res.stdout or '') + (res.stderr or ''))}{note}", code


async def read_text(env: BaseEnvironment, producer: str) -> str | None:
    """Run `producer` (e.g. "cat -- 'f.py'") and return its stdout as UTF-8, or None."""
    res = await env.exec(f"set -o pipefail; {producer} | base64 | tr -d '\\n'", timeout_sec=60)
    if res.return_code != 0:
        return None
    try:
        return base64.b64decode(res.stdout or "").decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


async def edit_file(env: BaseEnvironment, path: str, old: str, new: str) -> tuple[str, int]:
    quoted = shlex.quote(path)
    text = await read_text(env, f"cat -- {quoted}")
    if text is None:
        return f"[exit code 1] cannot read {path}: missing, binary, or not UTF-8", 1
    count = text.count(old)
    if count != 1:
        hint = "add surrounding lines to make it unique" if count else "check whitespace and indentation"
        return f"[exit code 1] old_str occurs {count} times in {path}; it must occur exactly once ({hint})", 1
    data = base64.b64encode(text.replace(old, new, 1).encode("utf-8")).decode("ascii")
    if len(data) > 1_500_000:
        return f"[exit code 1] {path} is too large for edit_file; edit it with bash", 1
    res = await env.exec(f"printf %s {data} | base64 -d > {quoted}", timeout_sec=60)
    if res.return_code != 0:
        return f"[exit code {res.return_code}] could not write {path}: {(res.stdout or '')[:500]}", res.return_code
    return f"[exit code 0] edited {path}: replaced 1 occurrence", 0


async def git_snapshot(env: BaseEnvironment, base: str) -> dict[str, str]:
    """{path: blob hash} for tracked files that differ from the base commit."""
    cmd = (f"git -c core.quotepath=off diff --name-only {shlex.quote(base)} 2>/dev/null | "
           "while IFS= read -r f; do if [ -e \"$f\" ]; then "
           "printf '%s\\t%s\\n' \"$(git hash-object -- \"$f\")\" \"$f\"; "
           "else printf 'deleted\\t%s\\n' \"$f\"; fi; done")
    res = await env.exec(cmd, timeout_sec=60)
    snapshot = {}
    for line in (res.stdout or "").splitlines():
        digest, _, path = line.partition("\t")
        if path:
            snapshot[path] = digest
    return snapshot


_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_IDENT = re.compile(r"`([^`]{2,80})`|([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")
_STOP = {"self", "none", "true", "false", "return", "class", "import", "from", "with", "this", "that",
         "error", "value", "string", "python", "should", "would", "which", "there", "their", "using"}


def issue_terms(text: str, limit: int = 30) -> list[str]:
    """Lower-cased words from code-like tokens in the issue (identifiers, dotted names, paths)."""
    counts: Counter[str] = Counter()
    for quoted, token in _IDENT.findall(text):
        tok = quoted or token
        if not (quoted or "_" in tok or "." in tok or re.search(r"[a-z][A-Z]", tok)):
            continue
        for word in re.split(r"[^a-z0-9]+", _CAMEL.sub(" ", tok).lower()):
            if len(word) >= 4 and word not in _STOP:
                counts[word] += 1
    return [w for w, _ in counts.most_common(limit)]


async def build_repo_map(env: BaseEnvironment, instruction: str, max_chars: int = 8000) -> str:
    """Deterministic repo overview for the plan call: no tools, no LLM tokens."""
    res = await env.exec("git ls-files 2>/dev/null | head -n 60000", timeout_sec=60)
    files = [f for f in (res.stdout or "").splitlines() if f.strip()]
    top = Counter(f.split("/", 1)[0] + ("/" if "/" in f else "") for f in files)
    lines = ["Top-level entries (tracked files): " +
             ", ".join(f"{k} ({v})" if k.endswith("/") else k for k, v in top.most_common(30))]
    terms = issue_terms(instruction)
    scored = []
    for f in files:
        parts = [p for p in re.split(r"[^a-z0-9]+", f.lower()) if len(p) >= 3]
        score = sum(any(t == p or (len(t) >= 5 and t in p) for p in parts) for t in terms)
        if score:
            scored.append((-score, len(f), f))
    if scored:
        lines.append(f"Files whose paths match terms from the issue ({', '.join(terms[:12])}):")
        lines += [f"  {f}" for _, _, f in sorted(scored)[:40]]
    return "\n".join(lines)[:max_chars]


@dataclass
class GateState:
    base: str = "HEAD"
    snapshot: dict[str, str] = field(default_factory=dict)
    active_file: str | None = None
    flagged: dict[str, set[str]] = field(default_factory=dict)


async def run_gates(env: BaseEnvironment, tool: str, args: BaseModel, code: int,
                    signals: Signals, state: GateState) -> str:
    """Lint gate and AST signature check on edited files; test gate on test commands."""
    new = await git_snapshot(env, state.base)
    changed = sorted(p for p in set(state.snapshot) | set(new) if state.snapshot.get(p) != new.get(p))
    state.snapshot = new
    notes = []
    for path in changed:
        if new.get(path, "deleted") == "deleted":
            continue
        state.active_file = path
        if not path.endswith(".py"):
            continue
        after = await read_text(env, f"cat -- {shlex.quote(path)}")
        before = await read_text(env, f"git show {shlex.quote(state.base + ':' + path)}")
        if after is None:
            continue
        err = syntax_error(after, path)
        if err and (before is None or syntax_error(before, path) is None):
            signals.gate_file, signals.gate_passed = path, False
            notes.append(f"[gate] lint failed: {err}")
        if before is not None:
            seen = state.flagged.setdefault(path, set())
            fresh = [s for s in removed_signatures(before, after) if s not in seen]
            if fresh:
                seen.update(fresh)
                signals.removed_signatures.extend(f"{path}: {s}" for s in fresh)
                notes.append(f"[gate] public API changed in {path}: removed or changed {'; '.join(fresh)}")
    if (tool == "bash" and state.active_file and signals.gate_passed is not False
            and is_test_command(args.command)):
        signals.gate_file, signals.gate_passed = state.active_file, code == 0
        notes.append(f"[gate] test run {'passed' if code == 0 else 'failed'} after editing {state.active_file}")
    return ("\n" + "\n".join(notes)) if notes else ""


# --- The agent -----------------------------------------------------------------------------

class RoutingOptions(AgentOptions):
    """Agent kwargs (--ak key=value). Both models are required: there are no defaults."""
    workhorse: str = Field(description="Workhorse model, MODEL_ID[:LEVEL], e.g. gemini-3.8-flash:low")
    frontier: str = Field(description="Frontier model, MODEL_ID[:LEVEL], e.g. gemini-4-argon:high")
    mode: Literal["routed", "frontier_only", "workhorse_only"] = "routed"
    gate_failure_threshold: int = Field(3, ge=1)
    max_frontier_turns: int = Field(15, ge=0)
    budget_usd: float = Field(3.0, gt=0, description="Per-task budget (current prices) for the downshift")
    downshift_at: float = Field(0.8, gt=0, le=1)
    max_turns: int = Field(100, ge=1)
    command_timeout_sec: int = Field(180, ge=10)
    ceiling_usd: float = Field(250.0, gt=0, description="Skip new trials once the ledger (list prices) reaches this")
    ledger_path: str | None = None
    label: str = ""


class GovernedRoutingAgent(BaseAgent):
    options_model = RoutingOptions

    @staticmethod
    def name() -> str:
        return "governed-routing"

    def version(self) -> str:
        return "0.1.0"

    @classmethod
    def preflight(cls, kwargs=None, env=None) -> None:
        """Fail before any container starts if a model spec or the project is wrong."""
        super().preflight(kwargs, env)
        opts = cls.parse_options(kwargs, env)
        pricing = load_pricing()
        check_spec(opts.workhorse, pricing)
        check_spec(opts.frontier, pricing)
        if not (os.environ.get("GOOGLE_CLOUD_PROJECT") or (env or {}).get("GOOGLE_CLOUD_PROJECT")):
            raise ValueError("GOOGLE_CLOUD_PROJECT is not set (run.py reads it from --project or .env).")

    def __init__(self, logs_dir: Path, model_name: str | None = None, **kwargs):
        super().__init__(logs_dir=logs_dir, model_name=model_name, **kwargs)
        self.opts: RoutingOptions = self.options
        self.pricing = load_pricing()
        self.specs = {WORKHORSE: check_spec(self.opts.workhorse, self.pricing),
                      FRONTIER: check_spec(self.opts.frontier, self.pricing)}
        here = Path(logs_dir).resolve()
        default_ledger = here.parents[2] / "ledger.jsonl" if len(here.parents) > 2 else here / "ledger.jsonl"
        self.ledger_path = Path(self.opts.ledger_path) if self.opts.ledger_path else default_ledger

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        o = self.opts
        trial = Path(self.logs_dir).parent.name
        cfg = RouterConfig(mode=o.mode, gate_failure_threshold=o.gate_failure_threshold,
                           max_frontier_turns=o.max_frontier_turns, budget_usd=o.budget_usd,
                           downshift_at=o.downshift_at)
        meta = {"task": trial.rsplit("__", 1)[0], "trial": trial, "label": o.label, "mode": o.mode,
                "workhorse": str(self.specs[WORKHORSE]), "frontier": str(self.specs[FRONTIER]),
                "router": vars(cfg), "max_turns": o.max_turns}
        tel = Telemetry(self.logs_dir, self.pricing, meta, self.ledger_path)
        if ledger_total(self.ledger_path, "cost_list") >= o.ceiling_usd:
            tel.finish(context, "spend_ceiling")
            return
        project = os.environ["GOOGLE_CLOUD_PROJECT"]
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        tiers = {tier: make_model(spec, project, location) for tier, spec in self.specs.items()}
        router = GovernedRouter(cfg)
        stop, error = "turn_limit", None
        try:
            head = await environment.exec("git rev-parse HEAD", timeout_sec=30)
            state = GateState(base=(head.stdout or "").strip() or "HEAD")
            repo_map = await build_repo_map(environment, instruction)

            decision = router.plan()  # Trigger 1: plan-only call, no tools
            planner = tiers[decision.tier]
            plan = await planner.step(PLAN_SYSTEM, [], [UserText(plan_prompt(instruction, repo_map))])
            tel.record(0, decision, planner.spec, plan, [], Signals())
            transcript = [UserText(task_message(instruction, repo_map, plan.text))]
            state.snapshot = await git_snapshot(environment, state.base)

            for turn in range(1, o.max_turns + 1):
                decision = router.route(turn, tel.cost_current)
                model = tiers[decision.tier]
                step = await model.step(SYSTEM_PROMPT, TOOLS, transcript)
                transcript.append(step)
                checked, schema_error = validate_calls(step)
                signals = Signals(schema_error=schema_error)
                results: list[tuple[ToolCall, str, int]] = []
                finished = False
                for call, args, problem in checked:
                    if problem:
                        results.append((call, f"[exit code 1] {problem}. Call the tool again with valid arguments.", 1))
                    elif call.name == "finish":
                        finished = True
                        results.append((call, "[exit code 0] finished", 0))
                    else:
                        if call.name == "bash":
                            output, code = await run_bash(environment, args.command, o.command_timeout_sec)
                        else:
                            output, code = await edit_file(environment, args.path, args.old_str, args.new_str)
                        output += await run_gates(environment, call.name, args, code, signals, state)
                        results.append((call, output, code))
                transcript.append(ToolResults([(c, out) for c, out, _ in results]) if step.calls
                                  else UserText(NO_TOOL_CALL_HINT))
                router.observe(signals)
                tel.record(turn, decision, model.spec, step, results, signals)
                if finished:
                    stop = "finished"
                    break
                if tel.loop_detected():
                    stop = "loop_breaker"  # the only hard stop besides the turn limit
                    break
        except asyncio.CancelledError:  # Harbor's agent timeout
            stop = "agent_timeout"
            raise
        except Exception as e:  # API errors that outlast SDK retries -> Harbor records + retries once
            stop, error = "error", f"{type(e).__name__}: {e}"[:1000]
            raise
        finally:
            tel.finish(context, stop, error)
            for m in tiers.values():
                try:
                    await m.aclose()
                except BaseException:  # never mask the original outcome
                    pass
