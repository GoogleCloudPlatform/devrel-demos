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

"""Offline test of the ADK adapter: a real LlmAgent and InMemoryRunner, with a test
double in place of Gemini. Skipped when google-adk isn't installed."""
import csv
import json
import os
import pathlib
import tempfile
import unittest

try:
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types
    HAVE_ADK = True
except ImportError:  # the offline self-test runs without google-adk
    HAVE_ADK = False

from agent_check.checkers import CheckContext
from agent_check.models import AdkModel
from agent_check.runner import run_tasks
from agent_check.tasks import load_tasks

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"
SKILL = ROOT.parent / "skills" / "k8s-1.37" / "SKILL.md"
REQUESTS = []  # every LlmRequest the test double received
TASK_BY_NAME = {"log-demo": "ep01-sidecar", "weights-demo": "ep01-image-volume", "sandboxed-shell": "ep01-userns"}

if HAVE_ADK:
    class ScriptedLlm(BaseLlm):
        """Answers like the fake model, but through ADK: the stale YAML first, the good
        YAML when the context file is in the system instruction or after feedback."""

        @classmethod
        def supported_models(cls):
            return [r"scripted-.*"]

        async def generate_content_async(self, llm_request, stream=False):
            REQUESTS.append(llm_request)
            system = str(llm_request.config.system_instruction or "")
            texts = [p.text for c in llm_request.contents for p in (c.parts or []) if p.text]
            task = next(t for name, t in TASK_BY_NAME.items() if any(name in x for x in texts))
            good = "Reference notes for Kubernetes 1.37" in system or any("failed these checks" in x for x in texts)
            body = (FIXTURES / task / ("good.yaml" if good else "bare.yaml")).read_text(encoding="utf-8")
            yield LlmResponse(
                content=types.Content(role="model", parts=[types.Part.from_text(text=f"```yaml\n{body}```")]),
                usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=100, candidates_token_count=40),
            )


@unittest.skipUnless(HAVE_ADK, "google-adk not installed")
class AdkAdapterTest(unittest.TestCase):
    def test_conditions_through_adk(self):
        REQUESTS.clear()
        model = AdkModel("", 0.0, SKILL, llm=ScriptedLlm(model="scripted-flash"))
        tasks = load_tasks(ROOT / "tasks" / "ep01.yaml")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "agent-check.csv")
            try:
                run_tasks("01", tasks, ["bare", "context_skill", "repair_loop"], 1, model, CheckContext(), 5, out)
            finally:
                model.close()
            with open(out, newline="", encoding="utf-8") as f:
                rows = {(r["task_id"], r["condition"]): r for r in csv.DictReader(f)}
            with open(os.path.join(tmp, "agent-check-details.jsonl"), encoding="utf-8") as f:
                details = [json.loads(line) for line in f]
        # One details line per turn: 3 bare + 3 context_skill + 6 repair_loop turns.
        self.assertEqual(len(details), 12)
        first = next(d for d in details if d["task_id"] == "ep01-sidecar" and d["condition"] == "bare")
        self.assertIn("```yaml", first["reply"])
        self.assertTrue(any(c["name"] == "stale_apis" and c["status"] == "fail" for c in first["checks"]))
        self.assertEqual(len(rows), 9)
        for task in TASK_BY_NAME.values():
            self.assertEqual(rows[(task, "bare")]["passed"], "false", task)
            self.assertEqual(rows[(task, "context_skill")]["passed"], "true", task)
            self.assertEqual(rows[(task, "repair_loop")]["passed"], "true", task)
            self.assertEqual(rows[(task, "repair_loop")]["turns"], "2", task)
            self.assertEqual(rows[(task, "repair_loop")]["tokens_in"], "200", task)
            self.assertEqual(rows[(task, "bare")]["model"], "scripted-flash")
        # The repair loop's second request carries the first reply and the feedback (same session).
        second_turns = [r for r in REQUESTS if len(r.contents) >= 3]
        self.assertEqual(len(second_turns), 3)
        # Only the context_skill condition sends the context file.
        with_skill = [r for r in REQUESTS if "Reference notes" in str(r.config.system_instruction)]
        self.assertEqual(len(with_skill), 3)
        self.assertEqual(float(rows[("ep01-sidecar", "bare")]["temperature"]), 0.0)

    def test_context_file_braces_are_not_templated(self):
        model = AdkModel("", 0.0, SKILL, llm=ScriptedLlm(model="scripted-flash"))
        try:
            self.assertIn("Writing manifests for Kubernetes 1.37", model.instruction("context_skill"))
            self.assertNotIn("name: kubernetes-1-37-manifests", model.instruction("context_skill"))
            self.assertNotIn("Reference notes", model.instruction("bare"))
        finally:
            model.close()


class RealModelGuardTest(unittest.TestCase):
    def test_real_runs_need_project_settings(self):
        env = {k: os.environ.pop(k) for k in ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION") if k in os.environ}
        try:
            with self.assertRaises(SystemExit):
                AdkModel("gemini-3.8-flash", 0.0, SKILL)
            with self.assertRaises(SystemExit):
                AdkModel("", 0.0, SKILL)
        finally:
            os.environ.update(env)


if __name__ == "__main__":
    unittest.main()
