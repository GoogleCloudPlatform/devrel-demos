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

"""Offline tests: no network, no Docker, no model calls."""

import asyncio
import base64
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import report  # noqa: E402
import routing_agent  # noqa: E402
import run as runner  # noqa: E402
from google.genai import types  # noqa: E402
from harbor.environments.base import ExecResult  # noqa: E402
from harbor.models.agent.context import AgentContext  # noqa: E402
from providers import (PLACEHOLDER_SIGNATURE, ClaudeModel, GeminiModel, ModelSpec, Step,  # noqa: E402
                       ToolCall, ToolResults, Usage, UserText, parse_spec)
from router import (FRONTIER, WORKHORSE, GovernedRouter, RouterConfig, Signals,  # noqa: E402
                    is_test_command, label_turn, removed_signatures, syntax_error)
from telemetry import call_cost, check_spec, ledger_total, load_pricing, rates, switch_tax  # noqa: E402

PRICING = load_pricing()


# --- Router ----------------------------------------------------------------------------------

def fail(router, path="a.py", times=1):
    for _ in range(times):
        router.observe(Signals(gate_file=path, gate_passed=False))


def test_plan_call_tier_per_mode():
    assert GovernedRouter(RouterConfig()).plan().tier == FRONTIER
    assert GovernedRouter(RouterConfig(mode="frontier_only")).plan().tier == FRONTIER
    assert GovernedRouter(RouterConfig(mode="workhorse_only")).plan().tier == WORKHORSE


def test_default_turn_goes_to_workhorse():
    router = GovernedRouter(RouterConfig())
    router.plan()
    assert router.route(1, 0.0).tier == WORKHORSE


def test_gate_failures_escalate_on_third_and_lock_until_that_file_passes():
    router = GovernedRouter(RouterConfig())
    fail(router, times=2)
    assert router.route(1, 0).tier == WORKHORSE
    fail(router)
    d = router.route(2, 0)
    assert (d.tier, d.reason) == (FRONTIER, "gate_failures")
    assert router.route(3, 0).reason == "sticky_lock"
    router.observe(Signals(gate_file="other.py", gate_passed=True))
    assert router.route(4, 0).reason == "sticky_lock"
    router.observe(Signals(gate_file="a.py", gate_passed=True))
    assert router.route(5, 0).tier == WORKHORSE


def test_a_pass_resets_the_consecutive_count():
    router = GovernedRouter(RouterConfig())
    fail(router, times=2)
    router.observe(Signals(gate_file="a.py", gate_passed=True))
    fail(router, times=2)
    assert router.route(1, 0).tier == WORKHORSE


def test_signature_and_schema_triggers_escalate_for_one_turn():
    router = GovernedRouter(RouterConfig())
    router.observe(Signals(removed_signatures=["m.py: def f(a)"]))
    assert router.route(1, 0).reason == "signature_mutation"
    assert router.route(2, 0).tier == WORKHORSE
    router.observe(Signals(schema_error="no tool call"))
    assert router.route(3, 0).reason == "schema_failure"
    assert router.route(4, 0).tier == WORKHORSE


def test_budget_downshift_suppresses_triggers():
    router = GovernedRouter(RouterConfig(budget_usd=1.0))
    router.observe(Signals(schema_error="x"))
    d = router.route(1, spend_usd=0.85)
    assert (d.tier, d.reason, d.suppressed) == (WORKHORSE, "budget_downshift", "schema_failure")


def test_cap_counts_the_plan_call():
    router = GovernedRouter(RouterConfig(max_frontier_turns=1))
    router.plan()
    router.observe(Signals(schema_error="x"))
    d = router.route(1, 0)
    assert (d.tier, d.reason, d.suppressed) == (WORKHORSE, "cap_reached", "schema_failure")


def test_forced_modes_record_the_trigger_they_ignored():
    router = GovernedRouter(RouterConfig(mode="workhorse_only"))
    router.observe(Signals(schema_error="x"))
    d = router.route(1, 0)
    assert (d.tier, d.reason, d.suppressed) == (WORKHORSE, "forced", "schema_failure")
    assert GovernedRouter(RouterConfig(mode="frontier_only")).route(1, 0).tier == FRONTIER


# --- Deterministic signals --------------------------------------------------------------------

BASE = '''
def compute(a, b=1, *, strict=False):
    return a
def _private(x):
    return x
class Parser:
    def __init__(self, text):
        self.text = text
    def parse(self, mode="fast"):
        return mode
    def _helper(self):
        return 1
'''


def test_removed_signatures_flags_changed_or_removed_public_api():
    assert removed_signatures(BASE, BASE.replace("b=1, *", "b=1, c=2, *")) == ["def compute(a, b=, *, strict=)"]
    assert "class Parser" in removed_signatures(BASE, BASE.replace("class Parser", "class TextParser"))
    assert removed_signatures(BASE, BASE.replace("def __init__(self, text)", "def __init__(self, text, enc)")) == [
        "def Parser.__init__(self, text)"]


def test_removed_signatures_ignores_safe_edits():
    assert removed_signatures(BASE, BASE.replace("return a\n", "return a + b\n")) == []
    assert removed_signatures(BASE, BASE.replace("def _private(x)", "def _private(x, y)")) == []
    assert removed_signatures(BASE, BASE.replace("def compute(a, b=1,", "def compute(a: int, b: int = 1,")) == []
    assert removed_signatures(BASE, BASE + "\ndef added(z):\n    return z\n") == []
    assert removed_signatures(BASE, "def broken(:") == []


def test_syntax_gate():
    assert syntax_error("x = 1\n") is None
    assert syntax_error("def f(:\n", "m.py").startswith("m.py:1:")


@pytest.mark.parametrize("cmd", [
    "pytest tests/test_x.py -q", "python -m pytest -x", "cd /testbed && python reproduce_issue.py",
    "timeout 60 python tests/runtests.py auth_tests", "bin/test sympy/core", "tox -e py39",
    "PYTHONPATH=. python -m unittest tests.test_a", "python repro.py 2>&1 | tail -5"])
def test_is_test_command_true(cmd):
    assert is_test_command(cmd)


@pytest.mark.parametrize("cmd", [
    "cat tests/test_x.py", "grep -rn pytest setup.cfg", "python setup.py develop", "ls tests",
    "python -c 'print(1)'", "sed -n 1,20p runtests.py"])
def test_is_test_command_false(cmd):
    assert not is_test_command(cmd)


@pytest.mark.parametrize("tool,args,label", [
    ("edit_file", {"path": "a.py"}, "edit"),
    ("bash", {"command": "grep -rn 'rm' src"}, "explore"),
    ("bash", {"command": "sed -n '1,40p' a.py"}, "explore"),
    ("bash", {"command": "sed -i 's/a/b/' a.py"}, "edit"),
    ("bash", {"command": "cat > repro.py << 'EOF'\nprint(1)\nEOF"}, "edit"),
    ("bash", {"command": "pytest -q tests/test_a.py"}, "test"),
    ("bash", {"command": "ls -la 2>/dev/null"}, "explore"),
    ("bash", {"command": "python -c \"v = 1e-4\nprint(v if v > 0 else -v)\""}, "explore"),
    ("bash", {"command": "echo 'x' > notes.txt"}, "edit"),
    ("bash", {"command": "pip install -e ."}, "other"),
    ("finish", {"summary": "done"}, "other")])
def test_label_turn(tool, args, label):
    assert label_turn(tool, args) == label


# --- Pricing and cost ---------------------------------------------------------------------------

def test_check_spec_validates_models_and_levels():
    assert check_spec("gemini-3.8-flash:low", PRICING) == ModelSpec("gemini-3.8-flash", "low")
    assert check_spec("claude-opus-5-5:MAX", PRICING).level == "max"
    with pytest.raises(ValueError, match="Unknown model"):
        check_spec("gpt-9", PRICING)
    with pytest.raises(ValueError, match="not supported"):
        check_spec("gemini-3.8-flash:max", PRICING)
    with pytest.raises(ValueError, match="not supported"):
        check_spec("claude-haiku-4-5:high", PRICING)


def test_parse_spec():
    assert str(parse_spec("gemini-4-argon:HIGH")) == "gemini-4-argon:high"
    assert parse_spec("claude-opus-5-5").level is None
    assert parse_spec("claude-opus-5-5").provider == "claude"


def test_rates_by_basis():
    assert rates(PRICING, "gemini-4-argon", "2026-11-30")["input"] == 2.0
    assert rates(PRICING, "gemini-4-argon", "2026-12-01")["input"] == 4.0
    assert rates(PRICING, "gemini-4-argon", "list")["output"] == 20.0
    assert rates(PRICING, "claude-opus-5-5", "2026-11-01")["input"] == 4.0  # no promo block


def test_call_cost_counts_cache_reads_writes_and_thinking():
    u = Usage(input_uncached=1_000_000, cache_read=1_000_000, output=1_000_000, thinking=400_000)
    assert call_cost(rates(PRICING, "gemini-3.8-flash", "list"), u) == pytest.approx(1.50 + 0.15 + 7.50)
    c = Usage(input_uncached=10, cache_read=1_000_000, cache_write=1_000_000)
    assert call_cost(rates(PRICING, "claude-opus-5-5", "list"), c) == pytest.approx(0.20 + 5.00 + 10 * 4 / 1e6)


def test_long_context_rates_apply_to_all_tokens():
    rate = rates(PRICING, "claude-haiku-5-5", "list")
    assert call_cost(rate, Usage(input_uncached=99_999)) == pytest.approx(99_999 * 0.10 / 1e6)
    assert call_cost(rate, Usage(input_uncached=100_000, output=1_000_000)) == pytest.approx(0.05 + 2.50)


def test_switch_tax_is_cold_minus_warm():
    assert switch_tax(rates(PRICING, "gemini-4-argon", "list"), Usage(input_uncached=1_000_000)) == pytest.approx(3.80)


# --- Provider rendering (stub clients, no network) ---------------------------------------------

def gemini_native(sig=b"real-sig"):
    return types.Content(role="model", parts=[types.Part(
        function_call=types.FunctionCall(name="bash", args={"command": "ls"}), thought_signature=sig)])


def with_result(step):
    return [UserText("task"), step, ToolResults([(step.calls[0], "out")])]


def test_gemini_replays_own_signature_and_placeholders_foreign_calls():
    flash = GeminiModel(ModelSpec("gemini-3.8-flash", "low"), "p", client=object())
    own = Step("gemini-3.8-flash", "", [ToolCall("g1", "bash", {"command": "ls"})], Usage(), native=gemini_native())
    assert flash.render(with_result(own))[1].parts[0].thought_signature == b"real-sig"
    argon = Step("gemini-4-argon", "", [ToolCall("g1", "bash", {"command": "ls"})], Usage(), native=gemini_native(b"x"))
    assert flash.render(with_result(argon))[1].parts[0].thought_signature == PLACEHOLDER_SIGNATURE
    opus = Step("claude-opus-5-5", "note", [ToolCall("toolu_1", "bash", {"command": "ls"})], Usage(),
                native=[{"type": "thinking", "thinking": "t", "signature": "s"}])
    contents = flash.render(with_result(opus))
    assert contents[1].parts[0].text == "note"
    assert contents[1].parts[1].thought_signature == PLACEHOLDER_SIGNATURE
    assert contents[2].parts[0].function_response.name == "bash"


def test_claude_replays_own_blocks_and_never_receives_foreign_thinking():
    opus = ClaudeModel(ModelSpec("claude-opus-5-5", "high"), "p", client=object())
    blocks = [{"type": "thinking", "thinking": "t", "signature": "sig"},
              {"type": "tool_use", "id": "toolu_1", "name": "bash", "input": {"command": "ls"}}]
    own = Step("claude-opus-5-5", "", [ToolCall("toolu_1", "bash", {"command": "ls"})], Usage(), native=blocks)
    assert opus.render(with_result(own))[1]["content"] == blocks
    sonnet = Step("claude-sonnet-5-5", "", [ToolCall("toolu_2", "bash", {"command": "ls"})], Usage(), native=blocks)
    msgs = opus.render(with_result(sonnet))
    assert all(b["type"] != "thinking" for b in msgs[1]["content"])
    assert msgs[2]["content"][0] == {"type": "tool_result", "tool_use_id": "toolu_2", "content": "out"}


def test_claude_merges_consecutive_user_turns():
    opus = ClaudeModel(ModelSpec("claude-opus-5-5", "high"), "p", client=object())
    call = ToolCall("g1", "bash", {"command": "ls"})
    msgs = opus.render([UserText("task"), Step("gemini-3.8-flash", "", [call], Usage()),
                        ToolResults([(call, "out")]), UserText("hint")])
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[2]["content"][-1] == {"type": "text", "text": "hint"}


# --- Agent loop against a fake container --------------------------------------------------------

class FakeEnv:
    """Stands in for the task container: one tracked file, scripted command results."""

    def __init__(self):
        self.files = {"pkg/mod.py": "def f(a):\n    return a\n"}
        self.head = dict(self.files)
        self.commands = []

    async def exec(self, command, cwd=None, env=None, timeout_sec=None, user=None):
        self.commands.append(command)
        if command.startswith("git rev-parse"):
            return ExecResult(stdout="abc123\n", return_code=0)
        if command.startswith("git ls-files"):
            return ExecResult(stdout="pkg/mod.py\ntests/test_mod.py\n", return_code=0)
        if "diff --name-only" in command:
            changed = [p for p in self.files if self.files[p] != self.head.get(p)]
            return ExecResult(stdout="".join(f"{abs(hash(self.files[p])):x}\t{p}\n" for p in changed), return_code=0)
        if "| base64 | tr -d" in command:
            text = self.head["pkg/mod.py"] if "git show" in command else self.files["pkg/mod.py"]
            return ExecResult(stdout=base64.b64encode(text.encode()).decode(), return_code=0)
        if "| base64 -d >" in command:
            data = command.split("printf %s ", 1)[1].split(" | base64 -d", 1)[0]
            self.files["pkg/mod.py"] = base64.b64decode(data).decode()
            return ExecResult(stdout="", return_code=0)
        if "pytest" in command:
            return ExecResult(stdout="1 failed", return_code=1)
        return ExecResult(stdout="ok", return_code=0)


class ScriptedModel:
    def __init__(self, spec, steps):
        self.spec, self.steps = spec, list(steps)

    async def step(self, system, tools, transcript):
        return self.steps.pop(0)

    async def aclose(self):
        return None


def step(model, *calls, text=""):
    return Step(model, text, [ToolCall(f"c{i}", name, args) for i, (name, args) in enumerate(calls)],
                Usage(input_uncached=1000, output=100))


def run_agent(tmp_path, monkeypatch, workhorse_steps, frontier_steps, trial="pkg__mod-1__abc", **opts):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    wh, fr = ModelSpec("gemini-3.8-flash", "low"), ModelSpec("claude-opus-5-5", "high")
    models = {wh: ScriptedModel(wh, workhorse_steps), fr: ScriptedModel(fr, frontier_steps)}
    monkeypatch.setattr(routing_agent, "make_model", lambda spec, project, location: models[spec])
    logs = tmp_path / "jobs" / "job1" / trial / "agent"
    agent = routing_agent.GovernedRoutingAgent(logs_dir=logs, workhorse=str(wh), frontier=str(fr),
                                               ledger_path=str(tmp_path / "ledger.jsonl"), **opts)
    env, ctx = FakeEnv(), AgentContext()
    asyncio.run(agent.run("Fix f in pkg/mod.py so `f` accepts `b`.", env, ctx))
    records = [json.loads(line) for line in (logs / "trajectory.jsonl").read_text().splitlines()] \
        if (logs / "trajectory.jsonl").exists() else []
    return records, json.loads((logs / "summary.json").read_text()), ctx, env, logs


def test_loop_routes_on_triggers_and_writes_telemetry(tmp_path, monkeypatch):
    W, F = "gemini-3.8-flash", "claude-opus-5-5"
    pytest_call = ("bash", {"command": "python -m pytest tests/test_mod.py"})
    workhorse = [step(W, ("edit_file", {"path": "pkg/mod.py", "old_str": "def f(a):", "new_str": "def f(a, b):"})),
                 step(W, pytest_call), step(W, pytest_call)]
    frontier = [step(F, text="1. edit f\n2. run tests"), step(F, pytest_call), step(F, ("finish", {"summary": "done"}))]
    records, summary, ctx, env, logs = run_agent(tmp_path, monkeypatch, workhorse, frontier)
    assert [r["tier"] for r in records] == ["frontier", "workhorse", "frontier", "workhorse", "workhorse", "frontier"]
    assert [r["reason"] for r in records] == ["planning", "default", "signature_mutation", "default", "default",
                                              "gate_failures"]
    assert summary["stop_reason"] == "finished"
    assert summary["triggers"]["fired"] == {"planning": 1, "signature_mutation": 1, "gate_failures": 1}
    assert "def f(a, b):" in env.files["pkg/mod.py"]
    assert set(ctx.model_usage) == {"gemini-3.8-flash:low", "claude-opus-5-5:high"} and ctx.cost_usd > 0
    assert ledger_total(tmp_path / "ledger.jsonl") > 0
    assert "Strip: `P W F W W F`" in (logs / "timeline.md").read_text()


def test_schema_failures_reach_the_frontier_and_get_an_error_back(tmp_path, monkeypatch):
    W, F = "gemini-3.8-flash", "claude-opus-5-5"
    workhorse = [step(W, text="I will look at the code now.")]  # no tool call
    frontier = [step(F, text="plan"), step(F, ("edit_file", {"path": "pkg/mod.py", "new_str": "x"})),
                step(F, ("finish", {"summary": "done"}))]
    records, summary, *_ = run_agent(tmp_path, monkeypatch, workhorse, frontier)
    assert [r["reason"] for r in records] == ["planning", "default", "schema_failure", "schema_failure"]
    assert "invalid arguments for edit_file" in records[2]["results"][0]["preview"]
    assert summary["triggers"]["fired"]["schema_failure"] == 2


def test_loop_breaker_and_spend_ceiling(tmp_path, monkeypatch):
    W, F = "gemini-3.8-flash", "claude-opus-5-5"
    ls = ("bash", {"command": "ls"})
    records, summary, *_ = run_agent(tmp_path, monkeypatch, [step(W, ls) for _ in range(7)], [step(F, text="plan")])
    assert summary["stop_reason"] == "loop_breaker" and summary["turns"] == 5
    records, summary, ctx, *_ = run_agent(tmp_path, monkeypatch, [], [], trial="pkg__mod-1__def", ceiling_usd=0.000001)
    assert summary["stop_reason"] == "spend_ceiling" and records == []


# --- run.py and report.py --------------------------------------------------------------------------

def test_env_file_precedence(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GOOGLE_CLOUD_PROJECT=from-file\nexport OTHER='1'\n# comment\n")
    env = {"GOOGLE_CLOUD_PROJECT": "from-shell"}
    runner.load_env_file(env_file, env)
    assert env == {"GOOGLE_CLOUD_PROJECT": "from-shell", "OTHER": "1"}


def test_task_ref_and_shared_baselines():
    assert runner.task_ref("swe-bench/swe-bench-verified", "a__b-1") == "swe-bench/a__b-1"
    assert runner.task_ref("swe-bench/swe-bench-verified", "x/a__b-1") == "x/a__b-1"
    assert runner.run_key("t", "frontier_only", "w1", "f", "") == runner.run_key("t", "frontier_only", "w2", "f", "")
    assert runner.run_key("t", "routed", "w1", "f", "") != runner.run_key("t", "routed", "w2", "f", "")


def write_trial(root, name, mode, reward, tokens, exc=None, wh="gemini-3.8-flash:low", fr="gemini-4-argon:high"):
    trial = root / "job" / name
    (trial / "agent").mkdir(parents=True)
    (trial / "result.json").write_text(json.dumps({
        "trial_name": name, "task_name": "swe-bench/t1",
        "config": {"agent": {"kwargs": {"mode": mode, "workhorse": wh, "frontier": fr, "label": ""}}},
        "verifier_result": {"rewards": {"reward": reward}} if reward is not None else None,
        "exception_info": {"exception_type": exc} if exc else None}))
    rec = {"turn": 1, "tier": "workhorse", "model_id": wh.split(":")[0], "model_switch": False, "cum_cost_current": 1.5,
           "usage": {"input_uncached": tokens, "cache_read": 0, "cache_write": 0, "output": 0, "thinking": 0}}
    (trial / "agent" / "trajectory.jsonl").write_text(json.dumps(rec) + "\n")
    (trial / "agent" / "summary.json").write_text(json.dumps({
        "turns": 1, "calls": 1, "tiers": {"frontier": {"calls": 0}}, "turn_labels": {"explore": 1},
        "triggers": {"fired": {"planning": 1}}, "model_switches": 0, "stop_reason": "finished"}))


def test_completed_trials_and_report(tmp_path):
    write_trial(tmp_path, "t1__a", "routed", 1.0, 1_000_000)
    write_trial(tmp_path, "t1__b", "routed", 0.0, 1_000_000)
    write_trial(tmp_path, "t1__c", "routed", None, 1_000_000, exc="DockerError")
    write_trial(tmp_path, "t1__d", "routed", 1.0, 1_000_000, exc="AgentTimeoutError")
    done = runner.completed_trials(tmp_path)
    assert done[runner.run_key("swe-bench/t1", "routed", "gemini-3.8-flash:low", "gemini-4-argon:high", "")] == 3
    trials = report.load_trials(tmp_path, PRICING, "list", [], [])
    agg = report.aggregate(report.pairing_rows(trials, "gemini-3.8-flash:low", "gemini-4-argon:high")["routed"])
    assert (agg["attempts"], agg["resolved"], agg["infra_errors"]) == (3, 2, 1)
    assert agg["cost_per_resolved"] == pytest.approx(4.50 / 2)
    text = report.render(trials, PRICING, "list")
    assert "Left out of the comparison" in text and "**$2.250**" in text
    report.plot(trials, tmp_path / "plots")
    assert {p.name for p in (tmp_path / "plots").iterdir()} == {"cost_per_resolved.png", "trajectory_strip.png",
                                                               "triggers.png"}


def test_dry_run_builds_the_harbor_command(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p")
    runner.main(["--task", "astropy__astropy-14508", "--workhorse", "gemini-3.8-flash:low",
                 "--frontier", "gemini-4-argon:high", "--modes", "routed", "--attempts", "1",
                 "--jobs-dir", str(tmp_path), "--dry-run"])
    out = capsys.readouterr().out
    for fragment in ("-i swe-bench/astropy__astropy-14508", "-a routing_agent:GovernedRoutingAgent",
                     "--ak workhorse=gemini-3.8-flash:low", "--ak frontier=gemini-4-argon:high",
                     "--agent-timeout-multiplier 2.0", "--max-retries 1", "project=p"):
        assert fragment in out
