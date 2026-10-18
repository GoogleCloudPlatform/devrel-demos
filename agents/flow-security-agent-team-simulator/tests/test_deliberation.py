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

import unittest
import sys
from unittest.mock import MagicMock, patch

if "anthropic" not in sys.modules:
    mock_anthropic = MagicMock()
    sys.modules["anthropic"] = mock_anthropic

if "google" not in sys.modules:
    mock_google = MagicMock()
    mock_google.genai.types.GenerateContentConfig.side_effect = lambda **kw: MagicMock(**kw)
    sys.modules["google"] = mock_google
    sys.modules["google.genai"] = mock_google.genai
    sys.modules["google.genai.types"] = mock_google.genai.types

from flow.synthetic_world import (
    SyntheticWorld,
    WorkloadRiskCategory,
)
from flow.ledger import (
    CommitmentLedger,
    ReservationStatus,
)
from flow.security_taskforce import (
    SecurityTaskforce,
    JointDecision,
    SecurityVerdict,
    OfficerPersonality,
    format_model_label,
    ModelQuotaExhaustedError,
    ModelInferenceError,
)

class TestDeliberationEngine(unittest.TestCase):
    def setUp(self):
        self.world = SyntheticWorld(seed=42)
        self.ledger = CommitmentLedger()
        self.slots = self.world.generate_seller_power_slots(day=1)
        for s in self.slots:
            self.ledger.register_power_slot(s)
        self.workloads = self.world.generate_workload_queue(day=1)
        self.taskforce = SecurityTaskforce(self.ledger, self.world.enterprises)

    def test_deliberation_on_clean_job_unanimous_allow(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        tri_council = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "gpt-5-frontier", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=tri_council, force_simulation=True
        )
        
        # Verify initial decisions are preserved
        self.assertEqual(len(res.votes), 3)
        for vote in res.votes:
            self.assertEqual(vote.verdict, SecurityVerdict.APPROVED)
        
        # Verify deliberation dialogue was generated
        self.assertTrue(len(res.deliberation_dialogue) >= 2)
        for msg in res.deliberation_dialogue:
            self.assertTrue(msg.speaker_id)
            self.assertTrue(msg.speaker_model)
            self.assertTrue(msg.message)
        
        # Verify joint consensus
        self.assertEqual(res.joint_decision, JointDecision.ALLOW)
        self.assertIn("Unanimous alignment", res.joint_rationale)
        self.assertEqual(res.consensus_verdict, SecurityVerdict.APPROVED)
        self.assertFalse(res.is_deadlocked)

    def test_deliberation_on_privileged_exploit_unanimous_deny(self):
        job = next(j for j in self.workloads if j.risk_category in (WorkloadRiskCategory.CROSS_TENANT_ESCAPE, WorkloadRiskCategory.PRIVILEGED_CONTAINER))
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        tri_council = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "gpt-5-frontier", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=tri_council, force_simulation=True
        )
        
        # Verify initial decisions
        self.assertEqual(len(res.votes), 3)
        # Verify joint consensus is DENY
        self.assertEqual(res.joint_decision, JointDecision.DENY)
        self.assertEqual(res.consensus_verdict, SecurityVerdict.REJECTED)
        self.assertTrue(len(res.deliberation_dialogue) >= 2)
        self.assertFalse(res.is_deadlocked)

    def test_deliberation_on_ambiguous_policy_deadlock_escalate(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        divergent_council = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-flash", "personality": "estj"},
            {"officer_id": "officer_2", "model_name": "gemini-3.8-flash", "personality": "infp"},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=divergent_council, force_simulation=True
        )
        
        # Check initial votes have disagreement (both APPROVED and FLAGGED/REJECTED)
        verdicts = {v.verdict for v in res.votes}
        self.assertTrue(len(verdicts) > 1, f"Expected split votes, got: {verdicts}")

        # Check joint consensus is ESCALATE
        self.assertEqual(res.joint_decision, JointDecision.ESCALATE)
        self.assertTrue(res.is_deadlocked)
        self.assertTrue(res.escalated_to_human)
        self.assertTrue(len(res.deliberation_dialogue) >= 2)
        self.assertIn("Council debate resulted in a principled policy impasse", res.joint_rationale)

    def test_deliberation_tri_model(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        tri_council = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "gpt-5-frontier", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=tri_council, force_simulation=True
        )
        self.assertEqual(len(res.votes), 3)
        self.assertEqual(res.joint_decision, JointDecision.ALLOW)
        models = [v.model_name for v in res.votes]
        self.assertEqual(models, ["gemini-3.8-pro", "claude-opus-5", "gpt-5-frontier"])

    def test_neutral_council_no_personality(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        dual_flash_neutral = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
        ]
        res_dual = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=dual_flash_neutral, force_simulation=True
        )
        self.assertEqual(len(res_dual.votes), 2)
        for v in res_dual.votes:
            self.assertEqual(v.personality.value, "neutral")

        tri_neutral = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "gpt-5-frontier", "personality": OfficerPersonality.NEUTRAL},
        ]
        res_tri = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=tri_neutral, force_simulation=True
        )
        self.assertEqual(len(res_tri.votes), 3)
        for v in res_tri.votes:
            self.assertEqual(v.personality.value, "neutral")

    def test_neutral_council_ambiguous_dual_use_consensus(self):
        # On non-PCI host with AMD SEV-SNP, tri-model arbitrates consensus ALLOW under quota
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE)
        slot = next(s for s in self.slots if "Stowe" in s.seller_name)
        contract = self.ledger.create_security_hold(slot, job)

        tri_neutral = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "gpt-5-frontier", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=tri_neutral, force_simulation=True
        )
        self.assertEqual(res.joint_decision, JointDecision.ALLOW)
        self.assertFalse(res.is_deadlocked)
        self.assertIn("Autonomous Resolution", res.joint_rationale)
        self.assertEqual(len(res.deliberation_dialogue), 3)

    def test_neutral_council_unverified_dependency_escalation(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.UNVERIFIED_DEPENDENCY)
        slot_non_pci = next(s for s in self.slots if "Stowe" in s.seller_name)
        contract = self.ledger.create_security_hold(slot_non_pci, job)

        tri_neutral = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "gpt-5-frontier", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot_non_pci, officers=tri_neutral, force_simulation=True
        )
        self.assertEqual(res.joint_decision, JointDecision.ESCALATE)
        self.assertTrue(res.is_deadlocked)
        self.assertTrue(res.escalated_to_human)
        self.assertIn("Unanimous Consensus", res.joint_rationale)

        slot_pci = next(s for s in self.slots if "Kove" in s.seller_name)
        contract_pci = self.ledger.create_security_hold(slot_pci, job)
        res_pci = self.taskforce.evaluate_reservation(
            contract_pci, job, slot_pci, officers=tri_neutral, force_simulation=True
        )
        self.assertEqual(res_pci.joint_decision, JointDecision.DENY)

    def test_neutral_council_differentiated_escalations(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE)
        slot = next(s for s in self.slots if "Stowe" in s.seller_name)

        # Dual Flash: fast tier consensus ALLOW
        council_dual_flash = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
        ]
        contract_e = self.ledger.create_security_hold(slot, job)
        res_e = self.taskforce.evaluate_reservation(contract_e, job, slot, officers=council_dual_flash, force_simulation=True)
        self.assertEqual(res_e.joint_decision, JointDecision.ALLOW)

        # Flash + Pro: multi-tier deadlock ESCALATE
        council_flash_pro = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
        ]
        contract_f = self.ledger.create_security_hold(slot, job)
        res_f = self.taskforce.evaluate_reservation(contract_f, job, slot, officers=council_flash_pro, force_simulation=True)
        self.assertEqual(res_f.joint_decision, JointDecision.ESCALATE)

        # Pro + Claude Opus: cross-vendor deadlock ESCALATE
        council_pro_claude = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
        ]
        contract_g = self.ledger.create_security_hold(slot, job)
        res_g = self.taskforce.evaluate_reservation(contract_g, job, slot, officers=council_pro_claude, force_simulation=True)
        self.assertEqual(res_g.joint_decision, JointDecision.ESCALATE)

    def test_format_model_label_claude_family(self):
        self.assertEqual(format_model_label("claude-opus-5"), "Claude Opus 5")
        self.assertEqual(format_model_label("claude-opus-5.5"), "Claude Opus 5.5")
        self.assertEqual(format_model_label("claude-sonnet-5"), "Claude Sonnet 5")
        self.assertEqual(format_model_label("claude-sonnet-5.5"), "Claude Sonnet 5.5")

    def test_custom_council_with_claude_models(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE)
        slot = next(s for s in self.slots if "Stowe" in s.seller_name)
        contract = self.ledger.create_security_hold(slot, job)

        custom_officers = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-sonnet-5.5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "gpt-5-frontier", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, force_simulation=True, custom_officers=custom_officers
        )
        self.assertEqual(len(res.votes), 3)
        self.assertEqual(res.joint_decision, JointDecision.ALLOW)
        self.assertEqual(res.votes[1].model_name, "claude-sonnet-5.5")
        self.assertIn("Claude Sonnet 5.5", res.votes[1].rationale)
        self.assertIn("telemetry triage", res.votes[1].rationale)

    def test_team_g_deliberation_dynamic_claude_label(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BORDERLINE_EGRESS)
        slot = next(s for s in self.slots if "Stowe" in s.seller_name)
        contract = self.ledger.create_security_hold(slot, job)

        custom_officers = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5.5", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, force_simulation=True, custom_officers=custom_officers
        )
        self.assertEqual(res.joint_decision, JointDecision.ESCALATE)
        self.assertIn("Claude Opus 5.5", res.joint_rationale)
        dialogue_models = [m.speaker_model for m in res.deliberation_dialogue]
        self.assertIn("claude-opus-5.5", dialogue_models)


    def test_format_model_label_openai_family(self):
        self.assertEqual(format_model_label("openai-o3"), "OpenAI o3")
        self.assertEqual(format_model_label("o3"), "OpenAI o3")
        self.assertEqual(format_model_label("openai-o3-mini"), "OpenAI o3-mini")
        self.assertEqual(format_model_label("o3-mini"), "OpenAI o3-mini")
        self.assertEqual(format_model_label("03-mini"), "OpenAI o3-mini")
        self.assertEqual(format_model_label("03"), "OpenAI o3")
        self.assertEqual(format_model_label("gpt-5-frontier"), "GPT-5 Frontier")

    def test_custom_council_with_openai_o3(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE)
        slot = next(s for s in self.slots if "Stowe" in s.seller_name)
        contract = self.ledger.create_security_hold(slot, job)

        custom_officers = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "openai-o3", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, force_simulation=True, custom_officers=custom_officers
        )
        self.assertEqual(len(res.votes), 3)
        self.assertEqual(res.joint_decision, JointDecision.ALLOW)
        self.assertEqual(res.votes[2].model_name, "openai-o3")
        self.assertIn("OpenAI o3", res.votes[2].rationale)
        self.assertIn("deep-reasoning verification", res.votes[2].rationale)
        
        # Verify dialogue has o3 proposal
        dialogue_text = " ".join(m.message for m in res.deliberation_dialogue)
        self.assertIn("OpenAI o3", dialogue_text)
        self.assertIn("Mathematical modeling", dialogue_text)

    def test_custom_council_with_openai_o3_mini(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE)
        slot = next(s for s in self.slots if "Stowe" in s.seller_name)
        contract = self.ledger.create_security_hold(slot, job)

        custom_officers = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-pro", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5.5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_3", "model_name": "openai-o3-mini", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, force_simulation=True, custom_officers=custom_officers
        )
        self.assertEqual(len(res.votes), 3)
        self.assertEqual(res.joint_decision, JointDecision.ALLOW)
        self.assertEqual(res.votes[2].model_name, "openai-o3-mini")
        self.assertIn("OpenAI o3-mini", res.votes[2].rationale)
        self.assertIn("static verification", res.votes[2].rationale)

        # Verify dialogue has o3-mini proposal
        dialogue_text = " ".join(m.message for m in res.deliberation_dialogue)
        self.assertIn("OpenAI o3-mini", dialogue_text)
        self.assertIn("Static analysis", dialogue_text)

    def test_dynamic_council_size_validation(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        # 1 officer must raise ValueError
        with self.assertRaises(ValueError):
            self.taskforce.evaluate_reservation(
                contract, job, slot,
                officers=[{"officer_id": "1", "model_name": "gemini-3.8-flash", "personality": "neutral"}],
                force_simulation=True
            )

        # 4 officers must raise ValueError
        with self.assertRaises(ValueError):
            self.taskforce.evaluate_reservation(
                contract, job, slot,
                officers=[{"officer_id": str(i), "model_name": "gemini-3.8-flash", "personality": "neutral"} for i in range(4)],
                force_simulation=True
            )

    def test_default_headless_council_structure(self):
        from flow.security_taskforce import DEFAULT_HEADLESS_COUNCIL
        self.assertEqual(len(DEFAULT_HEADLESS_COUNCIL), 2)
        self.assertEqual(DEFAULT_HEADLESS_COUNCIL[0]["model_name"], "gemini-3.8-flash")
        self.assertEqual(DEFAULT_HEADLESS_COUNCIL[1]["model_name"], "gemini-3.8-flash")
        self.assertEqual(DEFAULT_HEADLESS_COUNCIL[0]["personality"], OfficerPersonality.NEUTRAL)
        self.assertEqual(DEFAULT_HEADLESS_COUNCIL[1]["personality"], OfficerPersonality.NEUTRAL)

    def test_evaluate_dynamic_2_officer_council(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        officers = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "model_name": "claude-opus-5", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=officers, force_simulation=True
        )
        self.assertEqual(res.council_size, 2)
        self.assertEqual(len(res.votes), 2)
        self.assertEqual(res.votes[0].model_name, "gemini-3.8-flash")
        self.assertEqual(res.votes[1].model_name, "claude-opus-5")

    def test_evaluate_dynamic_3_officer_council(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        officers = [
            {"officer_id": "1", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "2", "model_name": "claude-sonnet-5", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "3", "model_name": "openai/gpt-oss-120b-maas", "personality": OfficerPersonality.NEUTRAL},
        ]
        res = self.taskforce.evaluate_reservation(
            contract, job, slot, officers=officers, force_simulation=True
        )
        self.assertEqual(res.council_size, 3)
        self.assertEqual(len(res.votes), 3)

    @patch("time.sleep", return_value=None)
    def test_quota_exhaustion_raises_error_without_failover_cascade(self, mock_sleep):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        officer = {"officer_id": "test_off", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL}

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED: Quota exceeded")

        with patch.object(self.taskforce, "_get_genai_client", return_value=mock_client):
            with self.assertRaises(ModelQuotaExhaustedError) as ctx:
                self.taskforce._evaluate_with_officer(
                    officer=officer,
                    contract=contract,
                    job=job,
                    slot=slot,
                    enterprise=None,
                    force_simulation=False,
                )
            self.assertIn("Quota exhaustion on Agent Platform model 'gemini-3.8-flash'", str(ctx.exception))
            self.assertIn("Failover cascade is prohibited", str(ctx.exception))

    @patch("time.sleep", return_value=None)
    def test_claude_quota_exhaustion_raises_error_without_failover(self, mock_sleep):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        officer = {"officer_id": "test_claude", "model_name": "claude-sonnet-5", "personality": OfficerPersonality.NEUTRAL}

        with patch("anthropic.AnthropicVertex") as mock_vertex_cls:
            mock_inst = MagicMock()
            mock_inst.messages.create.side_effect = Exception("429 rate_limit_error")
            mock_vertex_cls.return_value = mock_inst

            with self.assertRaises(ModelQuotaExhaustedError) as ctx:
                self.taskforce._evaluate_with_officer(
                    officer=officer,
                    contract=contract,
                    job=job,
                    slot=slot,
                    enterprise=None,
                    force_simulation=False,
                )
            self.assertIn("Quota exhaustion on Anthropic model 'claude-sonnet-5'", str(ctx.exception))
            self.assertIn("Failover cascade is prohibited", str(ctx.exception))

    @patch("time.sleep", return_value=None)
    def test_deliberation_quota_exhaustion_raises_error_without_failover(self, mock_sleep):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        officers = [
            {"officer_id": "1", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "2", "model_name": "gemini-3.8-flash", "personality": OfficerPersonality.NEUTRAL},
        ]

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")

        with patch.object(self.taskforce, "_get_genai_client", return_value=mock_client):
            with self.assertRaises(ModelQuotaExhaustedError) as ctx:
                self.taskforce._conduct_deliberation(
                    officers=officers,
                    initial_votes=[],
                    contract=contract,
                    job=job,
                    slot=slot,
                    enterprise=None,
                    force_simulation=False,
                )
            self.assertIn("Quota exhaustion during council deliberation on Agent Platform model 'gemini-3.8-flash'", str(ctx.exception))
            self.assertIn("Failover cascade is prohibited", str(ctx.exception))

    def test_dynamic_council_deliberation_preserves_officer_count_and_personality(self):
        job = next(j for j in self.workloads if j.risk_category == WorkloadRiskCategory.BENIGN)
        slot = self.slots[0]
        contract = self.ledger.create_security_hold(slot, job)

        officers = [
            {"officer_id": "officer_1", "name": "Officer 1", "model_name": "gemini-3.7-flash", "personality": OfficerPersonality.NEUTRAL},
            {"officer_id": "officer_2", "name": "Officer 2", "model_name": "gemini-3.7-flash", "personality": OfficerPersonality.NEUTRAL},
        ]

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''{
            "dialogue": [
                {"speaker_id": "officer_1", "speaker_model": "gemini-3.7-flash", "speaker_personality": "neutral", "message": "Host boundary invariants verified. No privilege elevation."},
                {"speaker_id": "officer_2", "speaker_model": "gemini-3.7-flash", "speaker_personality": "neutral", "message": "Concur with Officer 1. Container boundaries comply with baseline."}
            ],
            "joint_decision": "ALLOW",
            "joint_rationale": "Objective consensus: Workload complies with host invariants."
        }'''
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(self.taskforce, "_get_genai_client", return_value=mock_client):
            dialogue, joint_decision, joint_rationale = self.taskforce._conduct_deliberation(
                officers=officers,
                initial_votes=[],
                contract=contract,
                job=job,
                slot=slot,
                enterprise=None,
                force_simulation=False,
            )

        # Check call arguments to ensure system_instruction used dynamic prompt
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        config = call_kwargs.get("config")
        if hasattr(config, "system_instruction") and isinstance(config.system_instruction, str):
            sys_inst = config.system_instruction
        else:
            from google.genai import types
            sys_inst = types.GenerateContentConfig.call_args.kwargs.get("system_instruction", "")
        self.assertIn("EXACTLY 2 officers", sys_inst)
        self.assertIn("officer_1", sys_inst)
        self.assertIn("officer_2", sys_inst)
        self.assertNotIn("ESTJ", sys_inst)
        self.assertNotIn("INFP", sys_inst)
        self.assertNotIn("ISTP", sys_inst)

        # Verify parsed dialogue
        self.assertEqual(len(dialogue), 2)
        self.assertEqual(dialogue[0].speaker_id, "officer_1")
        self.assertEqual(dialogue[0].speaker_model, "gemini-3.7-flash")
        self.assertEqual(dialogue[0].speaker_personality, OfficerPersonality.NEUTRAL)

        self.assertEqual(dialogue[1].speaker_id, "officer_2")
        self.assertEqual(dialogue[1].speaker_model, "gemini-3.7-flash")
        self.assertEqual(dialogue[1].speaker_personality, OfficerPersonality.NEUTRAL)
        self.assertEqual(joint_decision, JointDecision.ALLOW)


if __name__ == "__main__":
    unittest.main()



