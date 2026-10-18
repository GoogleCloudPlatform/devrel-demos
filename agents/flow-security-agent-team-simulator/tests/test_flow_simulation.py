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
Unit and Integration Test Suite for Flow B2B Marketplace Simulation.
Tests all 5 core components: Synthetic World, Commitment Ledger, Dispatcher,
Security Taskforce (Multi-Model & Conflict Resolution), and Reporting Inbox.
"""

import threading
import unittest
from flow.synthetic_world import (
    SyntheticWorld,
    ComputeType,
    WorkloadRiskCategory,
    PowerSlot,
    WorkloadJob,
)
from flow.ledger import (
    CommitmentLedger,
    ReservationStatus,
    LedgerReceipt,
    ReservationContract,
)
from flow.dispatcher import DispatcherEngine, MatchCandidate
from flow.security_taskforce import (
    SecurityTaskforce,
    SecurityVerdict,
    OfficerPersonality,
)
from flow.inbox import EscalationQueue, DynamicReportingInbox
from flow.agent_platform_export import (
    get_dispatcher_agent_card,
    get_security_taskforce_agent_card,
    get_commitment_ledger_openapi_schema,
    get_agent_studio_playbook_instructions,
)


class TestSyntheticWorld(unittest.TestCase):
    def setUp(self):
        self.world = SyntheticWorld(seed=42)

    def test_enterprises_initialization(self):
        self.assertIn("kove_bank", self.world.enterprises)
        self.assertIn("stowe_architects", self.world.enterprises)

        kove = self.world.enterprises["kove_bank"]
        self.assertTrue(kove.pci_dss_enforced)
        self.assertTrue(kove.strict_sandbox_required)
        self.assertEqual(kove.base_idle_power_mw, 3.8)

        stowe = self.world.enterprises["stowe_architects"]
        self.assertFalse(stowe.pci_dss_enforced)
        self.assertEqual(stowe.base_idle_power_mw, 2.2)

    def test_frontier_labs_initialization(self):
        self.assertIn("cen_ai", self.world.frontier_labs)
        self.assertIn("laprus_ai", self.world.frontier_labs)

    def test_diurnal_power_curve(self):
        # 2 AM should be peak idle power
        kove_night = self.world.get_diurnal_idle_power_profile("kove_bank", 2)
        # 2 PM should be trough (near zero)
        kove_day = self.world.get_diurnal_idle_power_profile("kove_bank", 14)
        self.assertGreater(kove_night, 3.0)
        self.assertLess(kove_day, 0.1)

    def test_workload_queue_adversarial_coverage(self):
        jobs = self.world.generate_workload_queue(day=1)
        categories = {j.risk_category for j in jobs}
        self.assertIn(WorkloadRiskCategory.BENIGN, categories)
        self.assertIn(WorkloadRiskCategory.UNVETTED_BINARY, categories)
        self.assertIn(WorkloadRiskCategory.CROSS_TENANT_ESCAPE, categories)
        self.assertIn(WorkloadRiskCategory.COMPLIANCE_VIOLATION, categories)


class TestCommitmentLedger(unittest.TestCase):
    def setUp(self):
        self.ledger = CommitmentLedger()
        self.world = SyntheticWorld(seed=42)
        self.slots = self.world.generate_seller_power_slots(day=1)
        self.jobs = self.world.generate_workload_queue(day=1)

    def test_slot_registration(self):
        offer = self.ledger.register_power_slot(self.slots[0])
        self.assertEqual(offer.slot_id, self.slots[0].slot_id)
        self.assertIn(offer.offer_id, self.ledger.offers)

    def test_reservation_lifecycle_and_tamper_proofing(self):
        slot = self.slots[0]
        job = self.jobs[0]

        # 1. Hold
        contract = self.ledger.create_security_hold(slot, job)
        self.assertEqual(contract.status, ReservationStatus.SECURITY_HOLD)
        self.assertEqual(len(self.ledger.receipts), 1)

        # 2. Commit
        committed = self.ledger.commit_reservation(
            contract.contract_id,
            security_verdict="APPROVED",
            security_reason="Audit verified",
        )
        self.assertEqual(committed.status, ReservationStatus.COMMITTED)
        self.assertEqual(len(self.ledger.receipts), 2)

        # 3. Settle
        receipt = self.ledger.settle_reservation(contract.contract_id)
        self.assertEqual(receipt.action, "SETTLED")
        self.assertEqual(len(self.ledger.receipts), 3)

        # Audit chain verification
        self.assertTrue(self.ledger.verify_audit_trail())

        # Tamper detection
        original_hash = self.ledger.receipts[0].receipt_hash
        self.ledger.receipts[0].estimated_cost_usd = 999999.0  # Malicious alteration
        self.assertFalse(self.ledger.verify_audit_trail(), "Tampered receipt must invalidate audit trail")

    def test_concurrent_reservations_thread_safety(self):
        slot = self.slots[0]
        contracts = []

        def worker(idx):
            j = self.jobs[idx % len(self.jobs)]
            c = self.ledger.create_security_hold(slot, j)
            contracts.append(c)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(contracts), 10)
        self.assertEqual(len(self.ledger.receipts), 10)
        self.assertTrue(self.ledger.verify_audit_trail())


class TestDispatcherEngine(unittest.TestCase):
    def setUp(self):
        self.ledger = CommitmentLedger()
        self.dispatcher = DispatcherEngine(self.ledger)
        self.world = SyntheticWorld(seed=42)
        self.slots = self.world.generate_seller_power_slots(day=1)
        self.jobs = self.world.generate_workload_queue(day=1)

    def test_matchmaker_finds_compatible_pairs(self):
        matches = self.dispatcher.find_matches(self.slots, self.jobs)
        self.assertGreater(len(matches), 0)

        for m in matches:
            # Verified hard compatibility constraints
            self.assertEqual(m.slot.compute_type, m.job.required_compute)
            self.assertGreaterEqual(m.slot.node_count, m.job.node_count)
            self.assertLessEqual(m.slot.price_per_node_hour_usd, m.job.max_price_per_node_hour)
            self.assertGreater(m.score, 0.0)

    def test_dispatch_creates_security_hold(self):
        matches = self.dispatcher.find_matches(self.slots, self.jobs)
        contract = self.dispatcher.dispatch_match(matches[0])
        self.assertEqual(contract.status, ReservationStatus.SECURITY_HOLD)
        self.assertIn(contract.contract_id, self.ledger.contracts)


class TestSecurityTaskforce(unittest.TestCase):
    def setUp(self):
        self.world = SyntheticWorld(seed=42)
        self.ledger = CommitmentLedger()
        self.security = SecurityTaskforce(
            ledger=self.ledger,
            enterprises=self.world.enterprises,
            project_id="flow-simulation-sandbox",
        )
        self.slots = {s.slot_id: s for s in self.world.generate_seller_power_slots(day=1)}
        self.jobs = {j.job_id: j for j in self.world.generate_workload_queue(day=1)}

    def test_approves_benign_workload_on_stowe(self):
        slot = self.slots["slot_stowe_d1_01"]
        job = next(j for j in self.jobs.values() if j.risk_category == WorkloadRiskCategory.BENIGN)

        contract = self.ledger.create_security_hold(slot, job)
        evaluation = self.security.evaluate_reservation(
            contract=contract,
            job=job,
            slot=slot,
            force_simulation=True,
        )

        self.assertEqual(evaluation.consensus_verdict, SecurityVerdict.APPROVED)
        self.assertFalse(evaluation.is_deadlocked)
        self.assertEqual(contract.status, ReservationStatus.COMMITTED)

    def test_rejects_cross_tenant_memory_snoop(self):
        slot = self.slots["slot_kove_d1_01"]
        job = next(j for j in self.jobs.values() if j.risk_category == WorkloadRiskCategory.CROSS_TENANT_ESCAPE)

        contract = self.ledger.create_security_hold(slot, job)
        evaluation = self.security.evaluate_reservation(
            contract=contract,
            job=job,
            slot=slot,
            force_simulation=True,
        )

        self.assertEqual(evaluation.consensus_verdict, SecurityVerdict.REJECTED)
        self.assertEqual(contract.status, ReservationStatus.REJECTED)

    def test_escalates_on_model_deadlock(self):
        # Ambiguous or compliance-sensitive workload with divergent council:
        # Officer Alpha (Strict) rejects; Officer Beta (Pragmatic) approves -> Deadlock!
        slot = self.slots["slot_kove_d1_03"]
        job = next(j for j in self.jobs.values() if j.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE)

        contract = self.ledger.create_security_hold(slot, job)
        officers = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-flash", "personality": "estj"},
            {"officer_id": "officer_2", "model_name": "gemini-3.8-flash", "personality": "infp"},
        ]
        evaluation = self.security.evaluate_reservation(
            contract=contract,
            job=job,
            slot=slot,
            officers=officers,
            force_simulation=True,
        )

        self.assertTrue(evaluation.is_deadlocked)
        self.assertTrue(evaluation.escalated_to_human)
        self.assertEqual(contract.status, ReservationStatus.ESCALATED)


class TestEscalationQueueAndReportingInbox(unittest.TestCase):
    def setUp(self):
        self.world = SyntheticWorld(seed=42)
        self.ledger = CommitmentLedger()
        self.security = SecurityTaskforce(self.ledger, self.world.enterprises)
        self.escalations = EscalationQueue(self.ledger)
        self.inbox = DynamicReportingInbox(self.ledger, self.escalations)
        self.slots = self.world.generate_seller_power_slots(day=1)
        self.jobs = self.world.generate_workload_queue(day=1)

    def test_escalation_queue_enqueue_and_resolve(self):
        slot = self.slots[2]
        job = self.jobs[4]  # compliance violation
        contract = self.ledger.create_security_hold(slot, job)
        evaluation = self.security.evaluate_reservation(
            contract=contract,
            job=job,
            slot=slot,
            force_simulation=True,
        )

        item = self.escalations.enqueue(contract, evaluation)
        self.assertEqual(len(self.escalations.list_pending()), 1)

        resolved_contract = self.escalations.resolve(
            item_id=item.item_id,
            human_verdict="REJECT",
            human_notes="Violates PCI-DSS egress rules.",
        )
        self.assertEqual(resolved_contract.status, ReservationStatus.REJECTED)
        self.assertEqual(len(self.escalations.list_pending()), 0)

    def test_report_generation(self):
        seller_rep = self.inbox.generate_seller_report("kove_bank")
        self.assertIn("Flow Seller Statement", seller_rep)

        buyer_rep = self.inbox.generate_buyer_report("cen_ai")
        self.assertIn("Flow Buyer Compute Statement", buyer_rep)

        admin_rep = self.inbox.generate_master_admin_report()
        self.assertIn("Flow Master Administration", admin_rep)


class TestAgentPlatformExport(unittest.TestCase):
    def test_agent_cards_and_openapi(self):
        card_disp = get_dispatcher_agent_card()
        self.assertEqual(card_disp["name"], "flow-dispatcher-agent")
        self.assertTrue(card_disp["capabilities"]["human_in_the_loop"])

        card_sec = get_security_taskforce_agent_card()
        self.assertEqual(card_sec["name"], "flow-security-taskforce-officer")
        self.assertTrue(card_sec["capabilities"]["multi_model_consensus"])

        openapi = get_commitment_ledger_openapi_schema()
        self.assertEqual(openapi["openapi"], "3.0.0")
        self.assertIn("/api/slots", openapi["paths"])

        instructions = get_agent_studio_playbook_instructions()
        self.assertIn("dispatcher_instructions", instructions)
        self.assertIn("security_officer_instructions", instructions)


if __name__ == "__main__":
    unittest.main()
