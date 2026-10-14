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

"""Governed model routing: pure decision logic plus the deterministic signals it uses.

No I/O and no provider knowledge. The agent feeds `Signals` in after every tool call
and asks `route()` which tier should take the next turn.

Escalation triggers (Workhorse -> Frontier):
  1. Planning: the plan-only call before the loop (turn 0).
  2. Gate failures: a lint or test gate failed 3 consecutive times on the same file.
     Sets a sticky lock that holds Frontier until that file passes a test gate.
  3. Signature mutation: an edit removed or changed an existing public signature.
  4. Schema failure: the model's output had no tool call, an unknown tool, or invalid args.

Safeguards: an escalation cap (max Frontier turns per task) and a per-task budget that
downshifts to Workhorse at 80% spend. Baseline modes force one tier for comparison.
"""

from __future__ import annotations

import ast
import os
import re
import shlex
import warnings
from dataclasses import dataclass, field

WORKHORSE, FRONTIER = "workhorse", "frontier"
MODES = ("routed", "frontier_only", "workhorse_only")


@dataclass
class RouterConfig:
    mode: str = "routed"             # routed | frontier_only | workhorse_only
    gate_failure_threshold: int = 3  # Trigger 2: escalate on the 3rd consecutive failure
    max_frontier_turns: int = 15     # escalation cap per task (the plan call counts)
    budget_usd: float = 3.00         # per-task budget at current prices
    downshift_at: float = 0.80       # no Frontier once 80% of the budget is spent


@dataclass
class Signals:
    """Deterministic facts the harness observed after a model turn."""
    gate_file: str | None = None
    gate_passed: bool | None = None                              # None: no gate ran
    removed_signatures: list[str] = field(default_factory=list)  # Trigger 3
    schema_error: str | None = None                              # Trigger 4


@dataclass
class Decision:
    tier: str
    reason: str          # planning | gate_failures | sticky_lock | signature_mutation |
                         # schema_failure | default | forced | budget_downshift | cap_reached
    detail: str = ""
    suppressed: str = ""  # trigger that fired but was blocked by a safeguard or forced mode


class GovernedRouter:
    def __init__(self, cfg: RouterConfig):
        if cfg.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.cfg = cfg
        self.failures: dict[str, int] = {}
        self.sticky_file: str | None = None
        self.pending: list[tuple[str, str]] = []
        self.frontier_turns = 0

    def plan(self) -> Decision:
        """Trigger 1: the plan-only call (turn 0). Frontier, except in workhorse_only."""
        tier = WORKHORSE if self.cfg.mode == "workhorse_only" else FRONTIER
        self.frontier_turns += tier == FRONTIER
        reason = "planning" if self.cfg.mode == "routed" else "forced"
        return Decision(tier, reason, "plan-only call, no tools")

    def observe(self, s: Signals) -> None:
        if s.gate_file and s.gate_passed is not None:
            if s.gate_passed:
                self.failures[s.gate_file] = 0
                if self.sticky_file == s.gate_file:
                    self.sticky_file = None  # the file passes its gates: release the lock
            else:
                self.failures[s.gate_file] = self.failures.get(s.gate_file, 0) + 1
        if s.removed_signatures:
            self.pending.append(("signature_mutation", "; ".join(s.removed_signatures)))
        if s.schema_error:
            self.pending.append(("schema_failure", s.schema_error))

    def route(self, turn: int, spend_usd: float) -> Decision:
        trigger = self._trigger()
        if self.cfg.mode != "routed":
            tier = FRONTIER if self.cfg.mode == "frontier_only" else WORKHORSE
            d = Decision(tier, "forced", self.cfg.mode, trigger[0] if trigger else "")
        elif not trigger:
            d = Decision(WORKHORSE, "default")
        elif spend_usd >= self.cfg.downshift_at * self.cfg.budget_usd:
            d = Decision(WORKHORSE, "budget_downshift", f"${spend_usd:.2f} spent", trigger[0])
        elif self.frontier_turns >= self.cfg.max_frontier_turns:
            d = Decision(WORKHORSE, "cap_reached", f"{self.frontier_turns} frontier turns", trigger[0])
        else:
            d = Decision(FRONTIER, *trigger)
        self.frontier_turns += d.tier == FRONTIER
        return d

    def _trigger(self) -> tuple[str, str] | None:
        if self.sticky_file:
            return "sticky_lock", f"until gates pass on {self.sticky_file}"
        for path, n in self.failures.items():
            if n >= self.cfg.gate_failure_threshold:
                self.sticky_file = path
                return "gate_failures", f"{n} consecutive failures on {path}"
        if self.pending:
            reason, detail = self.pending[0]
            self.pending.clear()
            return reason, detail
        return None


# ---------------------------------------------------------------------------
# Deterministic signal helpers (pure functions, unit-tested)
# ---------------------------------------------------------------------------

_PUBLIC_DUNDERS = {"__init__", "__new__", "__call__"}


def _render_args(a: ast.arguments) -> str:
    """Parameter names and kinds only. Defaults are marked with '=', annotations ignored."""
    parts: list[str] = []
    positional = a.posonlyargs + a.args
    first_default = len(positional) - len(a.defaults)
    for i, arg in enumerate(positional):
        parts.append(arg.arg + ("=" if i >= first_default else ""))
        if a.posonlyargs and i == len(a.posonlyargs) - 1:
            parts.append("/")
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    elif a.kwonlyargs:
        parts.append("*")
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        parts.append(arg.arg + ("=" if default is not None else ""))
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    return ", ".join(parts)


def public_signatures(source: str) -> set[str] | None:
    """Public module-level functions, classes and their public methods. None if unparseable."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return None
    sigs: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
            sigs.add(f"def {node.name}({_render_args(node.args)})")
        elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            sigs.add(f"class {node.name}")
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                        not item.name.startswith("_") or item.name in _PUBLIC_DUNDERS):
                    sigs.add(f"def {node.name}.{item.name}({_render_args(item.args)})")
    return sigs


def removed_signatures(before: str, after: str) -> list[str]:
    """Trigger 3: public signatures present before an edit but missing (or changed) after it."""
    old, new = public_signatures(before), public_signatures(after)
    if old is None or new is None:
        return []
    return sorted(old - new)


def syntax_error(source: str, path: str = "<file>") -> str | None:
    """Lint gate: a syntax check that runs on the host. Returns 'path:line: message' or None."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            compile(source, path, "exec", dont_inherit=True)
    except SyntaxError as e:
        return f"{path}:{e.lineno}: {e.msg}"
    except ValueError as e:  # e.g. null bytes
        return f"{path}: {e}"
    return None


_SPLIT = re.compile(r"&&|\|\||[;|\n]")
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_PYTHON = re.compile(r"^python[\d.]*$")
_TEST_SCRIPT = re.compile(r"(^|/)(runtests|reproduce\w*|repro\w*|test_\w+|\w+_test)\.py$")
_TEST_RUNNERS = {"pytest", "py.test", "tox", "nox"}


def _segments(command: str) -> list[list[str]]:
    """Split a shell command into simple-command token lists, dropping env/timeout prefixes."""
    out = []
    for seg in _SPLIT.split(command):
        try:
            toks = shlex.split(seg)
        except ValueError:
            toks = seg.split()
        while toks:
            if _ENV_ASSIGN.match(toks[0]) or toks[0] in ("time", "env", "nice", "command", "exec"):
                toks = toks[1:]
            elif toks[0] == "timeout":
                toks = toks[1:]
                while toks and toks[0].startswith("-"):
                    toks = toks[1:]
                toks = toks[1:]  # the duration
            else:
                break
        if toks:
            out.append(toks)
    return out


def is_test_command(command: str) -> bool:
    """Test gate: does this command run tests or a reproduction script?"""
    for toks in _segments(command):
        exe = os.path.basename(toks[0])
        if exe in _TEST_RUNNERS or toks[0] in ("bin/test", "./bin/test") or _TEST_SCRIPT.search(toks[0]):
            return True
        if _PYTHON.match(exe):
            rest = toks[1:]
            if "-m" in rest:
                i = rest.index("-m")
                if i + 1 < len(rest) and rest[i + 1] in ("pytest", "unittest"):
                    return True
            script = next((t for t in rest if not t.startswith("-")), "")
            if script.endswith(".py") and _TEST_SCRIPT.search(script):
                return True
    return False


_READ_CMDS = {"cat", "head", "tail", "less", "more", "grep", "egrep", "fgrep", "rg", "ag", "ls", "find",
              "tree", "wc", "nl", "awk", "file", "stat", "pwd", "which", "diff", "git", "echo", "sort"}
_WRITE_CMDS = {"tee", "mv", "cp", "rm", "touch", "patch", "truncate"}
_REDIRECT = re.compile(r">{1,2}\s*[^&\s]")


def _is_write(toks: list[str]) -> bool:
    exe = os.path.basename(toks[0])
    if exe in _WRITE_CMDS:
        return True
    if exe in ("sed", "perl") and any(t.startswith("-i") or (t.startswith("-") and "i" in t[1:3]) for t in toks[1:]):
        return True
    return exe == "git" and len(toks) > 1 and toks[1] in ("apply", "checkout", "restore", "stash")


def label_turn(tool: str, args: dict) -> str:
    """Rule-based turn label (explore / edit / test / other) for the 'mostly mechanical' statistic."""
    if tool == "edit_file":
        return "edit"
    if tool != "bash":
        return "other"
    cmd = str(args.get("command", ""))
    if is_test_command(cmd):
        return "test"
    segments = _segments(cmd)
    unquoted = re.sub(r"'[^']*'|\"(?:\\.|[^\"\\])*\"", "''", cmd)  # ignore '>' inside quoted code
    cleaned = re.sub(r"\d?>{1,2}\s*/dev/null|\d?>&\d|&>\s*/dev/null", "", unquoted)
    if any(_is_write(t) for t in segments) or _REDIRECT.search(cleaned):
        return "edit"
    first = segments[0] if segments else []
    exe = os.path.basename(first[0]) if first else ""
    if exe in _READ_CMDS or (exe == "sed" and "-n" in first) or (_PYTHON.match(exe) and "-c" in first):
        return "explore"
    return "other"
