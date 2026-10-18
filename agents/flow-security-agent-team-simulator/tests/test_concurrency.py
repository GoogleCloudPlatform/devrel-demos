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
Concurrency and Thread Safety Tests for Flow Commitment Ledger and Escalation Queue.
"""

import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from flow.ledger import CommitmentLedger, PowerSlot, WorkloadJob
from flow.synthetic_world import ComputeType
from flow.inbox import EscalationQueue
from flow.security_taskforce import SecurityEvaluation, SecurityVerdict, OfficerVote


class TestConcurrencyAndLedger(unittest.TestCase):
    def setUp(self):
        self.ledger = CommitmentLedger()
        self.escalations = EscalationQueue(self.ledger)

    def test_concurrent_reservations_and_commits(self):
        """Verify that concurrent reservation creations and commits maintain unbroken SHA-256 chain."""
        def worker(i: int):
            slot = PowerSlot(
                slot_id=f"slot_test_{i}",
                seller_id=f"seller_{i % 3}",
                seller_name=f"Seller {i % 3}",
                compute_type=ComputeType.GPU_H100,
                node_count=16,
                start_hour=0,
                duration_hours=6,
                price_per_node_hour_usd=1.5,
                carbon_intensity_g_per_kwh=100.0,
                total_power_kw=150.0,
            )
            job = WorkloadJob(
                job_id=f"job_test_{i}",
                buyer_id=f"buyer_{i % 3}",
                buyer_name=f"Buyer {i % 3}",
                required_compute=ComputeType.GPU_H100,
                node_count=8,
                estimated_duration_hours=4,
                max_price_per_node_hour=2.0,
                target_start_hour=0,
                deadline_hour=6,
                workload_description="Batch AI training",
                container_image="us-docker.pkg.dev/cenai/train:latest",
            )
            contract = self.ledger.create_security_hold(slot=slot, job=job)
            if i % 2 == 0:
                self.ledger.commit_reservation(
                    contract_id=contract.contract_id,
                    security_verdict="APPROVED",
                    security_reason="Test approved",
                )
            else:
                self.ledger.reject_reservation(
                    contract_id=contract.contract_id,
                    security_verdict="REJECTED",
                    security_reason="Test rejected",
                )

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(worker, range(40)))

        self.assertEqual(len(self.ledger.contracts), 40)
        # 40 holds + 40 decisions = 80 receipts
        self.assertEqual(len(self.ledger.receipts), 80)
        self.assertTrue(self.ledger.verify_audit_trail(), "Audit trail must remain valid after concurrent updates")

    def test_concurrent_escalations(self):
        """Verify that concurrent enqueuing and resolving of escalations is thread-safe."""
        def worker(i: int):
            slot = PowerSlot(
                slot_id=f"slot_esc_{i}",
                seller_id="seller_1",
                seller_name="Seller 1",
                compute_type=ComputeType.GPU_H100,
                node_count=8,
                start_hour=0,
                duration_hours=4,
                price_per_node_hour_usd=1.0,
                carbon_intensity_g_per_kwh=100.0,
                total_power_kw=100.0,
            )
            job = WorkloadJob(
                job_id=f"job_esc_{i}",
                buyer_id="buyer_1",
                buyer_name="Buyer 1",
                required_compute=ComputeType.GPU_H100,
                node_count=8,
                estimated_duration_hours=4,
                max_price_per_node_hour=1.5,
                target_start_hour=0,
                deadline_hour=4,
                workload_description="Escalation test",
                container_image="us-docker.pkg.dev/cenai/train:latest",
            )
            contract = self.ledger.create_security_hold(slot=slot, job=job)
            eval_res = SecurityEvaluation(
                contract_id=contract.contract_id,
                job_id=job.job_id,
                team_type="dual_neutral",
                votes=[],
                initial_verdicts={},
                deliberation_dialogue=[],
                consensus_verdict=SecurityVerdict.FLAGGED,
                summary_reason="Deadlock test",
            )
            item = self.escalations.enqueue(contract, eval_res)
            if i % 2 == 0:
                self.escalations.resolve(item.item_id, "APPROVE", "Resolved by admin")

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(worker, range(30)))

        self.assertEqual(len(self.escalations.items), 30)
        pending = self.escalations.list_pending()
        self.assertEqual(len(pending), 15)

    def test_parallel_simulation_in_app_state(self):
        """Verify that FlowAppState.run_simulation works with max_workers=2 and preserves audit trail."""
        from flow_cli import FlowAppState
        state = FlowAppState()
        state.reset(seed=999, preseed=False)

        res = state.run_simulation(
            days=3,
            seed=999,
            force_simulation=True,
            auto_resolve=True,
            max_workers=2,
        )

        self.assertIn("summary", res)
        self.assertTrue(len(state.ledger.contracts) > 0)
        self.assertTrue(state.ledger.verify_audit_trail(), "Audit trail must remain unbroken after parallel simulation")


if __name__ == "__main__":
    unittest.main()
