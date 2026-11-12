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

"""Offline self-test: runs the Ep1 tasks with the fake model and checks the pipeline end to end."""
import csv
import os
import tempfile
import unittest

from agent_check.checkers import check_assertions, parse_docs
from agent_check.cli import main
from agent_check.stale_apis import find_stale


class PipelineTest(unittest.TestCase):
    def test_ep01_fake_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "agent-check.csv")
            self.assertEqual(main(["--ep", "01", "--fake-model", "--runs", "2", "--out", out]), 0)
            with open(out, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 3 * 3 * 2)  # tasks x conditions x runs
        by = {(r["task_id"], r["condition"]): r for r in rows}
        tasks = {r["task_id"] for r in rows}
        for task in tasks:
            self.assertEqual(by[(task, "bare")]["passed"], "false", task)
            self.assertEqual(by[(task, "context_skill")]["passed"], "true", task)
            self.assertEqual(by[(task, "repair_loop")]["passed"], "true", task)
            self.assertEqual(by[(task, "repair_loop")]["turns"], "2", task)
            self.assertEqual(by[(task, "bare")]["model"], "fake-model")
        self.assertTrue(any(int(by[(t, "bare")]["stale_api_hits"]) > 0 for t in tasks))


class FakeModelStaysOfflineTest(unittest.TestCase):
    def test_fake_model_ignores_kube_context_from_env(self):
        os.environ["KUBE_CONTEXT"] = "some-real-cluster"
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "agent-check.csv")
                main(["--ep", "01", "--fake-model", "--runs", "1", "--out", out])
                with open(out, newline="", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
            self.assertTrue(all("server_dry_run" in r["checks_skipped"] for r in rows))
        finally:
            del os.environ["KUBE_CONTEXT"]


class UnnamedTasksTest(unittest.TestCase):
    """ep01-unnamed.yaml checks the same outcomes as ep01.yaml: the good fixtures pass its
    assertions and the stale ones don't."""

    def test_assertions_match_the_named_round(self):
        import pathlib
        from agent_check.tasks import load_tasks
        root = pathlib.Path(__file__).resolve().parents[1]
        tasks = load_tasks(root / "tasks" / "ep01-unnamed.yaml")
        self.assertEqual(len(tasks), 3)
        for task in tasks:
            fixture = task.id.replace("-unnamed", "")
            spec = next(c["assert"] for c in task.checks if isinstance(c, dict) and "assert" in c)
            good = parse_docs((root / "fixtures" / fixture / "good.yaml").read_text())
            bare = parse_docs((root / "fixtures" / fixture / "bare.yaml").read_text())
            self.assertEqual(check_assertions(good, spec).status, "pass", task.id)
            self.assertEqual(check_assertions(bare, spec).status, "fail", task.id)
            self.assertNotIn("sidecar", task.spec.lower().replace("log shipper", ""), task.id)
            self.assertNotIn("image volume", task.spec.lower(), task.id)
            self.assertNotIn("user namespace", task.spec.lower(), task.id)
            self.assertNotIn("hostusers", task.spec.lower(), task.id)


class CheckerTest(unittest.TestCase):
    def test_removed_api_is_flagged(self):
        docs = parse_docs("apiVersion: policy/v1beta1\nkind: PodSecurityPolicy\nmetadata: {name: x}\n")
        self.assertTrue(find_stale(docs))

    def test_current_api_is_clean(self):
        docs = parse_docs("apiVersion: scheduling.k8s.io/v1beta1\nkind: PodGroup\nmetadata: {name: g}\n")
        self.assertEqual(find_stale(docs), [])

    def test_guaranteed_assertion(self):
        pod = """
apiVersion: v1
kind: Pod
metadata: {name: p}
spec:
  containers:
  - name: c
    image: busybox
    resources:
      limits: {cpu: "4", memory: 8Gi}
"""
        self.assertEqual(check_assertions(parse_docs(pod), {"qos_class": "Guaranteed", "integer_cpu": True}).status, "pass")
        burst = pod.replace('cpu: "4"', 'cpu: 1500m')
        self.assertEqual(check_assertions(parse_docs(burst), {"qos_class": "Guaranteed", "integer_cpu": True}).status, "fail")


if __name__ == "__main__":
    unittest.main()
