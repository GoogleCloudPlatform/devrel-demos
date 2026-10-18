# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Unit and integration tests for Dynamic Council Benchmark and Escalation Queue API.
Validates PRD Day 11–13, Day 14–15, and Day 19–20 specifications.
"""

import json
import unittest
from flow.synthetic_world import SyntheticWorld, WorkloadRiskCategory
from flow.ledger import CommitmentLedger, ReservationStatus
from flow.security_taskforce import SecurityTaskforce, SecurityVerdict
from flow.inbox import EscalationQueue, DynamicReportingInbox
from flow.benchmark import FlowBenchmarkRunner


class TestBenchmarkAndEscalation(unittest.TestCase):
    def setUp(self):
        self.world = SyntheticWorld(seed=42)
        self.ledger = CommitmentLedger()
        self.slots = self.world.generate_seller_power_slots(day=1)
        for s in self.slots:
            self.ledger.register_power_slot(s)
        self.workloads = self.world.generate_workload_queue(day=1)
        self.escalations = EscalationQueue(self.ledger)
        self.inbox = DynamicReportingInbox(self.ledger, self.escalations)
        self.taskforce = SecurityTaskforce(self.ledger, self.world.enterprises)

    def test_ambiguous_workloads_exist(self):
        categories = {w.risk_category for w in self.workloads}
        self.assertIn(WorkloadRiskCategory.AMBIGUOUS_DUAL_USE, categories)
        self.assertIn(WorkloadRiskCategory.UNVERIFIED_DEPENDENCY, categories)
        self.assertIn(WorkloadRiskCategory.CACHE_PURGE_UNCERTAIN, categories)
        self.assertIn(WorkloadRiskCategory.BORDERLINE_EGRESS, categories)

    def test_deadlock_and_escalation_flow(self):
        # Pick ambiguous dual use job
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        # Council with divergent personalities -> should deadlock
        officers = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-flash", "personality": "estj"},
            {"officer_id": "officer_2", "model_name": "gemini-3.8-flash", "personality": "infp"},
        ]
        evaluation = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=officers, force_simulation=True
        )
        self.assertTrue(evaluation.is_deadlocked)
        self.assertTrue(evaluation.escalated_to_human)

        # Enqueue in human escalation queue
        item = self.escalations.enqueue(contract, evaluation)
        self.assertIn(item.item_id, self.escalations.items)
        self.assertEqual(len(self.escalations.list_pending()), 1)

        # Human reviews and overrides with APPROVE
        resolved_contract = self.escalations.resolve(
            item.item_id, "APPROVE", "Human officer verified temporary gVisor sandbox exception"
        )
        self.assertEqual(resolved_contract.status, ReservationStatus.COMMITTED)
        self.assertTrue(item.resolved)
        self.assertEqual(item.human_verdict, "APPROVE")
        self.assertEqual(len(self.escalations.list_pending()), 0)

        # Verify receipt was generated
        self.assertTrue(self.ledger.verify_audit_trail())

    def test_benchmark_runner_dynamic_councils(self):
        runner = FlowBenchmarkRunner(seed=42)
        bench_data = runner.run_benchmark(force_simulation=True)
        results = bench_data["results"]

        # Default council is 2-officer Gemini 3.8 Flash Neutral
        self.assertEqual(len(results), 1)
        council_key = list(results.keys())[0]
        self.assertIn("2-Officer Council", council_key)

        res = results[council_key]
        self.assertEqual(res["false_negatives"], 0)
        self.assertEqual(res["precision"], 1.0)
        self.assertEqual(res["recall"], 1.0)

        # Multi-council comparative benchmark
        councils = [
            [
                {"officer_id": "o1", "model_name": "gemini-3.8-flash", "personality": "neutral"},
                {"officer_id": "o2", "model_name": "gemini-3.8-flash", "personality": "neutral"},
            ],
            [
                {"officer_id": "o1", "model_name": "gemini-3.8-flash", "personality": "estj"},
                {"officer_id": "o2", "model_name": "claude-opus-5", "personality": "infp"},
                {"officer_id": "o3", "model_name": "gpt-oss-120b-maas", "personality": "neutral"},
            ],
        ]
        multi_bench = runner.run_benchmark(force_simulation=True, councils=councils)
        self.assertEqual(len(multi_bench["results"]), 2)

        md = runner.generate_markdown_report(multi_bench)
        self.assertIn("Dynamic Multi-Model Security Council Benchmark", md)
        self.assertIn("Executive Summary Table", md)

if __name__ == "__main__":
    unittest.main()
