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

"""Model adapters: an offline fake for pipeline tests and an ADK agent for real runs."""
import asyncio
import os
import pathlib
import re
import uuid
from dataclasses import dataclass

SYSTEM = (
    "You write Kubernetes manifests. Reply with YAML only, in one fenced yaml block. "
    "Target Kubernetes 1.37."
)
CONTEXT_HEADER = "\n\nReference notes for Kubernetes 1.37 (use them when they apply):\n\n"
# feedback comes from checkers.feedback_text: the failed checks and their details.
REPAIR_PROMPT = "{feedback}\nReply with the complete corrected YAML in one fenced yaml block."
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)


@dataclass
class Reply:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0


class FakeModel:
    """Canned replies from fixtures/<task_id>/.

    bare          -> bare.yaml (usually stale or wrong)
    context_skill -> good.yaml
    repair_loop   -> bare.yaml on turn 1, good.yaml after feedback
    Tasks without fixtures get a reply that fails every check.
    """

    name = "fake-model"
    temperature = 0.0

    def __init__(self, fixtures):
        self.fixtures = pathlib.Path(fixtures)

    def _read(self, task_id, name):
        path = self.fixtures / task_id / name
        return path.read_text(encoding="utf-8") if path.exists() else None

    def generate(self, task, condition, turn, feedback=None):
        bare = self._read(task.id, "bare.yaml")
        good = self._read(task.id, "good.yaml")
        if condition == "context_skill":
            text = good
        elif condition == "repair_loop" and turn > 1:
            text = good
        else:
            text = bare or good
        if text is None:
            text = "# no fixture for this task\n"
        return Reply(text=f"```yaml\n{text}```", tokens_in=len(task.spec) // 4, tokens_out=len(text) // 4)

    def close(self):
        pass


def read_skill(path):
    """The context file the context_skill condition adds, without its frontmatter."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    return FRONTMATTER.sub("", text, count=1).strip()


class AdkModel:
    """Real runs: an ADK LlmAgent on Gemini, one session per run.

    bare          -> the system instruction only
    context_skill -> the system instruction plus the Kubernetes 1.37 context file
    repair_loop   -> the system instruction only; later turns send the checker
                     feedback in the same session, so the model sees its own
                     earlier reply and what failed

    Gemini is reached through the Google Gen AI SDK, configured from the environment:
    GOOGLE_GENAI_USE_ENTERPRISE=true, GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION.
    Pass `llm` (an ADK BaseLlm) to run the same code path against a test double.
    """

    APP = "agent_check"
    USER = "agent-check"

    def __init__(self, name, temperature, skill_path, llm=None):
        if llm is None:
            if not name:
                raise SystemExit("set PINNED_FLASH_MODEL (or pass --model) for real runs, or use --fake-model")
            missing = [v for v in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION") if not os.environ.get(v)]
            if missing:
                raise SystemExit(f"set {', '.join(missing)} (see shared/infra/env.example) for real runs")
            os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "true")
        self.name = name or getattr(llm, "model", "test-llm")
        self.temperature = temperature
        self.skill_text = read_skill(skill_path)
        self._llm = llm
        self._loop = asyncio.new_event_loop()
        self._runners = {}
        self._session_id = None

    def instruction(self, condition):
        if condition == "context_skill":
            return SYSTEM + CONTEXT_HEADER + self.skill_text
        return SYSTEM

    def _make_llm(self):
        if self._llm is not None:
            return self._llm
        from google.adk.models.google_llm import Gemini
        from google.genai import types
        return Gemini(model=self.name, retry_options=types.HttpRetryOptions(
            attempts=6, initial_delay=2.0, max_delay=60.0, http_status_codes=[429, 500, 502, 503, 504]))

    def _runner(self, condition):
        if condition not in self._runners:
            from google.adk.agents import LlmAgent
            from google.adk.runners import InMemoryRunner
            from google.genai import types
            text = self.instruction(condition)
            agent = LlmAgent(
                name="manifest_writer",
                model=self._make_llm(),
                # A callable instruction is used as is; a string would be treated as a
                # template, and the context file contains braces.
                instruction=lambda _ctx, text=text: text,
                generate_content_config=types.GenerateContentConfig(temperature=self.temperature),
            )
            self._runners[condition] = InMemoryRunner(agent=agent, app_name=self.APP)
        return self._runners[condition]

    async def _turn(self, runner, message):
        from google.genai import types
        content = types.Content(role="user", parts=[types.Part.from_text(text=message)])
        texts, tokens_in, tokens_out = [], 0, 0
        async for event in runner.run_async(user_id=self.USER, session_id=self._session_id, new_message=content):
            if event.error_code:
                raise RuntimeError(f"model call failed: {event.error_code} {event.error_message}")
            usage = event.usage_metadata
            if usage is not None:
                tokens_in += usage.prompt_token_count or 0
                tokens_out += (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)
            if event.content and event.content.parts and not event.partial:
                texts.extend(p.text for p in event.content.parts if p.text and not p.thought)
        return Reply(text="".join(texts), tokens_in=tokens_in, tokens_out=tokens_out)

    def generate(self, task, condition, turn, feedback=None):
        runner = self._runner(condition)
        if turn == 1 or self._session_id is None:
            self._session_id = f"{task.id}-{condition}-{uuid.uuid4().hex[:8]}"
            self._loop.run_until_complete(runner.session_service.create_session(
                app_name=self.APP, user_id=self.USER, session_id=self._session_id))
            message = task.spec
        else:
            message = REPAIR_PROMPT.format(feedback=feedback or "(no details)")
        return self._loop.run_until_complete(self._turn(runner, message))

    def close(self):
        for runner in self._runners.values():
            try:
                self._loop.run_until_complete(runner.close())
            except Exception:  # best effort at shutdown
                pass
        self._loop.close()


def make_model(fake, name, temperature, fixtures, skill_path):
    if fake:
        return FakeModel(fixtures)
    return AdkModel(name, temperature, skill_path)
